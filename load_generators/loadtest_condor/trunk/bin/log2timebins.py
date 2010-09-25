#!/usr/bin/env python

#
# Description:
#  This program parses a Condor-G job log file and
#  creates a second file containing a timeline of
#  counts regarding job submissions, globus submissions,
#  job starts and job terminations
# 
# Arguments:
#   (1) Condor-G job log file
#   (2) Output summary file
#   (3) optional number of date characters
#       default is 14 == 1s binning
#       other useful values: 13 == 10s binning
#                            11 ==  1m binning
#                            10 == 10m binning
#                             8 ==  1h binning
#
# Author:
#   Igor Sfiligoi <isfiligoi@ucsd.edu>
#


import sys,os
STARTUP_DIR=sys.path[0]
sys.path.append(os.path.join(STARTUP_DIR,"../lib"))
import condorLogParser

def usage():
    print "Usage: log2timebins.py [-rates|-abs|-all] <logfile> [<nrchars>]"


class TimeBinEl:
    def __init__(self,jobs):
        self.submitted=0
        self.grid_submitted=0
        self.started=0
        self.terminated=0
        self.aborted=0

        # get abs values of the current job dictionary
        self.total_jobs=0
        self.total_idle=0
        self.total_grid_idle=0
        self.total_running=0

        for j in jobs:
            self.total_jobs+=1
            el=jobs[j]
            if el[1:]=='00':
                self.total_idle+=1
            elif el[1:]=='01':
                self.total_running+=1
            elif el[1:]=='27':
                self.total_grid_idle+=1
            elif el[1:]=='06':
                self.total_jobs-=1 # was not cleaned up yet

        return

    def new_job(self):
        self.submitted+=1
        self.total_jobs+=1
        self.total_idle+=1

    def job_grid_submitted(self):
        self.grid_submitted+=1
        self.total_grid_idle+=1

    def job_started(self):
        self.started+=1
        self.total_idle-=1
        self.total_running+=1
        if self.total_grid_idle>0: # assume all jobs are either grid or not
            self.total_grid_idle-=1

    def job_terminated(self):
        self.terminated+=1
        self.total_running-=1
        self.total_jobs-=1
        if self.total_grid_idle>0: # assume all jobs are either grid or not
            self.total_grid_idle-=1

    def job_aborted(self):
        self.aborted+=1
        self.total_running-=1
        self.total_idle+=1
                

class TimeBins:
    def __init__(self,nr_chars=14):
        self.nr_chars=nr_chars
        self.jobs={}
        self.bins={}

    def log_callback(self,new_status_str,timestamp_str,job_str):
        datetime=timestamp_str[:self.nr_chars]
        if self.bins.has_key(datetime):
            el=self.bins[datetime]
        else:
            el=TimeBinEl(self.jobs)
        self.bins[datetime]=el

        if not self.jobs.has_key(job_str):
            self.jobs[job_str]=new_status_str
            el.new_job()
            return
            
        old_status_str=self.jobs[job_str]
        self.jobs[job_str]=new_status_str

        if new_status_str[1:]==old_status_str[1:]:
            return # not interested in partial changes

        if new_status_str[1:]=='05':
            el.job_terminated()
            del self.jobs[job_str]
        elif new_status_str[1:]=='01':
            el.job_started()
        else:
            el.job_aborted()
        return
    
def callback(tbins,new_status_str,timestamp_str,job_str):
    tbins.log_callback(new_status_str,timestamp_str,job_str)

def getBins(logfile,nr_chars=14):
    tbins=TimeBins(nr_chars)

    condorLogParser.parseSubmitLogFastRawCallback(logfile,lambda new_status_str,timestamp_str,job_str:callback(tbins,new_status_str,timestamp_str,job_str))

    return tbins.bins

def main(argv):
    if len(argv)<1:
        usage()
        sys.exit(1)

    rates=True
    abs=True
    if argv[0]=='-rates':
        abs=False
        argv=argv[1:]
    elif argv[0]=='-abs':
        rates=False
        argv=argv[1:]
    elif argv[0]=='-all':
        # default
        argv=argv[1:]
        

    logfile=argv[0]
    if len(argv)>=2:
        bins=getBins(logfile,int(argv[1]))
    else:
        bins=getBins(logfile)


    bin_keys=bins.keys()
    bin_keys.sort()
    for k in bin_keys:
        bin_el=bins[k]

        if abs==False: # rates only
            print "%s SB: %4i GB: %4i ST: %4i TM: %4i AB: %4i"%(k,bin_el.submitted,bin_el.grid_submitted,bin_el.started,bin_el.terminated,bin_el.aborted)
        elif rates==False: # abs only
            print "%s JB: %4i ID: %4i GI: %4i RN: %4i"%(k,bin_el.total_jobs,bin_el.total_idle,0,bin_el.total_running)
        else: # all
            print "%s SB: %4i GB: %4i ST: %4i TM: %4i JB: %4i ID: %4i GI: %4i RN: %4i AB: %4i"%(k,bin_el.submitted,bin_el.grid_submitted,bin_el.started,bin_el.terminated,bin_el.total_jobs,bin_el.total_idle,bin_el.total_grid_idle,bin_el.total_running, bin_el.aborted)


if __name__ == '__main__':
    main(sys.argv[1:])
