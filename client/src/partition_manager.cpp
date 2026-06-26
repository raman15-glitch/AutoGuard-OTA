#include "partition_manager.h"
#include <filesystem>

namespace fs = std::filesystem;

PartitionManager::PartitionManager() {
    state_file_ = "partition_state.txt";
    LoadState();
}

void PartitionManager::LoadState() {
    std::ifstream file(state_file_);
    if (file.is_open()) {
        std::getline(file, active_slot_);
        file.close();
    } else {
        // Default factory state
        active_slot_ = "SLOT_A"; 
        SaveState();
    }
}

void PartitionManager::SaveState() {
    std::ofstream file(state_file_);
    file << active_slot_;
    file.close();
}

std::string PartitionManager::GetActiveSlot() { return active_slot_; }

std::string PartitionManager::GetInactiveSlot() {
    return (active_slot_ == "SLOT_A") ? "SLOT_B" : "SLOT_A";
}

bool PartitionManager::FlashToInactive(const std::string& downloaded_file) {
    std::string target_slot = GetInactiveSlot();
    std::cout << "[Hardware] Erasing " << target_slot << "..." << std::endl;
    std::cout << "[Hardware] Flashing payload to " << target_slot << "..." << std::endl;
    
    try {
        // Simulate flashing by copying the verified temp file to the slot file
        fs::copy_file(downloaded_file, target_slot + ".bin", fs::copy_options::overwrite_existing);
        return true;
    } catch (const fs::filesystem_error& e) {
        std::cerr << "[Error] Flash failed: " << e.what() << std::endl;
        return false;
    }
}

bool PartitionManager::BootAndCommit() {
    std::string new_slot = GetInactiveSlot();
    std::cout << "[System] Rebooting into " << new_slot << "..." << std::endl;
    
    // Simulate a health check (in a real car, this checks watchdog timers and CAN bus activity)
    std::cout << "[System] Performing kernel health checks..." << std::endl;
    bool health_check_passed = true; // We will simulate failures later
    
    if (health_check_passed) {
        std::cout << "[SUCCESS] Health checks passed. Committing " << new_slot << " as Active." << std::endl;
        active_slot_ = new_slot;
        SaveState();
        return true;
    } else {
        std::cout << "[FATAL] Health checks failed!" << std::endl;
        Rollback();
        return false;
    }
}

void PartitionManager::Rollback() {
    std::cout << "[Rollback] Aborting boot. Reverting to known-good partition: " << active_slot_ << std::endl;
    // The active_slot_ pointer remains unchanged, so the next boot falls back safely.
}