#!/bin/bash

logTime="$(date +%F_%T)"
logLoc="/var/log/CSbackups/delete"
crumpitOutLoc="/mnt/nanostore"

logFile="${logLoc}/${logTime}.log"
touch $logFile

latestProgressLog=$(ls -trd /var/log/CSbackups/progress/20* | tail -n 1)
echo "using ${latestProgressLog}" | tee -a $logFile
for dir in $(grep f5 ${latestProgressLog}/toDelete)
do 
    echo "deleteing ${dir}" | tee -a $logFile
    rm -rf /mnt/nanostore/${dir}
    echo "completed ${dir}" | tee -a $logFile 
done
