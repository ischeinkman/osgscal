#!/bin/bash 

#
# Description:
#  This program submits a large number of condor jobs
#  to test the scalability of the system
#
# Arguments:
#  See Usage
#
#
# Authors:
#  Toni Coarasa <toni@coarasa.net>
#  Igor Sfiligoi <isfiligoi@ucsd.edu>
#

#
# Exit codes:
#  0 - success
#  1 - argumnent error
#  2 - system error
#

ScriptFileName=`basename $0`
# Where is it?
DIRECTORY=`echo "$0"|sed "s/${ScriptFileName}//"`
#echo `pwd`

LIBEXEC="$DIRECTORY/../libexec"
LIBDATA="$DIRECTORY/../libdata"

function Usage
{
   echo "Usage:"
   echo "  ${ScriptFileName} [options]"
   echo "Where options is any combination of:"
   echo "  -type <universe> [opts] (REQUIRED)"
   echo "        grid gt2 <resource_name> : Submit Grid GT2 jobs"
   echo "        grid cream <url> <batch> <queue> : Submit Grid CREAM jobs"
   echo "        vanilla                  : Submit vanilla jobs"
   echo "        local                    : Submit local jobs"
   echo "  -req[uirements] : Requirements of the job"
   echo "                    This maps to RSL for GT2 and REQUIREMENTS for vanilla jobs"
   echo "  -end fixed|sync|int[erval] <val> (REQUIRED)"
   echo "       fixed <seconds>    : Each job will sleep a fixed amount of seconds"
   echo "       sync <unix_time>   : All jobs will try to end exactly at the same time"
   echo "       interval <seconds> : All jobs will end at the next multiple of seconds"
   echo "  -jobs      <count> : How many jobs to submit, default=10"
   echo "  -clus[ter] <count> : How many jobs should I group per cluster, default=1000"
   echo "  -maxidle <count>   : How many idle jobs are allowed (delay submission else), default=-1 (disabled)"
   echo "  -maxjobs <count>   : How many jobs are allowed in the queue (delay submission else), default=-1 (disabled)"
   echo "  -in[file]  <file name> <file size> : Create an input file (default=no file)"
   echo "  -out[file] <file name> <file size> : Create an output file (default=no file)"
#   echo "  -owners <user_list> : Submit jobs for each and every owner, default=current user"
   echo "  -workdir <path>     : Where will the work directory be created, default=current dir"
}

######################################################################
# Parse Arguments
#

RunType="None"
JobUniverse="None"
JobRequirements=""
NrJobs=10
ClusterSize=1000
MaxIdle=-1
MaxJobs=-1

HaveInFile=0
HaveOutFile=0

#Owners="`id -nu`"
BaseWorkDir="$PWD"

while [ $# -gt 0 ]
do case "$1" in
    -type)
       JobUniverse="$2"
       if [ "$JobUniverse" == "grid" ]; then
         shift
         GridType="$2"
         if [ "$GridType" == "cream" ]; then
	    shift
            GridResource="$2 $3 $4"
            shift
            shift
         else # assume gt2-compatible format else
            shift
            GridResource="$2"
         fi
       fi
       ;;
    -req | -requirements)    
                 JobRequirements="$2";;
    -end)
       RunType="$2"
       shift
       RunVal="$2"
       ;;
    -jobs)       NrJobs="$2";;
    -clus | -cluster)    
                 ClusterSize="$2";;
    -maxidle)    MaxIdle="$2";;
    -maxjobs)    MaxJobs="$2";;

    -in | -infile)    
       HaveInFile=1
       InFileName="$2"
       shift
       InFileSize="$2"
       ;;
    -out | -outfile)    
       HaveOutFile=1
       OutFileName="$2"
       shift
       OutFileSize="$2"
       ;;

#    -owners)     Owners="$2";;
    -email)      EmailNotification="$2";;
    -h)  Usage; exit 0;;
    *)  (echo "Unknown option $1"; Usage) 1>&2; exit 1
esac
shift
shift
done

if [ "${JobUniverse}" == "None" ]; then
    (echo "Missing -type"; Usage) 1>&2; exit 1
fi

