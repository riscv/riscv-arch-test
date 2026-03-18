#include "model_test.h"
#include "arch_test.h"
#include "debug_defines.h"
RVTEST_ISA("RV64IZicsr_Sdtrig")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
  RVTEST_CASE(1,"//check ISA:=regex(.*I.*Zicsr.*Sdtrig.*);def TEST_CASE_1=True;",execute_match3)
  RVTEST_SIGBASE(x1, signature_x1_0)
  
   CHECK_MISA_AND_SETUP_TRIGGERS()
  
    # Set the value of tdata2 to the address to match
    # Load upper 20 bits
    # Step 1: Load the upper 32 bits (0xFFFFFFFF80000000)
     lui x10, 0x80000          # Load upper 20 bits, x10 = 0x0000000080000000

    # Step 2: Load the lower 32 bits (0x00001234)
   lui x11, 0x1234            # Load 0x123 into the upper part of x11, x11 = 0x000001230000
   slli x11, x11, 12         # Shift left by 4 bits to align, x11 = 0x00001230

   # Step 3: Combine the upper and lower parts
   or x10, x10, x11          # Combine the upper and lower parts, x10 = 0x0000000080001234
   csrw tdata2, x10
  
    
     # Set the value of tdata1 for address match trigger
    li t2, (CSR_TDATA1_TYPE_MCONTROL6 << 60 | \
            CSR_TDATA1_DMODE_BOTH << 59 | \
            CSR_MCONTROL6_SELECT_ADDRESS << 21 | \
            CSR_MCONTROL6_SIZE_ANY << 16 | \
            CSR_MCONTROL6_CHAIN_DISABLED << 11 | \
            CSR_MCONTROL6_ACTION_BREAKPOINT << 12 | \
            CSR_MCONTROL6_MATCH_LT << 7 | \
            CSR_MCONTROL6_M | \
            CSR_MCONTROL6_EXECUTE)
    csrw tdata1, t2
    csrr a3, tdata1
    RVTEST_SIGUPD(x1, a3)
    csrr t6, tdata2
    RVTEST_SIGUPD(x1, t6)
    
   # Code that accesses the matched data value (this should trigger the break)
    # Load upper 20 bits
   # Step 1: Load the upper 32 bits (0xFFFFFFFF80000000)
    lui t4, 0x80000          # Load upper 20 bits, x10 = 0x0000000080000000

   # Step 2: Load the lower 32 bits (0x00001234)
   lui t5, 0x1233           # Load 0x123 into the upper part of x11, x11 = 0x000001230000
   slli t5, t5, 0           # Shift left by 4 bits to align, x11 = 0x00001230


   # Step 3: Combine the upper and lower parts
    or t4, t4, t5          # Combine the upper and lower parts, x10 = 0x0000000080001234
    jalr x0,0(t4)         

#endif
trap_handler:
    # Save trap information
    csrr t0, mcause
    csrr t1, mepc
    csrr t2, mtval
    RVTEST_SIGUPD(x1, t0)
    RVTEST_SIGUPD(x1, t1)
    RVTEST_SIGUPD(x1, t2)

    # Check if the trigger hit bit is set (bit 25)
    csrr t3, tdata1
    RVTEST_SIGUPD(x1, t3)

end:
RVTEST_CODE_END
RVMODEL_HALT

# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

signature_x1_0:
  .fill 128 * (64 / 32), 4, 0xdeadbeef # Adjusted for 64-bit width

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
