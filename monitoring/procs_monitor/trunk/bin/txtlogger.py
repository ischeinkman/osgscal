#!/usr/bin/python
import sys
import time
import os

STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))

from osgmonplugin import Plugin
from osgmonplugin import XMLFileError

# this script requires path of xml file to be parsed as input argument
if len(sys.argv) <= 2:
  sys.stderr.write("Usage: %s XMLPATH OUTDIR [update threshold in seconds]\n" % sys.argv[0])
  sys.exit(1)

xmlpath = sys.argv[1]
outdir = sys.argv[2]
if len(sys.argv) > 3:
  threshold = sys.argv[3]
 
  if not Plugin.withinThresh(xmlpath, threshold):
    sys.exit(0)

plugin = Plugin(xmlpath)

# check if xml reported collector error and if so do nothing
if plugin.error['flag']:
  sys.exit(0)

if not os.path.isdir(outdir):
  os.mkdir(outdir)

for proc in plugin.processes:
  name = proc['name']
  if (name != None):
    filename = "%s/%s.log" % (outdir, name)
	
    if not os.path.exists(filename):
      fout = open(filename, 'w')
      fout.write("#%-12s %5s %5s %5s %5s %5s %5s\n" % ('time', 'pcpu', 'pmem', 'rss', 'vsize', 'procs', 'files'))
    else:
      fout = open(filename, 'a')

    fout.write(" %-12i %5.1f %5.1f %5i %5i %5i %5i\n" % (plugin.updated['UTC']['unixtime'], proc['pcpu'], 
      proc['pmem'], proc['rss'], proc['vsize'], proc['procs'], proc['files']))
		
