// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
// Developed by: Syed Ali Faraz Jaffery
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test validates the handling of Most Significant Bit (MSB) in mtimecmp and mtime registers
// to verify if these timers are considered signed or unsigned during comparison.
// -----------
// Test Methodology:
// - Disable global machine-mode interrupts
// - Verify initial machine interrupt pending (MIP) state
// - Set mtimecmp with MSB (bit 63) set to 1
// - Set mtime with different configurations to test comparison behavior
// - Observe and record machine interrupt pending (MIP) state changes
// -----------
// Test Cases:
// Case 1: Compare mtime with mtimecmp when MSB is set in mtimecmp
//         - Set mtimecmp to 0x8000000000000000
//         - Set mtime to a smaller value
//         - Verify no timer interrupt is pending
// Case 2: Compare mtime with mtimecmp when MSB is set in both registers
//         - Modify mtime to a value greater than mtimecmp
//         - Verify timer interrupt is triggered
// -----------
// Expected Behavior:
// - Correct handling of signed/unsigned comparison for timer registers
// - Proper timer interrupt generation based on register value comparisons
// - Accurate machine interrupt pending (MIP) state management
// ---------------------------------------------------------------------------------------------


#ifndef RVMODEL_MTIME_BASE 
#define RVMODEL_MTIME_BASE              0x0200bff8 	// Base address for the memory-mapped machine timer register.
#endif

#ifndef RVMODEL_MTIMECMP_BASE 
#define RVMODEL_MTIMECMP_BASE           0x02004000  	// Base address  for the memory-mapped machine timer-compare register.  
#endif

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
RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_MTIMECMP_SIGN)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
 	
#define TIMER_MAX_VALUE         0x8000000000000000  // Maximum Value for the memory-mapped machine timer-compare register.
#define TIMER_TEST_VALUE        0x200	    // Random Test Value

main:	
	
       	// Disable Global Interrupts:
    	// Mask the Machine Status Register (mstatus) Interrupt Enable (MIE) bit
    	// Prevents any maskable interrupts from interfering with the tests
    	LI(a1,    MSTATUS_MIE)		
    	csrrc x0, CSR_MSTATUS, a1 	  
       	
       	// Initial MIP State Capture:
    	// Read and store Machine Interrupt Pending (MIP) register
    	// Verifies initial timer interrupt state is clear
       	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3,  a4)
	
	// Timer Register Base and Test Value Initialization:
	// Load base addresses and predefined test values for timer comparison
	// Prepares registers for testing signed/unsigned timer behavior
	LI(a5,   RVMODEL_MTIMECMP_BASE) 
       	LI(a6,   RVMODEL_MTIME_BASE)
       	LI(t0,   TIMER_MAX_VALUE) 
       	LI(t1,   TIMER_TEST_VALUE)
       	 	
       	// Test Case 1: Signed Comparison with MSB Set
    	// Configure mtimecmp with Most Significant Bit (MSB) set to 1
    	// Demonstrates signed timer register comparison behavior    
       	SREG t0, 0(a5)		// mtimecmp = 0x8000000000000000 (set MSB to 1)
       	nop
       	SREG t1, 0(a6)		// mtime = 0x200 --> (mtime < mtimecmp)
       	nop
       	
       	
       	// Verify MIP State After First Test:
    	// Capture MIP register to confirm interrupt state
    	// Expects no timer interrupt triggered
       	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3,  a4)
	
	// Test Case 2: Trigger Timer Interrupt
	// Modify mtime to exceed mtimecmp
	// Validates timer interrupt generation mechanism
	ADDI t0, t0, 1
	nop
	SREG t0, 0(a6)		// mtime = 0x8000000000000001 --> (mtime > mtimecmp)
       	nop
       	
       	// Verify MIP State After Second Test:
    	// Capture MIP register to confirm timer interrupt pending
    	// Expects timer interrupt to be set
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
