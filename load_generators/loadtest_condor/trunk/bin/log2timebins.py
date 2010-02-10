#!/bin/env python

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


import sys

def usage():
    print "Usage: log2timebins.py <logfile> <outfile> [<nrchars>]"


class TimeBins:
    def __init__(self,nr_chars=14):
        self.nr_chars=nr_chars
        self.bins={}

    def parseLine(self,line):
        event=line[0:3]
        dt_start=line.find(')')+2
        datetime=line[dt_start:(dt_start+self.nr_chars)]
        if self.bins.has_key(datetime):
            el=self.bins[datetime]
        else:
            el={}

        if el.has_key(event):
            el[event]+=1
        else:
            el[event]=1
        self.bins[datetime]=el
                      


def getBins(logfile,nr_chars=14):
    tbins=TimeBins(nr_chars)

    fd=open(logfile,'r')
    try:
        lines=fd.readlines()
    finally:
        fd.close()

    nr_lines=len(lines)
    linenr=0
    while (linenr<(nr_lines-1)): # if last line is a ..., it is of no use
        if lines[linenr][:3]=='...':
            # next line us the interesting one
            linenr+=1
            tbins.parseLine(lines[linenr])
            linenr+=1
        else:
            linenr+=1
    return tbins.bins

def main(argv):
    if len(argv)<2:
        usage()
        sys.exit(1)

    logfile=argv[0]
    outfile=argv[1]
    if len(argv)>=3:
        bins=getBins(logfile,int(argv[2]))
    else:
        bins=getBins(logfile)

    total_jobs=0
    total_idle=0
    total_globusidle=0
    total_running=0
    fd=open(outfile,"w")
    try:
        bin_keys=bins.keys()
        bin_keys.sort()
        for k in bin_keys:
            bin_el=bins[k]
            submitted=0
            if bin_el.has_key('000'):
                submitted=bin_el['000']
                total_jobs+=submitted
                total_idle+=submitted
            submitted_globus=0
            if bin_el.has_key('027'):
                submitted_globus=bin_el['027']
                total_globusidle+=submitted
            started=0
            if bin_el.has_key('001'):
                started=bin_el['001']
                total_running+=started
                total_idle-=started
                total_globusidle-=started
            terminated=0
            if bin_el.has_key('005'):
                terminated=bin_el['005']
                total_running-=terminated

            fd.write("%s SB: %4i GB: %4i ST: %4i TM: %4i JB: %4i ID: %4i GI: %4i RN: %4i\n"%(k,submitted,submitted_globus,started,terminated,total_jobs,total_idle,total_globusidle,total_running))
    finally:
        fd.close()


if __name__ == '__main__':
    main(sys.argv[1:])
