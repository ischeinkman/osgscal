#!/bin/bash

#env

function Usage
{
   echo "Usage: `basename $0` <workdir> <id> <jobconfig> <result>"
}

#Error if not at least three arguments
if [ $# -lt 4 ]; then
   Usage
   exit 1
fi

WorkDir="$1"
RunID="$2"
source "$3"
result="$4"

JobMessage="Fail"

if [ "$result" -eq 0 ]; then
    # no need for error files if everything worked fine
    rm -f "${WorkDir}/job.err.${RunID}"
    JobMessage="OK"
fi

if [ "${CreateOutFile}" -eq 1 ]; then
    OutFileName="${OutFileBaseName}.${RunID}"
    if [ "$result" -eq 0 ]; then
        # check that the file is OK
	if [ -s "${WorkDir}/${OutFileName}.md5" ]; then
	    pushd ${WorkDir}
	    md5sum -c "${OutFileName}.md5"
	    res=$?
	    popd
	    if [ $res -eq 0 ]; then
		# remove only if validated, else leave for debugging
		rm -f "${WorkDir}/${OutFileName}.md5" "${WorkDir}/${OutFileName}"
	    else
		# corrupted file
		result=10
		echo "Corrupted file in $RunID" >> fileproblems.log
		JobMessage="Corrupted"
	    fi
	else
	    # file missing
	    result=10
	    echo "Missing file in $RunID" >> fileproblems.log
	    JobMessage="Missing"
	fi
    else
	# failed jobs output does not make sense in any case
	rm -f "${WorkDir}/${OutFileName}.md5" "${WorkDir}/${OutFileName}"
    fi
fi

echo "`date '+%m/%d %H:%M'` $RunID: $JobMessage" >> completed.log

exit $result
