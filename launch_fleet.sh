#!/bin/bash

cleanup() {
    echo ""
    echo "[System] Shutting down the fleet..."
    kill $(jobs -p) 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM

echo "=========================================="
echo "    Launching AutoGuard OTA Fleet         "
echo "=========================================="

# 1. Start the Server in the correct directory
echo "[Cloud] Booting up Python gRPC Server..."
source venv/bin/activate

cd server/src
python3 server.py &
SERVER_PID=$!
cd ../..  # Go back to root

# Give the server 2 seconds to bind to the port
sleep 2 

echo "------------------------------------------"
echo "[Fleet] Launching Vehicles Concurrently..."
echo "------------------------------------------"

# 2. Launch all cars from the correct directory
cd client/build
export SERVER_HOST="localhost:50051"

export DEVICE_ID="TSLA-999"
./ota_client &

export DEVICE_ID="RIVN-404"
./ota_client &

export DEVICE_ID="FORD-101"
./ota_client &

cd ../.. # Go back to root

# Wait for all background processes to finish
wait