if [ "${RunType}" == "None" ]; then
    (echo "Missing -end"; Usage) 1>&2; exit 1
fi

######################################################################
# Parse RunType
#

TimeSent=`date +"%s"`
case ${RunType} in 
    fixed )
      RunTypeCode="1"
      if [ "${RunVal}" -gt 0 ]; then
	  CmdArgs="fixed ${RunVal}"
      else
	  echo "Invalid fixed period '${RunVal}' (must be positive number)" 1>&2
	  exit 1
      fi
      ;; 
    sync )
      if [ "${RunVal}" -gt "${TimeSent}" ]; then
	  CmdArgs="sync ${RunVal}"
      else
	  echo "Invalid unix time '${RunVal}' (must be after {TimeSent}')" 1>&2
	  exit 1
      fi
      ;; 
    int | interval )
      if [ "${RunVal}" -gt 0 ]; then
	  CmdArgs="interval ${TimeSent} ${RunVal}"
      else
	  echo "Invalid interval '${RunVal}' (must be positive number)" 1>&2
	  exit 1
      fi
      ;; 
    *)  (echo "Unknown end type '$RunType' "; Usage) 1>&2; exit 1
  ;; 
esac

######################################################################
# Create the work directory and populate it with needed files
#
WorkDir="${BaseWorkDir}/`date '+%F_%H.%M.%S'`"
mkdir "${WorkDir}"
if [ $? -ne 0 ]; then
  echo "Failed to create '$WorkDir'" 1>&2
  exit 2
fi


cp "${LIBEXEC}/lt_job.sh" "${WorkDir}/"
if [ $? -ne 0 ]; then
  echo "Failed to copy ${LIBEXEC}/lt_job.sh" 1>&2
  exit 2
fi
chmod a+x "${WorkDir}/lt_job.sh"

cp "${LIBEXEC}/cleanup.sh" "${WorkDir}/"
if [ $? -ne 0 ]; then
  echo "Failed to copy ${LIBEXEC}/cleanup.sh" 1>&2
  exit 2
fi
chmod a+x "${WorkDir}/cleanup.sh"


CondorSubmitFile="${WorkDir}/job.sub"
cp "${LIBDATA}/job_submit_template.sub" "${CondorSubmitFile}"
if [ $? -ne 0 ]; then
  echo "Failed to copy ${LIBDATA}/job_submit_template.sub" 1>&2
  exit 2
fi



######################################################################
# Create the job config file
#
JobConfig="${WorkDir}/job.config"
touch "${JobConfig}"
cat >> "${JobConfig}" <<EOF
RunType=${RunType}
RunVal=${RunVal}
TimeSent=${TimeSent}

CreateOutFile=${HaveOutFile}
HaveInFile=${HaveInFile}
EOF

if [ "${HaveOutFile}" -eq 1 ]; then 
  cat >> "${JobConfig}" <<EOF
OutFileBaseName="${OutFileName}"
OutFileSize="${OutFileSize}"
EOF

fi

if [ "${HaveInFile}" -eq 1 ]; then
  cat >> "${JobConfig}" <<EOF
InFileName="${InFileName}"
EOF

fi

######################################################################
# Update the job submit template
#
echo "universe = ${JobUniverse}" >> "${CondorSubmitFile}"
if [ "$JobUniverse" == "grid" ]; then
    echo "grid_resource = ${GridType} ${GridResource}"  >> "${CondorSubmitFile}"
    if [ -n "${JobRequirements}" ]; then
	if [ "${GridType}" == "gt2" ]; then
	    echo "globus_rsl = ${JobRequirements}"  >> "${CondorSubmitFile}"
	else
	    echo "Don't know how to handle requirements for Grid type '${GridType}'" 1>&2
	    echo "Aborting" 2>&1
	    exit 1
	fi
    fi
else
    if [ -n "${JobRequirements}" ]; then
	if [ "$JobUniverse" == "vanilla" ]; then
	    echo "requirements = ${JobRequirements}"  >> "${CondorSubmitFile}"
	else
	    echo "Don't know how to handle requirements for universe '${JobUniverse}'" 1>&2
	    echo "Aborting" 1>&2
	    exit 1
	fi
    fi
fi


