#!/usr/bin/python
#
#  syslogger.py
#
#  Description:
#    Updates syslog file.
#
#  Usage:
#    syslogger.py [options] XMLPATH
#
#  Author:
#    Jeff Dost (Sept 2009)
#
##

import sys

import syslog
#import time
import os
import getopt

# add lib folder to import path
STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))
sys.path.append("/usr/local/lib/procs_monitor")

from plugin import Plugin
from plugin import XMLFileError

# list of syslog facility numbers
sysfacs = [syslog.LOG_LOCAL0, syslog.LOG_LOCAL1, syslog.LOG_LOCAL2, syslog.LOG_LOCAL3,
  syslog.LOG_LOCAL4, syslog.LOG_LOCAL5, syslog.LOG_LOCAL6, syslog.LOG_LOCAL7];

class SysLogger(Plugin):
  def __init__(self):
    super(SysLogger, self).__init__()
    # add option to choose syslog facility
    self.options += 's:' 
    self.sysfac = sysfacs[0]

  def getArgs(self, argv):
    super(SysLogger, self).getArgs(argv)
    optlist, args = getopt.getopt(argv, self.options)
    for opt in optlist:
      if opt[0] == '-s':
        try:
          self.sysfac = sysfacs[int(opt[1])]
        except (ValueError, IndexError):
          raise ValueError, "Invalid argument for %s:%s" % (opt[0], opt[1])
          
    if len(args) > 0:
      self.xmlPath = args[0]

  def printHelp(self):
    print '''\
Usage: %s [options] XMLPATH
  options:
    -h        show this help page
    -s 0-7    choose syslog local[0-7] facility (defaults to local0)
    -t n      threshold n seconds long.  xml file older than threshold
              will not be logged.  disabled by default (always logs)''' % sys.argv[0]

##
#
# Main
#
##

# create plugin and get command line arguments
logger = SysLogger()
logger.getArgs(sys.argv[1:])

# this script requires path of xml file to be parsed as input argument
if logger.xmlPath is None:
  logger.printHelp()
  sys.exit(1)

if logger.helpFlag:
  logger.printHelp()
  sys.exit(0)

syslog.openlog('osgmonitor', syslog.LOG_PID, logger.sysfac)

# exit if threshold was used and xml file is stale
if logger.threshold is not None:
  try:
    if not logger.withinThresh():
      sys.exit(0)
  except OSError, e:
    syslog.syslog(syslog.LOG_ERR, "Could not access XML: %s" % str(e))
    syslog.closelog()
    sys.exit(1)

# start logging and open xml
syslog.syslog(syslog.LOG_INFO, "Reading XML...")

try:
  logger.parseXML()
except Exception, e:
  syslog.syslog(syslog.LOG_ERR, "Failed parsing XML: %s" % str(e))
  syslog.closelog()
  sys.exit(1)

# log last xml update time
syslog.syslog(syslog.LOG_INFO, "XML last updated %s" % logger.updated['Local']['human'])

# check if xml reported collector error and if so log it and quit
if logger.error['flag']:
  syslog.syslog(syslog.LOG_ERR, "Collector Error: %s" % logger.error['message'])
  syslog.closelog()
  sys.exit(0)

# otherwise log everything else

# log load averages
syslog.syslog(syslog.LOG_INFO, "Load Average: %.2f, %.2f, %.2f" % (logger.cpu['loadavg']['1'], 
  logger.cpu['loadavg']['15'], logger.cpu['loadavg']['15']))

# loc cpu percentages
syslog.syslog(syslog.LOG_INFO, "Cpu(s): %.1f%%us, %.1f%%sy, %.1f%%id, %.1f%%wa" % (logger.cpu['user'], 
    logger.cpu['sys'], logger.cpu['idle'], logger.cpu['wait']))

#log process info
syslog.syslog(syslog.LOG_INFO, "Total Processes: %i" % (logger.numProcs))

for proc in logger.processes:
  syslog.syslog(syslog.LOG_INFO, ("%s: %%CPU %.1f and %%Physical Memory %.1f  (Resident Memory (kb): %i  Proportional Memory (kb): %i " + 
    ";Total Memory (kb): %i) in %i processes with NumberOfOpenFiles: %i") % (proc['name'], proc['pcpu'], 
        proc['pmem'], proc['rss'], proc['pss'], proc['vsize'], proc['procs'], proc['files']))

syslog.closelog()
