#!/bin/env python
########################################
#
# Description:
#  This program creates a glidein pool for
#  use as a large scale parallel test framework
#
# Author:
#  Igor Sfiligoi @ UCSD
#
########################################

import string
import random
import shutil
import sys,os,os.path
import traceback,signal
import copy
import re
from time import strftime,sleep,ctime

startTime=strftime("%Y%m%d_%H%M%S")

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

from logHelper import ilog
from logHelper import dbgp
from logHelper import setup_loggers
from configutils import KeyValueConfig, parse_argv, parse_kv_file, get_config_file_list
############################
# Configuration class
class ArgsParser:
    def __init__(self,argv):

        # glideTester.cfg values
        self.runId=None
        self.glideinWMSDir = None
        self.configDir = None
        self.proxyFile = None
        self.pilotFile = None
        self.delegateProxy = None
        self.collectorNode = None
        self.gfactoryNode = None
        self.gfactoryConstraint = None
        self.gfactoryClassadID = None
        self.myClassadID = None
        self.mySecurityName = None

        # parameters.cfg values
        self.executable = None
        self.inputFile = None
        self.outputFile = None
        self.environment = None
        self.getenv = None
        self.arguments = None
        self.x509userproxy = None
        self.concurrencyLevel = None
        self.runs = 1
        self.gfactoryAdditionalConstraint=None
        self.additionalClassAds = []

        # parse arguments
        valid_keys = ['-config', '-cfg', '--config', '-params', '-runId']
        arg_map = parse_argv(argv[1:], valid_kv_settings=valid_keys)
        passed_config_path = arg_map.get('-cfg') or arg_map.get('--config') or arg_map.get('-config')
        passed_params_path = arg_map.get('-params')
        self.cfg_paths = get_config_file_list(file_name='glideTester.cfg', arg_path=passed_config_path)
        self.params_path = get_config_file_list(file_name='parameters.cfg', arg_path=passed_params_path)
        self.runId = arg_map.get('-runId')

        # check and fix the attributes
        if self.runId==None:
            # not defined, create one specific for the account
            # should not be too random, or you polute the factory namespace
            self.runId="u%i"%os.getuid()
        
        # load external values
        self.load_cfg()
        self.verify_cfg()

        # set search path
        if self.glideinWMSDir is not None:
            sys.path.insert(0, self.glideinWMSDir)
            sys.path.insert(0,os.path.join(self.glideinWMSDir,".."))

        self.load_config_dir()

        self.load_params()
        self.setup_logger()

        ilog("Made glideTester: \n\n%s\n"%dbgp(self, 4))

    def setup_logger(self):
        setup_loggers(self.cfg_paths)
        import logging
        from glideinwms.lib import logSupport
        logSupport.log = logging.getLogger("frontend")
        logSupport.log.info("Logging initialized")

    def has_cfg(self):
        if self.glideinWMSDir is None:
            return False
        elif self.configDir is None:
            return False
        elif self.proxyFile is None:
            return False
        elif self.pilotFile is None:
            return False
        elif self.delegateProxy is None:
            return False
        elif self.collectorNode is None:
            return False
        elif self.gfactoryNode is None:
            return False
        elif self.gfactoryConstraint is None:
            return False
        elif self.gfactoryClassadID is None:
            return False
        elif self.myClassadID is None:
            return False
        elif self.mySecurityName is None:
            return False
        else:
            return True
    
    def load_cfg(self):
        file_paths = self.cfg_paths
        for fl in file_paths:
            if self.has_cfg():
                return 
            config = parse_kv_file(fl)

            if self.glideinWMSDir is None:
                key = 'glideinWMSDir'
                self.glideinWMSDir = _verify_path(key, config.settings.get(key))
            if self.configDir is None:
                key = 'configDir'
                self.configDir = _verify_path(key, config.settings.get(key))
            if self.proxyFile is None:
                key = 'proxyFile'
                self.proxyFile = _verify_path(key, config.settings.get(key))
            if self.pilotFile is None:
                key = 'pilotFile'
                self.pilotFile = _verify_path(key, config.settings.get(key))
            if self.delegateProxy is None and config.settings.get('delegateProxy') is not None:
                self.delegateProxy = eval(config.settings.get('delegateProxy'))
            if self.collectorNode is None:
                self.collectorNode = config.settings.get('collectorNode')
            if self.gfactoryNode is None:
                self.gfactoryNode = config.settings.get('gfactoryNode')
            if self.gfactoryConstraint is None:
                self.gfactoryConstraint = config.settings.get('gfactoryConstraint')
            if self.gfactoryClassadID is None:
                self.gfactoryClassadID = config.settings.get('gfactoryClassadID')
            if self.myClassadID is None:
                self.myClassadID = config.settings.get('myClassadID')
            if self.mySecurityName is None:
                self.mySecurityName = config.settings.get('mySecurityName')

        # If we found a proxy and we don't ahve a specific policy to not delegate,
        # we delegate to the proxy.
        if self.delegateProxy is None:
            self.delegateProxy = self.proxyFile is not None or self.pilotFile is not None
    def verify_cfg(self):
        # make sure all the needed values have been read,
        # and assign defaults, if needed
        if self.glideinWMSDir==None:
            raise RuntimeError, "glideinWMSDir was not defined!"
        elif self.configDir==None:
            raise RuntimeError, "configDir was not defined!"
        elif self.proxyFile==None:
            raise RuntimeError, "proxyFile was not defined!"
        elif self.collectorNode==None:
            raise RuntimeError, "collectorNode was not defined!"
        elif self.gfactoryClassadID==None:
            raise RuntimeError, "gfactoryClassadID was not defined!"
        elif self.myClassadID==None:
            raise RuntimeError, "myClassadID was not defined!"
        # it would be wise to verify the signature here, but will not do just now
        # to be implemented
        elif self.mySecurityName==None:
            raise RuntimeError, "mySecurityName was not defined!"
        else:
            return True

    def load_config_dir(self):
        import cgkWDictFile
        self.frontend_dicts=cgkWDictFile.glideKeeperDicts(self.configDir)
        self.frontend_dicts.load()

        self.groupName=self.frontend_dicts.group_name
        self.webURL=self.frontend_dicts.main_dicts.dicts['frontend_descript']['WebURL']
        self.descriptSignature,self.descriptFile=self.frontend_dicts.main_dicts.dicts['summary_signature']['main']
        self.groupDescriptSignature,self.groupDescriptFile=self.frontend_dicts.main_dicts.dicts['summary_signature']['group_%s'%self.groupName]


    def has_params(self):
        self.executable is not None and self.concurrencyLevel is not None

    def verify_params(self):
        if self.executable is None:
            raise RuntimeError, "executable was not defined!"
        elif self.concurrencyLevel is None:
            raise RuntimeError, "concurrency was not defined!"
        else:
            return True

    def load_additional_classads(self, config):
        for (key, val) in config.settings.iteritems():
            if key.startswith('+'):
                self.additionalClassAds.append((key, val))

    def load_params(self):
        file_paths = self.params_path

        for fl in file_paths:
            config = parse_kv_file(fl)
            self.load_additional_classads(config)
            if self.has_params():
                continue

            if self.executable is None:
                exec_path = config.settings.get('executable')
                if exec_path is None:
                    pass
                elif not os.path.exists(exec_path):
                    raise RuntimeError, "%s '%s' is not a valid executable"%('executable',exec_path)
                else:
                    self.executable = exec_path
            if self.inputFile is None:
                input_files = config.settings.get('transfer_input_files')
                if input_files is not None:
                    arr = input_files.split(',')
                    newarr = []
                    for f in arr:
                        if not os.path.exists(f):
                            raise RuntimeError, "'%s' is not a valid file"%f
                        newarr.append(os.path.abspath(f))
                    self.inputFile = string.join(newarr,',')
            if self.outputFile is None:
                output_files = config.settings.get('transfer_output_files')
                if output_files is not None:
                    self.outputFile = output_files
            if self.environment is None:
                self.environment = config.settings.get('environment')
            if self.getenv is None:
                self.getenv = config.settings.get('getenv')
            if self.arguments is None:
                self.arguments = config.settings.get('arguments')
            if self.x509userproxy is None:
                val = config.settings.get('x509userproxy')
                if (val is not None) and (val!='') and (not os.path.exists(val)):
                    raise RuntimeError, "'%s' is not a valid proxy"%val
                self.x509userproxy = val
            if self.concurrencyLevel is None:
                concurrency = config.settings.get('concurrency')
                self.concurrencyLevel = concurrency.split()
            if self.runs is None: 
                runs = config.settings.get('runs')
                self.runs = int(runs)
            if self.gfactoryAdditionalConstraint is None:
                self.gfactoryAdditionalConstraint = config.settings.get('gfactoryAdditionalConstraint')
            

