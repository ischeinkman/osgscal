
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



import sys
import os 
import shutil



def _parse_old_argv(builder, argv):
    if len(argv) !=6:
        raise RuntimeError, "Need 5 parameters: glideinWMSDir workDir webURL webStageDir gridmapFile"
    builder.glideinWMSDir=argv[1]
    builder.workDir=argv[2]
    builder.webURL=argv[3]
    builder.webStageDir=argv[4]
    builder.gridmapFile=argv[5]


def _parse_new_argv(builder, argv):

    valid_flags = ['--clean']

    valid_kv_settings = [
        '--cfg', '-cfg', '--config', 
        '--workdir',
        '--webstagedir', 
        '--glideinwmsdir', 
        '--gridmapfile', '--mapfile', '--gridmap',
        '-url', '--weburl', '--url'
    ]
    
    # Our flags are not case sensitive; first, remove the program's name, then
    # map them into the correct format.
    normed_argv = list( map(lambda arg: arg.strip().lower() if arg.startswith('--') else arg, argv[1:]) )
    flags = _parse_flags(normed_argv, valid_flags=valid_flags, valid_kv_settings=valid_kv_settings)
    builder.shouldClean = flags.get('--clean')
    builder.cfgFile = flags.get('--cfg') or flags.get('--config') or flags.get('-cfg')
    builder.workDir = flags.get('--workdir')
    builder.webStageDir = flags.get('--webstagedir')
    builder.glideinWMSDir = flags.get('--glideinwmsdir')
    builder.gridmapFile = flags.get('--gridmapfile') or flags.get('--gridmap') or flags.get('--mapfile')
    builder.webURL = flags.get('--weburl') or flags.get('--url') or flags.get('-url')

def _parse_flags(args, valid_flags = None, valid_kv_settings = None, key_marker = '--'):
    retval = {}
    idx = 0
    while idx + 1 < len(args):
        key = args[idx]
        assert(key.startswith(key_marker))
        next_item = args[idx + 1]
        if next_item.startswith(key_marker):
            assert(valid_flags is None or key in valid_flags)
            retval[key] = True 
        else:
            assert(valid_kv_settings is None or key in valid_kv_settings)
            retval[key] = next_item
            idx += 1
    return retval


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

    def __init__(self) :
        self.glideinWMSDir = None
        self.workDir = None
        self.webStageDir = None
        self.webURL = None
        self.gridmapFile = None
        self.shouldClean = None
        self.cfgFile = None

    def load_argv(self, argv):
        if not any(map(lambda a : '--' in a, argv)):
            _parse_old_argv(self, argv)
            return 

        _parse_new_argv(self, argv)
        if not self._isPopulated() and self.cfgFile is not None:
            self._loadCfgFile(self.cfgFile)
        ilog('Created Ilan WebStructBuilder: %s'%str(self))

        
    def _isPopulated(self):
        return self.glideinWMSDir != None and self.gridmapFile != None and self.webURL != None and self.webStageDir != None and self.workDir != None

    def _loadCfgFile(self, cfgFile):

        #Only load the file if we both can and need to 
        if self._isPopulated():
            return 
        if cfgFile is None:
            raise RuntimeError, "Tried loading cfg from None path!"
        import os 
        if not os.path.exists(cfgFile):
            raise RuntimeError, "Passed in config file %s does not exist!"%cfgFile
        
        # The file should be a simple commented key=value file; parse it as such.
        cur_path = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.join(cur_path,"../lib"))
        from KeyValueConfig import KeyValueConfig, parse_kv_file
        conf = parse_kv_file(cfgFile)

        # We are not case-sensitive in the keys.
        pairs = dict( map( lambda kv: (kv[0].lower(), kv[1]), conf.settings.items() ) )

        # We allow a key-value config file to add a prefix to the web struct's settings
        # to distinguish them from other runtime settings. If the prefix is used, get the relevant 
        # pairs and strip the prefix.
        key_prefix = 'webstruct.'
        if any(map(lambda key : key.startswith(key_prefix), pairs.keys())):
            print('Got prefixed items.')
            relevant_pairs = filter(lambda kv: kv[0].startswith(key_prefix), pairs.items())
            print('Relevant pairs: %s'%(str(relevant_pairs)))
            pairs = dict( map(lambda kv: (kv[0][len(key_prefix) : ], kv[1]), relevant_pairs) )
            print('Stripped pairs: %s'%(str(pairs)))


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
        if self.shouldClean is None:
            self.shouldClean = pairs.get('shouldclean')

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
        cur_path = os.path.dirname(os.path.abspath(__file__))
        sys.path.append(os.path.join(cur_path,"../lib"))
        print('Adding glideinwmsdir to path: %s'%(str(self.glideinWMSDir)))
        glideinwms_parent = os.path.join(self.glideinWMSDir, '..')
        print('Made parent: %s'%(str(glideinwms_parent)))
        sys.path.append(glideinwms_parent)
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
        self._create_empty_web_index()
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
    
    def _create_empty_web_index(self):
        # The V3 factory uses curl to download files from the web struct path. 
        # Curl will attempt to first go to the raw webStageDir root for some reason,
        # which in httpd by default will attempt to create the directory listing page.
        # Generally this is blocked, returning a HTTP 403:Forbidden error, which then
        # errors the ad in the factory. 
        # To circumvent this we create an empty index file at the web stage dir root.
        index_path = os.path.join(self.webStageDir, "index.html")
        if not (os.path.exists(index_path) and os.path.isfile(index_path)):
            index_file = open(index_path, 'w')
            index_file.write(' ')
            index_file.flush()
            index_file.close()
def main(argv):
    builder = WebStructBuilder()
    builder.load_argv(argv)
    builder.run()

if __name__ == '__main__':
    main(sys.argv)