import random
import string

def genName(num=10):
    salt = ''.join(random.sample(string.ascii_letters + string.digits, num))
    return salt