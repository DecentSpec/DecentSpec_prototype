class ModelPool:
    def __init__(self):
        # self.pool = set()
        # set can not include a dict so we still use list, but list is much slower in index
        # TODO change from list to set
        self.pool = []

    def getPool(self):
        return self.pool

    def add(self, model):
        # self.pool.add(model)
        self.pool.append(model)
    
    # we use a list instead of set, so substraction is not supported currently
    # def remove(self, subpool):
    #     self.pool = self.pool - subpool

    def clear(self):
        # self.pool = set()
        self.pool = []

class LocalModel:
    def __init__(self, model):
        self.model = model
    
    def getModel(self):
        return self.model

class ModelPara:
    def __init__(self):
        self.para = None
    
    def setPara(self, para):
        self.para = para