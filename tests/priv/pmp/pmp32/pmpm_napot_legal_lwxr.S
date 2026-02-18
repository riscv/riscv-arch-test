// --------------------------------------------------------------------------------
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
// Coverpoints : cp_cfg_A_napot, cp_cfg_X and cp_cfg_RW for PMPM are fully covered
//				 in this test file.
//
// Test Cases  : Checking XWR controls accesses in matching NAPOT region. For a
//				 standard region with pmpcfg_i.L = 1, pmpcfg_i.A=NAPOT, all
//				 legal pmpcfg_i.XWR: making {lw, sw, jalr} at that start of region,
//				 start - 4, start + 4, highest word in region, just beyond top
//				 of the region. Observing proper access faults for restricted
//				 regions, and accesses beyond the region and below the region
//				 should succeed because the bckground region is set to RWX.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','S','Smpmp']
# MARCH: rv${XLEN}i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpm_napot_legal_lwxr.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define rvtest_strap_routine

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#ifndef RVMODEL_PMP_GRAIN
	#define RVMODEL_PMP_GRAIN 4
#endif

#ifndef RVMODEL_NUM_PMPS
	#define RVMODEL_NUM_PMPS 16
#endif

#if RVMODEL_PMP_GRAIN != 0
  #define g   (1 << (RVMODEL_PMP_GRAIN + 2))
#else
  #define g   (1 << (RVMODEL_PMP_GRAIN + 3))
#endif

#define NOP 		0x13

.macro VERIFICATION_RWX ADDRESS  

	LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
	LA(x4, 1f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
1:
	nop
	nop

    addi a4, a4, -4                     // REGIONSTART - 4
	LA(x4, 2f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
2:
	nop
	nop

    addi a4, a4, 8                      // REGIONSTART + 4
	LA(x4, 3f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
3:
	nop
	nop

    addi a4, a4, (g-8)                  // REGIONSTART + g - 4
	LA(x4, 4f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
4:
	nop
	nop

    addi a4, a4, 4                      // REGIONSTART + g
	LA(x4, 5f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
5:
	nop
	nop

    LI(a4, NOP)                  							// Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)             							// Address to be verified
    sb a4, 0(a5)
    nop
    nop
    sh a4, 0(a5)
    nop
    nop
    sw a4, 0(a5)
    nop
    nop

    addi a5, a5, -4                                         // REGIONSTART - 4
    sw a4, 0(a5)
    nop
    nop

    addi a5, a5, 8                                          // REGIONSTART + 4
    sw a4, 0(a5)
    nop
    nop

    addi a5, a5, (g-8)                                      // REGIONSTART + g - 4
    sw a4, 0(a5)
    nop
    nop

    addi a5, a5, 4                                          // REGIONSTART + g
    sw a4, 0(a5)
    nop
    nop

    LA(a5, \ADDRESS)             							// Address to be verified
    lb a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_1_str)        							// Signature update
    lbu a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_2_str)                                   // Signature update
	lh a4, 0(a5)
    nop                                                    
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_3_str)        							// Signature update
	lhu a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_4_str)                                   // Signature update
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_5_str)        							// Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_6_str)        							// Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_7_str)        							// Signature update

    addi a5, a5, (g-8)                                      // REGIONSTART + g - 4
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_8_str)        							// Signature update

    addi a5, a5, 4                                          // REGIONSTART + g
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, test_9_str)       							// Signature update

.endm

main:
	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, CSR_PMPCFG0
	.rept RVMODEL_NUM_PMPS/4
	csrw pmpcfgi , x0
	.set pmpcfgi, pmpcfgi+1
	.endr

	// Loop to SET ALL pmpaddr REGs to zero
	.set pmpaddri, CSR_PMPADDR0
	.rept RVMODEL_NUM_PMPS
	csrw pmpaddri, x0
	.set pmpaddri, pmpaddri+1
	.endr

#define PMP_REGION_GLOBAL	((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R|            PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W	   |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|			  PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|PMP_R		 |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
#define REGIONSTART			0x80002000	// RAM_BASE_ADDR + PROGRAM_SIZE
#define PMP_MASK			~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
#define PMP_REGION_SIZE 	(1 << (RVMODEL_PMP_GRAIN - 1)) - 1

#if RVMODEL_PMP_GRAIN != 0
  #define STANDARD_REGION   (((REGIONSTART >> PMP_SHIFT) & PMP_MASK) | PMP_REGION_SIZE)
#else
  #define STANDARD_REGION   (REGIONSTART >> PMP_SHIFT)
#endif
	
#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg3, x4

//											Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 5

	LA(x5, STANDARD_REGION)
	csrw pmpaddr5, x5

    LI(x4, PMPREGION_LXWR_1000)
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 4

	LA(x5, STANDARD_REGION)
	csrw pmpaddr4, x5

    LI(x4, PMPREGION_LXWR_1001)
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 3

	LA(x5, STANDARD_REGION)
	csrw pmpaddr3, x5

    LI(x4, PMPREGION_LXWR_1011)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 2

	LA(x5, STANDARD_REGION)
	csrw pmpaddr2, x5

    LI(x4, PMPREGION_LXWR_1100)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 1

	LA(x5, STANDARD_REGION)
	csrw pmpaddr1, x5

    LI(x4, PMPREGION_LXWR_1101)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 0

	LA(x5, STANDARD_REGION)
	csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1111)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION


	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x2, x5, x4, a4, test_10_str)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
	.rept (1<<(RVMODEL_PMP_GRAIN+2))
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
test_1_str: .string "\"test: 1; cp: pmpm_napot_legal_lwxrl_lb\""
test_2_str: .string "\"test: 2; cp: pmpm_napot_legal_lwxrl_lbu\""
test_3_str: .string "\"test: 3; cp: pmpm_napot_legal_lwxrl_lh\""
test_4_str: .string "\"test: 4; cp: pmpm_napot_legal_lwxrl_lhu\""
test_5_str: .string "\"test: 5; cp: pmpm_napot_legal_lwxrl_lw\""
test_6_str: .string "\"test: 6; cp: pmpm_napot_legal_lwxrl_lw_REGIONSTART44\""
test_7_str: .string "\"test: 7; cp: pmpm_napot_legal_lwxrl__lw_REGIONSTART+4\""
test_8_str: .string "\"test: 8; cp: pmpm_napot_legal_lwxrl_lw_REGIONSTART-g\""
test_9_str: .string "\"test: 9; cp: pmpm_napot_legal_lwxrl_lw_REGIONSTART+g\""
test_10_str: .string "\"test: 10; cp: pmpm_napot_legal_lwxr\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP