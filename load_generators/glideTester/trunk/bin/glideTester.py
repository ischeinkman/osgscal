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

import random
import shutil
import sys,os,os.path
import copy
from time import strftime,sleep,ctime

startTime=strftime("%Y-%m-%d_%H:%M:%S")

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

############################
# Configuration class
class ArgsParser:
    def __init__(self,argv):
        # define defaults
        self.config=os.path.join(STARTUP_DIR,"../etc/glideTester.cfg")
        self.params=os.path.join(STARTUP_DIR,"../etc/parameters.cfg")
        self.runId=None

        # parse arguments
        idx=1
        while idx<len(argv):
            el=argv[idx]
            if el=='-config':
                idx+=1
                el=argv[idx]
                if not os.path.exists(el):
                    raise RuntimeError,"Config file '%s' not found!"%el
                self.config=el
            elif el=='-params':
                idx+=1
                el=argv[idx]
                if not os.path.exists(el):
                    raise RuntimeError,"Params file '%s' not found!"%el
                self.params=el
            elif el=='-runId':
                idx+=1
                el=argv[idx]
                self.runId=el
            else:
                raise RuntimeError, "Unknown argument '%s' at position %i"%(el, idx)
            idx+=1

        # check and fix the attributes
        if self.runId==None:
            # not defined, create one specific for the account
            # should not be too random, or you polute the factory namespace
            self.runId="glideTester_%s_%i"%(os.uname()[1],os.getuid())
        
        # load external values
        self.load_config()

        # set search path
        sys.path.append(os.path.join(self.glideinWMSDir,"lib"))
        sys.path.append(os.path.join(self.glideinWMSDir,"creation/lib"))
        sys.path.append(os.path.join(self.glideinWMSDir,"frontend"))

        self.load_config_dir()
        

    def load_config(self):
        # first load file, so we check it is readable
        fd=open(self.config,'r')
        try:
            lines=fd.readlines()
        finally:
            fd.close()

        # reset the values
        self.glideinWMSDir=None
        self.configDir=None
        self.proxyFile=None
        self.collectorNode=None
        self.gfactoryNode=None
        self.gfactoryConstraint=None
        self.gfactoryClassadID=None
        self.myClassadID=None

        # read the values
        for line in lines:
            line=line.strip()
            if line[0:1] in ('#',''):
                continue # ignore comments and empty lines
            arr=line.split('=',1)
            if len(arr)!=2:
                raise RuntimeError,'Invalid config line, missing =: %s'%line
            key=arr[0].strip()
            val=arr[1].strip()
            if key=='glideinWMSDir':
                if not os.path.exists(val):
                    raise RuntimeError, "%s '%s' is not a valid dir"%(key,val)
                self.glideinWMSDir=val
            elif key=='configDir':
                if not os.path.exists(val):
                    raise RuntimeError, "%s '%s' is not a valid dir"%(key,val)
                self.configDir=val
            elif key=='proxyFile':
                if not os.path.exists(val):
                    raise RuntimeError, "%s '%s' is not a valid dir"%(key,val)
                self.proxyFile=val
            elif key=='collectorNode':
                self.collectorNode=val
            elif key=='gfactoryNode':
                self.gfactoryNode=val
            elif key=='gfactoryConstraint':
                self.gfactoryConstraint=val
            elif key=='gfactoryClassadID':
                self.gfactoryClassadID=val
            elif key=='myClassadID':
                self.myClassadID=val
            else:
                raise RuntimeError, "Invalid config key '%s':%s"%(key,line)

        # make sure all the needed values have been read,
        # and assign defaults, if needed
        if self.glideinWMSDir==None:
            raise RuntimeError, "glideinWMSDir was not defined!"
        if self.configDir==None:
            raise RuntimeError, "configDir was not defined!"
        if self.proxyFile==None:
            raise RuntimeError, "proxyFile was not defined!"
        if self.collectorNode==None:
            raise RuntimeError, "collectorNode was not defined!"
        if self.gfactoryClassadID==None:
            raise RuntimeError, "gfactoryClassadID was not defined!"
        if self.myClassadID==None:
            raise RuntimeError, "myClassadID was not defined!"
        # it would be wise to verify the signature here, but will not do just now
        # to be implemented
        
    def load_config_dir(self):
        import cgkWDictFile
        self.frontend_dicts=cgkWDictFile.glideKeeperDicts(self.configDir)
        self.frontend_dicts.load()

        self.webURL=self.frontend_dicts.dicts['frontend_descript']['WebURL']
        self.descriptSignature,self.descriptFile=self.frontend_dicts.dicts['summary_signature']['main']


