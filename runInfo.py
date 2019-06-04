#! /usr/bin/python3

#Functionality to give information about a specific run
#
#Author: Jez Swann and Nicholas Sanderson
#Date: May 2019

import os

import pandas as pd

def splitName(r):
    return r.split(' ')[0]

class runInfo:
    def __init__(self,run: dict):
        self.run=run

    def getStats(self):
        try:
            finishTime = self.run["Finishtime"]
        except:
            finishTime = ""

        try:
            finishingTime = self.run["Finishingtime"]
        except:
            finishingTime = ""

        output = { 
            "Finishtime" : str(finishTime),
            "Finishingtime" : str(finishingTime)
        }
        return output

    def getLiveStats(self):
        try:
            batches=os.listdir('{0}/all_batches/'.format(self.run['cwd']))
            batch_number=len(batches)
        except:
            batches=[]
            batch_number=0

        df=pd.read_csv('{0}/trace.txt'.format(self.run['cwd']),sep='\t')
        df['process']=df.name.map(splitName)
        df['time']=pd.to_timedelta(df['duration'],unit='s').astype('timedelta64[s]')
        c=df[df.status == 'COMPLETED'].groupby('process')['status'].count()
        c=c.reset_index()

        m=df[df.status == 'COMPLETED'].groupby('process')['task_id'].min()
        m=m.reset_index()
        mdf=m[['process','task_id']].set_index('process').T
        mdf['run']=self.run['run_name']
        mdf=mdf.set_index('run')

        t=df.groupby('process')['time'].mean()
        t=t.reset_index()
        tdf=t[['process','time']].set_index('process').T
        tdf['run']=self.run['run_name']
        tdf=tdf.set_index('run')

        c['batches']=batch_number
        c['percent complete']=(c['status']/c['batches'])*100
        df=c[['process','percent complete']].set_index('process').T
        df['run']=self.run['run_name']
        df=df.set_index('run')
        percentDict = df.to_dict("index")
        minIdDict = mdf.to_dict("index")
        timeDict = tdf.to_dict("index")

        processInfo = {}
        for process, minTaskId in minIdDict[self.run['run_name']].items():
            processInfo[process] = { 'minTaskId' : minTaskId }        
        for process, percent in percentDict[self.run['run_name']].items():
            processInfo[process]['percent'] = percent
        for process, time in timeDict[self.run['run_name']].items():
            processInfo[process]['time'] = int(time)
        
        output = { 
            "batch_number" : batch_number,
            "processes" : processInfo
        }
        return output