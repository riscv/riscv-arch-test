// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
//
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test validates the global Machine Interrupt Enable (MIE) enable behavior
// by confirming interrupt processing when global interrupts are enabled.
// -----------
// Test Methodology:
// - Enable global machine-mode interrupts
// - Clear machine software interrupt delegation
// - Verify initial interrupt pending state
// - Generate a software interrupt
// - Confirm interrupt is processed when global MIE is enabled
// - Verify machine status changes during interrupt handling
// -----------
// Test Cases:
// Case 1: Verify initial interrupt pending state
// Case 2: Generate software interrupt
// Case 3: Verify mstatus state changes
// Case 4: Enable local software interrupt and process interrupt
// -----------
// Expected Behavior:
// - Interrupts processed when global MIE is enabled
// - Correct machine status modifications during interrupt handling
// - Proper interrupt delegation and processing
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
RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",EN_GLB_MIE)
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
	// Allows maskable interrupts to be recognized and processed
	LI(t0,    MSTATUS_MIE)
	csrrs x0, CSR_MSTATUS, t0

	// Clear Machine Software Interrupt Delegation:
	// Ensure software interrupts are handled in machine mode
	// Prevents potential redirection to lower privilege modes
	LI(a5, MIDELEG_MSI)
	csrrc  x0, CSR_MIDELEG, a5
	nop

	// Capture Initial MIP State:
	// Verify initial software interrupt bit (mip.msip) is clear
	// Establishes baseline interrupt state before testing
	csrrs a4, CSR_MIP, x0
	ANDI  a4, a4, 0x8
	nop
	RVTEST_SIGUPD(x3,  a4)

	// Generate Software Interrupt:
	// Trigger software interrupt by writing 1 to MSIP control register
	// Validates interrupt generation mechanism with global interrupts enabled
	LI(a5,   0x1)
	LI(x5,   MSIP_BASE)
	SREG a5, 0(x5)
	nop

	// Capture Initial Interrupt State:
	// Read mstatus to check interrupt-related status bits
	// Verifies MPIE and MIE states during interrupt generation
	csrrs a4, CSR_MSTATUS, x0
	RVTEST_SIGUPD(x3, a4)

	// Enable Local Software Interrupt:
	// Locally enable software interrupt handling
	// Prepares for potential interrupt processing
	LI(a5,    MIE_MSIP)
	csrrs x0, CSR_MIE, a5
	nop

	// Verify Mstatus After Interrupt:
	// Confirm MPIE and MIE status after interrupt processing
	// Validates global interrupt state transitions
	csrrs a4, CSR_MSTATUS, x0
	RVTEST_SIGUPD(x3, a4)

	// Verify Software Interrupt Cleared:
	// Confirm software interrupt bit is cleared in MIP register
	// Validates interrupt handling and clearing mechanism
	csrrs a4, CSR_MIP, x0
	ANDI  a4, a4, 0x8
	nop
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