def _verify_path(key, val):
    if val is None:
        return None 
    elif not os.path.exists(val):
        raise RuntimeError, "%s '%s' is not a valid dir"%(key,val)
    else: 
        return val

def process_concurrency(config,gktid,main_log,workingDir,concurrencyLevel,l,k):

    ilog('Processing concurrency level %s => %s run number %s.\n\tgktid: %s\n\tworkingDir: %s\n\t log: %s'%(str(k), str(concurrencyLevel[k]), str(l), str(gktid), str(workingDir), str(main_log)))
    from glideinwms.lib import condorMonitor
    from glideinwms.lib import condorManager

    universe = 'vanilla'
    transfer_executable = "True"
    when_to_transfer_output = "ON_EXIT"
    # disable the check for architecture, we are running a script
    # only match to our own glideins
    requirements = '(Arch =!= "fake")&&(%s)'%gktid.glidekeeper_constraint
    owner = 'Undefined'
    notification = 'Never'

    # request the glideins
    # we want 10% more glideins than the concurrency level
    requestedGlideins = int(concurrencyLevel[k])
    totalGlideins = int(requestedGlideins + .1 * requestedGlideins)
    gktid.request_glideins(totalGlideins)
    main_log.write("%s %i Glideins requested\n"%(ctime(),totalGlideins))

    # now we create the directories for each job and a submit file
    loop = 0
    dir1 = workingDir + '/concurrency_' + concurrencyLevel[k] + '_run_' + str(l) + '/'
    os.makedirs(dir1)
    logfile = workingDir + '/con_' + concurrencyLevel[k] + '_run_' + str(l) + '.log'
    outputfile = 'concurrency_' + concurrencyLevel[k] + '.out'
    errorfile = 'concurrency_' + concurrencyLevel[k] + '.err'
    filename =  workingDir + "/" + config.executable.replace('/', '__') + '_concurrency_' + concurrencyLevel[k] + '_run_' + str(l) + '_submit.condor'
    filecontent = ''
    condorSubmitFile=open(filename, "w")
    filecontent += ('universe = ' + universe + '\n' +
                           'executable = ' + config.executable + '\n' +
                           'transfer_executable = ' + transfer_executable + '\n' +
                           'when_to_transfer_output = ' + when_to_transfer_output + '\n' +
                           'Requirements = ' + requirements + '\n' +
         #                  '+Owner = ' + owner + '\n' +
                           'log = ' + logfile + '\n' +
                           'output = ' +  outputfile + '\n' +
                           'error = ' + errorfile + '\n' +
                           'notification = ' + notification + '\n' +
                           'periodic_remove = ((JobStatus!=2)&&(JobRunCount>0))||(JobRunCount>1)\n' +
                           '+GK_InstanceId = "' + gktid.glidekeeper_id + '"\n' +
                           '+GK_SessionId = "' + gktid.session_id + '"\n' +
                           '+IsSleep = 1\n')
    if config.inputFile != None:
        filecontent += ('transfer_input_files = ' + config.inputFile + '\n')
    if config.outputFile != None:
        filecontent += ('transfer_output_files = ' + config.outputFile + '\n')
    if config.environment != None:
        filecontent += ('environment = ' + config.environment + '\n')
    if config.getenv != None:
        filecontent += ('getenv = ' + config.getenv + '\n')
    if config.arguments != None:
        filecontent += ('arguments = ' + config.arguments + '\n')
    if config.x509userproxy!=None:
        filecontent += ('x509userproxy = ' + config.x509userproxy + '\n\n')
    else:
        filecontent += ('x509userproxy = ' + config.proxyFile + '\n\n')
    #Added support for additional classAdds:
    for classAdd in config.additionalClassAds:
        name = classAdd[0]
        value = classAdd[1]
        filecontent += (name + ' = ' + value +'\n')
    for j in range(0, int(concurrencyLevel[k]), 1):
        filecontent += ('Initialdir = ' + dir1 + 'job' + str(loop) + '\n')
        filecontent += ('Queue\n\n')
        loop = loop + 1
    for i in range(0, int(concurrencyLevel[k]), 1):
        dir2 = dir1 + 'job' + str(i) + '/'
        os.makedirs(dir2)
    ilog('Creating condor file %s:\n%s'%(filename, filecontent ))
    condorSubmitFile.write(filecontent)
    condorSubmitFile.close()

    # Need to figure out when we have all the glideins
    # Ask the glidekeeper object
    ilog('Now waiting until the thread retrieves enough glideins.')
    finished = "false"
    while finished != "true":
        errors=[]
        while 1:
            # since gktid runs in a different thread, pop is the only atomic operation I have
            try:
                errors.append(gktid.errors.pop())
            except IndexError:
                break

        errors.reverse()
        if not len(errors) == 0:
            ilog('Have errors!')
        for err  in errors:
            main_log.write("%s Error: %s\n"%(ctime(err[0]),err[1]))
            ilog('Found an error: %s'%err[1])
        if not gktid.isAlive():
            raise RuntimeError, "The glidekeeper thread unexpectedly died!"

        numberGlideins = gktid.get_running_glideins()
        ilog('Currently have %s running glideins out of %s.'%(numberGlideins, requestedGlideins))
        main_log.write("%s %s %s %s %s\n"%(ctime(), 'we have', numberGlideins, 'glideins, need', requestedGlideins))
        main_log.flush()
        sleep(5)
        if numberGlideins >= requestedGlideins:
            finished = "true"

    # Now we begin submission and monitoring
    ilog('Got the glideins. Now submitting %s.'%filename)
    submission = condorManager.condorSubmitOne(filename)
    main_log.write("%s %s\n"%(ctime(), "file submitted"))
    running = "true"
    while running != "false":
        ilog('Running condorQ to get the running jobs.')
        check1 = condorMonitor.CondorQ()
        try:
            # i actually want to see all jos, not only running ones
            check1.load('(JobStatus<3)&&(GK_InstanceId=?="%s")&&(GK_SessionId=?="%s")'%(gktid.glidekeeper_id,gktid.session_id), [("JobStatus","s")])
            data=check1.fetchStored()
            ilog('Success!')
        except RuntimeError,e:
            main_log.write("%s %s\n"%(ctime(), "condor_q failed (%s)... ignoring for now"%e))

            main_log.flush()
            sleep(2)
            continue # retry the while loop
        except:
            main_log.write("%s %s\n"%(ctime(), "condor_q failed (reason unknown)... ignoring for now"))

            main_log.flush()
            sleep(2)
            continue # retry the while loop
        ilog('Found %s jobs running.'%len(data.keys()))
        main_log.write("%s %s %s\n"%(ctime(), len(data.keys()), 'jobs running'))
        main_log.flush()
        if len(data.keys()) == 0:
            running = "false"
            main_log.write("%s %s\n"%(ctime(), "no more running jobs"))
        else:
            sleep(10)

