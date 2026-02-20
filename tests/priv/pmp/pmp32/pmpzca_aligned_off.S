// ---------------------------------------------------------------------------
// Title       	: Comprehensive PMP (Physical Memory Protection) Verification
// Authors     	: Umer Shahid, Allen Baum, David Harris
//				  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints : cp_misaligned_off for PMPZca is partially covered
//				 in this test file.
//
// Test Cases  :  Setting up 3 standard consecutive OFF PMP regions with L=1, XWR=111 
//				 (XWR = 000 for region 3).Place an uncompressed ret = jalr ra inside
//				 first region and inside second region. Attempt jalr to each ret.  
//
// Dependencies: model_test.h, arch_test.h
// ---------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','C','S','Smpmp']
# MARCH: rv${XLEN}ic_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpzca_aligned_tor.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#ifndef RVMODEL_PMP_GRAIN
	#define RVMODEL_PMP_GRAIN 4
#endif

#ifndef NUM_PMP_ENTRIES
	#define NUM_PMP_ENTRIES 16
#endif

#define REGION_SIZE    		(1<<(RVMODEL_PMP_GRAIN+2))

.macro VERIFICATION_RWX ADDRESS  

    LA(x15, \ADDRESS)             							// Address to be verified
	c.jalr x15
    nop

.endm

main:
	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, CSR_PMPCFG0
	.rept NUM_PMP_ENTRIES/4
	csrw pmpcfgi , x0
	.set pmpcfgi, pmpcfgi+1
	.endr

	// Loop to SET ALL pmpaddr REGs to zero
	.set pmpaddri, CSR_PMPADDR0
	.rept NUM_PMP_ENTRIES
	csrw pmpaddri, x0
	.set pmpaddri, pmpaddri+1
	.endr

#define PMP_REGION_GLOBAL			((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMP0CFG 					((((PMP_L|PMP_R|PMP_W|PMP_X          )&0xFF) << PMP0_CFG_SHIFT))
#define PMP1CFG 					((((PMP_L|PMP_R|PMP_W|PMP_X          )&0xFF) << PMP1_CFG_SHIFT))
#define PMP2CFG 					((((PMP_L|PMP_R|PMP_W|PMP_X          )&0xFF) << PMP2_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
#define REGIONSTART			        0x80002000	// RAM_BASE_ADDR + PROGRAM_SIZE
#define STANDARD_REGION1        	((REGIONSTART)       >> PMP_SHIFT)
#define STANDARD_REGION2        	((REGIONSTART+REGION_SIZE)     >> PMP_SHIFT)
#define STANDARD_REGION3        	((REGIONSTART+(2*REGION_SIZE)) >> PMP_SHIFT)
	
#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg3, x4

//											Verification Section
// Test Case: Setting up 3 OFF regions with LWXR = 1111 

	LA(x5, STANDARD_REGION1)
	csrw pmpaddr0, x5

	LA(x4, PMP0CFG)
	csrw pmpcfg0, x4

	LA(x5, STANDARD_REGION2)
	csrw pmpaddr1, x5

	LA(x4, PMP1CFG)
	csrw pmpcfg0, x4

	LA(x5, STANDARD_REGION3)
	csrw pmpaddr2, x5

	LA(x4, PMP2CFG)
	csrw pmpcfg0, x4

	// Test Case 1: Uncompressed return in 1st region
    VERIFICATION_RWX TEST_FOR_EXECUTION_1

    // Update signature for test case 1
    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)

    // Test Case 2: Uncompressed return in 2nd region
    VERIFICATION_RWX TEST_FOR_EXECUTION_2
    
    // Update signature for test case 2
    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)
    
    j exit														// Verification Complete, exit the test

.align 13
TEST_FOR_EXECUTION_1:
	jalr x0, x1, 0												// Uncompressed return inside the first region
	.rept (((1<<(RVMODEL_PMP_GRAIN+2)) - 4) / 2)						//(region size - jalr size)/ compressed nop size 
	nop
	.endr

TEST_FOR_EXECUTION_2:
	jalr x0, x1, 0												// Uncompressed return inside the second region
	.rept (((1<<(RVMODEL_PMP_GRAIN+2)) - 4) / 2)
	nop
	.endr

RETURN_INSTRUCTION:
	nop
	nop
	jr ra														// Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: pmpzca_aligned_off_region1_execute\""
test_2_str: .string "\"test: 2; cp: pmpzca_aligned_off_region2_execute\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP