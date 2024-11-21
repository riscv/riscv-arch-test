// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This test belongs to the test plan for RISC-V Machine Mode Interrupts developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1rwjSTbxKiXTDydAdFAE_o7mez_hcFj9a-9d3dXRVc4s/edit?usp=sharing
//
// ---------------------------------------------------------------------------------------------
// Test Description:
// This test verifies the functionality of the 64-bit RISC-V machine timer and timer compare 
// registers (mtime and mtimecmp) by testing different combinations of upper and lower 32-bit values.
// -----------
// The test consists of 16 test cases organized in 4 groups:
// Group 1: mtimecmp = 0x0000000000000000 (all zeros)
//   - Tests mtime combinations: all zeros, lower max, upper max, all max
// Group 2: mtimecmp = 0x00000000FFFFFFFF (lower half max)
//   - Tests mtime combinations: all zeros, lower max, upper max, all max
// Group 3: mtimecmp = 0xFFFFFFFF00000000 (upper half max)
//   - Tests mtime combinations: all zeros, lower max, upper max, all max
// Group 4: mtimecmp = 0xFFFFFFFFFFFFFFFF (all max)
//   - Tests mtime combinations: all zeros, lower max, upper max, all max
// -----------
// For each test case, the machine interrupt pending (mip.mtip) bit is checked:
// - mtip = 1 when mtime >= mtimecmp
// - mtip = 0 when mtime < mtimecmp
// -----------
// The test stores all mip values in the signature region for verification.
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
RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True; ",CHK_MTIME_LENGTH)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	2   
  	.option norvc

