//
// This test will check that when there is exception in M mode then it will be handled in 
// the M mode because traps never transition from a more-privileged mode to a less-privileged mode. 
// When a trap occurs, mtvec will hold the address of the respective trap handler. 
// This test verifies whether the system returns to the correct state after handling the trap. 
// It checks the value of mcause before entering the trap handler and after handling the trap 
// to ensure it reflects the expected values for different exceptions. Additionally, 
// it confirms that mtval contains the correct values for various exceptions.
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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", m_medeleg)

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
	
	csrr t3, mstatus           // read mstatus value 
	RVTEST_SIGUPD(x13,t3)
	
	// Traps never transition from a more-privileged mode to a less-privileged mode.
	// So if in M mode I delegate the illegal instructions to handle in S mode then
	// it will not handle in S mode instead of this m mode will handle the trap
	
	// Bit 2 corresponds to illegal instruction
	LI (t4, CSR_MEDELEG)    
	csrw medeleg, t4
	
	csrr a4,medeleg
	RVTEST_SIGUPD(x13, a4)

        ecall  // this ecall exception will be handled in the M mode
        nop 
        
        csrr a4, mstatus           // read mstatus value 
	RVTEST_SIGUPD(x13,a4)
        
        	
	li t1,1234
	csrw mvendorid,t1   // this will give an illegal instruction as trying to write the read only register and will bw handled in m MDOE
	nop
	 
	csrr t3, mstatus           // read mstatus value 
	RVTEST_SIGUPD(x13,t3)

	 nop
	 nop
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
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

#ifdef rvtest_strap_routine
strap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
