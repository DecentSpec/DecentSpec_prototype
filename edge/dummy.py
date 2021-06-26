# this is a dummy miner
from flask import Flask, request
import json
import torch
# TODO use TorchScript to serialize the model class
from model import SharedModel
from myutils import save_weights_into_dict

app = Flask(__name__)
initModel = SharedModel()
globalWeight = save_weights_into_dict(initModel)

preprocPara = {
    'x' : [0,1] ,
    'y' : [0,1] ,
    'z' : [0,1] ,
}
trainPara = {
    'batch' : 10,
    'lr'    : 0.001,
    'opt'   : 'Adam',
    'epoch' : 10,
}

def mix(base_model, local_weight, alpha = 0.5):
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
    globalWeight = mix(globalWeight, data['weight'])

@app.route('/get_global', methods=['GET'])
def getGlobal():
    data = {
        'weight' : globalWeight,
        'preprocPara' : preprocPara,
        'trainPara' : trainPara,
    }
    return json.dumps(data)

if __name__ == '__main__':
    app.run(port=8000)