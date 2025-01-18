/* 
//
//    Test trap entry, updates to relevant CSRs (mcause, mtval, scause and stval, etc.), and correct state restoration upon trap return.
//
    Developed by: Maria Rehman
*/
       // Trap here in this file is taken illegal instruction exceptions // 
/*
//	Scenerio 1:
//	This test will check the correct updated in the values of mcause and mtval when trap occurs in M mode
//	
//	Sceneario 2:
//	This test will check the correct updates in the value of mcause and mtval when trap occurs in S mode
//	
//	Scenerio 3:
//	This test will check the correct updates in the values of mcause and mtval when trap occurrs in U mode
//	
        // Delegate one of the exception like illegal instruction to be handled 
        // by S mode handler and then verify the following scenerios
        
//	Sceneario 4:
//	This test will check the correct updates in the value of scause and stval when trap occurs in S mode
//	
//	Scenerio 5:
//	This test will check the correct updates in the values of scause and stval when trap occurrs in U mode	

*/

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True ", m_trap_test_illegal_m_cause_tval, s_trap_test_illegal_m_cause_tval, u_trap_test_illegal_m_cause_tval, s_trap_test_illegal_s_cause_tval, u_trap_test_illegal_s_cause_tval) 

RVTEST_SIGBASE( x13,signature_x13_1)

main:
#ifdef rvtest_mtrap_routine	// Verification of existance of rvtest_mtrap_routine
	LI (a4, 0xceed)
	RVTEST_SIGUPD(x13,a4)
#endif

#ifdef rvtest_strap_routine	// Verification of existance of rvtest_mtrap_routine
	LI (a4, 0xbeed)
	RVTEST_SIGUPD(x13,a4)
#endif

	ALL_MEM_PMP          		  // set the PMP permissions for the whole memory
	csrw satp, zero  		  // write satp with all zeros (bare mode)

	// illegal instruction exception in M mode
	LI (t1, 0xdead)
	csrw 0xFFF, t1      // accessing non existing CSR will generate the illegal instruction exception
			    // exception will be handled in M mode 
	nop
	nop
		
	LI (a4, 0x0001) // this signature will give information that test for accessing "non existing csr" has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)
	
	RVTEST_GOTO_LOWER_MODE Smode    // goto S mode
	nop
	nop
	
	
	// illegal instruction exception in S mode
	LI (a4, 0xabcd)     
	csrrc t1,0xFFF,a4  // accessing non existing CSR will generate the illegal instruction exception
	nop
	nop
		
	LI (a4, 0x0002) // this signature will give information that test for accessing "non existing csr" has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)
	nop
	nop

	RVTEST_GOTO_MMODE       // goto M mode 
	nop
	nop

	
	RVTEST_GOTO_LOWER_MODE Umode
	nop
	nop

	// illegal instruction exception in U mode
	LI (a4, 0xbeef)
	csrrs t1,0xFFF,a4  // accessing non existing CSR will generate the illegal instruction exception
	nop
	nop
    
	LI (a4, 0x0003)
	RVTEST_SIGUPD(x13, a4)
	nop
	nop

	RVTEST_GOTO_MMODE
	nop
	nop

	LI (a4, 0x4)
	csrw medeleg, a4     // delegate illegal instruction exception 

	// illegal instruction exception in M mode
	LI (t1, 0xdead)
	csrw 0xFFF, t1      // accessing non existing CSR will generate the illegal instruction exception
			    // exception will be handled in M mode 
	nop
	nop
		
	LI (a4, 0x0004) // this signature will give information that test for accessing "non existing csr" has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)
	
	RVTEST_GOTO_LOWER_MODE Smode    // goto S mode
	nop
	nop
	
	
	// illegal instruction exception in S mode
	LI (a4, 0xabcd)     
	csrrc t1,0xFFF,a4  // accessing non existing CSR will generate the illegal instruction exception
					   // This exception will be handled in S mode
	nop
	nop
		
	LI (a4, 0x0005) // this signature will give information that test for accessing "non existing csr" has successfully returned from the trap handler
	RVTEST_SIGUPD(x13,a4)
	nop
	nop

	RVTEST_GOTO_MMODE      // goto m mode to avoid the other errors
	nop
	nop

	
	RVTEST_GOTO_LOWER_MODE Umode
	nop
	nop

	// illegal instruction exception in U mode
	LI (a4, 0xbeef)
	csrrs t1,0xFFF,a4  // accessing non existing CSR will generate the illegal instruction exception
	                // this exception will be handled in S mode
	nop
	nop
    
	LI (a4, 0x0006)
	RVTEST_SIGUPD(x13, a4)
	nop
	nop

	

#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 4
// -------------------------------------------------------------------------------------------------------------------------------
rvtest_data:
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe

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