def parse_result(config,workingDir,concurrencyLevel):
    # Create a loop to parse each log file into a summaries directory
    summDir = workingDir + '/summaries/'
    os.makedirs(summDir)
    for l in range(0, config.runs, 1):
        for k in range(0, len(concurrencyLevel), 1):

            # Initialize empty arrays for data
            results=[]
            hours=[]
            minutes=[]
            seconds=[]
            jobStartInfo=[]
            jobExecuteInfo=[]
            jobFinishInfo=[]
            jobStatus=[]

            # Parse each log file
            logFile = workingDir + '/con_' + concurrencyLevel[k] + '_run_' + str(l) + '.log'
            if not os.path.exists(logFile):
                # If the log file doesn't exist, then the run failed. 
                # Report that in the summaries. 
                filePath = summDir + 'con_' + concurrencyLevel[k] + '_run_' + str(l) + '.txt'
                file=open(filePath, 'w')
                header = "# Test Results for " + config.executable + " run at concurrency Level " + concurrencyLevel[k] + '\n\nJob\tExec\tFinish\tReturn\nNumber\tTime\tTime\tValue\n'
                file.write(header)
                file.write('#ERROR: Could not read log file. Did this level actually run?')
                file.close()

                filepath = summDir + 'results.txt'
                file=open(filepath, 'a')
                times = "Concurrency_Level = " + concurrencyLevel[k] + "\t  Execute_Time_(Ave/Min/Max) = " + 'ERROR: Failed' + '/' + 'ERROR: Failed' + '/' + 'ERROR: Failed' + "\t  Finish_Time_(Ave/Min/Max) = " + 'ERROR: Failed' + "/" + 'ERROR: Failed' + "/" + 'ERROR: Failed' + '\n'
                file.write(times)
                file.close()
                continue
            lf = open(logFile, 'r')
            try:
                lines1 = lf.readlines()
            finally:
                lf.close()
            jobsSubmitted = 0
            for line in lines1:
                line = line.strip()
                if line[0:1] not in ('0','1','2','3','4','5','6','7','8','9','('):
                    continue # ignore unwanted text lines
                arr1=line.split(' ',7)
                if len(arr1) < 5:
                    ilog('ERROR: Line too small for parsing: %s'%(str(arr1)))
                if arr1[5] == "Bytes" or arr1[4] =="Image":
                    continue
                if arr1[5] == "submitted":
                    jobNum = arr1[1].strip('()')
                    jobStartInfo.append(jobNum)
                    jobStartInfo.append(arr1[3])
                    jobsSubmitted=jobsSubmitted+1
                if arr1[5] == "executing":
                    jobNum = arr1[1].strip('()')
                    jobExecuteInfo.append(jobNum)
                    jobExecuteInfo.append(arr1[3])
                if arr1[5] == "terminated.":
                    jobNum = arr1[1].strip('()')
                    jobFinishInfo.append(jobNum)
                    jobFinishInfo.append(arr1[3])
                if arr1[4] == "value":
                    status=arr1[5].split(')',1)
                    jobFinishInfo.append(status[0])

            # Set some variables
            minExeTime=1e20
            maxExeTime=0
            minFinTime=1e20
            maxFinTime=0
            iter=0
            for i in range(0, len(jobStartInfo), 2):
                if jobStartInfo[i] in jobExecuteInfo:
                    index = jobExecuteInfo.index(jobStartInfo[i])
                    timeJobStart = jobStartInfo[i + 1]
                    timeJobExecute = jobExecuteInfo[index + 1]
                    timeStart = timeJobStart.split(':', 2)
                    timeExecute = timeJobExecute.split(':', 2)
                    diffHours = (int(timeExecute[0]) - int(timeStart[0])) * 3600
                    diffMinutes = (int(timeExecute[1]) - int(timeStart[1])) * 60
                    diffSeconds = int(timeExecute[2]) - int(timeStart[2])
                    executeTime = diffHours + diffMinutes + diffSeconds
                    index2 = jobFinishInfo.index(jobStartInfo[i])
                    timeJobFinish = jobFinishInfo[index2 + 1]
                    stat = jobFinishInfo[index2 +2]
                    timeFinish = timeJobFinish.split(':', 2)
                    diffHours2 = (int(timeFinish[0]) - int(timeExecute[0])) * 3600
                    diffMinutes2 = (int(timeFinish[1]) - int(timeExecute[1])) * 60
                    diffSeconds2 = int(timeFinish[2]) - int(timeExecute[2])
                    finishTime = diffHours2 + diffMinutes2 + diffSeconds2
                    resultData = [iter, executeTime, finishTime, stat]
                    results.append(resultData)
                    iter = iter + 1
                    if executeTime > maxExeTime:
                        maxExeTime = executeTime
                    if executeTime < minExeTime:
                        minExeTime = executeTime
                    if finishTime > maxFinTime:
                        maxFinTime = finishTime
                    if finishTime < minFinTime:
                        minFinTime = finishTime

            # Create summary directory structure
            filePath = summDir + 'con_' + concurrencyLevel[k] + '_run_' + str(l) + '.txt'
            file=open(filePath, 'w')
            header = "# Test Results for " + config.executable + " run at concurrency Level " + concurrencyLevel[k] + '\n\nJob\tExec\tFinish\tReturn\nNumber\tTime\tTime\tValue\n'
            file.write(header)
            exeTime=0
            finTime=0
            for i in range(0, int(concurrencyLevel[k])):
                exeTime = exeTime + results[i][1]
                finTime = finTime + results[i][2]
                writeData = str(results[i][0]) + '\t' + str(results[i][1]) + '\t' + str(results[i][2]) + '\t' + results[i][3] + '\n'
                file.write(writeData)

            aveExeTime = exeTime/int(concurrencyLevel[k])
            aveFinTime = finTime/int(concurrencyLevel[k])
            file.close()

            filepath = summDir + 'results.txt'
            file=open(filepath, 'a')
            times = "Concurrency_Level = " + concurrencyLevel[k] + "\t  Execute_Time_(Ave/Min/Max) = " + str(aveExeTime) + '/' + str(minExeTime) + '/' + str(maxExeTime) + "\t  Finish_Time_(Ave/Min/Max) = " + str(aveFinTime) + "/" + str(minFinTime) + "/" + str(maxFinTime) + '\n'
            file.write(times)
            file.close()

