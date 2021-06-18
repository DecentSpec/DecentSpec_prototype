import sys
import json
import requests
import time
from flask import Flask, request
from database import MinerDB, RewardDB
import threading

seed = Flask(__name__)
myport = "5000"
if (len(sys.argv) == 2):
    myport = sys.argv[1]

myMembers = MinerDB()

# register related api 
@seed.route('/miner_peers', methods=['GET'])
def get_peers():
    global myMembers
    return json.dumps(myMembers.getList())

@seed.route('/register', methods=['POST'])
def reg_miner():
    global myMembers
    reg_data = request.get_json()
    myMembers.regNew(reg_data["name"], reg_data["addr"])
    print("sending: " + " ".join(myMembers.getList()))
    return json.dumps(myMembers.getList())

# ask this new seed to reseed the network
# TODO change the consensus to seed prioritized instead of length preferred
# TODO currently is GET, change to POST later
@seed.route('/new_seed', methods=['GET'])
def flush():   
    global myMembers
    post_object = {
        'name' : 'seed1',
        'admin' : 'admin1',
        'model' : 'model1',
        'para' : 'para1',
    }
    for addr in myMembers.getList():
        requests.post(addr+"/seed_update",
                    json=post_object,
                    headers={'Content-type': 'application/json'})
    return "new seed injected", 200

# another thread printing registered list periodically
def myDaemon():
    global myMembers
    while (True):
        print("currently members: " + " ".join(myMembers.getList()))
        time.sleep(3)

t = threading.Thread(target=myDaemon)
t.setDaemon(True)
t.start()

if __name__ == '__main__':
    seed.run(port=int(myport))