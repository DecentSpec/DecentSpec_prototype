import sys
import json
import requests
import time
from flask import Flask, request
from database import MinerDB, RewardDB
from model import SharedModel # TODO 
from myutils import save_weights_into_dict, genName
import threading

seed = Flask(__name__)
myport = "5000"
if (len(sys.argv) == 2):
    myport = sys.argv[1]
myName = genName()  # name of this seed server
print("***** NODE init, I am seed {} *****".format(myName))
myMembers = MinerDB()

layerStructure = [2,50,50,50,1]
seedName = genName()    # name of this seed
seedModel = SharedModel(layerStructure)
# preprocPara = {
#     'x' : [43.07850074790703,0.026930841086101193] ,
#     'y' : [-89.3982621182465,0.060267757907425355] ,
#     'z' : [-58.52785514280172,7.434576197607559] ,
# }
preprocPara = {
    'avg' : [43.07850074790703,-89.3982621182465,-58.52785514280172] ,
    'std' : [0.026930841086101193, 0.060267757907425355,7.434576197607559] ,
}
trainPara = {
    'batch' : 10,
    'lr'    : 0.001,
    'opt'   : 'Adam',
    'epoch' : 5,       # local epoch nums
    'loss'  : 'MSE',
}
Para = {
    'alpha' : 1,
    'preprocPara' : preprocPara,
    'trainPara' : trainPara,
    'layerStructure' : layerStructure,
    'difficulty' : 3,
}

rewardRecord = RewardDB(myMembers, Para)

# register related api 
@seed.route('/miner_peers', methods=['GET'])
def get_peers():
    global myMembers
    return json.dumps({'peers' : myMembers.getList()})

@seed.route('/register', methods=['POST'])
def reg_miner():
    global myMembers
    global Para
    reg_data = request.get_json()
    myMembers.regNew(reg_data["name"], reg_data["addr"])
    ret = {
        'name' : seedName,
        'from' : myName,
        'seedWeight' : save_weights_into_dict(seedModel),
        'para' : Para,
        'list' : myMembers.getList(),
    }
    # print(ret)
    # print("reged a new node")
    # print(ret["para"])
    return json.dumps(ret)

# ask this new seed to reseed the network
# TODO change the consensus to seed prioritized instead of length preferred
# TODO currently is GET, change to POST later
@seed.route('/new_seed', methods=['GET'])
def flush():   
    global myMembers
    global seedModel
    global Para
    seedModel = SharedModel(layerStructure)
    globalWeight = save_weights_into_dict(seedModel)
    post_object = {
        'name' : 'seed1',
        'from' : myName,
        'seedWeight' : globalWeight,
        'para' : Para,
    }
    for addr in myMembers.getList():
        requests.post(addr+"/seed_update",
                    json=post_object,
                    headers={'Content-type': 'application/json'})
    return "new seed injected", 200

# another thread printing registered list periodically
def memberList():
    global myMembers
    while (True):
        print("[t1] currently members:")
        for i in range(myMembers.size):
            print(myMembers.showMember(i))
        time.sleep(5)

memListThread = threading.Thread(target=memberList)
memListThread.setDaemon(True)
# memListThread.start()

if __name__ == '__main__':
    seed.run(host='0.0.0.0', port=int(myport))
