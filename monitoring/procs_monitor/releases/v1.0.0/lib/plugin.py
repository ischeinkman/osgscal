#!/usr/bin/python

# this will have to be changed to xml.etree.ElementTree if python is 2.5 or higher
import elementtree.ElementTree as ET
#import xml.etree.ElementTree as ET
import sys
import time
import os
import getopt

class XMLFileError(Exception):
  pass

class Plugin(object):
  def __init__(self):
    self.options = 'ht:'
    self.xmlPath = None
    self.threshold = None
    self.helpFlag = False
    self.confPath = None  
    # values to be parsed from xml
    self.updated = None
    self.error = None
    self.cpu = None
    self.numProcs = None
    self.processes = None

  def getArgs(self, argv):
    optlist, args = getopt.getopt(argv, self.options)
    for opt in optlist:
      if opt[0] == '-h':
        self.helpFlag = True
      elif opt[0] == '-t':
        try:
          self.threshold = float(opt[1])
        except ValueError:
          raise ValueError, "Invalid argument for %s:%s" % (opt[0], opt[1])

# this assumed a plugin would always have XMLPATH as first argument
# however now plugins might have a config file as it's only argument instead
# so set this in inherited plugins
#    if len(args) > 0:
#      self.xmlPath = args[0]

  def withinThresh(self):
    return time.time() - os.path.getmtime(self.xmlPath) <= float(self.threshold)

  # ET.parse may raise Exception
  def parseXML(self):
    doc = ET.parse(self.xmlPath)
    
    self.updated = getUpdated(doc)
    self.error = getError(doc)
    self.cpu = getCpu(doc)
    self.numProcs = int(doc.findtext('./processes/procs_tot'))
    self.processes = getProcs(doc)
    
  def printHelp(self):
    pass

  def parseConf(self):
    pass

'''class Plugin(object):
  # ET.parse may raise Exception
  def __init__(self, path):
    
    doc = ET.parse(path)
    
    self.updated = getUpdated(doc)
    self.error = getError(doc)
    self.cpu = getCpu(doc)
    self.numProcs = int(doc.findtext('./processes/procs_tot'))
    self.processes = getProcs(doc)

  # may raise OSError
  @staticmethod
  def withinThresh(path, threshold):
    return time.time() - os.path.getmtime(path) <= float(threshold)
'''
####
#
# getElementDict:  
#   finds all elements with the same xml tag and returns a
#   dictionary using XML attribute values as its keys
#
# Arguments:
#   path - the tag or xml path search term of the same format as ElementTree.find
#   attrib - the XML attribute to be used as dictionary key
#
####
def getElementDict(element, path, attrib):
  # get array of all matching elements
  elements = element.findall(path) 

  # traverse array and build dictionary
  elementDict = {}
  for el in elements:
    elementDict[el.get(attrib)] = el
  return elementDict

def getUpdated(root):
  tzones = getElementDict(root, './updated/timezone', 'name')
  try:
    return {'Local': {'ISO8601': tzones['Local'].get('ISO8601'),
                      'RFC2822': tzones['Local'].get('RFC2822'),
                      'human': tzones['Local'].get('human')},
            'UTC': {'ISO8601': tzones['UTC'].get('ISO8601'),
                    'RFC2822': tzones['UTC'].get('RFC2822'),
                    'unixtime': long(tzones['UTC'].get('unixtime'))}}
  except KeyError:
    raise XMLFileError, "unable to parse update time"

def getError(root):
  errflag = root.findtext('./error/flag')

  if errflag != 'true' and errflag != 'false':
    raise XMLFileError, "error flag element text must be 'true' or 'false'"

  error = {}
  if errflag == 'true':
    error['flag'] = True
  else:
    error['flag'] = False
  error['message'] = root.findtext('./error/message')

  return error

#could raise KeyError
def getCpu(root):
  loads = getElementDict(root, './cpu/loadavg', 'min')

  try:
    return {'loadavg': {'1': float(loads['1'].text),
                       '5': float(loads['5'].text),
                       '15': float(loads['15'].text)},
            'user': float(root.findtext('./cpu/user')),
            'sys': float(root.findtext('./cpu/sys')),  
            'idle': float(root.findtext('./cpu/idle')),
            'wait': float(root.findtext('./cpu/wait'))}
  except KeyError:
    raise XMLFileError, "unable to parse load averages"

# could raise AttributeError
def getProcs(root):
  tmpArr = root.findall('./processes/process')

  procs = []

  try:
    for proc in tmpArr:
      tmpDict = {'name': proc.get('name'), 
                 'pcpu': float(proc.findtext('./pcpu')),
                 'pmem': float(proc.findtext('./pmem')),
                 'vsize': int(proc.findtext('./vsize')),
                 'rss': int(proc.findtext('./rss')),
                 'procs': int(proc.findtext('./procs')),
                 'files': int(proc.findtext('./files'))}

      procs.append(tmpDict)
  except AttributeError:
    raise XMLFileError, "unable to parse process info"
  
  return procs

if __name__ == '__main__':
  plugin = Plugin()
  plugin.getArgs(sys.argv[1:])
  plugin.parseXML()
  print plugin.updated

    



	
