import subprocess
import requests
import os

# Configuration
API_URL = "http://127.0.0.1:8000/campaigns"
CLIENT_BINARY = "./ota_client"

def test_ota_end_to_end_success():
    """
    Proves that a new device can connect, receive an active campaign,
    download the payload, and cryptographically verify it.
    """
    
    # 1. SETUP: Create a new campaign for the default 'general' cohort
    payload = {
        "target_version": "3.0",  # New version to force an update
        "target_cohort": "general",
        "is_active": True
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        assert response.status_code == 200, f"FastAPI failed to create campaign: {response.text}"
    except requests.exceptions.ConnectionError:
        assert False, "FastAPI server is not running on port 8000!"

    # 2. EXECUTION: Prepare environment variables for the C++ client
    env = os.environ.copy()
    env["SERVER_HOST"] = "localhost:50051"
    env["DEVICE_ID"] = "AUTO-TEST-004"  

    print("\n[Test] Purging old firmware files to ensure clean state...")
    old_files = ["./client/build/firmware_v2.tmp", "./client/build/active_firmware.bin"]
    for f in old_files:
        if os.path.exists(f):
            os.remove(f)

    # --- ATTEMPT 1: The Intentional Drop ---
    print("\n[Test] Launching C++ Client (Attempt 1 - Expecting Tunnel Drop)...")
    result1 = subprocess.run(
        [CLIENT_BINARY], env=env, cwd="./client/build", capture_output=True, text=True
    )
    
    assert "Download interrupted" in result1.stdout, "Server did not trigger the expected network drop."
    print("[Test] Network drop successfully detected. Testing resume capability...")

    # --- ATTEMPT 2: The Resume and Verify ---
    print("[Test] Launching C++ Client (Attempt 2 - Expecting Resume and Success)...")
    result2 = subprocess.run(
        [CLIENT_BINARY], env=env, cwd="./client/build", capture_output=True, text=True
    )
    
    output = result2.stdout
    print(output) # Print final output for visibility
    
    # 3. ASSERTIONS: Did the resume and security checks pass?
    assert "Resuming from byte" in output, "Client failed to resume the partial download."
    assert "[Security] Checksum valid" in output, "SHA-256 Integrity check failed."
    assert "[SUCCESS] SIGNATURE MATCHED!" in output, "RSA Authenticity check failed."
    assert "partition swapped successfully" in output, "System failed to apply the update."
    
    # Ensure it didn't crash
    assert result2.returncode == 0, "C++ client exited with a crash code."