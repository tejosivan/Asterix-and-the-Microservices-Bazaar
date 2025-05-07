#!/bin/bash
mkdir -p ~/stock-bazaar/results
echo "=== Testing with Cache Enabled ==="
for p in 0 0.2 0.4 0.6 0.8; do
  echo "Running client with p=$p (cache enabled)"
  python3 client_latency.py $p "results/cache_enabled_p${p}.json"
  sleep 2
done
echo "Stopping cached frontend..."
pkill -f "python3 frontend.py"
echo "Starting frontend with caching disabled..."
python3 frontend.py --cache=false > frontend_nocache.log 2>&1 &
sleep 5
echo "=== Testing with Cache Disabled ==="
for p in 0 0.2 0.4 0.6 0.8; do
  echo "Running client with p=$p (cache disabled)"
  python3 client_latency.py $p "results/cache_disabled_p${p}.json"
  sleep 2
done
echo "All cache tests completed"
echo "Restarting original frontend..."
pkill -f "python3 frontend.py"
python3 frontend.py > frontend.log 2>&1 &