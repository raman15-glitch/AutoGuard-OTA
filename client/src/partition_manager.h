#ifndef PARTITION_MANAGER_H
#define PARTITION_MANAGER_H

#include <string>
#include <iostream>
#include <fstream>

class PartitionManager {
public:
    PartitionManager();
    
    std::string GetActiveSlot();
    std::string GetInactiveSlot();
    
    // Simulate flashing the downloaded file into the inactive bank
    bool FlashToInactive(const std::string& downloaded_file);
    
    // Attempt to boot the new slot and mark it active if successful
    bool BootAndCommit();
    
    // Revert back to the known-good slot
    void Rollback();

private:
    std::string active_slot_;
    std::string state_file_;
    
    void LoadState();
    void SaveState();
};

#endif // PARTITION_MANAGER_H