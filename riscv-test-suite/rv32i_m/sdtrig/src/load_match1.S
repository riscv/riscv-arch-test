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
  RVTEST_CASE(1,"//check ISA:=regex(.*I.*Zicsr.*Sdtrig.*);def TEST_CASE_1=True;",load_match1)
  RVTEST_SIGBASE(x1, signature_x1_0)
 
    CHECK_MISA_AND_SETUP_TRIGGERS()
      
    # Set the value of tdata2 to the address to match
  
    la t2,0x80001001 
    csrw tdata2, t2
   
  
    # Set the value of tdata1 for address match trigger
    li t2, (CSR_TDATA1_TYPE_MCONTROL6 << 28 |\
           CSR_TDATA1_DMODE_BOTH << 27  | \
           CSR_MCONTROL6_SELECT_ADDRESS << 21 |\
           CSR_MCONTROL6_SIZE_ANY <<16 |\
           CSR_MCONTROL6_CHAIN_DISABLED << 11  | \
           CSR_MCONTROL6_ACTION_BREAKPOINT << 12 |\
           CSR_MCONTROL6_MATCH_NAPOT <<7 | \
           CSR_MCONTROL6_M |\
           CSR_MCONTROL6_LOAD)
    csrw tdata1,t2
    csrr a3,tdata1
    RVTEST_SIGUPD(x1,a3)
    csrr t6,tdata2
    RVTEST_SIGUPD(x1, t6)
    
    # Trigger setup complete; now perform an instruction that will hit the trigger
    la t4,0x80001000
    lw t4, 0(t4)    # Load to trigger match (this should trigger the break)
    nop
    nop       
	
#endif
trap_handler:
    # Save trap information
     # Save trap information
    csrr t0, mcause
    csrr t1, mepc
    csrr t2, mtval
    RVTEST_SIGUPD(x1, t0)
    RVTEST_SIGUPD(x1, t1)
    RVTEST_SIGUPD(x1, t2)
   
    # Check if the trigger hit bit is set (bit 22)
    csrr t3, tdata1
    RVTEST_SIGUPD(x1,t3)
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
