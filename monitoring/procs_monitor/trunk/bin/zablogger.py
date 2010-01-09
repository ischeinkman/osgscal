#!/usr/bin/python
#
#  zablogger.py
#
#  Description:
#    Uses zabbix_sender tool to send process info to Zabbix monitoring system
#
#  Usage:
#    zablogger.py [options] CONFIGFILE
#
#  Author:
#    Jeff Dost (Nov 2009)
#
##

import sys
import os
import time
import getopt

# add lib folder to import path
STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))
sys.path.append("/usr/local/lib/procs_monitor")

from plugin import Plugin
import configUtils

class ZabLogger(Plugin):
  def __init__(self):
    super(ZabLogger, self).__init__()
    self.sendTypes = [] # list of metrics chosen to send for each process
    # zabbix server arguments for zabbix_sender
    self.zabServer = None
    self.port = None
    self.host = None
    # add option for verbose mode
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

    # parse values from config file, try default values if not found
    configUtils.parse(self.confPath, confDict)

    if confDict['xmlpath'] is None:
      self.xmlPath = os.path.join(STARTUP_DIR,"../osgmonitoring.xml")
    else:
      self.xmlPath = confDict['xmlpath']

    # if wildcard, prepare all metrics
    if confDict['send_type'] == '*':
      self.sendTypes = ['pcpu', 'pmem', 'vsize', 'rss', 'procs', 'files']
    # otherwise prepare each one listed
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

##
#
# Main
#
##

# create plugin and get command line arguments
logger = ZabLogger()
logger.getArgs(sys.argv[1:])

if logger.confPath is None:
  logger.printHelp()
  sys.exit(1)

if logger.helpFlag:
  logger.printHelp()
  sys.exit(0)

logger.parseConf()

# exit if threshold was used and xml file is stale
if logger.threshold is not None:
  if not logger.withinThresh():
    sys.exit(0)

logger.parseXML()

# check if xml reported collector error and if so do nothing
if logger.error['flag']:
  sys.exit(0)

# traverse processes and send metrics
for proc in logger.processes:
  for type in logger.sendTypes:
    # if verbose mode, print commmand and output of zabbix_sender
    if logger.verbose == True:
      outstring = "zabbix_sender -z %s -p %i -s %s -k %s.%s -o %f" % (
        logger.zabServer, logger.port, logger.host, proc['name'], type, proc[type])
      print outstring
    else:
      outstring = "zabbix_sender -z %s -p %i -s %s -k %s.%s -o %f > /dev/null 2>&1" % (
        logger.zabServer, logger.port, logger.host, proc['name'], type, proc[type])

    os.system(outstring)
