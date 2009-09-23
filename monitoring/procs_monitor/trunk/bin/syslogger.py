#!/usr/bin/python
import sys

import syslog
#import time
import os

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

from osgmonplugin import Plugin
from osgmonplugin import XMLFileError

# this script requires path of xml file to be parsed as input argument
if len(sys.argv) <= 1:
  sys.stderr.write("Usage: %s PATHNAME [update threshold in seconds]\n" % sys.argv[0])
  sys.exit(1)

# use local0 for now, but change later to read this from config
syslog.openlog('osgmonitor', syslog.LOG_PID, syslog.LOG_LOCAL0)

path = sys.argv[1]

if len(sys.argv) > 2:
  threshold = sys.argv[2]
  try:
    if not Plugin.withinThresh(path, threshold):
      sys.exit(0)
  except OSError, e:
    syslog.syslog(syslog.LOG_ERR, "Could not access XML: %s" % str(e))
    syslog.closelog()
    sys.exit(1)

# start logging and open xml
syslog.syslog(syslog.LOG_INFO, "Reading XML...")
 
try:
  plugin = Plugin(path)
except Exception, e:
  syslog.syslog(syslog.LOG_ERR, "Failed parsing XML: %s" % str(e))
  syslog.closelog()
  sys.exit(1)

# log last xml update time
syslog.syslog(syslog.LOG_INFO, "XML last updated %s" % plugin.updated['Local']['human'])

# check if xml reported collector error and if so log it and quit
if plugin.error['flag']:
  syslog.syslog(syslog.LOG_ERR, "Collector Error: %s" % plugin.error['message'])
  syslog.closelog()
  sys.exit(0)

# otherwise log everything else

# log load averages
syslog.syslog(syslog.LOG_INFO, "Load Average: %.2f, %.2f, %.2f" % (plugin.cpu['loadavg']['1'], 
  plugin.cpu['loadavg']['15'], plugin.cpu['loadavg']['15']))

# loc cpu percentages
syslog.syslog(syslog.LOG_INFO, "Cpu(s): %.1f%%us, %.1f%%sy, %.1f%%id, %.1f%%wa" % (plugin.cpu['user'], 
    plugin.cpu['sys'], plugin.cpu['idle'], plugin.cpu['wait']))

#log process info
syslog.syslog(syslog.LOG_INFO, "Total Processes: %i" % (plugin.numProcs))

for proc in plugin.processes:
  syslog.syslog(syslog.LOG_INFO, ("%s: %%CPU %.1f and %%Physical Memory %.1f  (Resident Memory (kb): %i  " + 
    ";Total Memory (kb): %i) in %i processes with NumberOfOpenFiles: %i") % (proc['name'], proc['pcpu'], 
        proc['pmem'], proc['rss'], proc['vsize'], proc['procs'], proc['files']))

syslog.closelog()
