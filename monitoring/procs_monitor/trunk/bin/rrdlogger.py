#!/usr/bin/python
import sys
import os
import time
import rrdtool
import getopt

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

from plugin import Plugin
from rrdSupport import rrdSupport
import configUtils

class RRDLogger(Plugin):
  def __init__(self):
    super(RRDLogger, self).__init__()
    self.cpuRRD = None
    self.procRRDDir = None

  def getArgs(self, argv):
    super(RRDLogger, self).getArgs(argv)
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
                'cpu_rrd' : None,
                'proc_rrd_dir' : None}
    
    configUtils.parse(self.confPath, confDict)

    if confDict['xmlpath'] is None:
      self.xmlPath = os.path.join(STARTUP_DIR,"../etc/osgmonitoring.xml")
    else:
      self.xmlPath = confDict['xmlpath']
    
    if confDict['cpu_rrd'] is None:
      self.cpuRRD = os.path.join(STARTUP_DIR,"../etc/cpu.rrd")
    else:
      self.cpuRRD = confDict['cpu_rrd']

    if confDict['proc_rrd_dir'] is None:
      self.procRRDDir = os.path.join(STARTUP_DIR,"../etc/procrrds")
    else:
      self.procRRDDir = confDict['proc_rrd_dir']

logger = RRDLogger()
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

rrd_obj = rrdSupport()

step = 300
#step = 30
heartbeat = 1800
rows = 740
#rows = 20
rralist = [('AVERAGE',0.8,1,rows),
           ('AVERAGE',0.92,12,rows),
           ('AVERAGE',0.98,144,rows)]

# write cpu rrdb
if not os.path.exists(logger.cpuRRD):

  dslist = [('user','GAUGE',heartbeat,'0','100'),
    ('sys','GAUGE',heartbeat,'0','100'),
    ('idle','GAUGE',heartbeat,'0','100'),
    ('wait','GAUGE',heartbeat,'0','100'),
    ('load1','GAUGE',heartbeat,'0','U'),
    ('load5','GAUGE',heartbeat,'0','U'),
    ('load15','GAUGE',heartbeat,'0','U'),
    ('procs','GAUGE',heartbeat,'0','U')]

  rrd_obj.create_rrd_multi(logger.cpuRRD, step, rralist, dslist)

vals = {'user': logger.cpu['user'],
  'sys': logger.cpu['sys'],
  'idle': logger.cpu['idle'],
  'wait': logger.cpu['wait'],
  'load1': logger.cpu['loadavg']['1'],
  'load5': logger.cpu['loadavg']['5'],
  'load15': logger.cpu['loadavg']['15'],
  'procs': logger.numProcs}
rrd_obj.update_rrd_multi(logger.cpuRRD, long(time.time()), vals)

# write proc rrdb's
if not os.path.isdir(logger.procRRDDir):
  os.mkdir(logger.procRRDDir)

for proc in logger.processes:
  name = proc['name']

  if (name != None):
    rrdname = "%s/%s.rrd" % (logger.procRRDDir, name)

    if not os.path.exists(rrdname):
      dslist = [('pcpu','GAUGE',heartbeat,'0','100'),
        ('pmem','GAUGE',heartbeat,'0','100'),
        ('vsize','GAUGE',heartbeat,'0','U'),
        ('rss','GAUGE',heartbeat,'0','U'),
        ('procs','GAUGE',heartbeat,'0','U'),
        ('files','GAUGE',heartbeat,'0','U')]

      rrd_obj.create_rrd_multi(rrdname, step, rralist, dslist)

    vals = {'pcpu': proc['pcpu'],
      'pmem': proc['pmem'],
      'vsize': proc['vsize'],
      'rss': proc['rss'],
      'procs': proc['procs'],
      'files': proc['files']}

    rrd_obj.update_rrd_multi(rrdname, long(time.time()), vals)
