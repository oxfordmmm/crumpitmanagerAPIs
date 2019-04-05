#! /usr/bin/python3

import os

class runInfo:
    def __init__(self,run: dict):
        self.run=run

    def getLiveStats(self):
        try:
            batches=os.listdir('{0}/all_batches/'.format(self.run['cwd']))
            batch_number=len(batches)
        except:
            batches=[]
            batch_number=0

        try:
            f5s=os.listdir('{0}/f5s/'.format(self.run['cwd']))
            f5_numbers=len(f5s)
        except:
            f5s=[]
            f5_numbers=len(f5s)

        try:
            percent=(f5_numbers / batch_number)*100
        except:
            percent=0
        
        output = { 
            "batches" : batches,
            "batch_number" : batch_number,
            "f5s" : f5s,
            "f5_numbers" : f5_numbers,
            "percent" : percent
        }
        return output