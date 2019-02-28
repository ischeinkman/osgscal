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

STARTUP_DIR=sys.path[0]
sys.path.insert(0, os.path.join(STARTUP_DIR,"../lib"))
sys.path.insert(0, os.path.join(STARTUP_DIR,"../bin"))
from logHelper import ilog
from logHelper import dbgp

class GlideKeeperThread(threading.Thread):
    def __init__(self,
                 web_url,descript_fname,descript_signature,
                 group_name,group_descript_fname,group_descript_signature,
                 security_name,instance_id,
                 classad_id,
                 factory_pools,factory_constraint,
                 collector_node,
                 proxy_fname,
                 session_id=None): # session_id should be a uniq string

        ilog("Initting new GlideKeeperThread.")

        threading.Thread.__init__(self)

        # consts
        self.signature_type = "sha1"
        self.max_request=100

        # strings, describe Web downloadable info
        self.web_url=web_url
        self.descript_fname=descript_fname
        self.descript_signature=descript_signature

        ilog("Thread web info: \n\tweb_url: %s\n\tdescript_fname: %s\n\tdescript_signature: %s"%(web_url, descript_fname, descript_signature))

        self.group_name=group_name
        self.group_descript_fname=group_descript_fname
        self.group_descript_signature=group_descript_signature
        
        ilog("Thread group info: \n\tgroup_name: %s\n\tdescript_fname: %s\n\tdescript_signature: %s"%(group_name, group_descript_fname, group_descript_signature))

        # string, used for identification
        self.security_name=security_name
        self.instance_id=instance_id
        glidekeeper_id="%s_%s"%(security_name,instance_id)
        self.glidekeeper_id=glidekeeper_id
        client_name="%s.%s"%(glidekeeper_id,self.group_name)
        self.client_name=client_name

        ilog('Thread security info: \n\tsecurity_name: %s\n\tinstance_id: %s\n\tglidekeeper_id: %s\n\tclient_name: %s'%(security_name, instance_id, glidekeeper_id, client_name))

        if session_id==None:
            # should be as unique as possible
            # in the context of the instance_id
            session_id="%s_%s"%(time.time(),os.getpid())
        self.session_id=session_id

        ilog('Thread session_id: %s'%session_id)

        self.instance_constraint='GLIDETESTER_InstanceID=?="%s"'%self.glidekeeper_id
        if len(self.session_id) != 0:
            self.session_constraint='GLIDETESTER_SessionID=?="%s"'%self.session_id
            self.glidekeeper_constraint="(%s)&&(%s)"%(self.instance_constraint,self.session_constraint)
        else:
            self.session_constraint = 'TRUE'
            self.glidekeeper_constraint = self.instance_constraint
        
        ilog('Thread glidein constraints: %s'%self.glidekeeper_constraint)
        
        # string, what our ads will be identified at the factories
        self.classad_id=classad_id
        ilog('Thread classad_id: %s'%classad_id)
        
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

        ilog('Backend info:\n\tfactory_pools: %s\n\tfactory_constraint: %s\n\tcollector_node: %s\n\tproxy_fname: %s'%(dbgp(factory_pools), factory_constraint, collector_node, proxy_fname))

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
        ilog('Requesting %d glidens from thread.'%needed_glideins)
        self.needed_glideins=needed_glideins

    # use this for monitoring
    def get_running_glideins(self):
        return self.running_glideins

    def soft_kill(self):
        ilog('Requesting a soft kill from the thread.')
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
        ilog('Reloading proxy from fname: %s'%str(self.proxy_fname))
        if self.proxy_fname==None:
            self.proxy_data=None
            return
        proxy_fd=open(self.proxy_fname,'r')
        try:
            self.proxy_data=proxy_fd.read()
            (self.public_cert, self.private_cert) = self._parse_proxy_certs(self.proxy_data)
        finally:
            proxy_fd.close()
        return
    
    def _parse_proxy_certs(self, data):
        split_data = data.split('\n-')
        certs = [x.split('-\n')[1] for x in split_data if not 'END' in x and 'CERTIFICATE' in x]
        return certs 

    def cleanup_glideins(self):
        ilog('Thread is cleaning up glideins.')
        from glideinwms.frontend import glideinFrontendInterface
        from glideinwms.lib import condorMonitor, condorExe

        # Deadvertize my add, so the factory knows we are gone
        for factory_pool in self.factory_pools:
            factory_pool_node=factory_pool[0]
            ilog('Deadvertising for node %s'%dbgp(factory_pool_node))
            try:
                glideinFrontendInterface.deadvertizeAllWork(factory_pool_node,self.client_name)
            except RuntimeError, e:
                self.errors.append((time.time(),"Deadvertizing failed: %s"%e))
            except:
                tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                                sys.exc_info()[2])
                self.errors.append((time.time(),"Deadvertizing failed: %s"%string.join(tb,'')))

        
        # Stop all the glideins I can see
        ilog('Getting glidein pool status data.')
        try:
          pool_status=condorMonitor.CondorStatus()
          pool_status.load(self.glidekeeper_constraint,[('GLIDEIN_COLLECTOR_NAME','s'),('GLIDEIN_MASTER_NAME','s')])
          pool_data=pool_status.fetchStored()
        except:
          self.errors.append((time.time(),"condor_status failed"))

        for k in pool_data.keys():
            el=pool_data[k]
            ilog('Now killing pool with data: (%s -> %s)'%(dbgp(k), dbgp(el)))
            try:
                condorExe.exe_cmd("../sbin/condor_off","-master -pool %s %s"%(el['GLIDEIN_COLLECTOR_NAME'],el['GLIDEIN_MASTER_NAME']))
            except RuntimeError, e:
                self.errors.append((time.time(),"condor_off failed: %s"%e))
            except:
                tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                                sys.exc_info()[2])
                self.errors.append((time.time(),"condor_off failed: %s"%string.join(tb,'')))

        self.need_cleanup = False
        ilog('Finished cleanup.')
    
    def go_request_glideins(self):
        ilog('Entered go_request_glideins.')
        from glideinwms.frontend import glideinFrontendInterface
        from glideinwms.lib import condorMonitor, condorExe
        from glideinwms.frontend.glideinFrontendPlugins import proxy_plugins, createCredentialList
        # query job collector
        ilog('Checking the condor pool.')
        try:
          pool_status=condorMonitor.CondorStatus()
          pool_status.load('(IS_MONITOR_VM=!=True)&&(%s)'%self.glidekeeper_constraint,[('State','s')])
          running_glideins=len(pool_status.fetchStored())
          del pool_status
          self.running_glideins=running_glideins
          ilog('Found %d glideins in the pool.'%running_glideins)
        except:
          self.errors.append((time.time(),"condor_status failed"))
          return

        # query WMS collector
        ilog('Checking factory glideins.')
        glidein_dict={}
        for factory_pool in self.factory_pools:
            factory_pool_node=factory_pool[0]
            factory_identity=factory_pool[1]
            try:
                if self.proxy_data != None:
                    full_constraint = self.factory_constraint +' && (PubKeyType=?="RSA") && (GlideinAllowx509_Proxy=!=False)'
                else:
                    full_constraint = self.factory_constraint + ' && (GlideinRequirex509_Proxy=!=True)'
                ilog('Running findGlideins with these params: \n\tpool: %s\n\tident: %s\n\tsigtype: %s\n\tconstraints: %s'%(
                    str(factory_pool_node),
                    str(None),
                    str(self.signature_type),
                    str(full_constraint)
                    #str(self.proxy_data!=None),
                    #str(True)
                ))
                factory_glidein_dict=glideinFrontendInterface.findGlideins(
                    factory_pool_node,
                    None, #factory_identity, #TODO: How do we authenticate with the factory? 
                    self.signature_type,
                    full_constraint
                    #self.proxy_data!=None,
                    #get_only_matching=True
                )
            except RuntimeError, e:
                factory_glidein_dict={} # in case of error, treat as there is nothing there
                ilog('Error from findGlideins: %s'%str(e))
            ilog('Found %d possible in factory_pool %s'%(len(factory_glidein_dict.keys()), dbgp(factory_pool)))

            for glidename in factory_glidein_dict.keys():
                ilog('Now testing glidein with name %s'%glidename)
                glidein_el=factory_glidein_dict[glidename]
                ilog('Glidein stats: \n\n %s \n\n'%dbgp(glidein_el))
                if not glidein_el['attrs'].has_key('PubKeyType'): # no pub key at all, skip
                    ilog('%s has no PubKeyType -- skipping.'% glidename)
                    continue
                elif glidein_el['attrs']['PubKeyType']=='RSA': # only trust RSA for now
                    try:
                        # augment
                        glidein_el['attrs']['PubKeyObj']=glideinFrontendInterface.pubCrypto.PubRSAKey(str(re.sub(r"\\+n", r"\n", glidein_el['attrs']['PubKeyValue'])))
                        # and add
                        glidein_dict[(factory_pool_node,glidename)]=glidein_el
                        ilog('Adding %s to glidein_dict'%glidename)
                    except:
                        ilog('Hit error when adding %s to glidein_dict'%glidename)
                        continue # skip
                else: # invalid key type, skip
                    ilog('%s has invalid PubKeyType -- skipping.'% glidename)
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
        more_per_entry = int(more_per_entry) + 1
        max_glideins=0
        if self.needed_glideins>0:
          # put an arbitrary large number
          # we just want to get there, fast
          max_glideins=100000

        ilog('The glidein request stats: \n\trunning_glideins: %d\n\tneeded_glideins: %d\n\tadditional_glideins: %d\n\tnr_entries: %d\n\tmore_per_entry: %d'%(running_glideins, self.needed_glideins, additional_glideins, nr_entries, more_per_entry))
 
        ilog('Building advertiser.')

        # Note that at the moment the ID is hardcoded to '1' and the security class to '0'.
        if self.proxy_fname is None:
            proxy_plugin = None
        else:
            proxy_plugin = proxy_plugins['ProxyFirst'] (None, [CredentialShim('1', self.proxy_fname, '0').to_credential()] )

        #TODO: pass the workdir
        descript_obj=glideinFrontendInterface.FrontendDescript(self.client_name,
                                                               self.glidekeeper_id,self.group_name,
                                                               self.web_url,self.descript_fname,
                                                               self.group_descript_fname,
                                                               self.signature_type,self.descript_signature,
                                                               self.group_descript_signature,
                                                               x509_proxies_plugin= proxy_plugin)
        ilog(dbgp(descript_obj))

        # reuse between loops might be a good idea, but this will work for now
        key_builder=glideinFrontendInterface.Key4AdvertizeBuilder()

        advertizer=glideinFrontendInterface.MultiAdvertizeWork(descript_obj)

        advertizer.renew_and_load_credentials()

        successful_ads = 0
        for glideid in glidein_dict.keys():
            factory_pool_node,glidename=glideid
            glidein_el=glidein_dict[glideid]
            key_obj=key_builder.get_key_obj(self.classad_id,
                                            glidein_el['attrs']['PubKeyID'],glidein_el['attrs']['PubKeyObj'])
            glidein_params={'GLIDEIN_Collector':self.collector_node,
                            'GLIDETESTER_InstanceID':self.glidekeeper_id,
                            'GLIDEIN_Max_Idle':14400}
            if self.session_id is not None and len(self.session_id) > 0:
                            glidein_params['GLIDETESTER_SessionID']=self.session_id
            glidein_monitors={}
            advertizer.add_global(factory_pool=factory_pool_node, request_name=glidename, security_name=self.security_name, key_obj=key_obj)
            advertizer.add(factory_pool=factory_pool_node,
                           request_name=glidename,
                           glidein_name=glidename,
                           min_nr_glideins=more_per_entry,
                           max_run_glideins=max_glideins,
                           glidein_params=glidein_params,
                           glidein_monitors=glidein_monitors,
                           key_obj=key_obj,
                           glidein_params_to_encrypt={},
                           auth_method='grid_proxy', 
                           security_name=self.security_name)
            ilog((
                'Creating ad:\n'
                '\tpool: %s\n'
                '\treq_name: %s\n'
                '\tglide_name: %s\n'
                '\tmin_nr: %s\n'
                '\tmax_run: %s\n'
                '\tparams: %s\n'
                '\tmonitors: %s\n'
                '\tkey_obj: %s\n'
                '\tenc_params: %s\n'
                '\tremove_excess_str: False'
            )%(
                str(factory_pool_node),
                str(glidename),
                str(glidename),
                str(more_per_entry),
                str(max_glideins),
                str(glidein_params),
                str(glidein_monitors),
                str(key_obj),
                str({})
            ))
            ilog('Raw params: \n\n %s\n%s'%(dbgp(advertizer.factory_queue[factory_pool_node][-1][0]), dbgp(advertizer.factory_queue[factory_pool_node][-1][1])))
            successful_ads += 1

        for factory_pool in self.factory_pools:
            factory_pool_node=factory_pool[0]
            factory_identity=factory_pool[1]


        
        try:
            ilog('Trying to advertise for queue:\n%s'%dbgp(advertizer.factory_queue, indent=4))
            advertizer.do_global_advertize()
            advertizer.do_advertize()
            ilog('Successfully advertized %s ads.'%successful_ads)
            ilog('Queue:\n%s'%dbgp(advertizer.factory_queue, indent=4))
        except glideinFrontendInterface.MultiExeError, e:
            self.errors.append((time.time(),"Advertizing failed for %i requests: %s"%(len(e.arr),e)))
        except RuntimeError, e:
            self.errors.append((time.time(),"Advertizing failed: %s"%e))
        except:
            tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                        sys.exc_info()[2])
            self.errors.append((time.time(),"Advertizing failed: %s"%string.join(tb,'')))

        
        

