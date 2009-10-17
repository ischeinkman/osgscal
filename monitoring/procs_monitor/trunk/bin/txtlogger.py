#!/usr/bin/python
import sys
import time
import os
import getopt

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

from plugin import Plugin
from plugin import XMLFileError

class TxtLogger(Plugin):
  def __init__(self):
    super(TxtLogger, self).__init__()
    self.outdir = None
  
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

logger = TxtLogger()
logger.getArgs(sys.argv[1:])

if logger.xmlPath is None or logger.outdir is None:
  logger.printHelp()
  sys.exit(1)

if logger.helpFlag:
  logger.printHelp()
  sys.exit(0)

if logger.threshold is not None:
  if not logger.withinThresh():
    sys.exit(0)

logger.parseXML()

# check if xml reported collector error and if so do nothing
if logger.error['flag']:
  sys.exit(0)

if not os.path.isdir(logger.outdir):
  os.mkdir(logger.outdir)

for proc in logger.processes:
  name = proc['name']
  if (name != None):
    filename = "%s/%s.log" % (logger.outdir, name)
	
    if not os.path.exists(filename):
      fout = open(filename, 'w')
      fout.write("#%-12s %5s %5s %5s %5s %5s %5s\n" % ('time', 'pcpu', 'pmem', 'rss', 'vsize', 'procs', 'files'))
    else:
      fout = open(filename, 'a')

    fout.write(" %-12i %5.1f %5.1f %5i %5i %5i %5i\n" % (logger.updated['UTC']['unixtime'], proc['pcpu'], 
      proc['pmem'], proc['rss'], proc['vsize'], proc['procs'], proc['files']))
