import sys
import json
import requests
from flask import Flask, request
from database import MinerDB, RewardDB

seed = Flask(__name__)
myport = sys.argv[1]

myMembers = MinerDB()

@seed.route('/miner_peers', methods=['GET'])
def get_peers():
    global myMembers
    return json.dumps(myMembers.getList())

@seed.route('/register', methods=['POST'])
def reg_miner():
    global myMembers
    reg_data = request.get_json()
    myMembers.regNew(reg_data["name"], reg_data["addr"])

@app.route('/new_seed', methods=['POST'])
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


if __name__ == '__main__':
    seed.run(port=int(myport))