
def dbgp(obj, indent = 0):
    if not hasattr(obj, "__dict__"):
        return str(obj) + "\n"
    retval = (indent * " ") + "{\n"
    for k in obj.__dict__:
        retval += (indent * " ") + str(k) + ": " + dbgp(obj.__dict__[k], indent + 2)
    retval += (indent * " ") + "}\n"
    return retval 
        

import time
LOG_FILE = True 
LOG_PRINT = True

if LOG_FILE:
    ilanfile = open('ilan_log-%s.txt'%time.strftime('%Y-%m-%d %H:%M:%S'), 'w')
def ilog(line):
    if LOG_PRINT:
        print(line)
    if LOG_FILE:
        ilanfile.write(line + "\n")
        ilanfile.flush()



from createTesterWebStruct import run, ArgsParser

import sys
import os 
import shutil


class WebStructBuilder:
    def __repr__(self):
        return (
            "WebStructBuilder("
            "glideinWMSDir: %s, "
            "gridmapFile: %s, "
            "webURL: %s, "
            "workDir: %s, "
            "webStageDir: %s, "
            ")"
        )%(str(self.glideinWMSDir), str(self.gridmapFile), str(self.webURL), str(self.workDir), str(self.webStageDir))

    def __init__(self, argv) :
        self.glideinWMSDir = None
        self.workDir = None
        self.webStageDir = None
        self.webURL = None
        self.gridmapFile = None
        self.shouldClean = False

        if not any(map(lambda a : '--' in a, argv)):
            #By default, use the original ordering. 
            if len(argv) !=6:
                raise RuntimeError, "Need 5 parameters: glideinWMSDir workDir webURL webStageDir gridmapFile"
            else:
                self.glideinWMSDir=argv[1]
                self.workDir=argv[2]
                self.webURL=argv[3]
                self.webStageDir=argv[4]
                self.gridmapFile=argv[5]
            return 

        if '--ilan' in argv:
            self._loadIlanDefaults()
            return 
        
        cfgFile = None 
        idx = 1
        while idx < len(argv):
            flag = argv[idx].strip().lower()
            if flag == '--clean':
                self.shouldClean = True
            elif flag == '--cfg':
                idx += 1
                if idx >= len(argv):
                    raise RuntimeError, "Could not find argument after %s!"%argv[idx-1]
                cfgFile = argv[idx]
            elif flag == '--glideinwmsdir':
                idx += 1
                if idx >= len(argv):
                    raise RuntimeError, "could not find argument after %s!"%argv[idx-1]
                self.glideinWMSDir = argv[idx]
            elif flag == '--gridmapfile':
                idx += 1
                if idx >= len(argv):
                    raise RuntimeError, "could not find argument after %s!"%argv[idx-1]
                self.gridmapFile = argv[idx]
            elif flag == '--weburl':
                idx += 1
                if idx >= len(argv):
                    raise RuntimeError, "Could not find argument after %s!"%argv[idx-1]
                self.webURL = argv[idx]
            elif flag == '--workdir':
                idx += 1
                if idx >= len(argv):
                    raise RuntimeError, "Could not find argument after %s!"%argv[idx-1]
                self.workDir = argv[idx]
            elif flag == '--webstagedir':
                idx += 1
                if idx >= len(argv):
                    raise RuntimeError, "Could not find argument after %s!"%argv[idx-1]
                self.webStageDir = argv[idx]
            idx += 1
        if not self._isPopulated() and cfgFile is not None:
            self._loadCfgFile(cfgFile)
        ilog('Created Ilan WebStructBuilder: %s'%str(self))

        
    def _isPopulated(self):
        return self.glideinWMSDir != None and self.gridmapFile != None and self.webURL != None and self.webStageDir != None and self.workDir != None

    def _loadCfgFile(self, cfgFile):
        #Only load the file if we both can and need to 
        if self._isPopulated():
            return 
        if cfgFile is None:
            raise RuntimeError, "Tried loading cfg from None path!"

        #Load and parse the file
        import os 
        if not os.path.exists(cfgFile):
            raise RuntimeError, "Passed in CFG file %s does not exist!"%cfgFile
        fileObj = open(cfgFile, 'r')
        raw = fileObj.read()
        lines = raw.split('\n')
        noComments = [l.split('#', 2)[0] for l in lines]
        rawPairs = [l.split('=', 2) for l in noComments if '=' in l]
        pairs = dict([(p[0].strip().lower(), p[1].strip()) for p in rawPairs if len(p) == 2])

        #Populate ourself from the file
        if self.glideinWMSDir is None:
            self.glideinWMSDir = pairs.get("glideinwmsdir")
        if self.gridmapFile is None:
            self.gridmapFile = pairs.get('gridmapfile') or pairs.get('mapfile') or pairs.get('gridfile')
        if self.webURL is None:
            self.webURL = pairs.get('weburl') 
        if self.workDir is None:
            self.workDir = pairs.get('workdir') or pairs.get('configdir')
        if self.webStageDir is None:
            self.webStageDir = pairs.get('webstagedir')

    def cleanStructs(self):
        import shutil
        if self.workDir is not None and os.path.exists(self.workDir):
            ilog("Cleaning old workdir: %s"%self.workDir)
            shutil.rmtree(self.workDir)
        if self.webStageDir is not None and os.path.exists(self.webStageDir):
            ilog("Cleaning old webStageDir: %s"%self.webStageDir)
            shutil.rmtree(self.webStageDir)

    def createStructs(self):
        ilog('Running createStructs for builder: %s'%str(self))
        #Import the dictionary file and its dependencies
        STARTUP_DIR=sys.path[0]
        sys.path.append(os.path.join(STARTUP_DIR,"../lib"))
        sys.path.append(os.path.join(self.glideinWMSDir,".."))
        import cgkWDictFile
        try:
            import inspect
            srcf = inspect.getsourcefile(cgkWDictFile)
        except:
            srcf = 'ERROR'
        ilog("Imported cgkWDictFile from %s"%srcf)

        #Create the config files
        ilog('Creating struct.')
        dicts=cgkWDictFile.glideKeeperDicts(self.workDir,self.webStageDir)
        dicts.populate(self.webURL,self.gridmapFile)
        dicts.create_dirs()
        dicts.save()
        ilog('Done.')

        print "Created config files in %s\n"%dicts.work_dir
        print "Web files in %s"%dicts.stage_dir
        print "If needed, move them so they are accessible from\n  %s"%self.webURL
    
    def run(self):
        if not self._isPopulated():
            raise RuntimeError, "Not all the parameters were set correctly!\nRunning as struct: %s"%str(self)
        if self.shouldClean:
            self.cleanStructs()
        self.createStructs()

    def _loadIlanDefaults(self):
        self.shouldClean = True 
        self.glideinWMSDir = "/home/ilan/glideinwms"
        self.workDir = '/home/ilan/workDir'
        self.webStageDir = "/home/ilan/webStageDir"
        self.webURL = "http://test-001.t2.ucsd.edu/weburla"
        self.gridmapFile = "/home/ilan/test-gridmapfile"

def main(argv):
    builder = WebStructBuilder(argv)
    builder.run()

if __name__ == '__main__':
    main(sys.argv)