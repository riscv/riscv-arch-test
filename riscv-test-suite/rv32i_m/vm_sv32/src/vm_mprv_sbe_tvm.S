// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-32-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by:
// ----------------------------------------------------------------------------------------------------------------------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// ----------------------------------------------------------------------------------------------------------------------
// Test Explanation:
// RISC-V Privileged Architecture ISA Manual -- Section 10.3
// 
// Note: This test is based on RISC-V Privileged ISA version 1.12, which does not include SVADE and SVADU support.
// Future updates will align with ISA version 1.13.
// 
// This test sets the mprv bit of the mstatus register and attempts a load.
// This test will set tvm bit of mstatus (bit 20), use S mode, and generate an exception.
// This test sets the sbe bit of mstatus register.
//
// Total Expected Faults: 1
// ----------------------------------------------------------------------------------------------------------------------

//TODO: instead of using two different tests, use a single test for hart/software update.

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", mstatus_tvm)

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
	
	ALL_MEM_PMP          		                  	                      	// set the PMP permissions for the whole memory
	csrw satp, zero  		                                        			// write satp with all zeros (bare mode)

	#set the mstatus with the TVM bit
	LI (t4, MSTATUS_TVM)
	csrw mstatus, t4
	csrr t3, mstatus
	RVTEST_SIGUPD(x13,t3)



// ------------------------------------------------------------------------------------------------------------
// 												cross_mprv_load
// ------------------------------------------------------------------------------------------------------------
	
	RVTEST_GOTO_MMODE
	
	csrw satp, zero 	

	li t0,1
	#successful access
															//set the mtatus_mprv bit (17th bit)
	li t0, 1 << 17        						
	csrr t1, mstatus      
	or t1, t1, t0        
	csrw mstatus, t1              
	
 																	
	li t0, 0xFFFFE7FF    									
	csrr t1, mstatus     									
	and t1, t1, t0       									
	li t2, 0x080         									
	or t1, t1, t2        									
	csrw mstatus, t1     									
 
	

// ------------------------------------------------------------------------------------------------------------
// 												tvm_exception_s
// ------------------------------------------------------------------------------------------------------------

//This test will set tvm bit of mstatus (bit 20), use S mode, generate an exception using test case 2
	li t0,1
	#successful access

	li t0, 0                
	li t1, 1 << 20          
	csrr t0, mstatus        
	or t0, t0, t1           
	csrw mstatus, t0        


	RVTEST_GOTO_LOWER_MODE Smode       


	li t0, 1																//initial value for t0 = 1
	csrw satp, t0 
    csrr t0, satp 		                                        			// write satp with some value
	
    nop
	nop

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode



// ------------------------------------------------------------------------------------------------------------
// 										setting sbe in mstatus
// ------------------------------------------------------------------------------------------------------------
	li t0,1																  
	#successful access
	csrr t0, mstatush       												   
	li t1, 0x10      												  	      
	or t0, t0, t1          												    
	csrw mstatush, t0 
	csrr t3, mstatush       											    
	RVTEST_SIGUPD(x13,t3)


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