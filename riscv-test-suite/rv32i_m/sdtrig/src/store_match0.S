#include "model_test.h"
#include "arch_test.h"
#include "debug_defines.h"
RVTEST_ISA("RV32IZicsr_Sdtrig")

.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
  RVTEST_CASE(1,"//check ISA:=regex(.*I.*Zicsr.*Sdtrig.*);def TEST_CASE_1=True;",store_match0)
  RVTEST_SIGBASE(x1, signature_x1_0)
      
  CHECK_MISA_AND_SETUP_TRIGGERS()
   
  # Set the address for tdata2 where the trigger should occur
  la t2, 0x80001234
  csrw tdata2, t2

  
  # Set up trigger to cause a trap on a breakpoint
  # Configure tdata1 for address match control
  li t2, (CSR_TDATA1_TYPE_MCONTROL6 << 28 | \
         CSR_TDATA1_DMODE_BOTH << 27 | \
         CSR_MCONTROL6_SELECT_ADDRESS << 21 | \
         CSR_MCONTROL6_SIZE_ANY << 16 | \
         CSR_MCONTROL6_CHAIN_DISABLED << 11 | \
         CSR_MCONTROL6_ACTION_BREAKPOINT << 12 | \
         CSR_MCONTROL6_MATCH_EQUAL << 7 | \
         CSR_MCONTROL6_M | \
         CSR_MCONTROL6_STORE)
  csrw tdata1, t2
  csrr t4,tdata1
  RVTEST_SIGUPD(x1, t4)
  csrr t6, tdata2
  RVTEST_SIGUPD(x1, t6)
  
  # Trigger setup complete; now perform an instruction that will hit the trigger
  la t4, 0x80001234
  sw t5, 0(t4)       
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

