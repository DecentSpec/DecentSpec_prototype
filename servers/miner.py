# nomally flask is single process, single thread, blocking-mode request handling 

import json
import time
from threading import Thread, Lock

from flask import Flask, request
import requests

from block import Block, Blockchain, Modelpool

app = Flask(__name__)

# the node's copy of blockchain
bc_lock = Lock()
mychain = Blockchain()
mychain.create_genesis_block()

pool_lock = Lock()
mypool = Modelpool()

# the address to other participating members of the network
peers = set()

# ========================================================================================
# peer register related api

# endpoint to add new peers to the network. i.e. add new friends
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the peer list
    peers.add(node_address)

    # Return the consensus blockchain to the newly registered node
    # so that he can sync
    return get_chain()

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

    # TODO try to notify several peers simultaneously 

    if response.status_code == 200:
        global mychain
        global peers
        # update chain and the peers
        chain_dump = response.json()['chain']
        mychain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code

def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
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
    required_fields = ["author", "content"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    tx_data["timestamp"] = time.time()
    global mypool
    mypool.add(tx_data)
    # TODO share the tx among other peers
    return "Success", 201

# endpoint to query unconfirmed transactions
@app.route('/pending_tx')
def get_pending_tx():
    global mypool
    return json.dumps(mypool.getPool())

# ========================================================================================
# mychain related api

@app.route('/chain', methods=['GET'])
def get_chain():
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

    return "Block added to the chain", 201

# ========================================================================================
# the daemon thread for mining automatically

# now we init the mine as a daemon thread
def mine_unconfirmed_transactions():

    global mypool
    while True:
        time.sleep(3)
        result = mychain.mine(mypool)
        if not result:
            pass
        else:
            mypool.clear()
            chain_length = len(mychain.chain)
            consensus()
            if chain_length == len(mychain.chain):
                announce_new_block(mychain.last_block)
            print("Block #{} is mined.".format(mychain.last_block.index))

def consensus():
    """
    Our naive consensus algorithm. If a longer valid chain is
    found, our chain is replaced with it.
    """
    global mychain

    longest_chain = mychain
    current_len = len(mychain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and mychain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        mychain = longest_chain
        return True

    return False

    """
    TODO
    Neutrino:
    there may be some unawared contention happening. due to the Equal length of chain will not be compare.
    but statistically it seems not a big problem
    """

def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)

thread = Thread(name='mine_daemon', target=mine_unconfirmed_transactions)
thread.setDaemon(True)
thread.start()