import datetime
import json
import time

import requests
from flask import render_template, redirect, request

from app import app

# The node with which our application interacts, there can be multiple
# such nodes as well.
CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"
SEEDNODE_ADDRESS = "http://127.0.0.1:5000"
ADDRESS = "http://127.0.0.1:"

posts = []
# miner_list = ["8000","8001","8002"]


def fetch_posts():
    """
    Function to fetch the chain from a blockchain node, parse the
    data and store it locally.
    """
    get_chain_address = "{}/chain_print".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)
    if response.status_code == 200:
        content = []
        chain = json.loads(response.content)
        for i, block in enumerate(chain["chain"]):
            for tx in block["transactions"]:
                new_tx = tx.copy()
                new_tx["content"] = "<from block#{}>  ".format(i) + new_tx["content"]
                content.append(new_tx)

        global posts
        posts = sorted(content, key=lambda k: k['timestamp'],
                       reverse=True)

@app.route('/')
def index():
    fetch_posts()
    return render_template('index.html',
                           title='YourNet: Decentralized '
                                 'content sharing',
                           posts=posts,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string)

# ============================================ function migrated
@app.route('/new_seed', methods=['POST'])
def flush():    # a dummy flush
    requests.get(SEEDNODE_ADDRESS + "/new_seed")
    return redirect('/')

# @app.route('/miner_peers', methods=['GET'])
# def get_peers():
#     global miner_list
#     return json.dumps(miner_list)
# ============================================= function migrated

@app.route('/submit', methods=['POST'])
def submit_textarea():
    """
    Endpoint to create a new transaction via our application.
    """
    post_content = request.form["content"]
    author = request.form["author"]
    port = request.form["port"]
    if port == "":
        port = "8000"

    timestamp = time.time()

    post_object = {
        'author': author,
        'content': post_content,
        'timestamp' : timestamp,
        'type' : 'text',
    }

    # Submit a transaction
    new_tx_address = "{}/new_transaction".format(ADDRESS + port)

    requests.post(new_tx_address,
                  json=post_object,
                  headers={'Content-type': 'application/json'})

    return redirect('/')


def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M:%S')
