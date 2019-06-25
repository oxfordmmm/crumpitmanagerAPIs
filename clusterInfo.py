#! /usr/bin/python3

#Functionality to interact with the cluster running CRUMPIT
#
#Author: Jez Swann
#Date: May 2019

import os
import glob
import json

import subprocess, platform
import paramiko

class clusterInfo:
    def getDiskInfo(self, location: str):
        args = ["df", "-BG", location]
        p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
        p1.wait()

        diskSize = None
        diskUse = None
        if p1.returncode == 0:
            p2 = subprocess.Popen(['tail', '-n', '+2'], stdin=p1.stdout, stdout=subprocess.PIPE)
            line = p2.stdout.readline()
            if line:
                dfOutput = line.decode('utf-8').strip().split()
                diskSize = int(dfOutput[1][:-1])
                diskUse = int(dfOutput[2][:-1])

        if diskSize and diskUse:
            diskDict = {'diskSize': diskSize, 'diskUse': diskUse}
            return diskDict
        else:
            return None

    def getLocalInfo(self, clusterInfoDict: dict):
        localDict = {'grids': dict()}
        for grid in clusterInfoDict['gridIONS']:
            try:
                # adapted from https://stackoverflow.com/a/35625078
                # Ping
                ping_str = "-n 1" if  platform.system().lower()=="windows" else "-c 1"
                args = "ping " + " " + ping_str + " " + grid['IP']
                need_sh = False if  platform.system().lower()=="windows" else True
                pingResult = subprocess.run(args, stdout=subprocess.DEVNULL ,shell=need_sh).returncode == 0
                
                if pingResult:
                    # Get disk usage and size
                    diskInfo = self.getDiskInfo(grid['mountLocation'])
                    
                    # Count runs

                    # Put info into dict to be passed on
                    if diskInfo:
                        localDict['grids'][grid['name']] = {'status':pingResult, 'diskSize':diskInfo['diskSize'], 'diskUse':diskInfo['diskUse']}
                    else:
                        localDict['grids'][grid['name']] = {'status':pingResult}
                else:
                    localDict['grids'][grid['name']] = {'status':pingResult}
            except Exception as e:
                print("ERROR: Could not process gridION, skipping")
                print(e)

        # Get disk usage and size
        diskInfo = self.getDiskInfo(clusterInfoDict['storageLocation'])
        localDict['storage'] = diskInfo

        # count runs
        
        return localDict

    def getRemoteConnection(self, remoteInfo: dict = {}):
        host = ''
        try:
            host = remoteInfo['IP']
        except Exception as e:
            print("Did not provide an IP, cannot connect")
            return None
        
        user = ''
        try:
            user = remoteInfo['sshUsername']
        except Exception as e:
            print("Did not provide a SSH username, cannot connect")
            return None
        
        port = 22
        try:
            port = remoteInfo['port']
        except Exception as e:
            print("Did not provide a port, setting default")

        key = ''
        try:
            key = remoteInfo['sshKey']
        except Exception as e:
            print("Did not provide a SSH key, setting default")

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        try:
            if (key != ''):
                client.connect(host,port=port,username=user,key_filename=key, banner_timeout=20)
            else:
                client.connect(host,port=port,username=user)
            return client
        except Exception as e:
            print("Could not connect, quiting")
            print(e)
            client.close()
            return None

    def getRemoteDiskInfo(self, remoteInfo: dict = {}):
        try:
            client = self.getRemoteConnection(remoteInfo)
            try:
                args = ['df', '-BG', remoteInfo['storageLocation'], '|', 'tail', '-n', '+2']
                stdin, stdout, stderr = client.exec_command(' '.join(args))
            except Exception as e:
                print("Could not get data from SSH session, quiting")
                print(e)
                return None

            diskSize = None
            diskUse = None
            line = stdout.readline()
            if line:
                if len(line) < 1:
                    print('ERROR: No valid output on remote storage')
                    print(stderr.read())
                else:
                    dfOutput = line.strip().split()
                    diskSize = int(dfOutput[1][:-1])
                    diskUse = int(dfOutput[2][:-1])

            if diskSize and diskUse:
                diskDict = {'diskSize': diskSize, 'diskUse': diskUse}
                return diskDict
            else:
                return None

        finally:
            client.close()


    def getRemoteInfo(self, locations: dict):
        remoteDict = {}
        for location in locations:
            try:
                # adapted from https://stackoverflow.com/a/35625078
                # Ping
                ping_str = "-n 1" if  platform.system().lower()=="windows" else "-c 1"
                args = "ping " + " " + ping_str + " " + location['IP']
                need_sh = False if  platform.system().lower()=="windows" else True
                pingResult = subprocess.run(args, stdout=subprocess.DEVNULL ,shell=need_sh).returncode == 0
                
                if pingResult:
                    # Get disk usage and size
                    diskInfo = self.getRemoteDiskInfo(location)
                    
                    # Count runs

                    # Put info into dict to be passed on
                    if diskInfo:
                        remoteDict[location['name']] = {'status':pingResult, 'diskSize':diskInfo['diskSize'], 'diskUse':diskInfo['diskUse']}
                    else:
                        remoteDict[location['name']] = {'status':pingResult}
                else:
                    remoteDict[location['name']] = {'status':pingResult}
            except Exception as e:
                print("ERROR: Could not process storageLocation, skipping")
                print(e)

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