#!/usr/bin/env python3
import sys
import os
import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from pymongo import MongoClient

from runInfo import *

class runsInfo:
    def __init__(self,ip='127.0.0.1',port=27017):
        self.__client = MongoClient(ip, port)
        self.loadtable()

    def loadtable(self):
        self.db = self.__client['gridRuns']
        self.collection = self.db.gridRuns
        hce=self.collection.find()
        log={}
        for h in hce: log[h['run_name']]=h
        
        df=pd.DataFrame(log)
        df=df.transpose()
        self.df=df.sort_values(by=['starttime'],ascending=False)

    def __getLiveRunRows(self, r: pd.Series):
        rs=runInfo(r.to_dict()).getLiveStats()
        r['batches']=rs["batch_number"]
        r['f5s']=rs["f5_numbers"]
        r['percent complete']=rs["percent"]
        return r

    def __getRunRows(self, r: pd.Series):
        rs=runInfo(r.to_dict()).getStats()
        r['finishTime']=rs["finishTime"]
        r['finishingTime']=rs["finishingTime"]
        return r

    def getRuns(self):
        allRuns = self.df.sort_values(by=['starttime'],ascending=False)
        print(allRuns)
        df = allRuns.apply(self.__getRunRows,axis=1)
        print(df)
        return df.to_dict('index')

    def getRunsGraph(self):
        df=self.df[(self.df['PID'] != 'fake') & (self.df['Finishtime'] != 'NaN')]
        df['runcount'] = 1
        df.Finishtime = pd.to_datetime(df.Finishtime) - pd.to_timedelta(7, unit='D')
        df = df.resample('W', on='Finishtime').sum()
        #df = pd.read_csv('actualRunMongo.csv', index_col=0, parse_dates=True)

        ax = df.plot()
        fig = ax.get_figure()
        fig.savefig("temp.png")
        imgFilename = "temp.png"
        return imgFilename

    def getLiveRuns(self, timeFrame: int=7):
        if timeFrame > 0:
            df=self.df[self.df.status == 'Running']
            now=datetime.datetime.now()
            td=now-datetime.timedelta(days=timeFrame)
        return df[df.Submittedtime > td]

    def getLiveStats(self):
        liveRuns = self.getLiveRuns()
        df = liveRuns.apply(self.__getLiveRunRows,axis=1)
        try:
            df=df[['Submittedtime','batches','f5s','percent complete','cwd']]
        except:
            print("Error: Could not find Live Stats")

        return df.to_dict('index')

if __name__ == '__main__':
    print(runsInfo().getLiveStats())