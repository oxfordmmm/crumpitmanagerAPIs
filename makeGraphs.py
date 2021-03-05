#! /usr/bin/python3

import pathlib
import time

import app.config
from app.liveRuns.runsInfo import *

class liveRunsGraphs:
    def __init__(self):
        self.reload_cfg()
        mongoDBcfg = self.cfg.get('mongoDB')
        
        try:
            runs = runsInfo(mongoDBcfg['ip'], mongoDBcfg['port']).getLiveStats()
            for runName, run in runs.items():
                try:
                    run['run_name'] = runName
                    runInfo(run, mongoDBcfg['ip'], mongoDBcfg['port']).generateRunGraphs()
                    print('Made graph for run {}'.format(runName))
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    print("Error producing graph for run {}".format(runName))
                    print(e)

        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            print(e)
            print("could not connect to mongo db")
    
    def reload_cfg(self):
        configFile = pathlib.Path("configs/config.yaml")

        self.cfg = app.config.Config()
        self.cfg.load(str(configFile))


if __name__ == '__main__':
    try:
        while True:
            c=liveRunsGraphs()
            time.sleep(600)
    except KeyboardInterrupt:
        print('Stopping making graphs')
        
