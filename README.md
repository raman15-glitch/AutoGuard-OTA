# AutoGuard-OTA: Resilient Automotive Firmware Management

AutoGuard-OTA is a production-grade, secure Over-The-Air (OTA) firmware update engine designed for safety-critical automotive environments. It addresses the fundamental challenge of ensuring vehicle firmware updates are secure, resumeable, and fail-safe against "bricking" scenarios.


## Core Engineering Features

- **A/B Dual-Bank Partitioning:** Implements an atomic A/B bank swap mechanism. If an update fails health checks, the system performs an automated rollback to the known-good partition, preventing vehicle downtime.
- **Cryptographic Integrity:** Uses RSA-4096 asymmetric signature verification to ensure firmware authenticity before execution.
- **Fault-Tolerant Networking:** Features a resumeable gRPC stream protocol designed to handle network interruptions (e.g., passing through tunnels) without restarting the update.
- **CI/CD Pipeline:** Fully automated end-to-end integration testing via GitHub Actions, verifying security and network stability on every commit.

## Architecture

- **C++ Edge Client:** Handles hardware-level partition management and cryptographic verification.
- **Python gRPC Engine:** Manages secure firmware streaming and binary payload handling.
- **Admin API (FastAPI):** A control plane to manage deployment campaigns, device cohorts, and fleet status.

## Quick Start (Local)

1. **Setup:**
   bash
   # Clone the repo
   git clone [https://github.com/YOUR_USERNAME/AutoGuard-OTA.git](https://github.com/YOUR_USERNAME/AutoGuard-OTA.git)
   cd AutoGuard-OTA
   
   # Setup environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r server/requirements.txt

2. **Run the Fleet:**

    # Start the Admin API
    cd server/src && uvicorn admin_api:app --port 8000 &
    # Start the OTA Engine
    python3 server/src/server.py &
    # Run the integration test suite
    pytest server/tests/test_e2e.py
