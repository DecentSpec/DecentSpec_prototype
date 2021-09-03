import json
import time
from myutils import *

def mix(transactions, para, base_model):

    # uncomment it when edge device implemented

    alpha = para['alpha']
    local_weights = []
    training_num = 0
    for tx in transactions:
        if tx['type'] == 'localModelWeight':
            MLdata = tx['content']
            size = MLdata['stat']['size']
            training_num += size
            weight = MLdata['weight']
            local_weights.append( (size, dict2tensor(weight)) )
    
    # print("local weights:")
    # print(local_weights)
    # print("base model:")
    # print(base_model)
    if len(local_weights) < 1:
        return None
    averaged_params = {}
    for k in local_weights[0][1].keys():                      # for each parameter in a model
        for i in range(0, len(local_weights)):
            local_sample_number, local_model_params = local_weights[i]
            w = local_sample_number / training_num
            if i == 0:
                averaged_params[k] = local_model_params[k] * w
            else:
                averaged_params[k] += local_model_params[k] * w                             # dataset size-weighted average
        averaged_params[k] = (1-alpha) * base_model[k] + alpha * averaged_params[k]      # EWMA
    # print("avged weights:")
    # print(averaged_params)
    return tensor2dict(averaged_params)

class Block:
    def __init__(self, index, transactions, timestamp, previous_hash,  \
                base_model, miner, para, nonce=0,):     # TODO, add those new arguments
        
        # model update list, all those local weights
        # TODO might introduce extra bug, since list is copy by ref
        self.transactions = transactions.copy()
        self.tx_hash = hashValue(self.transactions) # use the hash of tx to generate the whole block's hash 
        # global model, we use a lazy policy to generate global model when we need it, to save time
        self.base_model = base_model            # the start model for those local weights
        self.global_model = None              # the gathered new global model

        # header, since we do not use a Merkle tree, no need to package them into a standalone head
        self.index = index                      # also, block id
        self.timestamp = timestamp              # timestamp
        self.previous_hash = previous_hash      # hash of previous block
        self.nonce = nonce                      # nonce
        self.miner = miner                      # miner's public key

        # some inherit constants
        self.para = para              # model aggregation parameters together with training para

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        the content do not include the lazy global model
        """
        content = self.__dict__
        return genHash(content)

    def get_global(self):
        if self.global_model != None:
            return self.global_model
        if self.transactions == None:
            return self.base_model
        mixed = mix(self.transactions, self.para, dict2tensor(self.base_model))
        if mixed:
            return mixed
        else:
            return self.base_model

class BlockChain:

    def __init__(self, name):
        self.chain = []
        self.name = name
        self.difficulty = 0

    def flush(self):
        self.chain = []
        self.difficulty = 0

    def create_genesis_block(self, global_model, para, genesisMiner):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        self.difficulty = para["difficulty"]
        genesis_block = Block(  0, [], 0, GENESIS_HASH, # timestamp must be zero to keep hash the same
                                base_model={"this is":"an genesis block"},
                                miner=genesisMiner,
                                para=para)
        genesis_block.hash = genesis_block.compute_hash()
        genesis_block.global_model = global_model # manually set global model 
        self.chain.append(genesis_block)
        print("first block hash: {}".format(genesis_block.hash))

    @property
    def last_block(self):
        return self.chain[-1]

    def add_block(self, block, proof):
        """
        A function that adds the block to the chain after verification.
        Verification includes:
        * Checking if the proof is valid.
        * The previous_hash referred in the block and the hash of latest block
          in the chain match.
        """
        previous_hash = self.last_block.hash

        if block.index != self.last_block.index + 1:
            print("[add block failed] index mismatch")
            # print("their block index: " + str(block.index))
            # print("our block latest index: " + str(self.last_block.index))
            return False

        if previous_hash != block.previous_hash:
            print("[add block failed] hash link mismatch")
            # print("myhash " + previous_hash)
            # print("yourhash " + block.previous_hash)
            return False

        if not is_valid_proof(block, proof, self.difficulty):
            print("[add block failed] hash value mismatch")
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    def mine(self, unconfirmed_transactions, intr):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        
        if not unconfirmed_transactions:
            return False
        if intr.checkAndRst():
            return False
        
        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash,
                          miner=self.name,
                          base_model=self.last_block.get_global(),
                          para=self.last_block.para
                          )

        succ, proof = proof_of_work(new_block, self.difficulty, intr)
    
        if succ:
            self.add_block(new_block, proof)
        else:
            del new_block

        # do not forget to empty the pool in outside context
        return succ
