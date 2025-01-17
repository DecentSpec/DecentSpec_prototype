# nomally flask is single process, single thread, blocking-mode request handling 

# some configuration
NAMED_POOL = 0     # use author of the model as the hash of the model

import json
import time
import sys
from threading import Thread, Lock

from flask import Flask, request, current_app
import requests

from block import Block, BlockChain
from pool import ModelPool, NamedPool
from myutils import genName, Intrpt, check_chain_validity

BLOCK_GEN_INTERVAL = 3 # unit second
POOL_MIN_THRESHOLD = 1
SEED_ADDRESS = "http://127.0.0.1:5000"
REG_PERIOD = 19

# miner id generation ===========================================================
app = Flask(__name__)
myport = sys.argv[1]       # we save the port num from the command line
# myaddr = "http://127.0.0.1:" + myport
myaddr = "http://api.decentspec.org:" + myport
myname = genName()
print("***** NODE init, I am miner {} *****".format(myname))
if (len(sys.argv) > 2):
    SEED_ADDRESS = sys.argv[2]
    print("seed is " + SEED_ADDRESS)

# global vars, together with their locks ========================================
# Very Important
# TODO currently all operation is LOCK FREE, need add lock in the future
bc_lock = Lock()
mychain = BlockChain(myname)

pool_lock = Lock()
mypool = NamedPool() if NAMED_POOL else ModelPool()            # candidate local models
    
peers_lock = Lock()
peers = set()

status_lock = Lock()
mystatus = False

intr = Intrpt()

mypara = None
seedWeight = None

adminName = None

# TODO add status machine to miner

# register to seed node, might repeat in the future ============================
def register():
    global peers
    global myport
    global mychain
    global myname
    global seedWeight
    global mypara
    global mystatus
    global adminName
    # Make a request to register with remote node and obtain information
    data = {"name": myname, "addr": myaddr}
    headers = {'Content-Type': "application/json"}
    response = requests.post(SEED_ADDRESS + "/register", 
                            data=json.dumps(data), headers=headers)
    peers = set(response.json()['list'])
    seedWeight = response.json()['seedWeight']
    mypara = response.json()['para']
    adminName = response.json()['from']
    mystatus = True
    peers.remove(myaddr)
    # print("peers:")
    # print(peers)
    # NOTICE: we ONLY give the new comer its peer list, 
    # the network will teach this new comer the model by concensus


def regThread():
    while True:
        register()
        time.sleep(REG_PERIOD)

regThread = Thread(target=regThread)
regThread.setDaemon(True)
regThread.start()

print("wait for registration ...")
while not mystatus:
    pass
mychain.create_genesis_block(seedWeight, mypara, adminName)           # progress only after reg

# ==============================================================================
# seed flush related api

@app.route('/seed_update', methods=['POST'])
def flush_chain():
    print("reseeding ...")
    global mypara
    global mypool
    global mychain
    global mypara
    global seedWeight
    seed_msg = request.get_json()
    if not valid_seed(seed_msg):
        return "Invalid seed", 400
    mypool.flush()
    mychain.flush()
    seedWeight = seed_msg['seedWeight']
    mypara = seed_msg['para']
    mychain.create_genesis_block(seedWeight, mypara, seed_msg['from'])
    return "Reseeded the chain", 201

def valid_seed(msg):    # from the same seed server
    global adminName
    return msg['from'] == adminName

# ========================================================================================
# mypool related api
@app.route('/new_transaction', methods=['POST'])
def new_transaction(): 
    tx_data = request.get_json()
    required_fields = ["author", "content", "timestamp", "type"]

    # TODO the tx should in consistence with our model packet structure and within certain generation of the model

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    global mypool

    if "plz_spread" in tx_data:         # if edge ask me to help him spread
        print("DEBUG: I am going to share this tx with others")
        tx_data.pop("plz_spread")
        mypool.add(tx_data)
        thread = Thread(target=spread_tx_to_peers, args=[tx_data])
        thread.start()
    else:
        print("DEBUG: I will not share this tx with others")
        mypool.add(tx_data)             # just add to the pool and do not spread
        

    return "Success", 201

def spread_tx_to_peers(tx):
    global peers
    print("DEBUG: I am starting sharing this tx with others")
    data = json.dumps(tx, sort_keys=True)
    for peer in peers:
        url = "{}/new_transaction".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data,
                      headers=headers)

# endpoint to query unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    global mypool
    return json.dumps(mypool.getPool())

# ========================================================================================
# mychain related api

