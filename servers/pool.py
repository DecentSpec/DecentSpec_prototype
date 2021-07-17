import json

class ModelPool:
    def __init__(self):
        self.pool = set()

    def getPool(self):      # return a list of dict , TODO sort it!
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

class NamedPool:
    def __init__(self):
        self.pool = {}
    def getPool(self):      # TODO sort it !!!
        return list( self.pool.values() )
    def add(self, new_model):
        author = new_model["author"]
        timestamp = new_model["timestamp"]
        if author in self.pool:
            if timestamp < self.pool[author]["timestamp"]:
                print("it is a staled tx")
                return False
        else:
            self.pool[author] = new_model
            return True
    def remove(self, subpool):
        for tx in subpool:
            au = tx["author"]
            if (au in self.pool) and (self.pool[au]["timestamp"] <= tx["timestamp"]):
                self.pool.pop(au)
    def flush(self):
        self.pool = {}
    def size(self):
        return len(self.pool)