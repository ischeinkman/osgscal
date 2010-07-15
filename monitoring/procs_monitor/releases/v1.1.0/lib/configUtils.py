#!/usr/bin/python
import re

def parse(file, vardict):
  config = open(file)

  lines = [line for line in config]

  config.close()

  for line in lines:
    # remove comments
    line = re.sub('#.*', '', line)
    
    # if line is blank, skip
    if re.match('^[\s]*$', line) is not None:
      continue

    opands = line.split('=')
    if len(opands) == 1:
      raise IOError, "Error parsing %s: syntax error" % file
    opands = [opand.strip() for opand in opands]


    if opands[0] in vardict:
      vardict[opands[0]] = opands[1]
    else:
      raise IOError, "Error parsing %s: invalid argument: %s" %(file, opands[0])

if __name__ == '__main__':
  vardict = {'xmlpath' : None, 
          'cpu_rrd' : None, 
          'proc_rrd_dir' : None}

  parse('/root/osgmonitoring/etc/rrdlogger.conf', vardict)
  for key in vardict:
      print "arg: %s, val: %s" % (key, vardict[key])
