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
// Coverpoints : cp_cret_tor for PMPZca is fully covered in this test file.
//
// Test Cases  : Check that 16-bit fetches adjacent to a TOR PMP boundary succeed.
//				 Set up a standard NAPOT PMP region with L=1, XWR = 111. Place four 
//				 c.ret = c.jr ra statements just below, at bottom, at top, and just 
//				 above PMP region, half of which are on 16-bit boundaries.  
//				 Attempt jalr to each c.ret.  
//				 
// Dependencies: model_test.h, arch_test.h
// ---------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','C','Smpmp']
# MARCH: rv${XLEN}ic_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpzca_cret_napot.S"
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

#define REGION_SIZE    (1<<(RVMODEL_PMP_GRAIN+2))

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

#define PMP_REGION_GLOBAL	((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT) &0xFF)   << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMP1CFG 			((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)   &0xFF)   << PMP1_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		                    -1												// All memory region
#define REGIONSTART			0x80002000	// RAM_BASE_ADDR + PROGRAM_SIZE

#define LOWER_BOUND         (REGIONSTART     >> PMP_SHIFT)
#define UPPER_BOUND         ((REGIONSTART+REGION_SIZE) >> PMP_SHIFT)
	
#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg3, x4

//											Verification Section
// Test Case: TOR Region with L->1 and XWR->111

	LA(x5, LOWER_BOUND)
	csrw pmpaddr0, x5

    LA(x6, UPPER_BOUND)
	csrw pmpaddr1, x6

	LA(x4, PMP1CFG)
	csrw pmpcfg0, x4

	 //Test case1
	VERIFICATION_RWX TEST_FOR_EXECUTION_0

     // Update signature for test case 1
    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)

    //Test case2
	VERIFICATION_RWX TEST_FOR_EXECUTION_1
    // Update signature for test case 1
    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)

    //Test case3
    VERIFICATION_RWX TEST_FOR_EXECUTION_2

     // Update signature for test case 1
    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_3_str)

    //Test case4
	VERIFICATION_RWX TEST_FOR_EXECUTION_3

     // Update signature for test case 1
    li a4, 0xdeadbeef
    RVTEST_SIGUPD(x2, x5, x4, a4, test_4_str)
    
    j exit														// Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)
.skip (0x1000 -2)
TEST_FOR_EXECUTION_0:
	ret															// Comrpessed return just before the start of region

TEST_FOR_EXECUTION_1:
    ret                                                         // Compressed return inside the region
	.rept (((1<<(RVMODEL_PMP_GRAIN+2)) -4 ) /2)					// (size of region - size of 2 returns) / size of nop
	nop
    .endr

TEST_FOR_EXECUTION_2:
    ret                       									// Compressed return at the top of the region                                  

TEST_FOR_EXECUTION_3:
    ret                                             			// Comrpessed return just above the region          
	nop       

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
test_1_str: .string "\"test: 1; cp: pmpzca_cret_napot_execute_at_just_before\""
test_2_str: .string "\"test: 2; cp: pmpzca_cret_napot_execute_at_inside\""
test_3_str: .string "\"test: 3; cp: pmpzca_cret_napot_execute_at_top\""
test_4_str: .string "\"test: 4; cp: pmpzca_cret_napot_execute_at_just_above_top\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP