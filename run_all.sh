cd seednode
source run_seed.sh
cd ../servers
sleep 1 # sleep for 1s to let seed finish setup
source run_miner.sh
cd ..
python run_view.py