def run(config):
    os.environ['_CONDOR_SEC_DEFAULT_AUTHENTICATION_METHODS']='GSI'
    os.environ['X509_USER_PROXY']=config.proxyFile
    import glideKeeper
    import condorMonitor,condorManager
    gktid=glideKeeper.GlideKeeperThread(config.webURL,config.descriptFile,config.descriptSignature,
                                        config.runId,
                                        config.myClassadID,
                                        [(config.gfactoryNode,config.gfactoryClassadID)],config.gfactoryConstraint,
                                        config.collectorNode,
                                        config.proxyFile)
    gktid.start()
    workingDir = os.getcwd()
    os.makedirs(workingDir + '/' + startTime)
    main_log_fname=workingDir + '/' + startTime + '/glideTester.log'
    main_log=open(main_log_fname,'w')

    try:
        # first load the file, so we check it is readable
        fd = open(config.params, 'r')
        try:
            lines = fd.readlines()
        finally:
            fd.close()

        # reset the values
        executable = None
        inputFile = None
        outputFile = None
        environment = None
        arguments = None
        concurrency = None
        runs = 1

        # read the values
        for line in lines:
            line = line.strip()
            if line[0:1] in ('#',''):
                continue # ignore comments and empty lines
            arr = line.split('=',1)
            if len(arr) != 2:
                raise RuntimeError, 'Invalid parameter line, missing =: %s'%line
            key = arr[0].strip()
            val = arr[1].strip()
            if key == 'executable':
                if not os.path.exists(val):
                    raise RuntimeError, "%s '%s' is not a valid executable"%(key,val)
                executable = val
            elif key == 'transfer_input_files':
                inputFile = val
            elif key == 'transfer_output_files':
                outputFile = val
            elif key == 'environment':
                environment = val
            elif key == 'arguments':
                arguments = val
            elif key == 'concurrency':
                concurrency=val
            elif key == 'runs':
                runs = int(val)
        concurrencyLevel = concurrency.split()

        # make sure all the needed values have been read,
        # and assign defaults, if needed
        universe = 'vanilla'
        if executable == None:
            raise RuntimeError, "executable was not defined!"
        transfer_executable = "True"
        when_to_transfer_output = "ON_EXIT"
        requirements = '(GLIDEIN_Site =!= "UCSD12") && (Arch =!= "abc")'
        owner = 'Undefined'
        notification = 'Never'

        # Create a testing loop for each run
        for l in range(0, runs, 1):
            main_log.write("Iteration %i\n"%l)

            # Create a testing loop for each concurrency
            for k in range(0, len(concurrencyLevel), 1):
                main_log.write("Concurrency %i\n"%int(concurrencyLevel[k]))

                # request the glideins
                # we want 10% more glideins than the concurrency level
                requestedGlideins = int(concurrencyLevel[k])
                totalGlideins = int(requestedGlideins + .1 * requestedGlideins)
                gktid.request_glideins(totalGlideins)
                main_log.write("%s %i Glideins requested\n"%(ctime(),totalGlideins))
		
                # now we create the directories for each job and a submit file
                workingDir = os.getcwd()
                loop = 0
                dir1 = workingDir + '/' + startTime + '/concurrency_' + concurrencyLevel[k] + '_run_' + str(l) + '/'
                os.makedirs(dir1)
                logfile = workingDir + '/' + startTime + '/con_' + concurrencyLevel[k] + '_run_' + str(l) + '.log'
                outputfile = 'concurrency_' + concurrencyLevel[k] + '.out'
                errorfile = 'concurrency_' + concurrencyLevel[k] + '.err'
                filename = executable + '_concurrency_' + concurrencyLevel[k] + '_run_' + str(l) + '_submit.condor'
                condorSubmitFile=open(filename, "w")
                condorSubmitFile.write('universe = ' + universe + '\n' +
                                       'executable = ' + executable + '\n' +
                                       'transfer_executable = ' + transfer_executable + '\n' +
                                       'when_to_transfer_output = ' + when_to_transfer_output + '\n' +
                                       'Requirements = ' + requirements + '\n' +
                                       '+Owner = ' + owner + '\n' +
                                       'log = ' + logfile + '\n' +
                                       'output = ' +  outputfile + '\n' +
                                       'error = ' + errorfile + '\n' +
                                       'notification = ' + notification + '\n' +
                                       '+IsSleep = 1\n')
                if inputFile != None:
                    condorSubmitFile.write('transfer_input_files = ' + inputFile + '\n')
                if outputFile != None:
                    condorSubmitFile.write('transfer_output_files = ' + outputFile + '\n')
                if environment != None:
                    condorSubmitFile.write('environment = ' + environment + '\n')
                if arguments != None:
                    condorSubmitFile.write('Arguments = ' + arguments + '\n')
                condorSubmitFile.write('x509userproxy = ' + config.proxyFile + '\n\n')
                for j in range(0, int(concurrencyLevel[k]), 1):
                    condorSubmitFile.write('Initialdir = ' + dir1 + 'job' + str(loop) + '\n')
                    condorSubmitFile.write('Queue\n\n')
                    loop = loop + 1
                for i in range(0, int(concurrencyLevel[k]), 1):
                    dir2 = dir1 + 'job' + str(i) + '/'
                    os.makedirs(dir2)
                condorSubmitFile.close()

                # Need to figure out when we have all the glideins
                # Ask the glidekeeper object
                finished = "false"
                while finished != "true":
                    numberGlideins = gktid.get_running_glideins()
                    main_log.write("%s %s %s %s %s\n"%(ctime(), 'we have', numberGlideins, 'glideins, need', requestedGlideins))
                    main_log.flush()
                    sleep(5)
                    if numberGlideins >= requestedGlideins:
                        finished = "true"

                # Now we begin submission and monitoring
                submission = condorManager.condorSubmitOne(filename)
                main_log.write("%s %s\n"%(ctime(), "file submitted"))
                shutil.move(filename, workingDir + '/' + startTime + '/' + filename)
                running = "true"
                while running != "false":
                    check1 = condorMonitor.CondorQ()
                    try:
                        # i actually want to see all jos, not only running ones
                        check1.load('JobStatus<3', [])
                        data=check1.fetchStored()
                    except:
                        main_log.write("%s %s\n"%(ctime(), "condor_q failed... ignoring for now"))
                        main_log.flush()
                        sleep(2)
                        continue # retry the while loop
                    main_log.write("%s %s %s\n"%(ctime(), len(data.keys()), 'jobs running'))
                    main_log.flush()
                    if len(data.keys()) == 0:
                        running = "false"
                        main_log.write("%s %s\n"%(ctime(), "no more running jobs"))
                    else:
                        sleep(10)

        main_log.write("%s %s\n"%(ctime(), "Done"))

        # Now we parse the log files

        # Create a loop to parse each log file into a summaries directory
        summDir = workingDir + '/' + startTime + '/summaries/'
        os.makedirs(summDir)
        for l in range(0, runs, 1):
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
                logFile = workingDir + '/' + startTime + '/con_' + concurrencyLevel[k] + '_run_' + str(l) + '.log'
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
                header = "# Test Results for " + executable + " run at concurrency Level " + concurrencyLevel[k] + '\n\nJob#\tExecuteTime\tFinishTime\tReturnValue\n'
                file.write(header)
                exeTime=0
                finTime=0
                for i in range(0, int(concurrencyLevel[k])):
                    exeTime = exeTime + results[i][1]
                    finTime = finTime + results[i][2]
                    writeData = str(results[i][0]) + '\t' + str(results[i][1]) + '\t\t' + str(results[i][2]) + '\t\t' + results[i][3] + '\n'
                    file.write(writeData)

                aveExeTime = exeTime/int(concurrencyLevel[k])
                aveFinTime = finTime/int(concurrencyLevel[k])
                file.close()

                filepath = summDir + 'results.txt'
                file=open(filepath, 'a')
                times = "Concurrency Level = " + concurrencyLevel[k] + "\tExecute Time(Ave/Min/Max) = " + str(aveExeTime) + '/' + str(minExeTime) + '/' + str(maxExeTime) + "\tFinish Time(Ave/Min/Max) = " + str(aveFinTime) + "/" + str(minFinTime) + "/" + str(maxFinTime) + '\n'
                file.write(times)
                file.close()

    finally:
        main_log.write("%s %s\n"%(ctime(), "getting out"))
        main_log.flush()
        gktid.soft_kill()
        gktid.join()
    
    return



###########################################################
# Functions for proper startup
def main(argv):
    config=ArgsParser(argv)
    run(config)

if __name__ == "__main__":
    main(sys.argv)
