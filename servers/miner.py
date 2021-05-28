# nomally flask is single process, single thread, blocking-mode request handling 

import json
import time
import sys
from threading import Thread, Lock

from flask import Flask, request, current_app
import requests

from block import Block, BlockChain
from model import ModelPool, ModelPara, LocalModel, SeedingMsg

BLOCK_GEN_INTERVAL = 3 # unit second
POOL_MIN_THRESHOLD = 1
SEED_ADDRESS = "http://127.0.0.1:5000"

app = Flask(__name__)

# global vars, together with their locks
# Very Important
# TODO currently all operation is LOCK FREE, need add lock in the future
bc_lock = Lock()
mychain = BlockChain()
mychain.create_genesis_block(None)

pool_lock = Lock()
mypool = ModelPool()            # candidate local models

para_lock = Lock()
mypara = ModelPara()            # model descriptor, template and related paras

peers_lock = Lock()
peers = set()
PEER_PREADDR = "http://127.0.0.1:"
myport = sys.argv[1]       # we save the port num from the command line

def getPeers():
    global peers
    global myport
    # Make a request to register with remote node and obtain information
    response = requests.get(SEED_ADDRESS + "/miner_peers")
    fulllist = response.json()
    fulllist.remove(myport)
    peers = set( map(lambda x: PEER_PREADDR+x+"/", fulllist) )
    print("peers:")
    print(peers)

getPeers()

# ========================================================================================
# model para related api

# flush the pool and chain when we get a new seed
# currently we did not use a knowledge transfer, just remove the old chain
@app.route('/seed_update', methods=['POST'])
def flush_chain():
    print("running at:")
    global mypara
    global mypool
    global mychain
    seed_msg = request.get_json()
    if not valid_seed(seed_msg):
        return "Invalid seed", 400
    mypara.setPara(SeedingMsg(seed_msg))
    mypool.clear()
    mychain.clear()
    mychain.create_genesis_block(None) # TODO extract the global model seed from seed msg
    return "Reseeded the chain", 201

def valid_seed(msg):
    # TODO check the seed sender is real admin
    return True

# ========================================================================================
# peer registrations related api

# comment this part because we only want the seed node to control your peer list
# seems centralize but not a bid deal

# # endpoint to add new peers to the network. i.e. add new friends
# @app.route('/register_node', methods=['POST'])
# def register_new_peers():
#     global peers
#     node_address = request.get_json()["node_address"]
#     if not node_address:
#         return "Invalid data", 400

#     # Add the node to the peer list
#     peers.add(node_address)

#     # Return the consensus blockchain to the newly registered node
#     # so that he can sync
#     return get_chain()

# i.e. ask myself to make friend with others (one another node)
# will be changed to the automatic sync with seed node
@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the node specified in the
    request, and sync the blockchain as well as peer data.
    """
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    global mychain
    global peers
    if response.status_code == 200:
        # update chain and the peers
        chain_dump = response.json()['chain']
        mychain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code

def create_chain_from_dump(chain_dump):
    generated_blockchain = BlockChain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain

# ========================================================================================
# mypool related api

# endpoint to submit a new transaction. This will be used by
# our application to add new data (posts) to the blockchain
@app.route('/new_transaction', methods=['POST'])
def new_transaction(): 
    tx_data = request.get_json()
    required_fields = ["author", "content", "timestamp"]
    # required_fields = list(LocalModel().__dict__.keys())  

    # TODO the tx should in consistence with our model packet structure and within certain generation of the model

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    global mypool

    if "do_not_spread" in tx_data:      # if it is from some other miners
        tx_data.pop("do_not_spread")
        mypool.add(tx_data)             # just add to the pool and do not spread
    else:                               # if it does not come from other miners
        mypool.add(tx_data)
        tx_data["do_not_spread"] = 1    # set the do not spread flag
        #  let a temporal thread to do the spread work to save time
        thread = Thread(target=spread_tx_to_peers, args=[tx_data])
        thread.start()

    return "Success", 201

def spread_tx_to_peers(tx):
    global peers
    for peer in peers:
        url = "{}new_transaction".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(tx, sort_keys=True),
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
    global mypara
    global_model = mychain.last_block().get_global()
    gen = mychain.last_block().index
    return json.dumps({ "global_model": global_model,
                        "generation": gen,
                        "seed": mypara.para.name})

@app.route('/chain', methods=['GET'])
def get_chain():
    global peers
    chain_data = []
    for block in mychain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       "peers": list(peers)})

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
                  block_data["nonce"])

    proof = block_data['hash']
    added = mychain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    # remove the duplicate tx in the received block from my local pool
    added_tx = set(map(lambda x: tuple(x.items()), block_data["transactions"])) # from list_of_dict to set_of_tuples, might remove this transition in the future
    
    global mypool
    mypool.remove(added_tx)

    return "Block added to the chain", 201

# ========================================================================================
# the daemon thread for mining automatically

# now we init the mine as a daemon thread
# TODO use a SNAPSHOT/buffered mining to avoid fork!
def mine_unconfirmed_transactions():

    global mypool
    while True:
        time.sleep(BLOCK_GEN_INTERVAL)  # check the pool size per BGI
        if mypool.size() >= POOL_MIN_THRESHOLD: # gen a new block when the size achieve our threshold
            print("i am trying mining")
            if mychain.mine(mypool.getPool()):  # TODO mine should be interrupt when receive a seed_update flush
                if consensus(): # i am the longest
                    announce_new_block(mychain.last_block)
                    mypool.clear()  # empty the pool once you finish your mine
                    print("Block #{} is mined.".format(mychain.last_block.index))
                else:
                    print("get a longer chain from somewhere else")
            else:
                print("sth wrong with the embedded mine method in the chain object")



def consensus():
    """
    Our naive consensus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global mychain
    global peers

    am_i_the_longest = True
    longest_chain = mychain.chain
    current_len = len(mychain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and mychain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain
            am_i_the_longest = False

    mychain.chain = longest_chain
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
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

thread = Thread(name='mine_daemon', target=mine_unconfirmed_transactions)
thread.setDaemon(True)  # auto stops when we shut down __main__
thread.start()

if __name__ == '__main__':
    app.run(port=int(myport))