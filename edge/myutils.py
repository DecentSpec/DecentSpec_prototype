import torch
import datetime
import time
import random
import string

# what you get from state_dict() is an list with tensor
# tensor can not be directly serialized
def dict2tensor(myDict):
    myWeight = {}
    for key in myDict.keys():
        myWeight[key] = torch.tensor(myDict[key])
    return myWeight

def tensor2dict(myWeight):
    myDict = {}
    for key in myWeight.keys():
        myDict[key] = myWeight[key].tolist()
    return myDict

# store and load weights
def save_weights_into_dict(model):
    return tensor2dict(model.state_dict())

def load_weights_from_dict(model, weights):
    model.load_state_dict(dict2tensor(weights))

def genName(num=10):
    salt = ''.join(random.sample(string.ascii_letters + string.digits, num))
    return salt

def genTimestamp():
    return time.time()