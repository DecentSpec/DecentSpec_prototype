# BCxFL for DecentSpct Project

run the seed node:
```sh
cd seednode
source run_seed.sh
```

run the miner servers:
```sh
cd ../servers
source run_miner.sh
```

run the blockchain viewer, the console will remain in viewer's terminal:
```sh
cd ..
python run_view.py
```

or you can just run all cmds above through one batch file:
```sh
source run_all.sh
```

current config:

seednode    @ localhost:5000

servernodes @ localhost:8000-8002

viewer      @ localhost:5001

xterm is needed.
