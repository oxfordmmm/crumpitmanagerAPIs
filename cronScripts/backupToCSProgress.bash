#!/bin/bash
# Author: Jez Swann (Jeremy.Swann@ndm.ox.ac.uk)

function checkProgressOnRunStep()
{
    runName=$1 
    step=$2
    logFile=$3 
    findLogLoc=$4 
    outputDir=$5
    gridLoc=$6
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
            ssh csana1 "cd ${outputDir}/Nanopore; find $runName/$step -type f -printf '%f\t%s\n'" > ${findLogLoc}/${runName}-${step}-remote.out
            cat ${findLogLoc}/${runName}-${step}-remote.out | sort > ${findLogLoc}/${runName}-${step}-remote.out.tmp && mv ${findLogLoc}/${runName}-${step}-remote.out.tmp ${findLogLoc}/${runName}-${step}-remote.out

            outputx="$(diff ${findLogLoc}/${runName}-${step}-local.out ${findLogLoc}/${runName}-${step}-remote.out; echo x$?)"
            diffStatus=${outputx##*x}
            output="${outputx%x*}"

            if [ "$diffStatus" == "0" ]; then
                # Check older than 7 days
                findOlder=$(find $runName/$step -type f -mtime +7 -printf "%f\t%s\n"| wc -l)
                if [ $findOlder -gt 0 ]; then
                    echo "$runName - $step - Local and Remote same - files older than 7 days, list for deletion - (1)" | tee -a $logFile
                    echo "${gridLoc}/${runName}/${step}" >> ${logLoc}/toDelete
                else
                    echo "$runName - $step - Local and Remote same - files newer than 7 days, not listing for deletion - (2)" | tee -a $logFile
                    echo "${gridLoc}/${runName}/${step}" >> ${logLoc}/futureDelete
                fi

                if [ "$step" != "sequencing_summary.txt.gz" ]; then
                    findBatches=$(find $runName/$step -type f -printf "%f\n" | awk '{split($0,a,"[_.]"); print a[2]}' | sort | uniq | wc -l)
                    if [ "$findBatches" == "1" ]; then
                        findBatches=$(find $runName/$step -type f -printf "%f\n" \( -iname \*.fast5* -o -iname \*.fastq* \) | wc -l)
                    fi
                    echo "{\"batches\" : $findBatches}" | tee -a $logFile
                fi
            elif [ "$diffStatus" == "1" ]; then
                echo "$runName - $step - Local and Remote different - (0)" | tee -a $logFile
                if [ "$step" != "sequencing_summary.txt.gz" ]; then
                    findBatches=$(find $runName/$step -type f -printf "%f\n" | awk '{split($0,a,"[_.]"); print a[2]}' | sort | uniq | wc -l)
                    if [ "$findBatches" == "1" ]; then
                        findBatches=$(find $runName/$step -type f -printf "%f\n" \( -iname \*.fast5* -o -iname \*.fastq* \) | wc -l)
                    fi
                    echo "{\"batches\" : $findBatches}" | tee -a $logFile
                fi
                echo "${output}" | tee -a $logFile
#                echo "${gridLoc}/${runName}/${step}" >> ${logLoc}/toUpload
            else
                echo "$runName - $step - Something happened - User Cancelled Script? - (-1)"  | tee -a $logFile
                echo "${output}" | tee -a $logFile
                break
            fi
        fi
    fi
}

grids=("grid0" "grid1" "grid2")
steps=("f5s" "basecalled_fastq" "sequencing_summary.txt.gz")
logTime="$(date +%F_%T)"
logLoc="/var/log/CSbackups/progress/${logTime}"
findLogLoc="${logLoc}/findLogs"
outputDir="/mnt/microbio"
timeToDelete="7"


mkdir -p $logLoc
mkdir $findLogLoc
touch ${logLoc}/toDelete
touch ${logLoc}/futureDelete
touch ${logLoc}/toUpload
chmod -R a+r $logLoc

for grid in "${grids[@]}"
do
    logFile="${logLoc}/run-${grid}.log"
    touch $logFile
    cd /mnt/nanostore/${grid}
    runs="$(ls -trd */)"

    for run in ${runs}
    do
        runCut=${run: : -1}
        echo ${runCut} | tee -a $logFile
        for step in ${steps[@]}
        do
            checkProgressOnRunStep $runCut $step $logFile $findLogLoc $outputDir $grid $timeToDelete
        done
        echo "-------------------------------------------------------------------------------" | tee -a $logFile
        echo "" | tee -a $logFile
    done
done