# The GlideinWMS frontend library relies on large nested hashmap called the ElementeMergeDescript to 
# pass around configuration parameters, such as the proxy information. This class emulates it 
# enough just to be able to pass the credentials to the library. 
class CredentialShim:
    def __init__(self, proxy_id, proxy_fname, security_class, update_frequency = 65535):
        self.proxy_id = proxy_id
        self.proxy_fname = proxy_fname
        self.merged_data = {}
        self.merged_data['ProxySecurityClasses'] = {proxy_fname : security_class}
        self.merged_data['ProxyTrustDomains'] = {proxy_fname : 'Any'} 
        self.merged_data['ProxyTypes'] = {proxy_fname : 'grid_proxy'} 
        self.merged_data['ProxyKeyFiles'] = {}
        self.merged_data['ProxyPilotFiles'] = {}
        self.merged_data['ProxyVMIds'] = {}
        self.merged_data['ProxyVMTypes'] = {}
        self.merged_data['ProxyCreationScripts'] = {}
        self.merged_data['ProxyUpdateFrequency'] = {proxy_fname : update_frequency}
        self.merged_data['ProxyVMIdFname'] = {}
        self.merged_data['ProxyVMTypeFname'] = {}
        self.merged_data['ProxyRemoteUsernames'] = {}
        self.merged_data['ProxyProjectIds'] = {}
    
    def to_credential(self):
        from glideinwms.frontend import glideinFrontendInterface
        return glideinFrontendInterface.Credential(self.proxy_id, self.proxy_fname, self)
