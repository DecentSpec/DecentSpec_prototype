# multithread testing

import threading
import time
import random
from flask import Flask

app = Flask(__name__)

data_store = {'a': 1}
def interval_query():
    while True:
        time.sleep(1)
        vals = {'a': random.randint(0,100)}
        data_store.update(vals)

thread = threading.Thread(name='interval_query', target=interval_query)
thread.setDaemon(True)
thread.start()

@app.route('/')
def hello_world():
    return str(data_store['a'])

if __name__ == "__main__":
    app.run()