#define MTIME_BASE              0x0200bff8 	// Base address  for the memory-mapped machine timer register.
#define MTIMECMP_BASE           0x02004000  	// Base address  for the memory-mapped machine timer-compare register.  	
#define TIMER_TEST_VALUE        0xFFFFFFFF      // Test Value to check the length of memory-mapped machine timers register.
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
	// Load base addresses for timer comparison
	LI(a1,   MTIMECMP_BASE) 
       	LI(a2,   MTIME_BASE)
       	LI(t1,   TIMER_TEST_VALUE)

    	          
    	          // GROUP 1: mtimecmp = 0x0000000000000000
    	          
    	          
    	// TEST CASE 1: Testing with mtimecmp all zeros and mtime all zeros
    	// Expected: mtip should be 1 as mtime equals mtimecmp
    	SREG zero, 0(a1)    	    	// mtimecmp (lower Half) = 0
    	nop
    	SREG zero, 4(a1)    	    	// mtimecmp (upper Half) = 0
    	nop
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0x0000000000000000 and mtime = 0x0000000000000000
    	// Read and store mip value after the 1st test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 2: Testing with mtimecmp all zeros and mtime lower half max
    	// Expected: mtip should be 1 as mtime is greater than mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0x0000000000000000 and mtime = 0x00000000FFFFFFFF
    	// Read and store mip value after the 2nd test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 3: Testing with mtimecmp all zeros and mtime upper half max
   	// Expected: mtip should be 1 as mtime is greater than mtimecmp
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0x0000000000000000 and mtime = 0xFFFFFFFF00000000
    	// Read and store mip value after the 3rd test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 4: Testing with mtimecmp all zeros and mtime all max
    	// Expected: mtip should be 1 as mtime is greater than mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0x0000000000000000 and mtime = 0xFFFFFFFFFFFFFFFF
    	// Read and store mip value after the 4th test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	          
    	          // GROUP 2: mtimecmp = 0x00000000FFFFFFFF
    	          
    	          
    	// TEST CASE 5: Testing with mtimecmp lower half max and mtime all zeros
    	// Expected: mtip should be 0 as mtime is less than mtimecmp
    	SREG t1,   0(a1)    	    	// mtimecmp (lower Half) = max
    	nop
    	SREG zero, 4(a1)    	    	// mtimecmp (upper Half) = 0
    	nop
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0x00000000FFFFFFFF and mtime = 0x0000000000000000
    	// Read and store mip value after the 5th test (mip.mtip should be 0)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 6: Testing with mtimecmp lower half max and mtime lower half max
    	// Expected: mtip should be 1 as mtime equals mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0x00000000FFFFFFFF and mtime = 0x00000000FFFFFFFF
    	// Read and store mip value after the 6th test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 7: Testing with mtimecmp lower half max and mtime upper half max
    	// Expected: mtip should be 1 as mtime is greater than mtimecmp
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0x00000000FFFFFFFF and mtime = 0xFFFFFFFF00000000
    	// Read and store mip value after the 7th test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 8: Testing with mtimecmp lower half max and mtime all max
    	// Expected: mtip should be 1 as mtime is greater than mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0x00000000FFFFFFFF and mtime = 0xFFFFFFFFFFFFFFFF
    	// Read and store mip value after the 8th test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	          
    	          // GROUP 3: mtimecmp = 0xFFFFFFFF00000000
    	
    	
    	// TEST CASE 9: Testing with mtimecmp upper half max and mtime all zeros
    	// Expected: mtip should be 0 as mtime is less than mtimecmp
    	SREG zero, 0(a1)    	    	// mtimecmp (lower Half) = 0
    	nop
    	SREG t1,   4(a1)    	    	// mtimecmp (upper Half) = max
    	nop
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFF00000000 and mtime = 0x0000000000000000
    	// Read and store mip value after the 9th test (mip.mtip should be 0)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)
	
    	// TEST CASE 10: Testing with mtimecmp upper half max and mtime lower half max
	// Expected: mtip should be 0 as mtime is less than mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFF00000000 and mtime = 0x00000000FFFFFFFF
    	// Read and store mip value after the 10th test (mip.mtip should be 0)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 11: Testing with mtimecmp upper half max and mtime upper half max
    	// Expected: mtip should be 1 as mtime equals mtimecmp
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFF00000000 and mtime = 0xFFFFFFFF00000000
    	// Read and store mip value after the 11th test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 12: Testing with mtimecmp upper half max and mtime all max
    	// Expected: mtip should be 1 as mtime is greater than mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFF00000000 and mtime = 0xFFFFFFFFFFFFFFFF
    	// Read and store mip value after the 12th test (mip.mtip should be 1)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	          
    	          // GROUP 4: mtimecmp = 0xFFFFFFFFFFFFFFFF
    	          
    	          
    	// TEST CASE 13: Testing with mtimecmp all max and mtime all zeros
    	// Expected: mtip should be 0 as mtime is less than mtimecmp
    	SREG t1,   0(a1)    	    	// mtimecmp (lower Half) = max
    	nop
    	SREG t1,   4(a1)    	    	// mtimecmp (upper Half) = max
    	nop
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFFFFFFFFFF and mtime = 0x0000000000000000
    	// Read and store mip value after the 13th test (mip.mtip should be 0)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 14: Testing with mtimecmp all max and mtime lower half max
    	// Expected: mtip should be 0 as mtime is less than mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG zero, 4(a2)    	    	// mtime (upper Half) = 0
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFFFFFFFFFF and mtime = 0x00000000FFFFFFFF
    	// Read and store mip value after the 14th test (mip.mtip should be 0)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 15: Testing with mtimecmp all max and mtime upper half max
    	// Expected: mtip should be 0 as mtime is less than mtimecmp
    	SREG zero, 0(a2)    	    	// mtime (lower Half) = 0
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFFFFFFFFFF and mtime = 0xFFFFFFFF00000000
    	// Read and store mip value after the 15th test (mip.mtip should be 0)
    	csrrs a4, CSR_MIP, x0
    	RVTEST_SIGUPD(x3,  a4)

    	// TEST CASE 16: Testing with mtimecmp all max and mtime all max
    	// Expected: mtip should be 1 as mtime equals mtimecmp
    	SREG t1,   0(a2)    	    	// mtime (lower Half) = max
    	nop
    	SREG t1,   4(a2)    	    	// mtime (upper Half) = max
    	nop
    	
    	// now mtimecmp = 0xFFFFFFFFFFFFFFFF and mtime = 0xFFFFFFFFFFFFFFFF
    	// Read and store mip value after the 16th test (mip.mtip should be 1)
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
    .fill 32*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 32*(XLEN/32),4,0xdeadbeef
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
