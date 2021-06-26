import requests
import json
import jsonpickle
import torch
from myutils import save_weights_into_dict, load_weights_from_dict
# TODO use TorchScript to serialize the model class
from model import SharedModel

SEED_ADDR = "https://127.0.0.1:5000"
LOCAL_DATASET = "GPS-power.dat"     # data structure 

class DataFeeder:                   # emulate each round dataset feeder
    def __init__(self, dataPath):
        self.standardize_avg = []
        self.standardize_var = []
        pass
    def setPreProcess(self, para):
        # set the pre-process para
        # check the data format compatibility
        for key in para.keys():
            self.standardize_avg.append(para[key][0])
            self.standardize_var.append(para[key][1])
        return True
    def fetch(self, size=20):
        # return a dataset of UNCERTAIN size everytime
        return []
    def haveData(self):
        return True
        # does this emulator have further dataset

def fetchList(addr):
    # request to SEED_ADDR
    # reorder by the ping latency
    # TODO change to real
    return ["https://127.0.0.1:8000"]

def getLatest(addr):
    response = json.loads(requests.get(addr + "/get_global"))
    return dict2torch(response['weight']), response['preprocPara'], response['trainPara']

def pushTrained(size, loss, weight, addr):
    data = {
        'stat' : {  'size' : size,
                    'loss' : loss,},
        'weight' : weight
    }
    requests.post(  addr + '/new_transaction',
                    json=data,
                    headers={'Content-type': 'application/json'})
    # send to server

def localTraining(model, data, para):
    return [], [], []

# emulator local init =======================================
localFeeder = DataFeeder(LOCAL_DATASET)

while localFeeder.haveData():
# full life cycle of one round ==============================
    # miner communication
    minerList = fetchList(SEED_ADDR)
    modelWeights, preprocPara, trainPara = getLatest(minerList[0])
    # model init, should have built according to miner response
    # TODO sharedModel is impossible in real situation
    myModel = SharedModel()
    load_weights_from_dict(myModel, modelWeights)
    # data preprocessing setup
    localFeeder.setPreProcess(preprocPara)
    # local training
    size, loss, weight = localTraining(myModel, localFeeder.fetch(), trainPara)
    # send back to server
    pushTrained(size, loss, weight, minerList[0])
# end of the life cycle =====================================


