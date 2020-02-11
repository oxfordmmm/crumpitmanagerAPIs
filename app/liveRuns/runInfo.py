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

        self.batches=[]
        try:
            self.batches=os.listdir('{0}/all_batches/'.format(self.run['cwd']))
        except:
            self.batches=[]

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
            "Finishingtime" : str(finishingTime),
            "batches" : len(self.batches)
        }
        return output

    def getLiveStats(self):
        try:
            f=os.listdir(self.run['cwd'])
            f=[i for i in f if i.startswith('trace.txt')]
            dfs=[]
            for i in f:
                dfs.append(pd.read_csv('{0}/{1}'.format(self.run['cwd'], i),sep='\t'))
            df=pd.concat(dfs)

            df['process']=df.name.map(splitName)
            df['time']=pd.to_timedelta(df['duration'],unit='s').astype('timedelta64[s]')
            c=df[df.status == 'COMPLETED'].groupby('process')['status'].count()
            c=c.reset_index()

            m=df[df.status == 'COMPLETED'].groupby('process')['task_id'].min()
            m=m.reset_index()
            mdf=m[['process','task_id']].set_index('process').T
            mdf['run']=self.run['run_name']
            mdf=mdf.set_index('run')

            t=df[df.status == 'COMPLETED'].groupby('process')['time'].mean()
            t=t.reset_index()
            tdf=t[['process','time']].set_index('process').T
            tdf['run']=self.run['run_name']
            tdf=tdf.set_index('run')

            c['percent complete']=(c['status']/len(self.batches))*100
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
                "batch_number" : len(self.batches),
                "processes" : processInfo
            }
        except Exception as e:
            output = { 
                "batch_number" : 0,
                "processes" : {}
            }
        return output