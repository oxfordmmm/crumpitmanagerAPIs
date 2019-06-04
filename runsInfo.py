#! /usr/bin/python3

#Functionality to give information about CRUMPIT runs 
#
#Author: Jez Swann
#Date: May 2019

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
    def __init__(self,ip: str='127.0.0.1',port: int=27017):
        self.__client = MongoClient(ip, port)
        self.loadtable()

    def loadtable(self):
        self.db = self.__client['gridRuns']
        self.collection = self.db.gridRuns
        hce=self.collection.find()
        log={}
        for h in hce:
            try:
                log[h['run_name']]=h
                if log[h['run_name']]['PID'] == 'fake':
                    log[h['run_name']]['PID'] = -1
            except Exception as e:
                print("Error: Could not load run")
                print(e)
                log[h['run_name']]['PID'] = -1
        
        df=pd.DataFrame(log)
        df=df.transpose()
        self.df=df.sort_values(by=['starttime'],ascending=False)

    def __getLiveRunRows(self, r: pd.Series):
        rs=runInfo(r.to_dict()).getLiveStats()
        r['batches']=rs["batch_number"]
        r['processes']=rs["processes"]
        return r

    def __getRunRows(self, r: pd.Series):
        rs=runInfo(r.to_dict()).getStats()
        r['Finishtime']=rs["Finishtime"]
        r['Finishingtime']=rs["Finishingtime"]
        r['batches']=rs['batches']
        return r

    def getRuns(self):
        allRuns = self.df.sort_values(by=['starttime'],ascending=False)
        df = allRuns.apply(self.__getRunRows,axis=1)
        return df.to_dict('index')

    def getRunsGraph(self):
        df=self.df[(self.df['PID'] != -1) & (self.df['Finishtime'] != 'NaN')]
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
            df=df[['Submittedtime','batches','processes','cwd']]
        except:
            print("Error: Could not find Live Stats")

        return df.to_dict('index')

if __name__ == '__main__':
    print(runsInfo().getLiveStats())