@app.route('/global_model', methods=['GET'])
def get_global():
    global mychain
    global_model = mychain.last_block.get_global()
    preprocPara = mychain.last_block.para["preprocPara"]
    trainPara = mychain.last_block.para["trainPara"]
    layerStructure = mychain.last_block.para["layerStructure"]
    gen = mychain.last_block.index
    return json.dumps({ "weight": global_model,
                        "generation": gen,
                        "preprocPara" : preprocPara,
                        "trainPara" : trainPara,
                        "layerStructure" : layerStructure,
                        })

@app.route('/chain', methods=['GET'])
def get_chain():
    global peers
    chain_data = []
    for block in mychain.chain:
        chain_data.append(block.__dict__)
    data = json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       })
    return data

@app.route('/chain_print', methods=['GET']) # API for viewer
def get_chain_print():
    global peers
    chain_data = []
    for block in mychain.chain:     # rewrite the block contents to shrink weights
        blockData = block.__dict__.copy()
        blockData["transactions"] = []
        for tx in block.transactions:
            if tx["type"] == "text":
                blockData["transactions"].append(tx)
            elif tx["type"] == "localModelWeight":
                shrinked_tx = tx.copy()
                shrinked_tx["content"] = "it is one local weights"
                blockData["transactions"].append(shrinked_tx)
            else:
                print("unrecognized tx type " + tx["type"])
        chain_data.append(blockData)
    data = json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       })
    return data

# endpoint to add a block mined by someone else to
# the node's chain. The block is first verified by the node
# and then added to the chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["base_model"],
                  block_data["miner"],
                  block_data["para"],
                  block_data["nonce"])
                # TODO block from dict to an object

    proof = block_data['hash']
    added = mychain.add_block(block, proof)

    if not added:
        print("outcome block get discarded")
        return "The block was discarded by the node", 400

    global intr
    intr.Raise()
    print("new outcome block added")
    # raiseInterupt2Miner()
    # remove the duplicate tx in the received block from my local pool
    added_tx = block_data["transactions"] if NAMED_POOL else set(map(lambda x: json.dumps(x, sort_keys=True), block_data["transactions"])) # from list_of_dict to set_of_tuples, might remove this transition in the future
    
    global mypool
    mypool.remove(added_tx)

    return "Block added to the chain", 201

# ========================================================================================
# the daemon thread for mining automatically
# TODO use a SNAPSHOT/buffered mining to avoid fork!
def mine_unconfirmed_transactions():

    global mypool
    global intr
    while True:
        time.sleep(BLOCK_GEN_INTERVAL)  # check the pool size per BGI
        if not mychain.difficulty:
            print("difficulty is not set")
            continue
        if mypool.size() >= POOL_MIN_THRESHOLD: # gen a new block when the size achieve our threshold
            print("i am trying mining")
            if mychain.mine(mypool.getPool(), intr):  # TODO mine should be interrupt when receive a seed_update flush
                if consensus(): # i am the longest
                    announce_new_block(mychain.last_block)
                    added_tx = mychain.last_block.transactions if NAMED_POOL else set(map(lambda x: json.dumps(x, sort_keys=True), mychain.last_block.transactions))
                    mypool.remove(added_tx)  # empty the pool once you finish your mine
                    print("Block #{} is mined.".format(mychain.last_block.index))
                    # print(mychain.last_block.__dict__)
                else:
                    print("get a longer chain from somewhere else")
            else:
                print("mine halted")
                
def create_list_from_dump(chain_dump):
    chain = []
    for idx, block_data in enumerate(chain_dump):
        # print("convert the folowing dict into object")
        # print(block_data)
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["base_model"],
                      block_data["miner"],
                      block_data["para"],
                      block_data["nonce"])
        block.hash = block_data["hash"]
        chain.append(block)
    return chain

def consensus():
    """
    Our naive consensus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global mychain
    global peers
    global mypool

    am_i_the_longest = True
    longest_chain = mychain.chain
    current_len = len(mychain.chain)

    for node in peers:
        response = requests.get('{}/chain'.format(node))
        data = response.json()
        length = data['length']
        chain = data['chain']
        # NOTICE this chain is a list of dict NOT an object!!!
        # print(length)
        # print(chain)
        if length > current_len and check_chain_validity(chain, mychain.difficulty):
            current_len = length
            longest_chain = create_list_from_dump(chain)
            am_i_the_longest = False

    mychain.chain = longest_chain
    mypool.flush()
    return am_i_the_longest
    """
    TODO
    Neutrino:
    there may be some unawared contention happening. due to the Equal length of chain will not be compare.
    but statistically it seems not a big problem; it does lead to problem
    """

def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    global peers
    for peer in peers:
        url = "{}/add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

mineThread = Thread(target=mine_unconfirmed_transactions)
mineThread.setDaemon(True)  # auto stops when we shut down __main__
mineThread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(myport))