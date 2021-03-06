#!/bin/bash
# Author: Jez Swann (Jeremy.Swann@ndm.ox.ac.uk)

function checkProgressOnRunStep()
{
    runName=$1 
    step=$2
    logFile=$3 
    findLogLoc=$4 
    outputDir=$5
    f5sToDel=$6
    timeToDelete=$7

    find $runName/$step -type f -printf "%f\t%s\n" > ${findLogLoc}/${runName}-${step}-local.out
    if [ "$?" -ne "0" ]; then
        echo "$runName - $step - Has no files - (4)" | tee -a $logFile
    else
        sizeLocal=$(wc -l ${findLogLoc}/${runName}-${step}-local.out | cut -f1 -d' ')
        if [ $sizeLocal == 0 ]; then
            echo "$runName - $step - Has a directory but no files - (4)" | tee -a $logFile
        else
            cat ${findLogLoc}/${runName}-${step}-local.out | sort > ${findLogLoc}/${runName}-${step}-local.out.tmp && mv ${findLogLoc}/${runName}-${step}-local.out.tmp ${findLogLoc}/${runName}-${step}-local.out
            ssh jez@rescomp.well.ox.ac.uk "ssh jez@dingo 'cd ${outputDir}/Nanopore; find $runName/$step -type f -printf \"%f\t%s\n\"'" > ${findLogLoc}/${runName}-${step}-remote.out
            cat ${findLogLoc}/${runName}-${step}-remote.out | sort > ${findLogLoc}/${runName}-${step}-remote.out.tmp && mv ${findLogLoc}/${runName}-${step}-remote.out.tmp ${findLogLoc}/${runName}-${step}-remote.out

            outputx="$(diff ${findLogLoc}/${runName}-${step}-local.out ${findLogLoc}/${runName}-${step}-remote.out; echo x$?)"
            diffStatus=${outputx##*x}
            output="${outputx%x*}"

            if [ "$diffStatus" == "0" ]; then
                if [ "$step" == "f5s" ]; then
                    # Check older than 60 days
                    findOlder=$(find $runName/$step -type f -mtime +60 -printf "%f\t%s\n"| wc -l)
                    if [ $findOlder -gt 0 ]; then
                        echo "$runName - $step - Local and Remote same - f5s older than 60 days, list for deletion - (1)" | tee -a $logFile
                        echo "${runName}" >> ${f5sToDel}
                    else
                        echo "$runName - $step - Local and Remote same - f5s newer than 60 days, not listing for deletion - (2)" | tee -a $logFile
                        echo "${runName}" >> ${f5sToDel}.future
                    fi
                else
                    echo "$runName - $step - Local and Remote same - files other than f5s do not get deleted - (2)" | tee -a $logFile
                fi
            elif [ "$diffStatus" == "1" ]; then
                echo "$runName - $step - Local and Remote different - (0)" | tee -a $logFile
                echo "${output}" | tee -a $logFile
            else
                echo "$runName - $step - Something happened - User Cancelled Script? - (-1)"  | tee -a $logFile
                echo "${output}" | tee -a $logFile
                break
            fi 
        fi
    fi
}

steps=("f5s" "basecalled_fastq" "sequencing_summary.txt.gz")
logTime="$(date +%F_%T)"
logLoc="/var/log/RESCOMPBackupLogs/progress/${logTime}"
findLogLoc="${logLoc}/findLogs"
logFile="${logLoc}/run.log"
f5sToDel="${logLoc}/f5sToDelete.log"
currentStorage="/mnt/microbio/Nanopore"
outputDir="/arc/bag/mmmbackup/microbio"
timeToDelete="60"

mkdir -p $logLoc
mkdir $findLogLoc
touch $logFile
touch $f5sToDel
touch $f5sToDel.future
chmod -R a+r $logLoc

cd ${currentStorage}
runs="$(ls -trd */)"

for run in ${runs}
do
    runCut=${run: : -1}
    echo ${runCut} | tee -a $logFile
    for step in ${steps[@]}
    do
        checkProgressOnRunStep $runCut $step $logFile $findLogLoc $outputDir $f5sToDel $timeToDelete
    done
    echo "-------------------------------------------------------------------------------" | tee -a $logFile
    echo "" | tee -a $logFile
done
