// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
//
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test verifies the functionality of the Machine Software Interrupt Pending (MSIP) mechanism
// by validating the generation, tracking, and clearing of software interrupt pending states.
// -----------
// Test Methodology:
// - Globally disable machine-mode interrupts
// - Clear any pre-existing software interrupt pending state
// - Verify initial MSIP register state
// - Generate a software interrupt by writing to the memory-mapped MSIP control register
// - Validate MSIP state changes
// - Clear the software interrupt and confirm state reset
// -----------
// Test Cases:
// Case 1: Validate initial MSIP state (zero)
// Case 2: Generate software interrupt
// Case 3: Verify software interrupt pending state
// Case 4: Clear software interrupt and verify state reset
// -----------
// Expected Behavior:
// - MSIP register accurately reflects software interrupt generation
// - Software interrupt can be set and cleared as expected
// - Interrupt pending state changes align with control register writes
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
RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_MSIP_FUNCTIONALITY)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
  	
#ifndef MSIP_BASE  	
#define MSIP_BASE               0x02000000	// Base address for the memory-mapped MSIP control register.
#endif
main:
	// Disable Global Interrupts:
	// Prevent any maskable interrupts during test execution
	// Ensures controlled test environment
	LI(a5,    MSTATUS_MIE)		
	csrrc x0, CSR_MSTATUS, a5	 

	// Clear Software Interrupt State:
	// Reset memory-mapped Software Interrupt Pending (MSIP) control register
	// Establish clean initial interrupt condition
	LI(a5,     MSIP_BASE)
	SREG zero, 0(a5)		
	nop

	// Capture Initial MIP State:
	// Read Machine Interrupt Pending (MIP) register
	// Verify initial software interrupt bit is clear
	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3,  a4) 

	// Generate Software Interrupt:
	// Write 1 to memory-mapped MSIP control register
	// Trigger software interrupt generation mechanism
	LI(a5,   0x1)		
	LI(x5,   MSIP_BASE)
	SREG a5, 0(x5)		
	nop

	// Verify Software Interrupt Pending:
	// Read MIP register to confirm software interrupt bit is set
	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3,  a4)

	// Clear Software Interrupt:
	// Reset MSIP control register
	// Validate interrupt clearing mechanism
	SREG zero, 0(x5)		
	nop

	// Confirm Interrupt Cleared:
	// Verify software interrupt bit returns to zero
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
