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
  RVTEST_CASE(1,"//check ISA:=regex(.*I.*Zicsr.*Sdtrig.*);def TEST_CASE_1=True;",icount_ge1_u_mode)
  RVTEST_SIGBASE(x1, signature_x1_0)
   
  CHECK_MISA_AND_SETUP_TRIGGERS()
   
  li t2, (CSR_TDATA1_TYPE_ICOUNT << 60 |\
          CSR_TDATA1_DMODE_BOTH << 59  |\
          CSR_ICOUNT_ACTION_BREAKPOINT << 0 |\
          (2 << 10) |\
          CSR_ICOUNT_M |\
          CSR_ICOUNT_U)
  csrw tdata1,t2                            #set trigger values in tdata1
  nop                                       #wait for trigger to fire

 #endif   
trap_handler:
    csrr a3,tdata1
    RVTEST_SIGUPD(x1,a3)
    csrr t0, mcause
    csrr t1, mepc
    csrr t6,mepc
    csrr t2, mtval
    RVTEST_SIGUPD(x1, t0)
    RVTEST_SIGUPD(x1, t6)
    RVTEST_SIGUPD(x1, t2)

    # Prepare to jump to user_mode
    la t3, user_mode          # Load address of user_mode code
    csrw mepc, t3             # Set User mode entry point
    mret                      # Return to User mode
    
user_mode:           
    # Execute one instruction in U-mode
    addi a0, zero, 1
    addi a0, a0, 1
    nop                       # No-operation placeholder
    RVTEST_SIGUPD(x1, a0)
    csrr a3, tdata1           # Read the trigger status
    RVTEST_SIGUPD(x1, a3)     # Log trigger status
    
    # Prepare to jump back to Machine mode
    la t0, trap_exit          # Load address of exit point
    csrw mepc, t0             # Set Machine mode return address
    mret                      # Return to Machine mode
    
trap_exit:
    nop                       # Placeholder for post-trap processing
    j end                     # Jump to end to avoid re-entering the trap
		
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

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
tsig_end_canary:
CANARY;

#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
