#! /usr/bin/python3

#Functionality to get barcode and sequencing kit details
#
#Author: Jez Swann
#Date: Feburary 2020

import itertools

class nanoporeSeqOptions:
    def __init__(self, basecallerFile: str, barcodeFile:str = None, customRefPath:str = None):
        self.flowcells = {}
        self.basecallerFile = basecallerFile
        self.barcodeFile = barcodeFile
        self.processBasecallers(self.basecallerFile)
        if barcodeFile != None:
            self.processBarcodes(self.barcodeFile)
        self.customRefPath = customRefPath
        
    def processBasecallers(self, basecallerFile: str):
        with open(basecallerFile, 'r') as basecallersIO:
            flowcells = {}

            for line in itertools.islice(basecallersIO, 2, None):
                splitLine = line.split()
                if splitLine[0] not in flowcells:
                    flowcells[splitLine[0]] = {}

                barcoding = splitLine[2]
                if barcoding[0] in ['d', 'r']:
                    flowcells[splitLine[0]][splitLine[1]] = False
                else:
                    flowcells[splitLine[0]][splitLine[1]] = True
        
            self.flowcells = flowcells
            return flowcells

    def processBarcodes(self, barcodeFile: str):
        with open(barcodeFile, 'r') as barcodesIO:
            barcodes = []

            for line in itertools.islice(barcodesIO, 1, None):
                barcodes.append(line.strip())
        
            self.barcodes = barcodes
            return barcodes

    def getFlowcells(self):
        return sorted(list(self.flowcells.keys()))

    def getSequencingKits(self):
        return sorted(list(set(seqKit for flowcellDict in self.flowcells.values() for seqKit in flowcellDict.keys())))

    def getSequencingKitsForFlowcell(self, flowcell:str):
        return sorted(list(set(self.flowcells[flowcell].keys())))

    def getBarcodes(self):
        return sorted(self.barcodes)

    def getOptionalBarcodes(self):
        barcodes = self.getBarcodes()
        seqKits = self.getSequencingKits()
        return sorted([kit for kit in barcodes if kit not in seqKits])

    def getBarcodesForSeqkit(self, flowcell:str, seqKit:str):
        barcodingInc = self.flowcells[flowcell][seqKit]
        if barcodingInc:
            return True
        else:
            return self.getOptionalBarcodes()