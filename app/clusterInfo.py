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

        timeout = 10
        try:
            if remoteInfo['timeout'] == 'short':
                timeout = 2
        except Exception as e:
            print("Did not provide a timeout, setting default")

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        try:
            if (key != ''):
                client.connect(host,port=port,username=user,key_filename=key, timeout=timeout)
            else:
                client.connect(host,port=port,username=user,timeout=timeout)
            return client
        except Exception as e:
            print("Could not connect, quiting")
            print(e)
            client.close()
            return None

    def getRemoteDiskInfo(self, remoteInfo: dict = {}):
        try:
            client = self.getRemoteConnection(remoteInfo)
            args = []
            timeout = 2
            try:
                tunnelIP = remoteInfo['tunnelIP']
                print("Using SSH tunnel to {}".format(tunnelIP))
                args = ['ssh', '{}@{}'.format(remoteInfo['sshUsername'], remoteInfo['tunnelIP']), '"', 'df', '-BG', remoteInfo['storageLocation'], '|', 'tail', '-n', '+2', '"']
            except Exception as e:
                print("No SSH tunnel needed")
                args = ['df', '-BG', remoteInfo['storageLocation'], '|', 'tail', '-n', '+2']

            try:
                stdin, stdout, stderr = client.exec_command(' '.join(args), timeout=timeout)
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
            else:
                print(stderr.read())

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
                
                if not pingResult:
                    location['timeout'] = 'short'

                # Get disk usage and size
                diskInfo = self.getRemoteDiskInfo(location)
                
                # Count runs

                # Put info into dict to be passed on
                if diskInfo:
                    remoteDict[location['name']] = {'status':True, 'diskSize':diskInfo['diskSize'], 'diskUse':diskInfo['diskUse']}
                else:
                    remoteDict[location['name']] = {'status':pingResult}
            except Exception as e:
                print("ERROR: Could not process storageLocation {}, skipping".format(location['name']))
                print(e)

        return remoteDict

    def processStep(self, fileStream, currentline):
        splitLine = currentline.strip().split('-')

        stepResult = {}
        stepResult['backup'] = int(splitLine[-1].strip('() \n'))
            # TODO deal with -1 status
        if stepResult['backup'] == 1 or stepResult['backup'] == 2:
            stepResult['step'] = splitLine[-4].strip()
        else:
            stepResult['step'] = splitLine[-3].strip()
        if stepResult['step'] == 'sequencing_summary.txt.gz':
            stepResult['step'] = 'sequencing_summary'

        currentline = fileStream.readline()
        additionalInfo = None
        if currentline:
            try:
                additionalInfo = json.loads(currentline.strip())
                for key, value in additionalInfo.items():
                    stepResult[key] = value
                currentline = fileStream.readline()
            except:
                pass

        if stepResult['backup'] == 0 and currentline:
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
                                

    def processBackupLog(self, line, backupLog):
        backupDict = {}
        try:
            while line:
                runName = line.strip()
                line = backupLog.readline()
                finishedRun = False
                backupDict[runName] = {}
                while not finishedRun:
                    stepResult, line, finishedRun = self.processStep(backupLog, line)
                    backupDict[runName][stepResult['step']] = {}
                    for key, value in stepResult.items():
                        if key != 'step':
                            backupDict[runName][stepResult['step']][key] = value

                if line:
                    line = backupLog.readline()

                if line:
                    line = backupLog.readline()
        except Exception as e:
            print("ERROR: Could not read log file correctly, quiting")
            print(e)

        return backupDict

    def processLocalBackupLog(self, backupLogFile: str):
        with open(backupLogFile, 'r') as backupLog:
            line = backupLog.readline()
            backupDict = self.processBackupLog(line, backupLog)
            return backupDict

    def processRemoteBackup(self, remoteInfo):
        try:
            logDir = remoteInfo['logDir']
        except Exception as e:
            print("No logDir for location {0}".format(remoteInfo['name']))
            return None

        try:
            client = self.getRemoteConnection(remoteInfo)
            args = []
            tunnelIP = None
            try:
                tunnelIP = remoteInfo['tunnelIP']
                print("Using SSH tunnel to {}".format(tunnelIP))
                args = ['ssh', '{}@{}'.format(remoteInfo['sshUsername'], remoteInfo['tunnelIP']), '"', 'find', logDir, '-maxdepth 1 -regextype posix-extended -regex \'.*/[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}:[0-9]{2}:[0-9]{2}\' | sort -r | head -n 1', '"']
            except Exception as e:
                print("No SSH tunnel needed")
                args = ['find', logDir, '-maxdepth 1 -regextype posix-extended -regex \'.*/[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{2}:[0-9]{2}:[0-9]{2}\' | sort -r | head -n 1']
            try:
                stdin, stdout, stderr = client.exec_command(' '.join(args))
            except Exception as e:
                print("Could not get data from SSH session, quiting")
                print(e)
                return None

            line = stdout.readline()
            if line and tunnelIP:
                args = ['ssh', '{}@{}'.format(remoteInfo['sshUsername'], remoteInfo['tunnelIP']), '"', 'cat', line.strip() + '/run.log', '"']
            elif line:
                args = ['cat', line.strip() + '/run.log']
            else:
                print('No suitable remote log - skipping')
                return None

            try:
                stdin, stdout, stderr = client.exec_command(' '.join(args))
            except Exception as e:
                print("Could not get data from SSH session, quiting")
                print(e)
                return None
            
            line = stdout.readline()                
            return self.processBackupLog(line, stdout)
        except Exception as e:
            print("ERROR: Could not read remote log file correctly, quiting")
            print(e)
            return None

        finally:
            client.close()

    def getBackupInfo(self, logDir: str="", dbRuns: dict={}, locations: dict={}):
        runStatusDict = {}
        if os.path.exists(logDir):
            # Find most recent log
            recentLogDir = max(glob.glob(os.path.join(logDir, '*-*-*_*:*:*')), key=os.path.getmtime)

            # Open each grid log file
            gridPath = os.path.join(recentLogDir,"run-grid*.log")
            for gridLogFile in glob.glob(gridPath):
                gridDict = self.processLocalBackupLog(gridLogFile)
                runStatusDict.update(gridDict)
        else:
            print("Error: Could not find local backup log location")

        if len(locations) > 0:
            for location in locations:
                try:
                    # Get backup
                    remoteBackup = self.processRemoteBackup(location)
                    
                    # Put info into dict to be passed on
                    if remoteBackup:
                        for run in remoteBackup.keys():
                            if run in runStatusDict:
                                for step, values in runStatusDict[run].items():
                                    values['remoteBackup'] = remoteBackup[run][step]['backup']
                except Exception as e:
                    print("ERROR: Could not process storageLocation {}, skipping".format(location['name']))
                    print(e)

        if len(dbRuns) > 0:
            for run in runStatusDict.keys():
                if run in dbRuns:
                    runStatusDict[run]['starttime'] = dbRuns[run]['starttime']
                    runStatusDict[run]['runLocation'] = dbRuns[run]['runLocation']
                    runStatusDict[run]['batches'] = dbRuns[run]['batches']

        return runStatusDict
