#!/bin/bash
mkdir -p ~/stock-bazaar/results
echo "Finding the current leader..."
LEADER_ID=$(grep "Leader selected: Replica" frontend.log | tail -1 | grep -o '[0-9]')
if [ -z "$LEADER_ID" ]; then
  echo "Could not find leader in logs, assuming Replica 0 is leader"
  LEADER_ID=0
fi
echo "Current leader is Replica $LEADER_ID"
echo "Running client before failure..."
python3 client_latency.py 0.8 "results/before_failure.json"
echo "Killing leader (Replica $LEADER_ID)..."
pkill -f "python3 order.py $LEADER_ID"
sleep 3
echo "Running client during failure..."
python3 client_latency.py 0.8 "results/during_failure.json"
echo "Restarting Replica $LEADER_ID..."
python3 order.py $LEADER_ID > order${LEADER_ID}_restarted.log 2>&1 &
sleep 5
echo "Running client after recovery..."
python3 client_latency.py 0.8 "results/after_recovery.json"
echo "Fault tolerance test completed"
echo "Checking replica consistency..."
for i in 0 1 2; do
  echo "Orders in replica $i:"
  cat data/orders$i.csv | wc -l
done