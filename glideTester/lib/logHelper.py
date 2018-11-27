from configutils import parse_kv_file, KeyValueConfig

_default_logger_name = 'frontend'
_default_directory = '/var/log/glidetester'
_default_levels = 'warn,err,info,debug'
_default_extension = '.log.txt'
_default_max_days = 10
_default_min_days = 1
_default_max_size = 10

"""  """
class LogConfig():
    def __init__(self):
        self.logger_name = None
        self.directory = None
        self.levels = None
        self.extension = None
        self.maxDays = None
        self.minDays = None
        self.maxSize = None

    def run(self):
        import logging
        from glideinwms.lib import logSupport

        logger_name = self.logger_name or _default_logger_name
        directory = self.directory or _default_directory
        extension = self.extension or _default_extension
        levels = self.levels or _default_levels
        max_days = self.maxDays or _default_max_days
        min_days = self.minDays or _default_min_days
        max_size = self.maxDays or _default_max_size

        logSupport.add_processlog_handler(logger_name, directory,
                                        levels, extension,
                                        max_days, min_days, 
                                        max_size
        )
        logSupport.log = logging.getLogger(self.logger_name)
        logSupport.log.info("GlideTester logging initialized.")

    def load_config_file(self, path):
        key_prefix = 'logger.'
        config = parse_kv_file(path, key_prefix=key_prefix, key_mapper= lambda k: k.lower())
        print('Got config map: %s'%str(config.settings))
        if self.directory is None:
            self.directory = config.settings.get('directory')
        if self.extension is None:
            self.extension = config.settings.get('extension')
        if self.levels is None:
            self.levels = config.settings.get('levels')
        if self.maxDays is None:
            vl = config.settings.get('maxdays')
            if vl is not None:
                self.maxDays = int(vl)
        if self.minDays is None:
            vl = config.settings.get('mindays')
            if vl is not None:
                self.minDays = int(vl)
        if self.maxSize is None:
            vl = config.settings.get('maxsize')
            if vl is not None:
                self.maxSize = int(vl)


def setup_loggers(config_paths):
    conf = LogConfig()
    for fl in config_paths:
        conf.load_config_file(fl)
    conf.run()

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

