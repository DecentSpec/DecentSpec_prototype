'''
a simulator of database in memory
might change to a real db lib later
'''
from threading import Thread, Lock

class MinerDB:
    def __init__(self):
        self.key = []     # primary key, the name of the seed or its pub key
        self.addr = []    # first entry, ip addr with port
        self.role = []    # second entry, role
        # the role, might be "miner" or "seed" or "admin" (mother seed)

        '''
        currently only implement a permanent registration, no timer
        '''
        # self.timer = []   # third entry, timer
        # TODO: define the lock to protect those entries
        # self.__runTick()  # init the timer ticking for leasing

    def getList(self):
        return self.addr

    def regNew(self, key, addr, role="miner"):
        self.key.append(key)
        self.key.append(addr)
        self.role.append(role)

    def tick(self):
        pass

    def __runTick(self):    # we do not use it currently
        tick_thread = Thread(target=self.tick)
        tick_thread.setDaemon(True)
        tick_thread.start()

class RewardDB:
    def __init__(self):
        pass