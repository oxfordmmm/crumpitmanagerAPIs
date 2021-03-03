#! /usr/bin/python3

#Functionality to give information about a specific run
#
#Author: Jez Swann and Nicholas Sanderson
#Date: May 2019

import os
import datetime

from pymongo import MongoClient
import pandas as pd
import seaborn as sns

def splitName(r):
    return r.split(' ')[0]

class runInfo:
    def __init__(self,run: dict, ip: str='127.0.0.1',port: int=27017):
        self.run=run
        self.ip=ip
        self.port=port

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
            df['time']=pd.to_timedelta(df['duration']).astype('timedelta64[s]')
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

    def getGridBasesGraph(self):
        try:
            b=self.df.sort_values(by='start_time',ascending=True)
            # calculate cumulative yeild of bases with cumsum()
            b['Yield (bases)']=b['queryLength'].cumsum().astype(int)
            # Create a column of time in minute, for longer runs you can do the same with hours
            b['run_time']=pd.to_datetime(b.start_time)
            b.run_time=((b.run_time-b.run_time.min())/ pd.Timedelta('1 hour')).astype(int)
            b2=b.sample(500)

            ax=sns.lineplot(x='run_time',y='Yield (bases)',data=b2)
            ax.ticklabel_format(style='plain', axis='y')
            fig = ax.get_figure()
            imgFilename = "images/{}-grid_bases.png".format(self.run['run_name'])
            fig.savefig("images/{}-grid_bases.png".format(self.run['run_name']))
            return imgFilename
        except Exception as e:
            print(e)
            print("Could not create grid bases graph for run {}".format(self.run['run_name']))
            return "images/blank.png"

    def getBatchGraph(self):
        f=os.listdir(self.run['cwd'])
        f=[i for i in f if i.startswith('trace.txt')]
        dfs=[]
        for i in f:
            dfs.append(pd.read_csv('{0}/{1}'.format(self.run['cwd'], i),sep='\t'))
        df=pd.concat(dfs)

        df['process']=df.name.map(splitName)
        c=df[df.status == 'COMPLETED']
        c['run_time']=pd.to_datetime(c.submit)
        c=pd.DataFrame(c.run_time-c.run_time.min())
        c = c.resample('T', on='run_time').count()
        c=c.rename(columns={"run_time":"batches"})

        ax = c.plot()
        fig = ax.get_figure()
        imgFilename = "images/{}-batches.png".format(self.run['run_name'])
        fig.savefig("images/{}-batches.png".format(self.run['run_name']))
        return imgFilename
    
    def getRunGraphs(self):
        client = MongoClient(self.ip, self.port)
        db = client[self.run['run_name']]
        collection = db.cent_stats
        hce=collection.find()
        log={}
        for h in hce:
            try:
                log[h['start_time']] = h
            except Exception as e:
                print("Error: Could not load entry for run {}".format(self.run['run_name']))
                print(e)
        
        df=pd.DataFrame(log)
        self.df=df.transpose()

        gridBasesFilename = self.getGridBasesGraph()
        batchFilename = self.getBatchGraph()

        return {'gridBases':gridBasesFilename, 'batches':batchFilename}