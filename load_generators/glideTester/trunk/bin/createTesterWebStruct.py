#!/bin/env python

#
# Description:
#  This program creates the Web structure needed by the glideTester
#
# Author:
#  Igor Sfiligoi @ UCSD
#

import sys,os,os.path
STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))


class ArgsParser:
    def __init__(self,argv):
        if len(argv)<6:
            raise RuntimeError, "Need 5 parameters: glideinWMSDir workDir webURL webStageDir gridmapFile"
        self.glideinWMSDir=argv[1]
        self.workDir=argv[2]
        self.webURL=argv[3]
        self.webStageDir=argv[4]
        self.gridmapFile=argv[5]

def run(config):
    sys.path.append(os.path.join(config.glideinWMSDir,"lib"))
    sys.path.append(os.path.join(config.glideinWMSDir,"creation/lib"))
    import cgkWDictFile

    dicts=cgkWDictFile.glideKeeperDicts(config.workDir,config.webStageDir)
    dicts.populate(config.webURL,config.gridmapFile)
    dicts.create_dirs()
    dicts.save()

    print "Created config files in %s\n"%dicts.work_dir
    print "Web files in %s"%dicts.stage_dir
    print "If needed, move them so they are accessible from\n  %s"%config.webURL


###########################################################
# Functions for proper startup
def main(argv):
    config=ArgsParser(argv)
    run(config)

if __name__ == "__main__":
    main(sys.argv)
