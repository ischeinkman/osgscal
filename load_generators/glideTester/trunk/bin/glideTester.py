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

# Need these modules
import condorMonitor
import condorManager

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

############################
# Configuration class
class ArgsParser:
    def __init__(self,argv):
        # define defaults
        self.config='glideTester.cfg' #just a random default
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
            elif el=='-runId':
                idx+=1
                el=argv[idx]
                self.runId=el
            else:
                raise RuntimeError, "Unknown argument '%s' at position %i"%(el, idx)
            idx+=1

        # check and fix the attributes
        if self.runId==None:
            # not defined, create a random one
            self.runId="glideTester_%s_%i_%i"%(os.uname()[1],os.getpid(),random.randint(1000,9999))
        
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
        #if self.proxyFile==None:
        #    if os.environ.has_key('X509_USER_PROXY'):
        #        self.proxyFile=os.environ['X509_USER_PROXY']
        #    else:
        #        self.proxyFile='/tmp/x509us_u%i'%os.getuid()
        #    if not os.path.exists(self.proxyFile):
        #        raise RuntimeError, "proxyFile was not defined, and '%s' does not exist!"%self.proxyFile
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
    gktid=glideKeeper.GlideKeeperThread(config.webURL,config.descriptFile,config.descriptSignature,
                                        config.runId,
                                        config.myClassadID,
                                        [(config.gfactoryNode,config.gfactoryClassadID)],config.gfactoryConstraint,
                                        config.proxyFile)
    gktid.start()
    try:
        # most of the code goes here
	
	# first load the file, so we check it is readable
	fd = open('parameters.cfg', 'r')
	try:
		lines = fd.readlines()
	finally:
		fd.close()

	# reset the values
	executable = None
	arguments = None
	concurrency = None
	owner = None

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
		elif key == 'owner':
			owner=val
		elif key == 'arguments':
			arguments = val
		elif key == 'concurrency':
			concurrency=val
	concurrencyLevel = concurrency.split()

	# make sure all the needed values have been read,
	# and assign defaults, if needed
	universe = 'vanilla'
	if executable == None:
		raise RuntimeError, "executable was not defined!"
		executable = raw_input("Enter executable: ");
	transfer_executable = "True"
	when_to_transfer_output = "ON_EXIT"
	requirements = '(GLIDEIN_Site =!= "UCSD12") && (Arch =!= "abc")'
	if owner == None:
		owner = 'Undefined'
	notification = 'Never'

	# Create a testing loop for each concurrency
	results = []
	for i in range(0, len(concurrencyLevel), 1):

		# request the glideins
		# we want 10% more glideins than the concurrency level
		requestedGlideins = int(concurrencyLevel[i])
		totalGlideins = int(requestedGlideins + .1 * requestedGlideins))
		gktid.request_glideins(totalGlideins)
		
		# now we create the directories for each job and a submit file
		workingDir = os.getcwd()
		for k in range(0, len(concurrencyLevel), 1):
			loop = 0
			dir1 = workingDir + '/' + 'test' + concurrencyLevel[k] + '/'
			os.makedirs(dir1)
			logfile = dir1 + 'test' + concurrencyLevel[k] + '.log'
			outputfile = 'test' + concurrencyLevel[k] + '.out'
			errorfile = 'test' + concurrencyLevel[k] + '.err'
			filename = dir1 + 'submit.condor'
			FILE=open(filename, "w")
			FILE.write('universe=' + universe + '\n')
			FILE.write('executable=' + executable + '\n')
			FILE.write('transfer_executable=' + transfer_executable + '\n')
			FILE.write('when_to_transfer_output=' + when_to_transfer_output + '\n')
			FILE.write('Requirements=' + requirements + '\n')
			FILE.write('+Owner=' + owner + '\n')
			FILE.write('log=' + logfile + '\n')
			FILE.write('output=' +  outputfile + '\n')
			FILE.write('error=' + errorfile + '\n')
			FILE.write('notification=' + notification + '\n' + '\n')
			if arguments != None:
				FILE.write('Arguments =' + arguments + '\n')
			for j in range(0, int(concurrencyLevel[k]), 1):
				FILE.write('Initialdir = ' + 'job' + str(loop) + '\n')
				FILE.write('Queue' + '\n' + '\n')
				loop = loop + 1
			for i in range(0, int(concurrencyLevel[k]), 1):
				dir2 = dir1 + 'job' + str(i) + '/'
				os.makedirs(dir2)
			FILE.close()

		# Need to figure out when we have all the glideins
		# Ask the glidekeeper object
		finished = "false"
		while finished != "true":
			numberGlideins = gktid.get_running_glideins()
			if numberGlideins = requestedGlideins:
				finished = "true"

		# Now we begin submission and monitoring
		
		## Need to figure this part out
 		submission = condorManager.condorSubmitOne(filename)
		running = "true"
		while running != "false":	
			check1 = condorMonitor.CondorQ()
		
			# Not sure if this is the correct constraint to put on the monitor
			if check1 == None:
				running = "false"

		# Need to check log files for when first
		# job submitted  and last job finished
		hours = []
		minutes = []
		seconds = []
		logCheck = open(logfile, 'r')
		try:
			lines1 = logCheck.readlines()
		finally:
			logCheck.close()
		for line in lines1:
			line = line.strip()
			if line[0:1] in ('(','.','U','R','J','C','G'):
				continue # ignore unwanted text lines
		        arr1 = line.split(') ',1)
		        if len(arr1) < 2:
            			    continue
        		arr2 = arr1[1].split(' ',2)
        		time = arr2[1].split(':',2)
       			hours.append(int(time[0]))
        		minutes.append(int(time[1]))
        		seconds.append(int(time[2]))
		diffHours = (hours[len(hours)-1] - hours[0]) * 3600
		diffMinutes = (minutes[len(minutes)-1] - minutes[0]) * 60
		diffSeconds = seconds[len(seconds)-1] - seconds[0]
		totalTime = diffHours + diffMinutes + diffSeconds
		final = [totalTime, concurrencyLevel[i]]
		results.append(final)
	
		# Cleanup all the directories and files made
		shutil.rmtree(dir1)	

	# Write results to a data file for plotting

#        pass
    finally:
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
