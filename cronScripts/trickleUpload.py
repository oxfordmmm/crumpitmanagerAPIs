#!/usr/bin/env python3
import sys
import os
import pandas as pd
import numpy as np
import datetime
from pymongo import MongoClient
import subprocess
import time

class uploadRun:
    def __init__(self,run,details,uploadRate=20000):
        self.run=run
        self.details=details
        self.uploadRate=uploadRate
        self.uploadF5s()

    def uploadF5s(self):
        uploadLoc='/home/ndm.local/Nanopore/{0}'.format(self.run)
       
        mkFolCommand=['ssh', 'csana1', 'mkdir -p {0}'.format(uploadLoc)]
        print(mkFolCommand)

	# f5s
        f5s='{0}/f5s'.format(self.details['cwd'])
        rsyncCommand=['rsync', '-avP','--bwlimit={0}'.format(self.uploadRate), f5s, 'csana1:{0}'.format(uploadLoc)]
        print(rsyncCommand)

        try:
            subprocess.run(mkFolCommand,shell=False, check=False)
        except subprocess.CalledProcessError as e:
            print(e.output)
        
        try:
            subprocess.run(rsyncCommand,shell=False, check=False)
        except subprocess.CalledProcessError as e:
            print(e.output)

	# fastqs
        fqs='{0}/basecalled_fastq'.format(self.details['cwd'])
        rsyncCommand=['rsync', '-avP','--bwlimit={0}'.format(self.uploadRate), fqs, 'csana1:{0}'.format(uploadLoc)]
        print(rsyncCommand)

        try:
            subprocess.run(rsyncCommand,shell=False, check=False)
        except subprocess.CalledProcessError as e:
            print(e.output)

class checkRuns:
    def __init__(self,ip='163.1.213.195',port=27017):
        self.client = MongoClient(ip, port)
        self.loadtable()
        self.getLiveRuns()
        self.uploadRuns()

    def loadtable(self):
        self.db = self.client['gridRuns']
        self.collection = self.db.gridRuns
        hce=self.collection.find()
        log={}
        for h in hce: log[h['run_name']]=h
        
        df=pd.DataFrame(log)
        df=df.transpose()
        self.df=df.sort_values(by=['starttime'],ascending=False)

    def getLiveRuns(self):
        df=self.df[self.df.status == 'Running']
        now=datetime.datetime.now()
        td=now-datetime.timedelta(days=7)
        liveRuns=df[df.Submittedtime > td]
        # get just finished runs
        df=self.df[self.df.status == 'Finished']
        td=now-datetime.timedelta(hours=6)
        justFinishedRuns=df[df.Finishtime > td]
        # all these runs together
        self.liveRuns=pd.concat([liveRuns,justFinishedRuns])

    def uploadRuns(self):
        runs=self.liveRuns.to_dict(orient='index')
        for run in runs:
            u=uploadRun(run,runs[run])


if __name__ == '__main__':
    try:
        while True:
            c=checkRuns()
            time.sleep(60)
    except KeyboardInterrupt:
        print('Stopping trickle upload')
        
