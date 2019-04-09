#!/usr/bin/env python3
import sys
import os
import pandas as pd
import numpy as np
import datetime
from pymongo import MongoClient

from runInfo import *

class runsInfo:
    def __init__(self,ip='127.0.0.1',port=27017):
        self.client = MongoClient(ip, port)
        self.loadtable()

    def loadtable(self):
        self.db = self.client['gridRuns']
        self.collection = self.db.gridRuns
        hce=self.collection.find()
        log={}
        for h in hce: log[h['run_name']]=h
        
        df=pd.DataFrame(log)
        df=df.transpose()
        self.df=df.sort_values(by=['starttime'],ascending=False)

    def getLiveRuns(self, timeFrame: int=7):
        if timeFrame > 0:
            df=self.df[self.df.status == 'Running']
            now=datetime.datetime.now()
            td=now-datetime.timedelta(days=timeFrame)
        return df[df.Submittedtime > td]

    def getRuns(self):
        return self.df.sort_values(by=['starttime'],ascending=False).to_dict('index')

    def getRunStatRows(self, r: pd.Series):
        rs=runInfo(r.to_dict()).getLiveStats()
        r['batches']=rs["batch_number"]
        r['f5s']=rs["f5_numbers"]
        r['percent complete']=rs["percent"]
        return r

    def getLiveStats(self):
        liveRuns = self.getLiveRuns()
        df = liveRuns.apply(self.getRunStatRows,axis=1)
        try:
            df=df[['Submittedtime','batches','f5s','percent complete','cwd']]
        except:
            print("Error: Could not find Live Stats")

        return df.to_dict('index')

if __name__ == '__main__':
    print(runsInfo().getLiveStats())