def run(config):
    os.environ['_CONDOR_SEC_DEFAULT_AUTHENTICATION_METHODS']='FS,GSI'
    os.environ['X509_USER_PROXY']=config.proxyFile
    import glideKeeper
    from glideinwms.lib import condorMonitor
    from glideinwms.lib import condorManager

    delegated_proxy=None
    if config.delegateProxy:
        if config.pilotFile is None:
            # use the service proxy as a backup solution
            delegated_proxy=config.proxyFile
        else:
            # use the pilto proxy, if available
            delegated_proxy=config.pilotFile
    
    if config.gfactoryAdditionalConstraint==None:
        gfactoryConstraint=config.gfactoryConstraint
    else:
        gfactoryConstraint="(%s)&&(%s)"%(config.gfactoryConstraint,config.gfactoryAdditionalConstraint)
    
    gktid=glideKeeper.GlideKeeperThread(config.webURL,config.descriptFile,config.descriptSignature,
                                        config.groupName,config.groupDescriptFile,config.groupDescriptSignature,
                                        config.mySecurityName,config.runId,
                                        config.myClassadID,
                                        [(config.gfactoryNode,config.gfactoryClassadID)],gfactoryConstraint,
                                        config.collectorNode,
                                        delegated_proxy)
    gktid.start()
    startupDir = os.getcwd()
    workingDir=startupDir + '/run_' + startTime
    
    os.makedirs(workingDir)
    main_log_fname=workingDir + '/glideTester.log'
    main_log=open(main_log_fname,'w')

    try:
        main_log.write("Starting at: %s\n\n"%ctime())

        main_log.write("Factory:       %s\n"%config.gfactoryNode)
        main_log.write("Constraint:    %s\n"%gfactoryConstraint)
        main_log.write("Service Proxy: %s\n"%config.proxyFile)
        main_log.write("Pilot Proxy:   %s\n"%delegated_proxy)
        main_log.write("InstanceID:    %s\n"%gktid.glidekeeper_id)
        main_log.write("SessionID:     %s\n\n"%gktid.session_id)

        concurrencyLevel=config.concurrencyLevel

        try:
            # Create a testing loop for each run
            for l in range(0, config.runs, 1):
                main_log.write("Iteration %i\n"%l)

                # Create a testing loop for each concurrency
                for k in range(0, len(concurrencyLevel), 1):
                    main_log.write("Concurrency %i\n"%int(concurrencyLevel[k]))
                    process_concurrency(config,gktid,main_log,workingDir,concurrencyLevel,l,k)
            main_log.write("%s %s\n"%(ctime(), "Done"))
        except:
            tb = traceback.format_exception(sys.exc_info()[0],sys.exc_info()[1],
                                            sys.exc_info()[2])
            main_log.write("%s %s\n"%(ctime(), "Exception: %s"%string.join(tb,'')))
            

        # Now we parse the log files
        parse_result(config,workingDir,concurrencyLevel)
    finally:
        main_log.write("%s %s\n"%(ctime(), "cleaning, then getting out"))
        main_log.flush()
        gktid.soft_kill()
        gktid.join()
        # print out any last minute errors
        for err  in gktid.errors:
            main_log.write("%s Error: %s\n"%(ctime(err[0]),err[1]))
        main_log.write("Terminated at: %s\n"%ctime())
    
    return



###########################################################
# Functions for proper startup
def main(argv):
    config=ArgsParser(argv)
    run(config)

def termsignal(signr,frame):
    raise KeyboardInterrupt, "Received signal %s"%signr

if __name__ == '__main__':
    signal.signal(signal.SIGTERM,termsignal)
    signal.signal(signal.SIGQUIT,termsignal)
    main(sys.argv)
