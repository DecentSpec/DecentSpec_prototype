cd seednode
source run_seed.sh
sleep 1 # sleep for 1s to let seed finish setup

cd ../servers
source run_miner.sh
sleep 1

cd ../edge
source run_edge.sh
sleep 1

python run_view.py