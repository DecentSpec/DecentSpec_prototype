import random
import string
import json
from hashlib import sha256

def genName(num=10):
    salt = ''.join(random.sample(string.ascii_letters + string.digits, num))
    return salt

def genHash(content):               # generate hash from block dict
    contentDup = content.copy()     # list in python is "ref" as function argument, so 
                                    # to avoid change the original dict, we copy it
    if 'global_model' in content:
        contentDup.pop('global_model') # remove the global_model cause it is lazy generated
    if 'hash' in content:
        contentDup.pop('hash')         # remove the hash itself
    block_string = json.dumps(contentDup, sort_keys=True)
    return sha256(block_string.encode()).hexdigest()