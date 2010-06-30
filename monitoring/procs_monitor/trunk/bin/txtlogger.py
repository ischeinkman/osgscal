#!/usr/bin/python
#
#  txtlogger.py
#
#  Description:
#    Creates and updates log files for each process monitored.     
#
#  Usage:
#    txtlogger.py [options] XMLPATH OUTDIR
#
#  Author:
#    Jeff Dost (Sept 2009)
#
##

import sys
import time
import os
import getopt

# add lib folder to import path
STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))
sys.path.append("/usr/local/lib/procs_monitor")

from plugin import Plugin
from plugin import XMLFileError

class TxtLogger(Plugin):
  def __init__(self):
    super(TxtLogger, self).__init__()
    self.outdir = None # location to write log files
  
  def getArgs(self, argv):
    super(TxtLogger, self).getArgs(argv)
    optlist, args = getopt.getopt(argv, self.options)
    
    if len(args) > 1:
      self.xmlPath = args[0]
      self.outdir = args[1]

  def printHelp(self):
    print '''\
Usage: %s [options] XMLPATH OUTDIR
  options:
    -h        show this help page
    -t n      threshold n seconds long.  xml file older than threshold
              will not be logged.  disabled by default (always logs)''' % sys.argv[0]

##
#
# Main
#
##

# create plugin and get command line arguments
logger = TxtLogger()
logger.getArgs(sys.argv[1:])

if logger.xmlPath is None or logger.outdir is None:
  logger.printHelp()
  sys.exit(1)

if logger.helpFlag:
  logger.printHelp()
  sys.exit(0)

# exit if threshold was used and xml file is stale
if logger.threshold is not None:
  if not logger.withinThresh():
    sys.exit(0)

logger.parseXML()

# check if xml reported collector error and if so do nothing
if logger.error['flag']:
  sys.exit(0)

if not os.path.isdir(logger.outdir):
  os.mkdir(logger.outdir)

# traverse process fields and update log files
for proc in logger.processes:
  name = proc['name']
  if (name != None):
    filename = "%s/%s.log" % (logger.outdir, name)
	
    # create log file if not already there
    if not os.path.exists(filename):
      fout = open(filename, 'w')
      fout.write("#%-12s %5s %5s %5s %5s %5s %5s %5s\n" % ('time', 'pcpu', 'pmem', 'rss', 'pss', 'vsize', 'procs', 'files'))
    else:
      fout = open(filename, 'a')

    fout.write(" %-12i %5.1f %5.1f %5i %5i %5i %5i %5i\n" % (logger.updated['UTC']['unixtime'], proc['pcpu'], 
      proc['pmem'], proc['rss'], proc['pss'], proc['vsize'], proc['procs'], proc['files']))
