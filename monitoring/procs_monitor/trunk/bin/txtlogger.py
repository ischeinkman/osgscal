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
import gzip
import pickle

# add lib folder to import path
STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))
sys.path.append("/usr/local/lib/procs_monitor")

from plugin import Plugin
from plugin import XMLFileError
import configUtils

#constants
timeConv = {'daily': 86400,
            'weekly': 604800,
            'monthly': 2592000}

class TxtLogger(Plugin):
  def __init__(self):
    super(TxtLogger, self).__init__()
    self.outdir = None # location to write log files
    self.count = None
  
  def getArgs(self, argv):
    super(TxtLogger, self).getArgs(argv)
    optlist, args = getopt.getopt(argv, self.options)
    
    if len(args) > 0:
#      self.xmlPath = args[0]
#      self.outdir = args[1]
      self.confPath = args[0]

  def printHelp(self):
    print '''\
Usage: %s [options] XMLPATH OUTDIR
  options:
    -h        show this help page
    -t n      threshold n seconds long.  xml file older than threshold
              will not be logged.  disabled by default (always logs)''' % sys.argv[0]

  def parseConf(self):
    confDict = {'xmlpath' : None,
                'outdir' : None,
                'interval' : None,
                'count' : None}

    # parse values from config file, try default values if not found 
    configUtils.parse(self.confPath, confDict)
    
    if confDict['xmlpath'] is None:
      self.xmlPath = os.path.join(STARTUP_DIR,"../osgmonitoring.xml")
    else:
      self.xmlPath = confDict['xmlpath'] 
   
    if confDict['outdir'] is None:
      self.outdir = os.path.join(STARTUP_DIR,"../logs")
    else:
      self.outdir = confDict['outdir'] 

    if confDict['interval'] is None:
      self.interval = timeConv['daily']
    else:
      self.interval = timeConv[confDict['interval']]

    if confDict['count'] is None:
      self.count = 7
    else:
      self.count = int(confDict['count']) # throw exception?

  def rotate(self, filename):
    max = 0

    if os.path.exists("%s.1" % filename): 
      max += 1   
 
    while True:
      if not os.path.exists("%s.%i.gz" % (filename, max + 1)): 
        break 
    
      max += 1 

    if (max == logger.count):
      os.unlink("%s.%i.gz" % (filename, logger.count)) # throws exception

      max -= 1

    if (max > 1):
      for i in range(max, 1, -1):
        os.rename("%s.%i.gz" % (filename, i), "%s.%i.gz" % (filename, i + 1))

    if (max >= 1):
      fin = open("%s.1" % filename, 'rb')
      fout = gzip.open("%s.2.gz" % filename, 'wb')
      fout.writelines(fin)
      fout.close()
      fin.close()
       
    os.rename(filename, "%s.1" % filename)

##
#
# Main
#
##

# create plugin and get command line arguments
logger = TxtLogger()
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

if not os.path.isdir(logger.outdir):
  os.mkdir(logger.outdir)

filename = "%s/cpu.log" % logger.outdir

# first write log for machine
if not os.path.exists(filename):
  fout = open(filename, 'w')
  fout.write("#%-12s %6s %6s %6s %6s %6s %6s %6s %6s\n" % ('time', 'usr', 'sys',
    'idle', 'wait', 'load1', 'load5', 'load15', 'procs'))

  rotdict = {}

  rotdict['cpu'] = logger.updated['UTC']['unixtime']
  rout = open("%s/.rotated" % logger.outdir, 'wb')
  pickle.dump(rotdict, rout)
  rout.close()

# otherwise check if time to rotate
else:
  rin = open("%s/.rotated" % logger.outdir, 'rb')
  rotdict = pickle.load(rin)
  rin.close()
  
  if logger.updated['UTC']['unixtime'] - rotdict['cpu'] > logger.interval:
    logger.rotate(filename)

    rout = open("%s/.rotated" % logger.outdir, 'wb')
    rotdict['cpu'] = logger.updated['UTC']['unixtime']
    pickle.dump(rotdict, rout)
    rout.close()
    fout = open(filename, 'w')
    fout.write("#%-12s %6s %6s %6s %6s %6s %6s %6s %6s\n" % (
        'time', 'usr', 'sys', 'idle', 'wait', 'load1', 'load5', 'load15',
        'procs'))
  else:
    fout = open(filename, 'a')

#(check compare interval with time when x.1 is created)
'''elif (logger.updated['UTC']['unixtime'] - os.path.getmtime("%s/.rotated"
  % logger.outdir) > interval['daily']):
  logger.rotate(filename) 

  # save timestamp of rotation
  open("%s/.rotated" % logger.outdir, 'w').close()
  fout = open(filename, 'w')
  fout.write("#%-12s %6s %6s %6s %6s %6s %6s %6s %6s\n" % ('time', 'usr', 'sys',
    'idle', 'wait', 'load1', 'load5', 'load15', 'procs'))

# finally just append to prev
else:
  fout = open(filename, 'a')
'''
fout.write(" %-12i %6.1f %6.1f %6.1f %6.1f %6.1f %6.1f %6.1f %6i\n" %
  (logger.updated['UTC']['unixtime'], logger.cpu['user'], logger.cpu['sys'], 
   logger.cpu['idle'], logger.cpu['wait'], logger.cpu['loadavg']['1'],
   logger.cpu['loadavg']['5'], logger.cpu['loadavg']['15'], logger.numProcs))

fout.close()

# traverse process fields and update log files
for proc in logger.processes:
  name = proc['name']
  if (name != None):
    filename = "%s/%s.log" % (logger.outdir, name)

    # create log file if not already there
    if not os.path.exists(filename):
      fout = open(filename, 'w')
      fout.write("#%-12s %5s %5s %5s %5s %5s %5s %5s\n" % ('time', 'pcpu', 'pmem',
        'rss', 'pss', 'vsize', 'procs', 'files'))
      
      rin = open("%s/.rotated" % logger.outdir, 'rb')
      rotdict = pickle.load(rin)

      rin.close()

      rotdict['%s' % proc['name']] = logger.updated['UTC']['unixtime']
      rotdict['cpu'] = logger.updated['UTC']['unixtime']
      rout = open("%s/.rotated" % logger.outdir, 'wb')
      pickle.dump(rotdict, rout)
      rout.close()

    else:
      if (logger.updated['UTC']['unixtime'] - rotdict['%s' % proc['name']]
          > logger.interval):
        logger.rotate(filename)

        rout = open("%s/.rotated" % logger.outdir, 'wb')
        rotdict['%s' % proc['name']] = logger.updated['UTC']['unixtime']
        pickle.dump(rotdict, rout)
        rout.close()
        fout = open(filename, 'w')
        fout.write("#%-12s %5s %5s %5s %5s %5s %5s %5s\n" % (
            'time', 'pcpu', 'pmem', 'rss', 'pss', 'vsize', 'procs', 'files'))

      else:
        fout = open(filename, 'a')

    fout.write(" %-12i %5.1f %5.1f %5i %5i %5i %5i %5i\n" % 
      (logger.updated['UTC']['unixtime'], proc['pcpu'], proc['pmem'], proc['rss'],
        proc['pss'], proc['vsize'], proc['procs'], proc['files']))

    fout.close()
