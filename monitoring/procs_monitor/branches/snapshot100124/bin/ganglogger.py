#!/usr/bin/python
#
#  ganglogger.py
#
#  Description:
#    Uses Ganglia gmetric tool to send process info to Ganglia monitoring system
#
#  Usage:
#    ganglogger.py [options] CONFIGFILE
#
#  Author:
#    Jeff Dost (Oct 2009)
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

class GangLogger(Plugin):
  def __init__(self):
    super(GangLogger, self).__init__()
    self.sendTypes = [] # list of metrics chosen to send for each process
 
  def getArgs(self, argv):
    super(GangLogger, self).getArgs(argv)
    optlist, args = getopt.getopt(argv, self.options)
    
    if len(args) > 0:
      self.confPath = args[0]

  def printHelp(self):
    print '''\
Usage: %s [options] CONFIGFILE
  options:
    -h        show this help page
    -t n      threshold n seconds long.  xml file older than threshold
              will not be logged.  disabled by default (always logs)''' % sys.argv[0]  

  def parseConf(self):
    confDict = {'xmlpath' : None,
                'send_type' : None}

    # parse values from config file, try default values if not found
    configUtils.parse(self.confPath, confDict)

    if confDict['xmlpath'] is None:
      self.xmlPath = os.path.join(STARTUP_DIR,"../osgmonitoring.xml")
    else:
      self.xmlPath = confDict['xmlpath']

    if confDict['send_type'] is None:
      return

    # if wildcard, prepare all metrics
    if confDict['send_type'] == '*':
      self.sendTypes = ['pcpu', 'pmem', 'vsize', 'rss', 'procs', 'files']
      return

    # otherwise prepare each one listed
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

##
#
# Main
#
##

# create plugin and get command line arguments
logger = GangLogger()
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

step = 300
#step = 30
heartbeat = 1800

# traverse processes and send metrics
for proc in logger.processes:
  for type in logger.sendTypes:
    os.system("gmetric --name %s_%s --value %f --type float --tmax=%s --dmax=%s"
      % (proc['name'], type, proc[type], step, heartbeat))    
