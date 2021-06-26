# NOTICE !!!
# normally edge device have no knowledge of the NN class definition
# so this model.py sharing is IMPOSSIBLE
# TODO use TorchScript to serialize the model class

import torch.nn as nn
import torch.nn.functional as F
class SharedModel(nn.Module):

    # parameter-related operation is defined in init as nn
    def __init__(self):
        super(SharedModel, self).__init__()
        # input of network is a 2-dimensional feature(latitude, longitude)
        self.il = nn.Linear(2,50)  # inputlayer 
        self.hl1 = nn.Linear(50,50) # hiddenlayer 1
        self.hl2 = nn.Linear(50,50) # hiddenlayer 2
        self.ol = nn.Linear(50,1)   # outputlayer

    # parameter-irrelative operation is recommended as function
    def forward(self, x): # input x is the 2-dimensional spatial coordinates
        x = F.relu(self.il(x))
        x = F.relu(self.hl1(x))
        x = F.relu(self.hl2(x))
        x = self.ol(x)
        return x