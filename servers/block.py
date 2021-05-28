from hashlib import sha256
import json
import time

def mix(local_weights, aggr_para, base_model):

    # uncomment it when edge device implemented

    # alpha = aggr_para.alpha
    # training_num = 0
    # for idx in range(len(local_weights)):
    #     (sample_num, averaged_params) = local_weights[idx]
    #     training_num += sample_num

    # (sample_num, averaged_params) = local_weights[0]
    # for k in averaged_params.keys():                                                        # for each parameter in a model
    #     for i in range(0, len(local_weights)):
    #         local_sample_number, local_model_params = local_weights[i]
    #         w = local_sample_number / training_num
    #         if i == 0:
    #             averaged_params[k] = local_model_params[k] * w
    #         else:
    #             averaged_params[k] += local_model_params[k] * w                             # dataset size-weighted average
    #     averaged_params[k] = (1-alpha) * local_weights[k] + alpha * averaged_params[k]      # EWMA
    # return averaged_params

    return None

class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0, \
                base_model=None, miner="anonymous", difficulty=2, aggr_para=None):     # TODO, add those new arguments
        
        # model update list, all those local weights
        self.transactions = transactions
        # global model, we use a lazy policy to generate global model when we need it, to save time
        self.base_model = base_model            # the start model for those local weights
        self.global_model = None              # the gathered new global model

        # header, since we do not use a Merkle tree, no need to package them into a standalone head
        self.index = index                      # also, block id
        self.timestamp = timestamp              # timestamp
        self.previous_hash = previous_hash      # hash of previous block
        self.nonce = nonce                      # nonce
        self.miner = miner                      # miner's public key
        self.difficulty = difficulty            # difficulty

        # model aggregation parameters
        self.aggr_para = aggr_para              # model aggregation parameters

    def compute_hash(self):
        """
        A function that return the hash of the block contents.
        the content do not include the lazy global model
        """
        content = self.__dict__
        if 'global_model' in content:
            content.pop('global_model') # remove the gobal_model cause it is lazy generated
        block_string = json.dumps(content, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()

    def get_global(self):
        if self.global_model != None:
            return self.global_model
        if self.transactions == None or self.aggr_para == None:
            return None
        return mix(self.transactions, self.aggr_para, self.base_model)


class BlockChain:
    # difficulty of our PoW algorithm
    # currently it is fixed, but we will make it modifiable TODO
    difficulty = 2

    def __init__(self):
        self.chain = []
    
    def clear(self):
        self.chain = []

    def create_genesis_block(self):
        """
        A function to generate genesis block and appends it to
        the chain. The block has index 0, previous_hash as 0, and
        a valid hash.
        """
        genesis_block = Block(0, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

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

        if previous_hash != block.previous_hash:
            return False

        if not BlockChain.is_valid_proof(block, proof):
            return False

        block.hash = proof
        self.chain.append(block)
        return True

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block 
        and satisfies the difficulty criteria.
        """
        return (block_hash.startswith('0' * cls.difficulty) and
                block_hash == block.compute_hash())

    @classmethod
    def proof_of_work(cls, block):
        """
        Function that tries different values of nonce to get a hash
        that satisfies our difficulty criteria.
        """
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * cls.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            # remove the hash field to recompute the hash again
            # using `compute_hash` method.
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break

            block.hash, previous_hash = block_hash, block_hash

        return result

    def mine(self, unconfirmed_transactions):
        """
        This function serves as an interface to add the pending
        transactions to the blockchain by adding them to the block
        and figuring out Proof Of Work.
        """
        # unconfirmed_transactions = list(unconfirmed_transactions)
        # map(lambda x: x.getModel(), unconfirmed_transactions)
        # because set can not include dict, so we turn set into list and map each element in list from object to dict
        
        if not unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)

        self.add_block(new_block, proof)

        # do not forget to empty the pool in outside context
        return True
