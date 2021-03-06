#! /usr/bin/python3

#Functionality to give information about CRUMPIT runs 
#
#Author: Jez Swann
#Date: May 2019

import sys
import os
import datetime
import re
import collections

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from pymongo import MongoClient

from crumpitmanagerapi.liveRuns.runInfo import *

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

                # Format string fake PID into int
                if log[h['run_name']]['PID'] == 'fake':
                    log[h['run_name']]['PID'] = -1

                # Try to determine human readable run location (e.g. grid1)
                log[h['run_name']]['runLocation'] = log[h['run_name']]['cwd'].split('/')[-2]
            except Exception as e:
                print("Error: Could not load run {}".format(h['run_name']))
                print(e)
                log[h['run_name']]['PID'] = -1
                log[h['run_name']]['runLocation'] = ''
        
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
        imgFilename = "images/temp.png"
        fig.savefig(imgFilename, bbox_inches = "tight")
        plt.close(fig)
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
            df=df[['Submittedtime','batches','processes','cwd','runLocation']]
        except:
            print("Error: Could not find Live Stats")

        return df.to_dict('index')

    def getProjects(self):
        allRuns = self.getRuns()

        projects = {}
        for run in allRuns:
            project = run.rsplit('_',1)[0]
            if project in projects:
                projects[project].append(run)
            else:
                projects[project] = [run]
        
        # Some code for auto incrementing runs before reliasing that the number can be elsewhere in the run name 
        incremental_regex = re.compile("_[0-9]{1,3}$")
        returnProjects = {}
        #iterableProjects = {}
        # Only add to list if there's > 1 run
        for project, projectList in {key:value for (key, value) in projects.items() if len(value) > 1}.items():
            # Sort by incremental number at end of run name if all run names are int only. Otherwise sort by text only.
            if len(list(filter(incremental_regex.search, projectList))) == len(projectList):
                returnProjects[project] = [project + "_" + str(num) for num in sorted([int(i.rsplit('_',1)[1]) for i in projectList])]
                #iterableProjects[project] = returnProjects[project][-1].rsplit('_',1)[1]
            else:
                returnProjects[project] = sorted(projectList)
        return collections.OrderedDict(sorted(returnProjects.items(), key=lambda x: x[0].lower()))

if __name__ == '__main__':
    print(runsInfo().getLiveStats())
