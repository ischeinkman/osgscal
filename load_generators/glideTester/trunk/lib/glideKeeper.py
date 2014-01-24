############################################################
#
# Description:
#   This module is responsible for getting a specified number
#   of glideins up and runninng
#
# Author:
#   Igor Sfiligoi @UCSD
#
############################################################

import threading
import time, string, re
import sys,os,traceback

# these ones come from the glideinWMS package
# they are located in the lib and frontend subdirectories
import glideinFrontendInterface
import condorMonitor
import condorExe

class GlideKeeperThread(threading.Thread):
    def __init__(self,
                 web_url,descript_fname,descript_signature,
                 security_name,instance_id,
                 classad_id,
                 factory_pools,factory_constraint,
                 collector_node,
                 proxy_fname,
                 session_id=None): # session_id should be a uniq string
        threading.Thread.__init__(self)
        # consts
        self.signature_type = "sha1"
        self.max_request=100

        # strings, describe Web downloadable info
        self.web_url=web_url
        self.descript_fname=descript_fname
        self.descript_signature=descript_signature

        # string, used for identification
        self.security_name=security_name
        self.instance_id=instance_id
        glidekeeper_id="%s_%s"%(security_name,instance_id)
        self.glidekeeper_id=glidekeeper_id

        if session_id==None:
            # should be as unique as possible
            # in the context of the instance_id
            session_id="%s_%s"%(time.time(),os.getpid())
        self.session_id=session_id

        self.instance_constraint='GLIDETESTER_InstanceID=?="%s"'%self.glidekeeper_id
        self.session_constraint='GLIDETESTER_SessionID=?="%s"'%self.session_id

        self.glidekeeper_constraint="(%s)&&(%s)"%(self.instance_constraint,self.session_constraint)
        
        # string, what our ads will be identified at the factories
        self.classad_id=classad_id
        
        # factory pools is a list of pairs, where
        #  [0] is factory node
        #  [1] is factory identity
        self.factory_pools=factory_pools

        # string or None
        self.factory_constraint=factory_constraint

        # string
        self.collector_node = collector_node

        self.proxy_fname=proxy_fname
        self.reload_proxy() # provides proxy_data

        #############################
        
        # keep it simple, start with 0, requests will come later
        self.needed_glideins=0

        self.need_cleanup = False # if never requested more than 0, then no need to do cleanup

        self.running_glideins=0
        self.errors=[]

        ##############################
        self.shutdown=False

    # if you request 0, all the currenty running ones will be killed
    # in all other cases, it is just requesting for more, if appropriate
    def request_glideins(self,needed_glideins):
        self.needed_glideins=needed_glideins

    # use this for monitoring
    def get_running_glideins(self):
        return self.running_glideins

    def soft_kill(self):
        self.shutdown=True
        
    # this is the main of the class
    def run(self):
        self.shutdown=False
        first=True
        while (not self.shutdown) or self.need_cleanup:
            if first:
                first=False
            else:
                # do not sleep the first round
                time.sleep(20)

            self.reload_proxy()
            if (self.needed_glideins>0) and (not self.shutdown): # on shutdown clean up, don't ask for more
                self.go_request_glideins()
                self.need_cleanup = True
            else:
                if self.need_cleanup:
                    self.cleanup_glideins()

    ##############
    # INTERNAL
    def reload_proxy(self):
        if self.proxy_fname==None:
            self.proxy_data=None
            return
        
        proxy_fd=open(self.proxy_fname,'r')
        try:
            self.proxy_data=proxy_fd.read()
        finally:
            proxy_fd.close()
        return

    def cleanup_glideins(self):
        # Deadvertize my add, so the factory knows we are gone
        for factory_pool in self.factory_pools:
            factory_pool_node=factory_pool[0]
            try:
                glideinFrontendInterface.deadvertizeAllWork(factory_pool_node,self.glidekeeper_id)
            except RuntimeError, e:
                self.errors.append((time.time(),"Deadvertizing failed: %s"%e))
            except:
                tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                                sys.exc_info()[2])
                self.errors.append((time.time(),"Deadvertizing failed: %s"%string.join(tb,'')))

        
        # Stop all the glideins I can see
        try:
          pool_status=condorMonitor.CondorStatus()
          pool_status.load(self.glidekeeper_constraint,[('GLIDEIN_COLLECTOR_NAME','s'),('GLIDEIN_MASTER_NAME','s')])
          pool_data=pool_status.fetchStored()
        except:
          self.errors.append((time.time(),"condor_status failed"))

        for k in pool_data.keys():
            el=pool_data[k]
            try:
                condorExe.exe_cmd("../sbin/condor_off","-master -pool %s %s"%(el['GLIDEIN_COLLECTOR_NAME'],el['GLIDEIN_MASTER_NAME']))
            except RuntimeError, e:
                self.errors.append((time.time(),"condor_off failed: %s"%e))
            except:
                tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                                sys.exc_info()[2])
                self.errors.append((time.time(),"condor_off failed: %s"%string.join(tb,'')))

        self.need_cleanup = False
    
    def go_request_glideins(self):
        # query job collector
        try:
          pool_status=condorMonitor.CondorStatus()
          pool_status.load('(IS_MONITOR_VM=!=True)&&(%s)'%self.glidekeeper_constraint,[('State','s')])
          running_glideins=len(pool_status.fetchStored())
          del pool_status
          self.running_glideins=running_glideins
        except:
          self.errors.append((time.time(),"condor_status failed"))
          return

        # query WMS collector
        glidein_dict={}
        for factory_pool in self.factory_pools:
            factory_pool_node=factory_pool[0]
            factory_identity=factory_pool[1]
            try:
                factory_glidein_dict=glideinFrontendInterface.findGlideins(factory_pool_node,factory_identity,self.signature_type,self.factory_constraint,self.proxy_data!=None,get_only_matching=True)
            except RuntimeError, e:
                factory_glidein_dict={} # in case of error, treat as there is nothing there

            for glidename in factory_glidein_dict.keys():
                glidein_el=factory_glidein_dict[glidename]
                if not glidein_el['attrs'].has_key('PubKeyType'): # no pub key at all, skip
                    continue
                elif glidein_el['attrs']['PubKeyType']=='RSA': # only trust RSA for now
                    try:
                        # augment
                        glidein_el['attrs']['PubKeyObj']=glideinFrontendInterface.pubCrypto.PubRSAKey(str(re.sub(r"\\+n", r"\n", glidein_el['attrs']['PubKeyValue'])))
                        # and add
                        glidein_dict[(factory_pool_node,glidename)]=glidein_el
                    except:
                        continue # skip
                else: # invalid key type, skip
                    continue

        nr_entries=len(glidein_dict.keys())

        if running_glideins>=self.needed_glideins:
            additional_glideins=0
        else:
            # ask for 2/3 since it takes a few cycles to stabilize
            additional_glideins=(self.needed_glideins-running_glideins)*2/3+1
            if additional_glideins>self.max_request:
                additional_glideins=self.max_request

        if nr_entries>1: # scale down, or we will get much more than we need
            if nr_entries>5:
                # go to exponential mode at this point, for simplicty
                more_per_entry=(additional_glideins/(nr_entries-1))+1
            else:
                more_per_entry=(additional_glideins*(10-1.5*nr_entries)/10)+1
        else:
            # if we have just 1 or less, ask each the maximum
            more_per_entry=additional_glideins
       
        max_glideins=0
        if self.needed_glideins>0:
          # put an arbitrary large number
          # we just want to get there, fast
          max_glideins=100000
 
        # here we have all the data needed to build a GroupAdvertizeType object
        if self.proxy_data==None:
            proxy_arr=None
        else:
            proxy_arr=[('0',self.proxy_data)]
        descript_obj=glideinFrontendInterface.FrontendDescriptNoGroup(self.glidekeeper_id,self.glidekeeper_id,
                                                                      self.web_url,self.descript_fname,
                                                                      self.signature_type,self.descript_signature,
                                                                      proxy_arr)
        # reuse between loops might be a good idea, but this will work for now
        key_builder=glideinFrontendInterface.Key4AdvertizeBuilder()

        advertizer=glideinFrontendInterface.MultiAdvertizeWork(descript_obj)
        for glideid in glidein_dict.keys():
            factory_pool_node,glidename=glideid
            glidein_el=glidein_dict[glideid]
            key_obj=key_builder.get_key_obj(self.classad_id,
                                            glidein_el['attrs']['PubKeyID'],glidein_el['attrs']['PubKeyObj'])
            glidein_params={'GLIDEIN_Collector':self.collector_node,
                            'GLIDETESTER_InstanceID':self.glidekeeper_id,
                            'GLIDETESTER_SessionID':self.session_id,
                            'GLIDEIN_Max_Idle':14400}
            glidein_monitors={}
            advertizer.add(factory_pool_node,
                           glidename,glidename,
                           more_per_entry,max_glideins,
                           glidein_params,glidein_monitors,
                           key_obj,glidein_params_to_encrypt=None,
                           security_name=self.security_name)

        
        try:
            advertizer.do_advertize()
        except glideinFrontendInterface.MultiExeError, e:
            self.errors.append((time.time(),"Advertizing failed for %i requests: %s"%(len(e.arr),e)))
        except RuntimeError, e:
            self.errors.append((time.time(),"Advertizing failed: %s"%e))
        except:
            tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                        sys.exc_info()[2])
            self.errors.append((time.time(),"Advertizing failed: %s"%string.join(tb,'')))

        

        
