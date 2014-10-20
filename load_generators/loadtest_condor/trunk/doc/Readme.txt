Tools included in the package
=============================

The main tool in this package is
loadtest_condor.sh

A support tool named
log2timebins.py
is also included.

But are executable.

loadtest_condor.sh
==================

This script submits a bunch of batch jobs with the intention of putting
load on the target resource. Condor is used to handle the batch jobs.
Any Condor supported resource should work, but the tool has only been
tested against preWS Globus (GT2) resources.

Usage
-----
loadtest_condor.sh [options]

Where options is any combination of:
  -type <universe> [opts] (REQUIRED)
        grid gt2 <resource_name> : Submit Grid GT2 jobs
	grid condor schedd.example.com machine1.example.com : Submit HTCondor C jobs
        vanilla                  : Submit vanilla jobs
        local                    : Submit local jobs
  -req[uirements] : Requirements of the job
                    This maps to RSL for GT2 and REQUIREMENTS for vanilla jobs
  -end fixed|sync|int[erval] <val> (REQUIRED)
       fixed <seconds>    : Each job will sleep a fixed amount of seconds
       sync <unix_time>   : All jobs will try to end exactly at the same time
       interval <seconds> : All jobs will end at the next multiple of seconds
  -jobs      <count> : How many jobs to submit, default=10
  -clus[ter] <count> : How many jobs should I group per cluster, default=1000
  -maxidle <count>   : How many idle jobs are allowed (delay submission else), default=-1 (disabled)
  -maxjobs <count>   : How many jobs are allowed in the queue (delay submission else), default=-1 (disabled)
  -in[file]  <file name> <file size> : Create an input file (default=no file)
  -out[file] <file name> <file size> : Create an output file (default=no file)
  -workdir <path>     : Where will the work directory be created, default=current dir

Output and log files
--------------------
The tool will create a directory in your working directory with the date and time of the launching.

The directory will contain:
- all information of the run;
- one subdiretory per each cluster at most with the log/error/output files for these jobs
- a general log file (condor_submit.log) and a "control file" (control_file.log) (contains the cluster condor id)

Example
-------
loadtest_condor.sh -type grid gt2 osg-gw-5.t2.ucsd.edu/jobmanager-condor \
                   -req "(condor_submit=('+SleepSlot' 'TRUE'))" \
                   -end fixed 1800 -jobs 5000 -cluster 100 \
                   -in infile 100 -out outfile 123

log2timebins.py
===============

This tool summarizes a Condor job log file, grouping job state transitions
in a specific time period.

Usage
-----
log2timebins.py infile outfile chars

Output
------

The output file will contain a line per time period.
Each line will contain the count of jobs submitted to the local schedd (SB),
the count of jobs submitted to the remote Globus resource (GB),
the count of jobs started (ST) and jobs ended (TM).

Here are few example lines:
08/30 05 SB: 2000 GB:  715 ST:  718 TM:  286
08/30 06 SB: 1432 GB:  313 ST:  346 TM:  474
08/30 07 SB:    0 GB:   10 ST:    8 TM:  667
08/30 08 SB:    0 GB:    0 ST:    0 TM:  683

Example
-------
To get a per-hour summary:
log2timebins.py job.log job.log.hr 8

To get a summary for every 10 minutes:
log2timebins.py job.log job.log.tm 10
