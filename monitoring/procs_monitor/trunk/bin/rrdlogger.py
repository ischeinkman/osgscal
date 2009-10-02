#!/usr/bin/python
import sys
import os
import time
import rrdtool

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

from plugin import Plugin
from rrdSupport import rrdSupport

if len(sys.argv) <= 2:
  sys.stderr.write("Usage: %s XMLPATH RRDPATH [update threshold in seconds]\n" % sys.argv[0])
  sys.exit(1)

xmlpath = sys.argv[1]
rrdpath = sys.argv[2]
if len(sys.argv) > 3:
  threshold = sys.argv[3]
 
  if not Plugin.withinThresh(xmlpath, threshold):
    sys.exit(0)

plugin = Plugin(xmlpath)

# check if xml reported collector error and if so do nothing
if plugin.error['flag']:
  sys.exit(0)

rrd_obj = rrdSupport()

if not os.path.exists(rrdpath):
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

  rrd_obj.create_rrd_multi(rrdpath, step, rralist, dslist)

vals = {'user': plugin.cpu['user'],
  'sys': plugin.cpu['sys'],
  'idle': plugin.cpu['idle'],
  'wait': plugin.cpu['wait'],
  'load1': plugin.cpu['loadavg']['1'],
  'load5': plugin.cpu['loadavg']['5'],
  'load15': plugin.cpu['loadavg']['15'],
  'procs': plugin.numProcs}
rrd_obj.update_rrd_multi(rrdpath, long(time.time()), vals)

