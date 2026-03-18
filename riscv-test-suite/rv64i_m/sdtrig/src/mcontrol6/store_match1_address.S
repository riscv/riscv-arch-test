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
  RVTEST_CASE(1,"//check ISA:=regex(.*I.*Zicsr.*Sdtrig.*);def TEST_CASE_1=True;",store_address_match1)
  RVTEST_SIGBASE(x1, signature_x1_0)
     
     CHECK_MISA_AND_SETUP_TRIGGERS()
     
       # Set the value of tdata2 to the address to match
    # Load upper 20 bits
   # Step 1: Load the upper 32 bits (0xFFFFFFFF80000000)
    lui x10, 0x80000          # Load upper 20 bits, x10 = 0x0000000080000000

   # Step 2: Load the lower 32 bits (0x00001234)
   lui x11, 0x1001            # Load 0x123 into the upper part of x11, x11 = 0x000001230000
   slli x11, x11, 16          # Shift left by 4 bits to align, x11 = 0x00001230
   slli x11, x11, 11          # Shift left by 8 bits to get 0x00001234 in the lower part

  # Step 3: Combine the upper and lower parts
   or x10, x10, x11          # Combine the upper and lower parts, x10 = 0x0000000080001234

    csrw tdata2, x10
   
  # Set up trigger to cause a trap on a breakpoint
  # Configure tdata1 for address match control
  li t2, (CSR_TDATA1_TYPE_MCONTROL6 << 60 | \
         CSR_TDATA1_DMODE_BOTH << 59 | \
         CSR_MCONTROL6_SELECT_ADDRESS << 21 | \
         CSR_MCONTROL6_SIZE_ANY << 16 | \
         CSR_MCONTROL6_CHAIN_DISABLED << 11 | \
         CSR_MCONTROL6_ACTION_BREAKPOINT << 12 | \
         CSR_MCONTROL6_MATCH_NAPOT << 7 | \
         CSR_MCONTROL6_M | \
         CSR_MCONTROL6_STORE)
  csrw tdata1, t2
  csrr t4,tdata1
  RVTEST_SIGUPD(x1, t4)
  csrr t6, tdata2
  RVTEST_SIGUPD(x1, t6)
  
    # Step 1: Load the upper 32 bits (0xFFFFFFFF80000000)
    lui t4, 0x80000          # Load upper 20 bits, x10 = 0x0000000080000000

   # Step 2: Load the lower 32 bits (0x00001234)
   lui t5, 0x1000            # Load 0x123 into the upper part of x11, x11 = 0x000001230000
   slli t5, t5, 12         # Shift left by 4 bits to align, x11 = 0x00001230


   # Step 3: Combine the upper and lower parts
    or t4, t4, t5          # Combine the upper and lower parts, x10 = 0x0000000080001234
    sd t5, 0(t4)           # store to trigger match (this should trigger the break)
    nop
    nop
 #endif

trap_handler:
  # Save trap information
  csrr t0, mcause         # Cause of the trap
  csrr t1, mepc           # Program counter at the time of trap
  csrr t2, mtval          # Trap value
  RVTEST_SIGUPD(x1, t0)   # Update signature with mcause
  RVTEST_SIGUPD(x1, t1)   # Update signature with mepc
  RVTEST_SIGUPD(x1, t2)   # Update signature with mtval

 #  # Check if the trigger hit bit is set (bit 22 in tdata1)
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
  .fill 128*(XLEN/32),4,0xdeadbeef

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
