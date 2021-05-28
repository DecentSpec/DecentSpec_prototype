class ModelPool:
    def __init__(self):
        self.pool = set()

    def getPool(self):      # return a list of dict 
        return list( map(lambda x: dict(x), self.pool) )

    def add(self, model):   # send in a dict and convert it to tuple to include it into the set
        t = tuple(model.items())
        if t in self.pool:  # if i already have this tx, return False
            print("I already have this tx")
            return False
        else:
            self.pool.add(t)
            return True

    def remove(self, subpool):
        self.pool = self.pool - subpool

    def clear(self):
        self.pool = set()


class ModelPara:
    def __init__(self):
        self.para = None
    
    def setPara(self, para):
        self.para = para