if [ "${HaveInFile}" -eq 1 ]; then
    cat >> "${CondorSubmitFile}" <<EOF
transfer_input_files = ${JobConfig},../${InFileName},../${InFileName}.md5
EOF
else
    cat >> "${CondorSubmitFile}" <<EOF
transfer_input_files = ${JobConfig}
EOF
fi

if [ "${HaveOutFile}" -eq 1 ]; then
    cat >> "${CondorSubmitFile}" <<EOF
transfer_output_files = ${OutFileName}.\$(tcluster).\$(tprocess),${OutFileName}.\$(tcluster).\$(tprocess).md5
EOF
fi

   
cat >> "${CondorSubmitFile}" <<EOF
log = ${WorkDir}/job.log
Initialdir  = ${WorkDir}/\$(tcluster)
queue
EOF

######################################################################
# Create the cluster submit files and the dagman file
#
DagConfig="${WorkDir}/dag.config"
touch "${DagConfig}"

cat >> "${DagConfig}" <<EOF
DAGMAN_MAX_SUBMITS_PER_INTERVAL=${ClusterSize}
EOF

JobDag="${WorkDir}/job.dag"
touch "${JobDag}"

#Let's build up the series to split up the jobs in directories

Series=""
let NrClusters=${NrJobs}/${ClusterSize}
let Remainder=${NrJobs}-${NrClusters}*${ClusterSize}

for i in `seq ${NrClusters}`; do
    Series="${Series} ${ClusterSize}" 
done
if [ ${Remainder} -gt 0 ]; then
    Series="${Series} ${Remainder}"
fi


jobs=""

# this will be the counter
SubDirNr=0

for NumberOfJobs in ${Series}; do 
   SubDir="${WorkDir}/${SubDirNr}"
   mkdir ${SubDir}

   
   for JobNr in `seq ${NumberOfJobs}`; do
     cat >> "${JobDag}" <<EOF
JOB  p${SubDirNr}.${JobNr} job.sub
VARS p${SubDirNr}.${JobNr} tcluster="${SubDirNr}"
VARS p${SubDirNr}.${JobNr} tprocess="${JobNr}"
SCRIPT POST p${SubDirNr}.${JobNr} cleanup.sh ${SubDirNr} ${SubDirNr}.${JobNr} job.config \$RETURN
EOF
     jobs="${jobs} p${SubDirNr}.${JobNr}"
   done

   # this is a for loop, so increase the counter
   let SubDirNr=${SubDirNr}+1
done

######################################################################
# If needed, create the input job
#
InFileSubmit="${WorkDir}/infile.sub"
if [ "${HaveInFile}" -eq 1 ]; then
    cp "${LIBEXEC}/create_infile.sh" "${WorkDir}/"
    if [ $? -ne 0 ]; then
	echo "Failed to copy ${LIBEXEC}/create_infile.sh" 1>&2
	exit 2
    fi
    chmod a+x "${WorkDir}/create_infile.sh"

    cp "${LIBDATA}/infile_template.sub" "${InFileSubmit}"
    cat >> "${InFileSubmit}" <<EOF
log = ${WorkDir}/job.log
Initialdir  = ${WorkDir}
queue
EOF

     cat >> "${JobDag}" <<EOF
JOB  infile infile.sub
VARS infile filename="${InFileName}"
VARS infile filesize="${InFileSize}"
PARENT infile CHILD $jobs
EOF

fi

######################################################################
# Submit dag and save ID
#

pushd "${WorkDir}"

opts=""

if [ "${MaxIdle}" -gt 0 ]; then
    opts="$opts -maxidle ${MaxIdle}"
fi

if [ "${MaxJobs}" -gt 0 ]; then
    opts="$opts -maxjobs ${MaxJobs}"
fi

CondorSubmitLog=condor_submit.log
ControlFileLog=control_file.log

condor_submit_dag  -notification Never -config dag.config $opts "${JobDag}"| tee -a "${CondorSubmitLog}"
if [ $? -ne 0 ]; then
  echo "Failed to submit dag" 1>&2
  exit 2
fi

ClusterINFO="`head -3 $CondorSubmitLog |tail -1`"

echo `hostname` ${ClusterINFO} > $ControlFileLog

popd

