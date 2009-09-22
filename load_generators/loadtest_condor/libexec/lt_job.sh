#!/bin/bash

#env

function Usage
{
   echo "Usage: `basename $0` <id> <config_file>"
   echo
   echo "The config file must define:"
   echo "  RunType"
   echo "  RunVal"
   echo "  TimeSent"
   echo "  CreateOutFile"
   echo "  HaveInFile"
}

#Error if not at least two arguments
if [ $# -lt 2 ]; then
   Usage
   exit 1
fi


echo "`hostname` executed @ `date +'%F_%H:%M:%S'`"
RunID="$1"
ConfigFile="$2"

source "$2"

echo "RunID:   ${RunID}"
echo "RunType: ${RunType} ${RunVal}"

GenerateFile()
{
   gf_FileName=$1
   gf_FileSizeInKB=$2
   echo "`hostname` Creating file $gf_FileName of $gf_FileSizeInKB KB"
   dd if=/dev/urandom of=${gf_FileName} bs=1k count=${gf_FileSizeInKB}
   if [ $? -ne 0 ]
      then
      echo "`hostname` Problem creating file ${gf_FileName} of ${gf_FileSizeInKB} KB" 1>&2
      exit 2
   else
      echo "`hostname` Created file ${gf_FileName} of ${gf_FileSize} KB"
      md5sum $gf_FileName > ${gf_FileName}.md5
   fi
   
}

# generate output file as the first step, so it is always available
# else OCndor will go belly up :(
if [ "${CreateOutFile}" -eq 1 ]; then
    GenerateFile "${OutFileBaseName}.${RunID}" "${OutFileSize}"
fi


# Fixed Time sleeping.
function FixedExit {
    TimeToSleep="$1"
    if [ -z "${TimeToSleep}" ] || [ "${TimeToSleep}" -lt 0 ]; then
	TimeToSleep=${FIXEDSleepingTimeDefault}
    fi
    StillToSleep=$TimeToSleep
}

# Fixed exit time.
function UTimeExit {
    TimeToExit="$1"
    if [ -z "${TimeToExit}" ] || [ "${TimeToExit}" -le 0 ]; then
	echo "No proper exit time given"
	echo "Exit time given: ${TimeToExit}"
	exit 1
    fi

    let StillToSleep=${TimeToExit}-${Now}
}


# Fixed exit window time.
function IntervalExit {
    Sent="$1"
    DieAtIntervalsOfSeconds="$2"

    if [ -z "${Sent}" ] || [ "${Sent}" -lt 0 ]; then
	echo "No proper Sent time given"
	echo "Sent time given: ${Sent}"
	exit 1
    fi

    if [ -z "${DieAtIntervalsOfSeconds}" ] || [ "${DieAtIntervalsOfSeconds}" -le 0 ]; then
	DieAtIntervalsOfSeconds=${DieAtIntervalsOfSecondsDefault}
    fi
    
    TotalRampingTime=${DieAtIntervalsOfSeconds}
    Now=`date +"%s"`
    #How much intervals (times) have passed since sent
    let Interval=${Now}-${Sent} 
    let times=${Interval}/${TotalRampingTime}

    #Get the time to sleep till next window to die
    let StillToSleep=${times}*${TotalRampingTime}
    let StillToSleep=${TimeToSleep}+${TotalRampingTime}-${Interval}
}

case ${RunType} in 
fixed ) FixedExit "${RunVal}" ;; 
sync ) UTimeExit "${RunVal}";; 
interval ) IntervalExit "${TimeSent}" "${RunVal}";; 
*)  (echo "Unknown RunType ${RunType}"; Usage) 1>&2; exit 1
esac   

if [ "${HaveInFile}" -eq 1 ]; then
  if [ -s "${InFileName}.md5" ]; then
      md5sum -c "${InFileName}.md5"
      if [ $? -eq 0 ]; then
	  echo "In file ${InFileName} found and verified"
      else
	  echo "md5sum check failed for ${InFileName}" 1>&2
	  exit 3
      fi
  else
      echo "Input file ${InFileName}.md5 missing!" 1>&2
      exit 3
  fi
fi

#Sleep it
echo "`hostname` Going to Sleep for ${StillToSleep} s"
if [ ${StillToSleep} -ge 0 ]; then
   sleep ${StillToSleep}
   echo "`hostname` Slept for ${StillToSleep} s"
else
   echo "`hostname` Not sleeping negative times"
fi
echo "`hostname` finished @ `date +'%F_%H:%M:%S'`"


exit 0
