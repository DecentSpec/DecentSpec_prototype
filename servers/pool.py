import json
from threading import Lock

class ModelPool:
    def __init__(self):
        self.pool = set()

    def getPool(self):      # return a list of dict 
        return list( map(lambda x: json.loads(x), self.pool) )

    def add(self, model):   # send in a dict and convert it to tuple to include it into the set
        t = json.dumps(model, sort_keys=True)
        if t in self.pool:  # if i already have this tx, return False
            # TODO try to use hash to boost compare
            print("I already have this tx")
            return False
        else:
            self.pool.add(t)
            return True

    def remove(self, subpool):
        self.pool = self.pool - subpool

    def flush(self):
        self.pool = set()

    def size(self):
        return len(self.pool)

# class ModelPara:
#     def __init__(self):
#         self.para = None
    
#     def setPara(self, para):
#         self.para = para

# class LocalModel:       # this is not an actual class we will use, just format the json structure of tx we received
#     def __init__(self):
#         self.id = None          # client id, or pub_key
#         self.weights = None     # local parameters
#         self.size = None        # size of dataset
#         self.base = None        # version of base_global_model, may sha256 to uniquely assign it

# class SeedingMsg:             # this is not an actual class we will use, just format the json structure of seed we received
#     def __init__(self, raw):
#         self.admin = raw["admin"]
#         self.name = raw["name"]
#         self.model = raw["model"]
#         self.para = raw["para"]

class Intrpt:
    def __init__(self, desc="noDescription"):
        self.flag = False
        self.lock = Lock()
    def checkAndRst(self):
        with self.lock:
            ret = self.flag
            self.flag = False
        return ret
    def Raise(self):
        with self.lock:
            self.flag = True