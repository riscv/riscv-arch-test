// ---------------------------------------------------------------------------------------------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// ---------------------------------------------------------------------------------------------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
// Developed by: Syed Ali Faraz Jaffery
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test verifies the 64-bit precision of machine timer (mtime) and 
// machine timer compare (mtimecmp) registers in RISC-V systems.
// -----------
// For each test case, the machine interrupt pending (mip.mtip) bit is checked:
// - mtip = 1 when mtime >= mtimecmp
// - mtip = 0 when mtime < mtimecmp
// - The test stores all mip values in the signature region for verification.
// ---------------------------------------------------------------------------------------------

#ifndef RVMODEL_MTIME_BASE 
#define RVMODEL_MTIME_BASE              0x0200bff8 	// Base address for the memory-mapped machine timer register.
#endif

#ifndef RVMODEL_MTIMECMP_BASE 
#define RVMODEL_MTIMECMP_BASE           0x02004000  	// Base address for the memory-mapped machine timer-compare register.  
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
RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_MTIME_LENGTH)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
	
// Test Value to check the length of memory-mapped machine timers register.
#define TIMER_TEST_VALUE_1      0x00000000FFFFFFFF
#define TIMER_TEST_VALUE_2      0xFFFFFFFF00000000

main:
	// Disable Global Interrupts
	LI(a1,    MSTATUS_MIE)	 
	csrrc x0, CSR_MSTATUS, a1	
	
	// Capture initial MIP state
	csrrs a4, CSR_MIP, x0		
	RVTEST_SIGUPD(x3, a4)
	
	// Load base addresses for timer registers
	LI(a1, RVMODEL_MTIMECMP_BASE) 
	LI(a2, RVMODEL_MTIME_BASE)
	
	// TEST CASE 1: Verify mtime 64-bit precision
	// Check behavior when lower 32-bits are max and upper 32-bits are zero
	LI(t1, TIMER_TEST_VALUE_1)
	SREG t1,   0(a2)
	nop			// Lower half of mtime = max (0xFFFFFFFF)
	
	// Read and store mip value
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3, a4)

	// TEST CASE 2: Verify mtime 64-bit precision
	// Check behavior when upper 32-bits are max and lower 32-bits are zero
	LI(t1, TIMER_TEST_VALUE_2)
	SREG zero, 0(a2)			// Upper half of mtime = max (0xFFFFFFFF)
	nop
	
	// Read and store mip value
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3, a4)

	// TEST CASE 3: Verify mtimecmp 64-bit precision
	// Check behavior when lower 32-bits are max and upper 32-bits are zero
	LI(t1, TIMER_TEST_VALUE_1)
	SREG t1,   0(a1)			// Lower half of mtimecmp = max (0xFFFFFFFF)
	nop
	
	// Read and store mip value
	csrrs a4, CSR_MIP, x0
	RVTEST_SIGUPD(x3, a4)

	// TEST CASE 4: Verify mtimecmp 64-bit precision
	// Check behavior when upper 32-bits are max and lower 32-bits are zero
	LI(t1, TIMER_TEST_VALUE_2)
	SREG zero, 0(a1)			// Upper half of mtimecmp = max (0xFFFFFFFF)
	nop
	
	// Read and store mip value
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
    .fill 12*(XLEN/32),4,0xdeadbeef

#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
