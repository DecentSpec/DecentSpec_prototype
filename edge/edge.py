import requests
import json
import jsonpickle
import torch
import torch.nn as nn
import torch.optim as optim

from myutils import save_weights_into_dict, load_weights_from_dict
# TODO use TorchScript to serialize the model class
from model import SharedModel

SEED_ADDR = "http://127.0.0.1:5000"
LOCAL_DATASET = "GPS-power.dat"     # data structure 

class DataFeeder:                   # emulate each round dataset feeder
    def __init__(self, filePath):
        self.st_avg = []
        self.st_dev = []
        f = open(filePath, "r")
        rawList = f.readlines()
        f.close()
        print(f"file {filePath} is read into memory")
        print(f"totally {len(rawList)} lines")
        self.fullList = list(map(   lambda x: list( map(float, x.split(" "))), 
                                    rawList))
        self.ctr = 0
    def setPreProcess(self, para):
        # set the pre-process para
        # check the data format compatibility
        for key in para.keys():
            self.st_avg.append(para[key][0])    # average
            self.st_dev.append(para[key][1])    # std deviation
    def _preproc(self, partialList):
        st_list = []
        for i, line in enumerate(partialList):
            st_line = []
            for j, item in enumerate(line):
                st_line.append( (item - self.st_avg[j])/self.st_dev[j] )
            st_list.append(st_line)
        return st_list
    def fetch(self, size=10000):
        # return a dataset of UNCERTAIN size everytime
        partialList = self.fullList[self.ctr:self.ctr+size]
        self.ctr += size
        return self._preproc(partialList)
    def haveData(self):
        return self.ctr < len(self.fullList)
        # does this emulator have further dataset

def fetchList(addr):
    # request to SEED_ADDR
    # reorder by the ping latency
    # TODO change to real
    return ["http://127.0.0.1:8000"]

def getLatest(addr):
    response = requests.get("{}/get_global".format(addr))
    data = json.loads(response.content)
    return data['weight'], data['preprocPara'], data['trainPara']

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

class getDataSet(torch.utils.data.Dataset):
    def __init__(self, myList):
        self.myList = myList
    
    def __getitem__(self, index):
        row = self.myList[index]
        gps_tensor = torch.tensor([row[0], row[1]])
        power_tensor = torch.tensor([row[2]])
        return gps_tensor, power_tensor

    def __len__(self):
        return len(self.myList) 

def localTraining(model, data, para):
    batch = para['batch']
    lrate = para['lr']
    epoch = para['epoch']
    lossf = para['loss']
    opt = para['opt']
    size = len(data)
    trainset = getDataSet(data)
    trainLoader = torch.utils.data.DataLoader(  trainset,
                                                batch_size=batch,
                                                shuffle = True,
                                                num_workers=8)
    lossFunc = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr = lrate)

    for ep in range(epoch):
        loss_sum = 0.0
        for i, data in enumerate(trainLoader, 0):
            inputs, truth = data
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = lossFunc(outputs, truth)
            loss.backward()
            optimizer.step()
            loss_sum += loss.item()
        print(f"[epoch {ep+1}]\t[avg loss]\t{loss_sum/i}")
    return size, loss_sum/i, save_weights_into_dict(model)

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

# TODO loss estimation and map visualization