/* 
/*
        Note: Trap here in this file is taken load store address misaligned traps 
/*
//
//      Test trap entry, updates to relevant CSRs (mcause, mtval, scause and stval, etc.), and correct state restoration upon trap return.
//
//      Developed by: Maria Rehman

//	Scenerio 1:
//	This test will check the correct updated in the values of mcause and mtval when trap occurs in M mode
//	
//	Sceneario 2:
//	This test will check the correct updates in the value of mcause and mtval when trap occurs in S mode
//	
//	Scenerio 3:
//	This test will check the correct updates in the values of mcause and mtval when trap occurrs in U mode
//	
        // Delegate the exceptions load and store address misaligned exceptions to 
        // be handled by S mode handler and then verify the following scenerios
        
//	Sceneario 4:
//	This test will check the correct updates in the value of scause and stval when trap occurs in S mode
//	
//	Scenerio 5:
//	This test will check the correct updates in the values of scause and stval when trap occurrs in U mode	

*/

#include "model_test.h"

#include "arch_test.h"

// RVTEST_ISA("RV32I_Zicsr,RV32IFD_Zicsr,RV32EF_Zicsr,RV32EFD_Zicsr")
RVTEST_ISA("RV32IF_Zicsr,RV32IFD_Zicsr,RV64IF_Zicsr,RV64IFD_Zicsr,RV32EF_Zicsr,RV32EFD_Zicsr,RV64EF_Zicsr,RV64EFD_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True ", m_trap_test_load_m_cause_tval, m_trap_test_store_m_cause_tval,s_trap_test_load_m_cause_tval,s_trap_test_store_m_cause_tval, u_trap_test_load_m_cause_tval, u_trap_test_store_m_cause_tval, s_trap_test_load_s_cause_tval,s_trap_test_store_s_cause_tval, u_trap_test_load_s_cause_tval, u_trap_test_store_s_cause_tval) 

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
	

	LI (a4, 0xaaaa) 
   	LA(x17,rvtest_data)
	lw x5,3(x17)
	nop  
    	RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for loas address misaligned has successfullty returned from trap
    
    
	
	LA(x17,rvtest_data)
	sw t1,0(x17)    // will not give any exception
	sw t2,2(x17)    // will cause the exception
	nop
	nop
	
        LI (a4, 0xaaaa)   
    	RVTEST_SIGUPD(x13, a4)     // this signature will give information that test for store address misaligned has successfullty returned from trap
    
	
	
	RVTEST_GOTO_LOWER_MODE Smode
	nop
	nop

	LI (a4, 0xbbbb) 
   	LA(x17,rvtest_data)
	lw x5,3(x17)
	nop  
    RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for loas address misaligned has successfullty returned from trap
    
    
	
	LA(x17,rvtest_data)
	sw t1,0(x17)    // will not give any exception
	sw t2,2(x17)    // will cause the exception
	nop
	nop
	
        LI (a4, 0xbbbb)   
	RVTEST_SIGUPD(x13, a4)     // this signature will give information that test for store address misaligned has successfullty returned from trap
    
    	RVTEST_GOTO_MMODE 
    	nop
    	nop
    	
    	RVTEST_GOTO_LOWER_MODE Umode
    	nop
    	nop
    	
    	LI (a4, 0xcccc) 
   	LA(x17,rvtest_data)
	lw x5,1(x17)          // exception
	nop  
    	RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for loas address misaligned has successfullty returned from trap
    
    
	
	LA(x17,rvtest_data)
	sw t1,0(x17)    // will not give any exception
	sw t2,2(x17)    // will cause the exception
	nop
	nop
	
        LI (a4, 0xcccc)   
    	RVTEST_SIGUPD(x13, a4)  
    	
    	RVTEST_GOTO_MMODE
    	nop
    	nop
    	
	                       // Delegate and then check the same valuse for scause and stval//
	LI (a4, 0x50)
	csrw medeleg, a4
	
	RVTEST_GOTO_LOWER_MODE Smode
	nop
	nop

	LI (a4, 0xdddd) 
   	LA(x17,rvtest_data)
	lw x5,1(x17)
	nop  
    RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for loas address misaligned has successfullty returned from trap
    
    
	
	LA(x17,rvtest_data)
	sw t1,0(x17)    // will not give any exception
	sw t2,2(x17)    // will cause the exception
	nop
	nop
	
        LI (a4, 0xdddd)   
	RVTEST_SIGUPD(x13, a4)     // this signature will give information that test for store address misaligned has successfullty returned from trap
    
	RVTEST_GOTO_MMODE
    	nop
    	nop
    	
    	RVTEST_GOTO_LOWER_MODE Umode
	nop
	nop

	LI (a4, 0xeeee) 
   	LA(x17,rvtest_data)
	lw x5,1(x17)
	nop  
    RVTEST_SIGUPD(x13, a4)    // this signature will give information that test for load address misaligned has successfullty returned from trap
                              // will be handled in S
    
	
	LA(x17,rvtest_data)
	sw t1,0(x17)    // will not give any exception
	sw t2,2(x17)    // will cause the exception
	                // will be handled in S
	nop
	nop
	
        LI (a4, 0xeeee)   
	RVTEST_SIGUPD(x13, a4)     // this signature will give information that test for store address misaligned has successfullty returned from trap
    
    	
    	

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
    .fill 256*(XLEN/64),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 256*(XLEN/64),4,0xdeadbeef
#endif

#ifdef rvtest_strap_routine
strap_sigptr:
    .fill 256*(XLEN/64),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
