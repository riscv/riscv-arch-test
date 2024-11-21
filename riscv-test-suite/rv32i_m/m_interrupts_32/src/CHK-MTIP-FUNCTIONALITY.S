// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
//
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test verifies the functionality of the Machine Timer Interrupt Pending (MTIP) mechanism
// by validating the generation, tracking, and clearing of timer interrupt pending states.
// -----------
// Test Methodology:
// - Globally disable machine-mode interrupts
// - Configure machine timer compare (mtimecmp) and machine time (mtime) registers
// - Clear any pre-existing timer interrupt pending state
// - Verify initial MTIP register state
// - Generate a timer interrupt by setting mtime equal to mtimecmp
// - Validate MTIP state changes
// - Clear the timer interrupt and confirm state reset
// -----------
// Expected Behavior:
// - MTIP register accurately reflects timer interrupt generation
// - Timer interrupt can be set and cleared as expected
// - Interrupt pending state changes align with timer register comparisons
// ---------------------------------------------------------------------------------------------

#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32I_Zicsr")
# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT

RVTEST_CODE_BEGIN
 # ---------------------------------------------------------------------------------------------
#ifdef TEST_CASE_1
RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_MTIP_FUNCTIONALITY)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	2   
  	.option norvc
  	
#define MTIME_BASE              0x0200bff8 	// Base address  for the memory-mapped machine timer register.
#define MTIMECMP_BASE           0x02004000  	// Base address  for the memory-mapped machine timer-compare register.  	
#define TIMER_MAX_VALUE         0xFFFF	// Maximum Value for the memory-mapped machine timer-compare register.
main:

	// Disable Global Interrupts:
	// Prevent maskable interrupts during test execution
	// Ensures a controlled test environment
	LI(a5,    MSTATUS_MIE)
	csrrc x0, CSR_MSTATUS, a5	 

	// Initialize Timer Registers:
	// Configure timer compare and timer base addresses
	// Prepare for timer interrupt testing
	LI(a1,    MTIMECMP_BASE)
	LI(a2,    MTIME_BASE)
	LI(t0,    TIMER_MAX_VALUE)

	// Reset Timer Registers:
	// Clear any existing timer interrupt conditions
	// Establish a clean initial state
	SREG t0,   0(a1)
	nop
	SREG zero, 4(a1)
	nop
	SREG zero, 0(a2)
	nop
	SREG zero, 4(a2)
	nop

	// Capture Initial MIP State:
	// Verify initial timer interrupt pending (mtip) bit is clear
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Generate Pending Timer Interrupt:
	// Set mtime equal to mtimecmp to trigger interrupt condition
	SREG t0, 0(a2)
	nop

	// Verify Timer Interrupt Pending:
	// Confirm mtip bit is set in Machine Interrupt Pending register
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Clear Timer Interrupt:
	// Reset mtime to be less than mtimecmp
	// Validate interrupt clearing mechanism
	SREG zero, 0(a2)
	nop

	// Confirm Interrupt Cleared:
	// Verify timer interrupt bit returns to zero
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
