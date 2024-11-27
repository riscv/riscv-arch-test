// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
//
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test validates the software interrupt handling mechanism in RISC-V Machine Mode
// by examining interrupt behavior under various global and local interrupt enable configurations.
// -----------
// Test Methodology:
// - Enable global machine-mode interrupts
// - Clear machine software interrupt delegation
// - Test interrupt handling under different interrupt enable scenarios
// - Verify machine interrupt pending (MIP) state changes
// -----------
// Test Cases:
// Case 1: Disable MIE while MSIP is clear
// Case 2: Enable  MIE while MSIP is clear
// Case 3: Disable MIE while MSIP is set
// Case 4: Enable  MIE while MSIP is set
// -----------
// Expected Behavior:
// - Correct interrupt pending state management
// - Proper interrupt suppression when MIE is disabled
// - Interrupt taken when MIE is enabled
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
RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_M_SOFTWARE_INTR)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	2   
  	.option norvc

#ifndef MSIP_BASE  	
#define MSIP_BASE               0x02000000	// Base address for the memory-mapped MSIP control register.
#endif
main:	
	// Enable Global Interrupts:
	// Set Machine Status Register (mstatus) MIE bit
	// Allows maskable interrupts to be recognized
	LI(t0,    MSTATUS_MIE)
	csrrs x0, CSR_MSTATUS, t0

	// Clear Machine Software Interrupt Delegation:
	// Ensure software interrupts are handled in machine mode
	// Prevents potential redirection to lower privilege modes
	LI(a5, MIDELEG_MSI)
	csrrc  x0, CSR_MIDELEG, a5
	nop

	// Initialize MSIP Base: Clear Pending Software Interrupt
	// Reset memory-mapped Software Interrupt Pending control register
	// Establish a clean initial interrupt state
	LI(a5,     MSIP_BASE)
	SREG zero, 0(a5)
	nop

	// Test Case 01: Disable MSIE with Clear MIP
	// Verify interrupt behavior when MSIE is disabled and no pending interrupt exists
	LI(t0,    MIE_MSIP)
	csrrc x0, CSR_MIE, t0
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Test Case 02: Enable MSIE with Clear MIP
	// Confirm interrupt state when MSIE is enabled but no interrupt is pending
	csrrs x0, CSR_MIE, t0
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Test Case 03: Disable MSIE with Set MIP
	// Check program execution with pending interrupt but MSIE disabled
	csrrc x0, CSR_MIE, t0
	LI(t1,    0x1)
	SREG t1,  0(a5)
	nop
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3, a4)

	// Test Case 04: Enable MSIE with Set MIP
	// Validate interrupt handling when MSIE is enabled and interrupt is pending
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
