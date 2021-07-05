'''
a simulator of database in memory
might change to a real db lib later
'''

# TODO add lock for the database

from threading import Thread, Lock
import time
import requests
from myutils import check_chain_validity

SCAN_RATE = 20      # compute reward per 10s
LEASING_RATE = 1    # rate of leasing timer reduction
LEASING_INIT = 20
class MinerDB:
    def __init__(self):
        self.key = []     # primary key, the name of the seed or its pub key
        self.addr = []    # first entry, ip addr with port
        self.role = []    # second entry, role
        # the role, might be "miner" or "seed" or "admin" (mother seed)

        '''
        currently only implement a permanent registration, no timer
        '''
        self.timer = []   # third entry, timer
        # TODO: define the lock to protect those entries
        self.__runTick()  # init the timer ticking for leasing

    def getList(self):
        return self.addr
    
    @property
    def size(self):
        return len(self.key)

    def regNew(self, key, addr, role="miner"):
        if not (key in self.key):       # if a new reg
            self.key.append(key)
            self.addr.append(addr)
            self.role.append(role)
            self.timer.append(LEASING_INIT)
        else:
            idx = self.key.index(key)
            self.addr[idx] = addr
            self.role[idx] = role
            self.timer[idx] = LEASING_INIT
        return 0

    def tick(self):
        while True:
            self.timer = list(map(lambda x:x-1, self.timer))
            # TODO a small bug here
            # can not use for to 
            i = 0
            while i < self.size:
                if self.timer[i] < 0:
                    self.key.pop(i)
                    self.addr.pop(i)
                    self.role.pop(i)
                    self.timer.pop(i)
                else:
                    i = i + 1
            time.sleep(LEASING_RATE) 

    def __runTick(self):    # we do not use it currently
        tick_thread = Thread(target=self.tick)
        tick_thread.setDaemon(True)
        tick_thread.start()
    
    def showMember(self, idx):
        return self.key[idx] + '\t' + self.addr[idx] + '\t' + str(self.timer[idx])

class Contributor:
    DELTA_THRESHOLD = 0.0
    def __init__(self, key, role):
        self.key = key
        self.role = role
        self.mined_block = 0
        self.shared_weight = 0
        self.reward = 0
    def submit(self, size, lossDelta):
        self.shared_weight += 1
        # print("get a local update with size {} and loss {}".format(size, lossDelta))
        if lossDelta > Contributor.DELTA_THRESHOLD:
            self.reward += int(size) * float(lossDelta)
    def mine(self):
        self.mined_block += 1
    def showContribution(self):
        return  self.key + '\t' + self.role + ' \t' + \
                str(self.mined_block) + '   \t' + \
                str(self.shared_weight) + '    \t' +str(self.reward)

class RewardDB:
    def __init__(self, MinerDB, para):
        self.rewardDict = {}
        
        self.myMember = MinerDB # link with memberlist for scan
        self.para = para        # link with para
        self.__runscan()
    
    def __flush(self):
        self.rewardDict = {}

    def scan(self):
        while True:
            peers = self.myMember.getList()
            print("scan the memberlist to compute reward")
            current_len = 0
            chain = []
            fromwhom = 'nobody'
            longest_chain = []
            for miner in peers:
                response = requests.get('{}/chain'.format(miner))
                length = response.json()['length']
                chain = response.json()['chain']
                if length > current_len and check_chain_validity(chain, self.para["difficulty"]):
                    current_len = length
                    longest_chain = chain
                    fromwhom = miner
            print("longest chain from {}".format(fromwhom))
            self.updateReward(longest_chain)
            print("============== Reward Database ===============")
            print("key     \trole \tmined\tupdate\treward")
            for node in self.rewardDict:
                print(self.rewardDict[node].showContribution())
            print("============== =============== ===============")
            time.sleep(SCAN_RATE)
    
    def updateReward(self, dictChain):
        self.__flush()  # calculate reward from the very first block
        for block in dictChain:
            # calculate miner contribution
            # print("the miner of this block is {}".format(block['miner']))
            key = block['miner']
            if block['index'] == 0:
                self.rewardDict[key] = Contributor(key, 'seed')
                self.rewardDict[key].mine()
                continue
            if not block['miner'] in self.rewardDict:
                self.rewardDict[key] = Contributor(key, 'miner')
            self.rewardDict[key].mine()

            for tx in block["transactions"]:
                if tx["type"] == "localModelWeight":
                    # calculate edge contribution
                    # print("the author of this update is {}".format(tx['author']))
                    key = tx['author']
                    if not tx['author'] in self.rewardDict:
                        self.rewardDict[key] = Contributor(key, 'edge')
                    self.rewardDict[key].submit(tx['content']['stat']['size'],
                                                tx['content']['stat']['lossDelta'])

    def __runscan(self):
        scan_thread = Thread(target=self.scan)
        scan_thread.setDaemon(True)
        scan_thread.start()