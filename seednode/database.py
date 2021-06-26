'''
a simulator of database in memory
might change to a real db lib later
'''

# TODO add lock for the database

from threading import Thread, Lock
import time

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
        return self.key[idx] + ' ' + self.addr[idx] + ' ' + str(self.timer[idx])

class RewardDB:
    def __init__(self):
        pass