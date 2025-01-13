//
// This test will check that when M mode has delegated the illegal instruction exception to S mode, 
// and S mode executes an illegal instruction then trap is taken in S mode, So after delegation 
// we will check that wheather it is being handled by expected handler if delegation is not done 
// then trap will be handled in the M mode. When a trap occurs, stvec will hold the address of the 
// respective trap handler. This test also check whether the system returns to the correct state 
// after handling the trap. It checks the value of scause before entering the trap handler and 
// after handling the trap to ensure it shows the expected values for different exceptions. 
// Additionally, it confirms that stval contains the correct values for various exceptions.

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", S_handler)

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


	ALL_MEM_PMP          		         // set the PMP permissions for the whole memory
	csrw satp, zero  		         // write satp with all zeros (bare mode)
	
	LI (t4, MSTATUS_TVM)    
	csrw mstatus, t4
	
	csrr t3, mstatus
	RVTEST_SIGUPD(x13,t3)
	
	// Traps never transition from a more-privileged mode to a less-privileged mode.
	// but if in M mode I delegate the illegal instructions to handle in S mode then
	// it will handle illegal instructions in S mode that occured in S mode

	LI a4, 1 << 2
	csrw medeleg, a4
	
	csrr a4,medeleg
	RVTEST_SIGUPD(x13, a4)      // will give sig value 4
	
	RVTEST_GOTO_LOWER_MODE Smode
	nop
	
	// Now use the satp it will generate illegal exception 
	li t1, 1																
	csrw satp, t1  		                   // writing satp exceptions will occur here
						   // will be handled in the S mode
	nop
	nop
					   
	csrr a4, scause           
 	RVTEST_SIGUPD(x13,a4) // will give sig value 2 
 	
 	csrr a4, stval
 	RVTEST_SIGUPD(x13,a4)  // the sig val (instruction that caused exception)
	
	nop
	nop
	nop

	RVTEST_GOTO_MMODE

		                                        

#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 22

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

#ifdef rvtest_strap_routine
.align 12                       //complete the 4KB permission memory range
rvtest_slvl1_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0,1,PTE_V | PTE_A | PTE_D | PTE_G)
#endif

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
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
