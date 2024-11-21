---------------------------------------------------------------------------------------------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
---------------------------------------------------------------------------------------------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
// Developed by: Syed Ali Faraz Jaffery
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test validates the timer interrupt handling mechanism in RISC-V Machine Mode
// by examining interrupt behavior under various timer and interrupt enable configurations.
// -----------
// Test Methodology:
// - Enable global machine-mode interrupts
// - Clear machine timer interrupt delegation
// - Configure timer compare (mtimecmp) and time (mtime) registers
// - Test interrupt handling under different timer and interrupt enable scenarios
// - Verify machine interrupt pending (MIP) state changes
// -----------
// Test Cases:
// Case 1: Disable MTIE when mtime < mtimecmp
// Case 2: Enable  MTIE when mtime < mtimecmp
// Case 3: Disable MTIE when mtime = mtimecmp
// Case 4: Enable  MTIE when mtime = mtimecmp
// -----------
// Expected Behavior:
// - Correct timer interrupt pending state management
// - Proper interrupt suppression when MTIE is disabled
// - Interrupt taken when MTIE is enabled
// - Consistent machine state preservation during interrupt handling
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
RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_M_TIMER_INTR)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	2   
  	.option norvc

#define MTIME_BASE              0x0200bff8 	// Base address  for the memory-mapped machine timer register.
#define MTIMECMP_BASE           0x02004000  	// Base address  for the memory-mapped machine timer-compare register.  	
#define TIMER_MAX_VALUE         0xFFFF	// Maximum Value for the memory-mapped machine timer-compare register.
main:	
	// Enable Global Interrupts:
	// Set Machine Status Register (mstatus) MIE bit
	// Allows maskable interrupts to be recognized
	LI(t0,     MSTATUS_MIE)
	csrrs x0,  CSR_MSTATUS, t0

	// Clear Machine Timer Interrupt Delegation:
	// Ensure timer interrupts are handled in machine mode
	// Prevents potential redirection to lower privilege modes
	LI(t0, MIDELEG_MTI)
	csrrc  x0, CSR_MIDELEG, t0
	nop

	// Initialize Timer Registers:
	// Configure timer compare (mtimecmp) and timer (mtime)
	// Create a controlled timer interrupt scenario
	LI(a0,     MTIMECMP_BASE) 
	LI(a1,     MTIME_BASE)
	LI(t1,     TIMER_MAX_VALUE)	
	SREG t1,   0(a0)
	nop
	SREG zero, 0(a1)
	nop

	// Test Case 01: Disable MTIE with mtime < mtimecmp
	// Verify interrupt behavior when MTIE is disabled and no timer interrupt is pending
	LI(t0,    MIE_MTIP)
	csrrc x0, CSR_MIE, t0
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Test Case 02: Enable MTIE with mtime < mtimecmp
	// Confirm interrupt state when MTIE is enabled but no timer interrupt is pending
	csrrs x0, CSR_MIE, t0
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Test Case 03: Disable MTIE when mtime = mtimecmp
	// Check program execution with pending timer interrupt but MTIE disabled
	csrrc x0, CSR_MIE, t0
	SREG  t1,  0(a1)
	nop
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Test Case 04: Enable MTIE when mtime = mtimecmp
	// Validate timer interrupt handling when MTIE is enabled and interrupt is pending
	csrrs x0, CSR_MIE, t0
	nop
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
