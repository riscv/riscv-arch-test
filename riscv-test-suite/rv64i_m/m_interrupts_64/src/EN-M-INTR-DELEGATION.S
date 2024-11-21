// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
//
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test validates M-mode interrupt delegation behavior
// by ensuring M-mode interrupts remain within machine mode when delegation is enabled.
// -----------
// Test Methodology:
// - Enable global machine-mode interrupts
// - Enable machine software interrupt delegation
// - Generate a software interrupt
// - Verify interrupt pending state
// - Enable local software interrupt
// - Confirm interrupt processing within machine mode
// -----------
// Expected Behavior:
// - Software interrupt handled within machine mode
// - Correct interrupt delegation mechanism
// - Proper machine status modifications during interrupt handling
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
RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",EN_M_INTR_DELEGATION)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc

#define MSIP_BASE               0x02000000	// Base address for the memory-mapped MSIP control register.
main:
	// Enable Global Interrupts:
	// Set Machine Status Register (mstatus) MIE bit
	// Allows maskable interrupts to be recognized and processed
	LI(t0,    MSTATUS_MIE)
	csrrs x0, CSR_MSTATUS, t0

	// Enable Machine Software Interrupt Delegation:
	// Configure interrupt delegation to allow potential redirection
	// Demonstrates interrupt delegation mechanism
	LI(a5, MIDELEG_MSI)
	csrrs  x0, CSR_MIDELEG, a5
	nop

	// Generate Software Interrupt:
	// Trigger software interrupt by writing 1 to MSIP control register
	// Validates interrupt generation under delegation configuration
	LI(a5,   0x1)
	LI(x5,   MSIP_BASE)
	SREG a5, 0(x5)
	nop

	// Capture Initial Interrupt Pending State:
	// Verify machine interrupt pending (MIP) register
	// Confirms software interrupt generation and pending status
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3,  a4)

	// Enable Local Software Interrupt:
	// Locally enable software interrupt handling
	// Triggers interrupt processing under delegation
	LI(a5,    MIE_MSIP)
	csrrs x0, CSR_MIE, a5
	nop

	// Verify Interrupt Handling:
	// Confirm MIP register after interrupt processing
	// Validates interrupt delegation and handling mechanism
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
