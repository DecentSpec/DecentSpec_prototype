import requests
import json
import torch

SEED_ADDR = "https://127.0.0.1:5000"
LOCAL_DATASET = "GPS-power.dat"

class DataFeeder:
    def __init__(self, dataPath):
        pass
    def setPreProcess(self, para):
        # set the pre-process para
        # check the data format compatibility
        return True
    def fetch(self):
        # return a dataset of UNCERTAIN size everytime
        return []

def fetchList(addr):
    # request to SEED_ADDR
    # reorder by the ping latency
    return ["https://127.0.0.1:8000"]

def getLatest(mList):
    return [], [], []

def initModel(para):
    return []

def localTraining(model, data, para):
    return [], [], []

def pushTrained(size, loss, weight, addr):
    pass
    # send to server

# a full life cycle =========================================

# local init
localFeeder = DataFeeder(LOCAL_DATASET)
minerList = fetchList(SEED_ADDR)
modelPara, standradPara, trainPara = getLatest(minerList[0])

# training related
myModel = initModel(modelPara)
if not localFeeder.setPreProcess(standradPara):
    print("incompatible data format, quit")
    exit(0)
size, loss, weight = localTraining(myModel, localFeeder.fetch(), trainPara)
pushTrained(size, loss, weight, minerList[0])

# end of the life cycle =====================================


