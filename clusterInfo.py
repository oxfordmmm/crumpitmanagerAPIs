#! /usr/bin/python3

#Functionality to interact with the cluster running CRUMPIT
#
#Author: Jez Swann
#Date: May 2019

import os
import glob

class clusterInfo:
    def processStep(self, fileStream, currentline):
        splitLine = currentline.split('-')

        stepResult = {}
        stepResult['result'] = int(splitLine[-1].strip('() \n'))
        if stepResult['result'] == 1 or stepResult['result'] == 2:
            stepResult['step'] = splitLine[-4].strip()
        else:
            stepResult['step'] = splitLine[-3].strip()

        currentline = fileStream.readline()
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
                        gridDict[runName][stepResult['step']] = stepResult['result']

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

        return runStatusDict