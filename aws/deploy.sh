#!/bin/bash
pkill -f "python3 catalog.py" || true
pkill -f "python3 order.py" || true
pkill -f "python3 frontend.py" || true
mkdir -p ~/stock-bazaar/data
cd ~/stock-bazaar
echo "Starting catalog service..."
python3 catalog.py > catalog.log 2>&1 &
sleep 5
echo "Starting order service replica 0..."
python3 order.py 0 > order0.log 2>&1 &
sleep 2
echo "Starting order service replica 1..."
python3 order.py 1 > order1.log 2>&1 &
sleep 2
echo "Starting order service replica 2..."
python3 order.py 2 > order2.log 2>&1 &
sleep 5
echo "Starting frontend service..."
python3 frontend.py > frontend.log 2>&1 &
echo "All services deployed!"
ps aux | grep python3