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
    sys.path.append(os.path.join(config.glideinWMSDir,".."))
    import cgkWDictFile

    dicts=cgkWDictFile.glideKeeperDicts(config.workDir,config.webStageDir)
    dicts.populate(config.webURL,config.gridmapFile)
    dicts.create_dirs()
    dicts.save()

    # The V3 factory uses curl to download files from the web struct path. 
    # Curl will attempt to first go to the raw webStageDir root for some reason,
    # which in httpd by default will attempt to create the directory listing page.
    # Generally this is blocked, returning a HTTP 403:Forbidden error, which then
    # errors the ad in the factory. 
    # To circumvent this we create an empty index file at the web stage dir root.
    index_path = os.path.join(config.webStageDir, "index.html")
    if not (os.path.exists(index_path) and os.path.isfile(index_path)):
        index_file = open(index_path, 'w')
        index_file.write(' ')
        index_file.flush()
        index_file.close()

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
