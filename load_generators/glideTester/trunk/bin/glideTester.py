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
import sys,os,os.path
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

        # chaeck and fix the attributes
        if self.runId==None:
            # not defined, create a random one
            self.runId="glideTester_%s_%i_%i"%(os.uname()[1],os.getpid(),random.randint(1000,9999))
        
        # load external values
        self.load_config()

    def load_config(self):
        # first load file, so we dcheck it is readable
        fd=open(self.config,'r')
        try:
            lines=fd.readlines()
        finally:
            fd.close()

        # reset the values
        self.glideinWMSDir=None
        self.proxyFile=None
        self.gfactoryNode=None
        self.gfactoryConstraint=None
        self.gfactoryClassadID=None

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
            elif key=='proxyFile':
                if not os.path.exists(val):
                    raise RuntimeError, "%s '%s' is not a valid dir"%(key,val)
                self.proxyFile=val
            elif key=='gfactoryNode':
                self.gFactoryNode=val
            elif key=='gfactoryConstraint':
                self.gFactoryConstraint=val
            elif key=='gfactoryClassadID':
                self.gfactoryClassadID=val
            else:
                raise RuntimeError, "Invalid config key '%s':%s"%(key,line)

        # make sure all the needed values have been read,
        # and assign defaults, if needed
        if self.glideinWMSDir==None:
            raise RuntimeError, "glideinWMSDir was not defined!"
        if self.proxyFile==None:
            if os.environ.has_key('X509_USER_PROXY'):
                self.proxyFile=os.environ['X509_USER_PROXY']
            else:
                self.proxyFile='/tmp/x509us_u%i'%os.getuid()
            if not os.path.exists(self.proxyFile):
                raise RuntimeError, "proxyFile was not defined, and '%s' does not exist!"%self.proxyFile
        if self.gfactoryClassadID==None:
            raise RuntimeError, "gfactoryClassadID was not defined!"


def run(config):
    sys.path.append(os.path.join(config.glideinWMSDir,"lib"))
    sys.path.append(os.path.join(config.glideinWMSDir,"frontend"))
    import glideKeeper
    gktid=glideKeeper.glideKeeperThread(config.runId,
                                        config.gfactoryClassadID,
                                        [config.gfactoryNode],config.gFactoryConstraint,
                                        config.proxyFile)
    gktid.start()
    try:
        # most of the code goes here
        pass
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
