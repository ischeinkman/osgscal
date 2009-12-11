#!/usr/bin/python
import sys
import os
import time
import getopt

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

from plugin import Plugin
import configUtils

class ZabLogger(Plugin):
  def __init__(self):
    super(ZabLogger, self).__init__()
    self.sendTypes = []
    self.zabServer = None
    self.port = None
    self.host = None
    self.options += 'v'
    self.verbose = False
 
  def getArgs(self, argv):
    super(ZabLogger, self).getArgs(argv)
    optlist, args = getopt.getopt(argv, self.options)
    
    for opt in optlist:
      if opt[0] == '-v':
        self.verbose = True
    
    if len(args) > 0:
      self.confPath = args[0]

  def printHelp(self):
    print '''\
Usage: %s [options] CONFIGFILE
  options:
    -h        show this help page
    -t n      threshold n seconds long.  xml file older than threshold
              will not be logged.  disabled by default (always logs)
    -v        verbose''' % sys.argv[0]  

  def parseConf(self):
    confDict = {'xmlpath' : None,
                'send_type' : None,
                'zabbix_server' : None,
                'port' : None,
                'host' : None}

    configUtils.parse(self.confPath, confDict)

    if confDict['xmlpath'] is None:
      self.xmlPath = os.path.join(STARTUP_DIR,"../etc/osgmonitoring.xml")
    else:
      self.xmlPath = confDict['xmlpath']

    if confDict['send_type'] == '*':
      self.sendTypes = ['pcpu', 'pmem', 'vsize', 'rss', 'procs', 'files']
    elif confDict['send_type'] is not None:
      sendTypes = confDict['send_type'].split(',')
      sendTypes = [type.strip() for type in sendTypes]
      for type in sendTypes:
        if type == '': continue
        if (type == 'pcpu' or type == 'pmem' or type == 'vsize' or
              type == 'rss' or type == 'procs' or type == 'files'):
          if type not in self.sendTypes:
            self.sendTypes.append(type)
        else:
          raise IOError, "Error parsing %s: invalid send_type: %s" % (self.confPath,
            type)

    # if server not specified in conf, give it local host ip
    if confDict['zabbix_server'] is None:
      self.zabServer = '127.0.0.1'
    else:
      self.zabServer = confDict['zabbix_server']

    # if port not specified in conf, give it zabbix default 
    if confDict['port'] is None:
      self.port = 10051
    else:
      self.port = int(confDict['port'])

    # if host not specified in conf, try 'ZABBIX Server' 
    if confDict['host'] is None:
      self.host = '"ZABBIX Server"'
    else:
      self.host = confDict['host']

logger = ZabLogger()
logger.getArgs(sys.argv[1:])

if logger.confPath is None:
  logger.printHelp()
  sys.exit(1)

if logger.helpFlag:
  logger.printHelp()
  sys.exit(0)

if logger.threshold is not None:
  if not logger.withinThresh():
    sys.exit(0)

logger.parseConf()
logger.parseXML()

# check if xml reported collector error and if so do nothing
if logger.error['flag']:
  sys.exit(0)

for proc in logger.processes:
  for type in logger.sendTypes:
    if logger.verbose == True:
      outstring = "zabbix_sender -z %s -p %i -s %s -k %s.%s -o %f" % (
        logger.zabServer, logger.port, logger.host, proc['name'], type, proc[type])
      print outstring
    else:
      outstring = "zabbix_sender -z %s -p %i -s %s -k %s.%s -o %f > /dev/null 2>&1" % (
        logger.zabServer, logger.port, logger.host, proc['name'], type, proc[type])

    os.system(outstring)
    #os.system("zabbix_sender -z %s -p %i -s %s -k %s.%s -o %f"
    #  % (logger.zabServer, logger.port, logger.host, proc['name'], type, proc[type]))