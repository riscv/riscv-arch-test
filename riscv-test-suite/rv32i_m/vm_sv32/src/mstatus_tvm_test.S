// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-32-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by: Muhammad Hammad Bashir, Allen Baum, Umer Shahid
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
// This test verifies the functionality of mstatus.TVM bit with the satp and sfence.vma
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
//	1. satp and sfence.vma accessed in M Mode with mstatus.tvm bit set -> Successful
//	2. satp and sfence.vma accessed in S Mode with mstatus.tvm bit set -> illegal instruction exception
//
// Total Expected Faults: 4
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
// 										satp access in M Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------
	li t0, 1																//initial value for t0 = 1
	#successful access
	csrw satp, t0  		                                        			// write satp with some value
	csrr t3, satp
	RVTEST_SIGUPD(x13,t3)

	#successful access
	sfence.vma
	nop
	nop

// ------------------------------------------------------------------------------------------------------------
// 										satp access in S Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------

	RVTEST_GOTO_LOWER_MODE Smode

	li t0, 1																//initial value for t0 = 1
	csrw satp, t0  		                                        			// write satp with some value
	nop

	li t0, 1
    csrrc t1, satp, t0  
    nop

    li t0, 1           
    csrrs t1, satp, t0
    nop

	sfence.vma
	nop
	nop

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode

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
