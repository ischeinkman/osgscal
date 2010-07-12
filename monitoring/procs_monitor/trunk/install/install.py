#!/usr/bin/python

import os
import sys
import shutil
# subprocess module is not in python 2.3
#import subprocess
#from subprocess import Popen

STARTUP_DIR = sys.path[0]
ROOT_DIR = os.path.join(STARTUP_DIR,"../")
NUM_OPTIONS = 5
INTERVAL = 5 # time interval for cron calls
THRESHOLD = 1800 # threshold for plugins

def buildDirs(instdir):
  if not os.path.exists(instdir):
    os.mkdir(instdir)
  if not os.path.exists("%s/etc/" % instdir):
    os.mkdir("%s/etc/" % instdir)
  if not os.path.exists("%s/bin/" % instdir):
    os.mkdir("%s/bin/" % instdir)
  if not os.path.exists("%s/lib/" % instdir):
    os.mkdir("%s/lib/" % instdir)

def updateConfPath(path, instdir):
  config = open(path)
  lines = config.readlines()
  config.close()
  lines = [line.replace("$PROC_MON", os.path.abspath(instdir)) for line in lines]
  config = open(path, 'w')
  config.writelines(lines)
  config.close()

''' options defined as:
  1. syslogger
  2. txtlogger
  3. rrdlogger
  4. ganglogger
  5. zablogger
'''
def populateDirs(instdir, options):
  # copy collector files
  shutil.copyfile("%s/README" % ROOT_DIR,
    "%s/README" % instdir)
  os.chmod("%s/README" % instdir, 0644)

  shutil.copyfile("%s/LICENSE" % ROOT_DIR,
    "%s/LICENSE" % instdir)
  os.chmod("%s/LICENSE" % instdir, 0644)

  shutil.copyfile("%s/bin/proc_collector.pl" % ROOT_DIR,
    "%s/bin/proc_collector.pl" % instdir)
  os.chmod("%s/bin/proc_collector.pl" % instdir, 0755)

  shutil.copyfile("%s/etc/osgmonitoring.conf" % ROOT_DIR,
    "%s/etc/osgmonitoring.conf" % instdir)
  os.chmod("%s/etc/osgmonitoring.conf" % instdir, 0644)
  updateConfPath("%s/etc/osgmonitoring.conf" % instdir, instdir)

  shutil.copyfile("%s/etc/procs_to_watch.conf" % ROOT_DIR,
    "%s/etc/procs_to_watch.conf" % instdir)
  os.chmod("%s/etc/procs_to_watch.conf" % instdir, 0644)

  shutil.copyfile("%s/lib/plugin.py" % ROOT_DIR,
    "%s/lib/plugin.py" % instdir)
  os.chmod("%s/lib/plugin.py" % instdir, 0644)

  shutil.copyfile("%s/lib/configUtils.py" % ROOT_DIR,
    "%s/lib/configUtils.py" % instdir)
  os.chmod("%s/lib/configUtils.py" % instdir, 0644)

  shutil.copyfile("%s/lib/rrdSupport.py" % ROOT_DIR,
    "%s/lib/rrdSupport.py" % instdir)
  os.chmod("%s/lib/rrdSupport.py" % instdir, 0644)

  # will fail if not root
  if 1 in options:
    shutil.copyfile("%s/bin/syslogger.py" % ROOT_DIR,
      "%s/bin/syslogger.py" % instdir)
    os.chmod("%s/bin/syslogger.py" % instdir, 0755)

    shutil.copyfile("%s/etc/osg_log_rotate" % ROOT_DIR,
      "/etc/logrotate.d/osgmonitoring")
    os.chmod("/etc/logrotate.d/osgmonitoring", 0644)

  if 2 in options:
    shutil.copyfile("%s/bin/txtlogger.py" % ROOT_DIR,
      "%s/bin/txtlogger.py" % instdir)
    os.chmod("%s/bin/txtlogger.py" % instdir, 0755)

    shutil.copyfile("%s/etc/txtlogger.conf" % ROOT_DIR,
      "%s/etc/txtlogger.conf" % instdir)
    updateConfPath("%s/etc/txtlogger.conf" % instdir, instdir)
    os.chmod("%s/etc/txtlogger.conf" % instdir, 0644)

  if 3 in options:
    shutil.copyfile("%s/bin/rrdlogger.py" % ROOT_DIR,
      "%s/bin/rrdlogger.py" % instdir)
    os.chmod("%s/bin/rrdlogger.py" % instdir, 0755)

    shutil.copyfile("%s/etc/rrdlogger.conf" % ROOT_DIR,
      "%s/etc/rrdlogger.conf" % instdir)
    updateConfPath("%s/etc/rrdlogger.conf" % instdir, instdir)
    os.chmod("%s/etc/rrdlogger.conf" % instdir, 0644)

  if 4 in options:
    shutil.copyfile("%s/bin/ganglogger.py" % ROOT_DIR,
      "%s/bin/ganglogger.py" % instdir)
    os.chmod("%s/bin/ganglogger.py" % instdir, 0755)

    shutil.copyfile("%s/etc/ganglogger.conf" % ROOT_DIR,
      "%s/etc/ganglogger.conf" % instdir)
    updateConfPath("%s/etc/ganglogger.conf" % instdir, instdir)
    os.chmod("%s/etc/ganglogger.conf" % instdir, 0644)

  if 5 in options:
    shutil.copyfile("%s/bin/zablogger.py" % ROOT_DIR,
      "%s/bin/zablogger.py" % instdir)
    os.chmod("%s/bin/zablogger.py" % instdir, 0755)

    shutil.copyfile("%s/etc/zablogger.conf" % ROOT_DIR,
      "%s/etc/zablogger.conf" % instdir)
    updateConfPath("%s/etc/zablogger.conf" % instdir, instdir)
    os.chmod("%s/etc/zablogger.conf" % instdir, 0644)

