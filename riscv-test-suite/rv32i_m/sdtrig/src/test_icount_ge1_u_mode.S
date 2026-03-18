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
  RVTEST_CASE(1,"//check ISA:=regex(.*I.*Zicsr.*Sdtrig.*);def TEST_CASE_1=True;",icount_ge1_u_mode)
  RVTEST_SIGBASE(x1, signature_x1_0)
   
  CHECK_MISA_AND_SETUP_TRIGGERS()
   
  li t2, (CSR_TDATA1_TYPE_ICOUNT << 28 |\
          CSR_TDATA1_DMODE_BOTH << 27  |\
          CSR_ICOUNT_ACTION_BREAKPOINT << 0 |\
          (2 << 10) |\
          CSR_ICOUNT_M |\
          CSR_ICOUNT_S |\
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

    la t0, user_mode                
    csrw mepc, t0
    mret                    #upon mret switch to switch to user mode
    
user_mode:           
    csrr t1, mstatus               
    li t0, (0 << 11) 
    and t1, t1, t0              
    csrw mstatus, t1
   
    # Execute one instruction in U-mode
    li a0, 42                          
    
    csrr t1, mstatus
    li t0, (3 << 11)              
    or t1, t1, t0                
    csrw mstatus, t1              
    
    csrr a3,tdata1
    RVTEST_SIGUPD(x1,a3)  # checking if hit bit is set


    

end:
RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
  .align 12
   page_4k:
  .fill   4096/REGWIDTH, REGWIDTH, 0
RVTEST_DATA_END

  .align 12
rvtest_Sroot_pg_tbl:
  .fill   4096/REGWIDTH, REGWIDTH, 0
.section .data


# Output data section.
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

signature_x1_0:
  .fill 128*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine
mtrap_sigptr:

  .fill 128*4, 4, 0xabcdabcd
#endif

#ifdef rvtest_gpr_save
gpr_save:
  .fill 32*(XLEN/32), 4, 0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
