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
import time, string
import sys,traceback

# these ones come from the glideinWMS package
# they are located in the lib and frontend subdirectories
import glideinFrontendInterface
import condorMonitor

class GlideKeeperThread(threading.Thread):
    def __init__(self,
                 web_url,descript_fname,descript_signature,
                 glideinkeeper_id,classad_id,
                 factory_pools,factory_constraint,
                 proxy_fname):
        threading.Thread.__init__(self)
        # consts
        self.signature_type = "sha1"
        self.max_request=100

        # strings, describe Web downloadable info
        self.web_url=web_url
        self.descript_fname=descript_fname
        self.descript_signature=descript_signature

        # string, used for identification
        self.glidekeeper_id=glidekeeper_id

        # string, what our ads will be identified at the factories
        self.classad_id=classad_id
        
        # factory pools is a list of pairs, where
        #  [0] is factory node
        #  [1] is factory identity
        self.factory_pools=factory_pools

        # string or None
        self.factory_constraint=factory_constraint

        self.proxy_fname=proxy_fname
        self.reload_proxy() # provides proxy_data

        #############################
        
        # keep it simple, start with 0, requests will come later
        self.needed_glideins=0

        self.need_cleanup = False # if never requested more than 0, then no need to do cleanup

        self.running_glideins=0
        self.last_error=None

        ##############################
        self.shutdown=False

    # if you request 0, all the currenty running ones will be killed
    # in all other cases, it is just requesting for more, if appropriate
    def request_glideins(self,needed_glideins):
        self.needed_glidein=needed_glideins

    # use this for monitoring
    def get_running_glideins(self):
        return self.running_glideins

    def soft_kill(self):
        self.shutdown=True
        
    # this is the main of the class
    def run(self):
        self.shutdown=False
        self.last_error=None
        first=True
        while (not self.shutdown) or self.need_cleanup:
            if first:
                first=False
            else:
                # do not sleep the first round
                time.sleep(120)

            self.reload_proxy()
            if (self.needed_glideins>0) and (not self.shutdown): # on shutdown clean up, don't ask for more
                self.request_glideins()
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
        #to be implemented
        # for now, just try to deadvertize and claim you are done
        # in the future, we need to do better than this (i.e. actually kill the gldieins)
        self.last_error=None
        for factory_pool in self.factory_pools:
            factory_pool_node=factory_pool[0]
            try:
                glideinFrontendInterface.deadvertizeAllWork(factory_pool_node,self.glidekeeper_id)
            except RuntimeError, e:
                self.last_error="Deadvertizing failed: %s"%e
            except:
                tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                                sys.exc_info()[2])
                self.last_error="Deadvertizing failed: %s"%string.join(tb,'')
        self.need_cleanup = False
    
    def request_glideins(self):
        # query job collector
        pool_status=condorMonitor.CondorStatus()
        pool_status.load(None,[])
        running_glideins=len(pool_status.fetchStored())
        del pool_status
        self.running_glideins=running_glideins

        # query WMS collector
        glidein_dict={}
        for factory_pool in self.factory_pools:
            factory_pool_node=factory_pool[0]
            factory_identity=factory_pool[1]
            try:
                factory_glidein_dict=glideinFrontendInterface.findGlideins(factory_pool_node,self.signature_type,self.factory_constraint,self.proxy_data!=None,get_only_matching=True)
            except RuntimeError, e:
                factory_glidein_dict={} # in case of error, treat as there is nothing there

            for glidename in factory_glidein_dict.keys():
                glidein_dict[(factory_pool_node,glidename)]=factory_glidein_dict[glidename]
        nr_entries=len(glidein_dict.keys())

        if running_glideins>=self.needed_glideins:
            additional_glideins=0
        else:
            # ask for a third since it takes a few cycles to stabilize
            additional_glideins=(self.needed_glideins-running_glideins)/3+1
            if additional_glideins>self.max_request:
                additional_glideins=self.max_request

        if nr_entries>2: # overrequest, as some entries may not give us anything
            more_per_entry=(additional_glideins/(nr_entries-1))+1
        else:
            # if we have just 2 or less, ask each the maximum
            more_per_entry=additional_glideins
        
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
            key_obj=key_builder.get_key_obj(self.classad_identity,
                                            glidein_el['attrs']['PubKeyID'],glidein_el['attrs']['PubKeyObj'])
            advertizer.add(factory_pool_node,
                           glidename,glidename,
                           more_per_entry,self.needed_glideins*12/10,
                           glidein_params,glidein_monitors,
                           key_obj,glidein_params_to_encrypt=None)

        
        try:
            advertizer.do_advertize()
            self.last_error=None
        except glideinFrontendInterface.MultiExeError, e:
            self.last_error="Advertizing failed for %i requests: %s"%(len(e.arr),e)
        except RuntimeError, e:
            self.last_error="Advertizing failed: %s"%e
        except:
            tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                        sys.exc_info()[2])
            self.last_error="Advertizing failed: %s"%string.join(tb,'')

        

        
