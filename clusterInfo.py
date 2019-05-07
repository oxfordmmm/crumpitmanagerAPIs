#! /usr/bin/python3

import os
import glob

class clusterInfo:
    def processStep(self, fileStream, currentline):
        splitLine = currentline.split('-')
        print(splitLine)

        stepResult = {}
        stepResult['runName'] = splitLine[0]
        stepResult['step'] = splitLine[1]
        stepResult['result'] = splitLine[-1].strip('()')
        currentline = fileStream.readline()
        print(currentline)

        if stepResult['result'] == 0 and currentline:
            while (not currentline == '') or currentline:
                currentline = fileStream.readline()
                print(currentline)
            if currentline:
                currentline = fileStream.readline()
                print(currentline)
        
        finishRun = True
        if currentline:
            if not currentline == '-------------------------------------------------------------------------------\n':
                finishRun = False

        return stepResult, currentline, finishRun
                                

    def processGridLog(self, gridLogFile: str):
        gridDict = {}
        with open(gridLogFile, 'r') as gridLog:
            line = gridLog.readline()
            print(line)
            while line:
                runName = line
                line = gridLog.readline()
                print(line)
                finishedRun = False
                while not finishedRun:
                    stepResult, line, finishedRun = self.processStep(gridLog, line)
                    gridDict[runName] = stepResult

                if line:
                    line = gridLog.readline()
                    print(line)

                if line:
                    line = gridLog.readline()
                    print(line)

        #testDict = {gridLogFile : {'f5s' : 1}}
        #return testDict
        return gridDict

    def getBackupInfo(self, logDir: str=""):
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
        return runStatusDict