def buildCronFile(instdir, options, facility):
  dirpath = os.path.abspath(instdir)
  fout = open("%s/bin/osgmon_cron.sh" % instdir, 'w')
  fout.write("#!/bin/sh\n")
  fout.write("%s/bin/proc_collector.pl %s/etc/osgmonitoring.conf\n"
    % (dirpath, dirpath))
  if 1 in options:
    fout.write("%s/bin/syslogger.py -s %i -t %i %s/osgmonitoring.xml\n"
      % (dirpath, facility, THRESHOLD, dirpath))
  if 2 in options:
    fout.write("%s/bin/txtlogger.py -t %i %s/etc/txtlogger.conf\n"
      % (dirpath, THRESHOLD, dirpath))
  if 3 in options:
    fout.write("%s/bin/rrdlogger.py -t %i %s/etc/rrdlogger.conf\n"
      % (dirpath, THRESHOLD, dirpath))
  if 4 in options:
    fout.write("%s/bin/ganglogger.py -t %i %s/etc/ganglogger.conf\n"
      % (dirpath, THRESHOLD, dirpath))
  if 5 in options:
    fout.write("%s/bin/zablogger.py -t %i %s/etc/zablogger.conf\n"
      % (dirpath, THRESHOLD, dirpath))

  fout.close()
  os.chmod("%s/bin/osgmon_cron.sh" % instdir, 0755)

def updateCron(instdir):
#  cmdin = Popen("crontab -l", shell=True, stdout=subprocess.PIPE).stdout
  cmdin = os.popen("crontab -l", 'r')

  lines = cmdin.readlines()
  cmdin.close()

  inCron = False # assume line isn't in crontab
  dirpath = os.path.abspath(instdir)

  for line in lines:
    if "%s/bin/osgmon_cron.sh" % dirpath in line:
      inCron = True
      break

  if not inCron:
    lines.append("*/%i * * * * %s/bin/osgmon_cron.sh\n"
      % (INTERVAL, dirpath))
#    cmdout = Popen("crontab -", shell=True, stdin=subprocess.PIPE).stdin
    cmdout = os.popen("crontab -", 'w')
    cmdout.writelines(lines)
    cmdout.close()

# will fail if not root
def updateSyslog(facility):
  sysconf = open("/etc/syslog.conf")
  lines = sysconf.readlines()
  sysconf.close()

  inConf = False # assume line is not in syslog
  for line in lines:
    if "local%i" % facility in line and "osgmonitoring" in line:
      inConf = True
      break

  if not inConf:
    sysconf = open("/etc/syslog.conf", 'a')
    sysconf.write("local%i.*                                                /var/log/osgmonitoring.log\n" % facility)
    sysconf.close()
    print "Restarting syslog..."
    os.system("/etc/init.d/syslog restart")

###
#
# Main
#
##


print "Please type directory name to install procs_monitor and hit <ENTER>:",

instdir = raw_input()

while True:
  valid = True # assume valid input until checked
  print '''
Please type the numbers of plugins to install separated by commas,
then hit <ENTER>.

  1. syslogger ***must be root user to install syslogger plugin***
  2. text logger
  3. rrd logger
  4. ganglia logger
  5. zabbix logger
  '''
  input = raw_input()
  values = input.split(',') # split values by comma
  values = [value.strip() for value in values] # take out whitespace

  options = []

  for value in values:
    # skip if nothing left
    if value == '':
      continue

    # try to convert to number
    try:
      num = int(value)
      # make sure number is valid
      if num < 0 or num > NUM_OPTIONS:
        print "\"%s\" is not a valid option. Press <ENTER> to try again." % value
        raw_input()
        valid = False
        break
      
      if num not in options:
        options.append(num)

    # if not a number, try again
    except ValueError:
      print "\"%s\" is not a valid option. Press <ENTER> to try again." % value
      raw_input()
      valid = False
      break

  if valid:
    # if chose syslogger get facility number
    facility = -1 # -1 if syslogger not chosen
    if 1 in options:
      while True:
        print '''Please type the number of the local syslog facility [0-7] you would like
to use, then hit <Enter>:''',
        facility = raw_input()

        try:
          facility = int(facility)
          if facility >= 0 and facility < 8:
            break

          print "\"%i\" is not a valid option. Press <ENTER> to try again." % facility
          raw_input()
          
        except ValueError:
          print "\"%s\" is not a valid option. Press <ENTER> to try again." % facility
          raw_input()

    buildDirs(instdir)
    populateDirs(instdir, options)
    buildCronFile(instdir, options, facility)
    updateCron(instdir)

    # if installed syslogger update syslog
    if 1 in options:
      updateSyslog(facility)

    print "Installation complete!"
    break
