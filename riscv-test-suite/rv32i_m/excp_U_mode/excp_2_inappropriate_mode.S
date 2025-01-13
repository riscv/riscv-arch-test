//
// In this access to the csr without appropriate privillage mode will cause the illegal 
// instruction mcause will have the exception code 2 like if try to access the mepc and 
// mstatus register then will cause illegal instruction
//

#include "model_test.h"

#include "arch_test.h"

RVTEST_ISA("RV32I_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", apro_prv_mod)

RVTEST_SIGBASE( x13,signature_x13_1)

main:
#ifdef rvtest_mtrap_routine					                				// Verification of existance of rvtest_mtrap_routine
	LI a4, 0xceed
	RVTEST_SIGUPD(x13,a4)
#endif
#ifdef rvtest_strap_routine					                				// Verification of existance of rvtest_strap_routine
	LI a4, 0xbeed
	RVTEST_SIGUPD(x13,a4)
#endif

 	ALL_MEM_PMP          		  // set the PMP permissions for the whole memory
	csrw satp, zero  		  // write satp with all zeros (bare mode)
	
	csrr a4, mstatus           // read mstatus value 
	RVTEST_SIGUPD(x13,a4)
	
	RVTEST_GOTO_LOWER_MODE Umode
	// Try to read the machine mode or Supervisor mode CSR now will raise exception because the 
	// lower privillege mode cannot access the higher privillege mode CSRs
	li t0,1
	csrw sstatus,t0           // try to write random value to sstatus  
	nop 

	// here we will update the signal with ffff because we are in U mode and we can not read the value of 
	// mcause
	
	LI a4, 0xffff         
	RVTEST_SIGUPD(x13,a4)
	
	// switching back to the M mode
	RVTEST_GOTO_MMODE
#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 22

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------



RVTEST_DATA_END                
.align 12
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

// test signatures initialization
signature_x13_1:
    .fill 64*(XLEN/32),4,0xcafebeef

// trap signatures initialization

#ifdef rvtest_strap_routine
strap_sigptr:
    .fill 64*(XLEN/32),4,0xbeefbeef
#endif

#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
