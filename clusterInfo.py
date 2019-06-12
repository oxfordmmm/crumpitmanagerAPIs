#! /usr/bin/python3

#Functionality to interact with the cluster running CRUMPIT
#
#Author: Jez Swann
#Date: May 2019

import os
import glob
import json

class clusterInfo:
    def getLocalInfo(self, grids: dict):
        localDict = {}
        #for grid in grids.items():
            # if state == OK
            # df
            # count runs
        
        # df nanostore
        # count runs
        
        return localDict

    def getRemoteInfo(self, locations: dict):
        remoteDict = {}
        #for location in locations.items():
            # ping location
            # if state == OK
                # ssh df command
                # count runs
        return remoteDict

    def processStep(self, fileStream, currentline):
        splitLine = currentline.split('-')

        stepResult = {}
        stepResult['result'] = int(splitLine[-1].strip('() \n'))
            # TODO deal with -1 status
        if stepResult['result'] == 1 or stepResult['result'] == 2:
            stepResult['step'] = splitLine[-4].strip()
        else:
            stepResult['step'] = splitLine[-3].strip()
        if stepResult['step'] == 'sequencing_summary.txt.gz':
            stepResult['step'] = 'sequencing_summary'

        currentline = fileStream.readline()
        additionalInfo = None
        if currentline:
            try:
                additionalInfo = json.loads(currentline)
                for key, value in additionalInfo.items():
                    stepResult[key] = value
                currentline = fileStream.readline()
            except:
                pass

        if stepResult['result'] == 0 and currentline:
            lineLen = len(currentline.strip())
            while len(currentline.strip()) != 0 and currentline:
                currentline = fileStream.readline()
                lineLen = len(currentline.strip())
            if currentline:
                currentline = fileStream.readline()
        
        finishRun = True
        if currentline:
            if not currentline == '-------------------------------------------------------------------------------\n':
                finishRun = False

        return stepResult, currentline, finishRun
                                

    def processGridLog(self, gridLogFile: str):
        gridDict = {}
        with open(gridLogFile, 'r') as gridLog:
            line = gridLog.readline()
            try:
                while line:
                    runName = line.strip()
                    line = gridLog.readline()
                    finishedRun = False
                    gridDict[runName] = {}
                    while not finishedRun:
                        stepResult, line, finishedRun = self.processStep(gridLog, line)
                        gridDict[runName][stepResult['step']] = {}
                        for key, value in stepResult.items():
                            if key != 'step':
                                gridDict[runName][stepResult['step']][key] = value

                    if line:
                        line = gridLog.readline()

                    if line:
                        line = gridLog.readline()
            except Exception as e:
                print("ERROR: Could not read log file correctly, quiting")
                print(e)

        return gridDict

    def getBackupInfo(self, logDir: str="", dbRuns: dict={}):
        runStatusDict = {}
        if os.path.exists(logDir):
            # Find most recent log
            recentLogDir = max(glob.glob(os.path.join(logDir, '*-*-*_*:*:*')), key=os.path.getmtime)

            # Open each grid log file
            gridPath = os.path.join(recentLogDir,"run-grid*.log")
            for gridLogFile in glob.glob(gridPath):
                gridDict = self.processGridLog(gridLogFile)
                runStatusDict.update(gridDict)
        else:
            print("Error: Could not find Live Stats")

        if len(dbRuns) > 0:
            for run in runStatusDict.keys():
                if run in dbRuns:
                    runStatusDict[run]['starttime'] = dbRuns[run]['starttime']
                    runStatusDict[run]['batches'] = dbRuns[run]['batches']

        return runStatusDict