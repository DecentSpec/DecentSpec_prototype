# this is a dummy miner
from flask import Flask, request
import json
import torch
# TODO use TorchScript to serialize the model class
from model import SharedModel
from myutils import save_weights_into_dict, dict2tensor, tensor2dict

app = Flask(__name__)
initModel = SharedModel()
globalWeight = save_weights_into_dict(initModel)

preprocPara = {
    'x' : [43.07850074790703,0.026930841086101193] ,
    'y' : [-89.3982621182465,0.060267757907425355] ,
    'z' : [-58.52785514280172,7.434576197607559] ,
}
trainPara = {
    'batch' : 10,
    'lr'    : 0.001,
    'opt'   : 'Adam',
    'epoch' : 10,       # local epoch nums
    'loss'  : 'MSE',
}

def mix(base_model, local_weight, alpha = 1):
    if not base_model:
        return local_weight
    new_global = local_weight
    for k in new_global.keys():
        new_global[k] = (1-alpha) * base_model[k] \
                             + alpha * local_weight[k]        # EWMA
    return new_global

@app.route('/new_transaction', methods=['POST'])
def uploadLocal():
    global globalWeight
    data = request.get_json()
    stat = data['stat']
    print("get a new local with size {} and loss {}".format(stat['size'], stat['loss']))
    globalWeight = tensor2dict( mix( dict2tensor(globalWeight),     # only tensor can array operation
                                     dict2tensor(data['weight'])))  # so change to tensor temporarily
    return "success", 201

@app.route('/global_model', methods=['GET'])
def getGlobal():
    global globalWeight
    global preprocPara
    global trainPara
    data = {
        'weight' : globalWeight,
        'preprocPara' : preprocPara,
        'trainPara' : trainPara,
    }
    return json.dumps(data)

if __name__ == '__main__':
    app.run(port=8000)