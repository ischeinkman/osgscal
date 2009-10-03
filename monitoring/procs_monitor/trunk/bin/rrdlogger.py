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

class RRDLogger(Plugin):
  def __init__(self):
    super(RRDLogger, self).__init__()
    self.rrdpath = None

  def getArgs(self, argv):
    super(RRDLogger, self).getArgs(argv)
    optlist, args = getopt.getopt(argv, self.options)
    
    if len(args) > 1:
      self.rrdpath = args[1]

  def printHelp(self):
    print '''\
Usage: %s [options] XMLPATH RRDPATH
  options:
    -h        show this help page
    -t n      threshold n seconds long.  xml file older than threshold
              will not be logged.  disabled by default (always logs)''' % sys.argv[0]  

logger = RRDLogger()
logger.getArgs(sys.argv[1:])

if logger.path is None or logger.rrdpath is None:
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

rrd_obj = rrdSupport()

if not os.path.exists(logger.rrdpath):
  step = 300
  heartbeat = 1800
  rows = 740

  rralist = [('AVERAGE',0.8,1,rows),
             ('AVERAGE',0.92,12,rows),
             ('AVERAGE',0.98,144,rows)]

  dslist = [('user','GAUGE',60,'0','100'),
    ('sys','GAUGE',60,'0','100'),
    ('idle','GAUGE',60,'0','100'),
    ('wait','GAUGE',60,'0','100'),
    ('load1','GAUGE',60,'0','U'),
    ('load5','GAUGE',60,'0','U'),
    ('load15','GAUGE',60,'0','U'),
    ('procs','GAUGE',60,'0','U')]

  rrd_obj.create_rrd_multi(logger.rrdpath, step, rralist, dslist)

vals = {'user': logger.cpu['user'],
  'sys': logger.cpu['sys'],
  'idle': logger.cpu['idle'],
  'wait': logger.cpu['wait'],
  'load1': logger.cpu['loadavg']['1'],
  'load5': logger.cpu['loadavg']['5'],
  'load15': logger.cpu['loadavg']['15'],
  'procs': logger.numProcs}
rrd_obj.update_rrd_multi(logger.rrdpath, long(time.time()), vals)

