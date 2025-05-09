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
// This test verifies the functionality of satp register in M, S and U Mode using csrrw, csrrs, csrrc.
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
//	1. satp register accessed in M, S Mode -> Successful
//	2. satp register accessed in U Mode -> Illegal Instruction exception
//	3. Walking ones on the PPN of satp -> Successful
//	4. Walking ones on the ASID of satp -> Successful
// Total Expected Faults: 3
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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", satp_access_all_modes)

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

// ------------------------------------------------------------------------------------------------------------
// 										satp access in M Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------
	li t0, 1																//initial value for t0 = 1
	csrw satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrs satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrc satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

// ------------------------------------------------------------------------------------------------------------
// 										satp access in S Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------

	//Go to S mode
	RVTEST_GOTO_LOWER_MODE Smode

	li t0, 1																//initial value for t0 = 1
	csrw satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrs satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrc satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode

// ------------------------------------------------------------------------------------------------------------
// 										satp access in U Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------

	RVTEST_GOTO_LOWER_MODE Umode

	li t0, 1																//initial value for t0 = 1
	csrw satp, t0  		                                        			// write satp with some value
	nop
	nop

	csrs satp, t0  		                                        			// write satp with some value
	nop
	nop

	csrc satp, t0  		                                        			// write satp with some value
	nop
	nop

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode

// ------------------------------------------------------------------------------------------------------------
// PPN	Write all zeros, ones and walking ones to the PPN bits of satp register	csrw instruction
// ------------------------------------------------------------------------------------------------------------
	csrw satp, zero														// All ZEROES
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)

	li t0, 0x3FFFFF																//All ONES in the PPN
	csrw satp, t0
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)

RVTEST_SIGBASE( x14,signature_x14_1)

//Walking one test for PPN bits of satp register
	li t2, 0                                                                // shift left value
    li t3, 22                                                               // max value of shift left (PPN Width)
walking_ones_satp:
	li t0, 1																//initial value for t0 = 1
    sll t0, t0, t2
    addi t2, t2, 1
	csrw satp, t0
	csrr t1, satp
	RVTEST_SIGUPD(x14,t1)
	addi x14, x14, REGWIDTH
	bne t3, t2, walking_ones_satp

// ------------------------------------------------------------------------------------------------------------
// 							Walking ones to the ASID bitfield of satp register using csrw 
// ------------------------------------------------------------------------------------------------------------

	li t1, 0                		// Temporary storage for read-back
	li t0, 0x400000         		// Initial value

	// Loop for multiple satp writes and reads
	li t2, 8                		// Number of iterations (8 shifts)
walking_ones_asid:		
    csrw satp, t0     				// Write satp with the current value
    csrr t1, satp     				
    RVTEST_SIGUPD(x13, t1) 			
    slli t0, t0, 1    				// Shift left to prepare the next value
    addi t2, t2, -1   				// Decrement loop counter
    bnez t2, walking_ones_asid 		

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

// test signatures initialization
signature_x14_1:
    .fill 256*(XLEN/32),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
