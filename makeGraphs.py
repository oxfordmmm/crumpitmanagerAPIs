#! /usr/bin/python3

import pathlib
import time
from threading import Thread
import os.path
import argparse

import app.config
from app.liveRuns.runsInfo import *
from app.metadata.metaDataConnection import *
from graphs.plot_depth_by_barcode import *

class graphGenerator:
    def __init__(self):
        self.reload_cfg()
        self.mongoDBcfg = self.cfg.get('mongoDB')
    
    def reload_cfg(self):
        configFile = pathlib.Path("configs/config.yaml")

        self.cfg = app.config.Config()
        self.cfg.load(str(configFile))

    def getMetadata(self):
        try:
            sqlDBcfg = self.cfg.get('sqlDB')
            try:
                sqlDBcfg['ip']
                try:
                    sqlDBcfg['port']
                    try:
                        sqlDBcfg['database']
                        return metaDataConnection(ip=sqlDBcfg['ip'], port=sqlDBcfg['port'], database=sqlDBcfg['database'])
                    except Exception as e:
                        return metaDataConnection(ip=sqlDBcfg['ip'], port=sqlDBcfg['port'])
                except Exception as e:
                    try:
                        sqlDBcfg['database']
                        return metaDataConnection(ip=sqlDBcfg['ip'], database=sqlDBcfg['database'])
                    except Exception as e:
                        return metaDataConnection(ip=sqlDBcfg['ip'])
            except:
                try:
                    sqlDBcfg['port']
                    try:
                        sqlDBcfg['database']
                        return metaDataConnection(port=sqlDBcfg['port'], database=sqlDBcfg['database'])
                    except Exception as e:
                        return metaDataConnection(port=sqlDBcfg['port'])
                except Exception as e:
                    try:
                        sqlDBcfg['database']
                        return metaDataConnection(database=sqlDBcfg['database'])
                    except Exception as e:
                        logging.exception('Config file does not contain valid sql info, using defaults')

        except Exception as e:
            logging.exception('Could not find sql config info, using defaults')

    def liveRunGraphs(self):
        try:
            runs = runsInfo(self.mongoDBcfg['ip'], self.mongoDBcfg['port']).getLiveStats()
            for runName, run in runs.items():
                try:
                    run['run_name'] = runName
                    print('Starting live graphs for run {}'.format(runName))
                    live_start = time.time()
                    runInfo(run, self.mongoDBcfg['ip'], self.mongoDBcfg['port']).generateRunGraphs()
                    print('Finished live graphs for run {} in {:.2f} seconds'.format(runName, time.time() - live_start))
                except KeyboardInterrupt as e:
                    raise e
                except Exception as e:
                    print("Error producing graph for run {}".format(runName))
                    print(e)
            print("Finished live graphs")
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            print(e)
            print("could not connect to mongo db")
    
    def metaRunGraphs(self):
        try:
            liveRuns = runsInfo(self.mongoDBcfg['ip'], self.mongoDBcfg['port']).getLiveStats()
            metaRuns = self.getMetadata().getPreRunInfo()
            customRefPath = self.cfg.get('clusterInfo')['customRefsLocation']
            singImg = self.cfg.get('singImg')
            for run_name, run_data in metaRuns.items():
                if not os.path.exists(f'images/{run_name}-depth.png'):
                    if 'custom_refs' in run_data and run_name not in liveRuns.keys():
                        run_ref = os.path.join(customRefPath, run_data['custom_refs'])
                        if run_data['base_dir'] and os.path.exists(run_ref):
                            fq_path = os.path.join('/', *run_data['base_dir'].split('/')[:-1], 'basecalled_fastq')
                            if os.path.isdir(fq_path):
                                print('Starting meta graphs for run {}'.format(run_name))
                                meta_start = time.time()
                                plot_depth_by_barcode.run(run_name, ref_path=os.path.join(customRefPath, run_data['custom_refs']), fq_path=fq_path, sing_img=singImg, ref_name=run_data['custom_refs'], out_dir='images/')
                                print('Finished meta graphs for run {} in {:.2f} seconds'.format(run_name, time.time() - meta_start))
            
            print("Finished post run graphs")
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            print(e)
            print("Error occurred while generating metadata graphs, exiting.")
    
    def metaRunGraph(self, run_name: str):
        try:
            liveRuns = runsInfo(self.mongoDBcfg['ip'], self.mongoDBcfg['port']).getLiveStats()
            metaRuns = self.getMetadata().getPreRunInfo()
            customRefPath = self.cfg.get('clusterInfo')['customRefsLocation']
            singImg = self.cfg.get('singImg')
            if run_name in metaRuns:
                if not os.path.exists(f'images/{run_name}-depth.png'):
                    run_data = metaRuns[run_name]
                    if 'custom_refs' in run_data and run_name not in liveRuns.keys():
                        run_ref = os.path.join(customRefPath, run_data['custom_refs'])
                        if os.path.exists(run_ref):
                            fq_path = os.path.join('/', *run_data['base_dir'].split('/')[:-1], 'basecalled_fastq')
                            if os.path.isdir(fq_path):
                                print('Starting meta graphs for run {}'.format(run_name))
                                meta_start = time.time()
                                plot_depth_by_barcode.run(run_name, ref_path=os.path.join(customRefPath, run_data['custom_refs']), fq_path=fq_path, sing_img=singImg, ref_name=run_data['custom_refs'], out_dir='images/')
                                print('Finished meta graphs for run {} in {:.2f} seconds'.format(run_name, time.time() - meta_start))
                            else:
                                print("fastqs not avalable for meta graphs of run {}, exiting.".format(run_name))
                else:
                    print("graph already exists for run {}, exiting.".format(run_name))
            else:
                print("run {} doesn't exist in metadata DB, exiting.".format(run_name))
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            print(e)
            print("Error occurred while generating metadata graph for run {}, exiting.".format(run_name))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--run_name",
                        action = "store", 
                        dest = "run_name", 
                        metavar = "run_name",
                        help = "[OPTIONAL] run name")
    options = parser.parse_args()

    if not options.run_name:
        try:
            gg = graphGenerator()
            lgT = None
            mgT = None
            print("Starting graph threads")
            while True:
                if lgT == None:
                    print("Generating live graphs")
                    lgT=Thread(target=gg.liveRunGraphs())
                    lgT.start()
                else:
                    if not lgT.is_alive():
                        lgT = None

                if mgT == None:
                    print("Checking post run graphs")
                    mgT=Thread(target=gg.metaRunGraphs())
                    mgT.start()
                else:
                    if not mgT.is_alive():
                        mgT = None
                time.sleep(20)
        except KeyboardInterrupt:
            print('Stopping graphs threads')
    else:
        print("Running graph generation for run {}".format(options.run_name))
        graphGenerator().metaRunGraph(options.run_name)