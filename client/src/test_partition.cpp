#include "partition_manager.h"
#include <cassert>

int main() {
    PartitionManager pm;
    std::string initial_slot = pm.GetActiveSlot();
    
    // Simulate a successful flash
    pm.FlashToInactive("dummy_firmware.bin");
    
    // Test the swap
    bool success = pm.BootAndCommit();
    assert(success == true);
    assert(pm.GetActiveSlot() != initial_slot);
    
    std::cout << "Partition Manager logic verified successfully!" << std::endl;
    return 0;
}