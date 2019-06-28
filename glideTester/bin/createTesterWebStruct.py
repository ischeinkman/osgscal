
import os
import sys
cur_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cur_path,"../lib"))
from configutils import KeyValueConfig, parse_kv_file, parse_argv, get_config_file_list
from logHelper import ilog, setup_loggers
import shutil

def _parse_old_argv(builder, argv):
    builder.glideinWMSDir=argv[1]
    builder.workDir=argv[2]
    builder.webURL=argv[3]
    builder.webStageDir=argv[4]
    builder.gridmapFile=argv[5]


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
        if len(argv) == 6 and not any(map(lambda flag : flag.startswith('-'), argv)):
            _parse_old_argv(self, argv)
            return
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
        flags = parse_argv(normed_argv, valid_flags=valid_flags, valid_kv_settings=valid_kv_settings)
        self.shouldClean = flags.get('--clean')
        self.cfgFile = flags.get('--cfg') or flags.get('--config') or flags.get('-cfg')
        self.workDir = flags.get('--workdir')
        self.webStageDir = flags.get('--webstagedir')
        self.glideinWMSDir = flags.get('--glideinwmsdir')
        self.gridmapFile = flags.get('--gridmapfile') or flags.get('--gridmap') or flags.get('--mapfile')
        self.webURL = flags.get('--weburl') or flags.get('--url') or flags.get('-url')


        self.load_cfg()
        self._setup_logger()
        ilog('Created Ilan WebStructBuilder: %s'%str(self))

        
    def _isPopulated(self):
        return self.gridmapFile != None and self.webURL != None and self.webStageDir != None and self.workDir != None

    def load_cfg(self):
        paths = get_config_file_list(file_name = 'glideTester.cfg', arg_path=self.cfgFile)
        for fl in paths:
            if self._isPopulated():
                return 
            key_prefix = 'webstruct.'
            conf = parse_kv_file(fl, key_prefix=key_prefix, key_mapper= lambda k: k.lower())
            pairs = conf.settings
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

    def _setup_gwms_path(self):
        if self.glideinWMSDir is None:
            return
        if not self.glideinWMSDir in sys.path:
            sys.path.insert(0, self.glideinWMSDir)
        glideinwms_parent = os.path.join(self.glideinWMSDir, '..')
        if not glideinwms_parent in sys.path:
            sys.path.insert(0,glideinwms_parent)

    def _setup_logger(self):
        self._setup_gwms_path()
        paths = get_config_file_list(file_name = 'glideTester.cfg', arg_path=self.cfgFile)
        setup_loggers(paths)

    def createStructs(self):
        ilog('Running createStructs for builder: %s'%str(self))
        self._setup_gwms_path()
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