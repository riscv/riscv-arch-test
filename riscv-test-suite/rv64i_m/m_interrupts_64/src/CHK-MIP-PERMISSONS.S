// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
//
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test validates the read-only protection mechanism of the Machine Interrupt Pending (MIP) register
// by verifying that direct write attempts to MIP register bits do not modify the actual interrupt pending state.
// -----------
// Test Methodology:
// - Globally disable machine-mode interrupts
// - Clear potential pre-existing timer and software interrupt pending states
// - Attempt to write 1 to different interrupt pending bits (MSIP, MTIP, MEIP)
// - Verify that the MIP register remains unchanged after write attempts
// -----------
// Test Cases:
// Case 1: Validate initial MIP register state is zero
// Case 2: Attempt to write software interrupt pending bit (MIP.MSIP)
// Case 3: Attempt to write timer interrupt pending bit (MIP.MTIP)
// Case 4: Attempt to write external interrupt pending bit (MIP.MEIP)
// -----------
// Expected Behavior:
// - MIP register should remain read-only
// - No interrupt pending bits should change after write attempts
// - System maintains control over interrupt pending state
// ---------------------------------------------------------------------------------------------
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV64I_Zicsr")
# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT

RVTEST_CODE_BEGIN
 # ---------------------------------------------------------------------------------------------
#ifdef TEST_CASE_1
RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_MIP_PERMISSONS)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
  	
#ifndef MSIP_BASE  	
#define MSIP_BASE               0x02000000	// Base address for the memory-mapped MSIP control register.
#endif

#ifndef MTIME_BASE 
#define MTIME_BASE              0x0200bff8 	// Base address for the memory-mapped machine timer register.
#endif

#ifndef MTIMECMP_BASE 
#define MTIMECMP_BASE           0x02004000  	// Base address for the memory-mapped machine timer-compare register.  
#endif

main:	
	// Disable Global Interrupts:
	// Mask the Machine Status Register (mstatus) Interrupt Enable (MIE) bit
	// Prevents any maskable interrupts from being recognized during the test
	LI(a5,    MSTATUS_MIE)		
	csrrc x0, CSR_MSTATUS, a5	 

	// Clear Potential Timer Interrupt Pending:
	// Ensure a clean initial state by clearing any pre-existing timer interrupt
	// Prevents interference from previous timer interrupt states
	LI(a5,     -1)
	LI(a4,     MTIMECMP_BASE)	
	SREG a5,   0(a4)		
	nop

	// Clear Potential Software Interrupt Pending:
	// Reset software interrupt state to eliminate any pre-existing interrupt conditions
	LI(a5,     MSIP_BASE)
	SREG zero, 0(a5)		
	nop

	// Capture Initial MIP State:
	// Read and record Machine Interrupt Pending (MIP) register before test execution
	// Verifies initial interrupt state is clear (all zeros)
	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3,  a4) 

	// Force MIP Bit Setting:
	// Manually set software, timer, and external interrupt pending bits
	// Validate MIP register's read-only behavior
	LI(a0,    MIP_MSIP)		
	csrrw x0, CSR_MIP, a0		  

	LI(a0,    MIP_MTIP)
	csrrw x0, CSR_MIP, a0		  

	LI(a0,    MIP_MEIP)	
	csrrw x0, CSR_MIP, a0		  

	// Capture Final MIP State:
	// Verify that MIP register remains unchanged after attempted write operations
	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3,  a4)	
#endif
 # ---------------------------------------------------------------------------------------------
    # HALT
RVTEST_CODE_END
RVMODEL_HALT

RVTEST_DATA_BEGIN
.align 4

rvtest_data:
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
RVTEST_DATA_END


RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;
signature_x3_1:
    .fill 12*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 12*(XLEN/32),4,0xdeadbeef
tsig_end_canary:
CANARY;

#endif

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*(XLEN/32),4,0xdeadbeef

#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
