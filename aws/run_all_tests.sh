#!/bin/bash
mkdir -p ~/stock-bazaar/results
mkdir -p ~/stock-bazaar/plots
echo "=== Running all tests ==="
echo "Deploying services..."
./deploy.sh
sleep 10
echo "Running cache comparison tests..."
./test_cache.sh
echo "Running fault tolerance tests..."
./test_fault.sh
echo "Giving All Results post Analyzing"
python3 analyze.py
echo "=== Testing is Complete ==="
echo "Results can be found in the results/ directory"
echo "Plots can be found in the plots/ directory"