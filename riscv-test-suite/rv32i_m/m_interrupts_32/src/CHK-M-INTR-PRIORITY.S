// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
// Developed by: Syed Ali Faraz Jaffery
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test validates the interrupt priority mechanism in RISC-V Machine Mode, 
// specifically demonstrating that software interrupts take precedence over timer interrupts 
// when both are simultaneously pending.
// -----------
// Test Methodology:
// - Enable global machine-mode interrupts
// - Disable interrupt delegation to ensure interrupts are handled in machine mode
// - Simultaneously generate a software interrupt and a timer interrupt
// - Verify interrupt handling priority and state transitions
// -----------
// Test Scenarios:
// Case 1: Generate concurrent software and timer interrupts
// - Set timer compare (mtimecmp) to trigger a timer interrupt
// - Manually create a software interrupt pending state
// - Enable local software and timer interrupt handling
// -----------
// Key Validation Points:
// - Interrupt priority resolution mechanism
// - Software interrupt precedence over timer interrupts
// - Correct machine interrupt pending (MIP) state management
// - Proper interrupt enable and handling sequence
// -----------
// Expected Behavior:
// - Software interrupt should be processed before timer interrupt
// - Machine Interrupt Pending (MIP) register should reflect interrupt state changes
// - Interrupt handling follows strict priority rules defined in RISC-V specification
// ---------------------------------------------------------------------------------------------

#ifndef RVMODEL_MSIP_BASE
#define RVMODEL_MSIP_BASE               0x02000000	// Base address for the memory-mapped MSIP control register.
#endif

#ifndef RVMODEL_MTIME_BASE 
#define RVMODEL_MTIME_BASE              0x0200bff8 	// Base address for the memory-mapped machine timer register.
#endif

#ifndef RVMODEL_MTIMECMP_BASE 
#define RVMODEL_MTIMECMP_BASE           0x02004000  	// Base address for the memory-mapped machine timer-compare register.  
#endif 

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
RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_M_INTR_PRIORITY)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	2   
  	.option norvc
  		
#define TIMER_MAX_VALUE         0xFFFF	// Maximum Value for the memory-mapped machine timer-compare register.
main:
    	// Enable Global Interrupts:
    	// Set the Machine Status Register (mstatus) Interrupt Enable (MIE) bit
    	// Allows maskable interrupts to be recognized during the test
    	LI(t0,    MSTATUS_MIE)
    	csrrs x0, CSR_MSTATUS, t0 	
       	
    	// Clear Machine Interrupt Delegations:
    	// Disable delegation of both software and timer interrupts
    	// Ensures interrupts are handled in machine mode
    	LI(a3, MIDELEG_MSI)		
    	LI(a4, MIDELEG_MTI)		
    	OR a3, a3, a4
       	csrrc  x0, CSR_MIDELEG, a3
       	nop
       	
    	// Initialize Timer Registers:
    	// Load base addresses and maximum timer value
    	// Prepare for generating timer and software interrupts
    	LI(a1,     RVMODEL_MTIMECMP_BASE)
       	LI(a2,     RVMODEL_MTIME_BASE)
       	LI(t0,     TIMER_MAX_VALUE)
       	
    	// Configure Timer Interrupt:
    	// Set mtime and mtimecmp to trigger a timer interrupt
    	// Demonstrates timer interrupt generation mechanism
    	SREG t0,   0(a1)
       	nop
       	SREG zero, 4(a1)		
       	nop
       	SREG t0,   0(a2)
       	nop		
       	SREG zero, 4(a2)		
       	nop
       	
    	// Generate Software Interrupt:
    	// Write to memory-mapped Software Interrupt Pending (MSIP) register
    	// Creates a pending software interrupt alongside timer interrupt
    	LI(a3,   0x1)		
       	LI(t0,   RVMODEL_MSIP_BASE)
       	SREG a3, 0(t0)		
       	nop
       	
    	// Initial MIP State Capture:
    	// Read Machine Interrupt Pending (MIP) register before interrupt handling
    	// Verifies initial interrupt pending states
    	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3, a4)
    	      	       	
    	// Enable Local Interrupts:
    	// Locally enable both software and timer interrupts
    	// Prepares processor to handle pending interrupts
    	LI(a1,    MIE_MSIP)		
    	LI(a2,    MIE_MTIP)		
    	OR a1,    a1, a2
       	csrrs x0, CSR_MIE, a1
       	nop		 
    			       	
    	// Final MIP State Capture:
    	// Read MIP register after interrupt handling
    	// Verifies interrupt processing and state changes
	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3, a4)	
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
