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
// Coverpoints : cp_cfg_A_off_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A=OFF never matches for each region. For each 
//               standard region with pmpcfg.L=1, pmpcfg.A=OFF, pmpcfg.XWR=000.
//               Fetching, reading and writting from that region. Should succeed
//               because region is off even though inaccessible.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32I_Zicsr")
# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifndef RVMODEL_PMP_GRAIN
	#define RVMODEL_PMP_GRAIN 0
#endif

#ifndef RVMODEL_NUM_PMPS
	#define RVMODEL_NUM_PMPS 16
#endif

RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_off_all)
RVTEST_CASE(2,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_off_all)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		0x13

.macro VERIFICATION_RWX ADDRESS   
    // Execution Access Check
    LA (a4, \ADDRESS)
	LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
	LA(x4, 1f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
1:
	nop

	// Store Access Check
	LA(a5, \ADDRESS)             							// Address to be verified
	LI(a4, NOP)                  							// Value to write (NOP)
	sw a4, 0(a5)                 							// Word store test
	nop

	// Load Access Check
	lw a4, 0(a5)                 							// Word load test
	nop
	RVTEST_SIGUPD(x13, a4)       							// Signature update

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

#define PMP_REGION_GLOBAL	((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  	// Background region with RWX enable.

#define PMPADDRESS_TOP_GLOBAL		-1										// All memory region
#define REGIONSTART			0x80002000		// RAM_BASE_ADDR + PROGRAM_SIZE
#define PMP_MASK			~(1 << (RVMODEL_PMP_GRAIN - 1))
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
	LI(x4, (PMP_REGION_GLOBAL << PMP3_CFG_SHIFT))
	csrw pmpcfg3, x4

//											Verification Section
// Test Case: 1 -- No Permissions given to the PMP Region 14

	LA(x5, STANDARD_REGION)
	csrw pmpaddr14, x5

    LI(x4, (0x80 << PMP2_CFG_SHIFT))
	csrw pmpcfg3, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 2 -- No Permissions given to the PMP Region 13

	LA(x5, STANDARD_REGION)
	csrw pmpaddr13, x5

    LI(x4, (0x80 << PMP1_CFG_SHIFT))
	csrw pmpcfg3, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 3 -- No Permissions given to the PMP Region 12

	LA(x5, STANDARD_REGION)
	csrw pmpaddr12, x5

    LI(x4, (0x80 << PMP0_CFG_SHIFT))
	csrw pmpcfg3, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 4 -- No Permissions given to the PMP Region 11

	LA(x5, STANDARD_REGION)
	csrw pmpaddr11, x5

    LI(x4, (0x80 << PMP3_CFG_SHIFT))
	csrw pmpcfg2, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 5 -- No Permissions given to the PMP Region 10

	LA(x5, STANDARD_REGION)
	csrw pmpaddr10, x5

    LI(x4, (0x80 << PMP2_CFG_SHIFT))
	csrw pmpcfg2, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 6 -- No Permissions given to the PMP Region 9

	LA(x5, STANDARD_REGION)
	csrw pmpaddr9, x5

    LI(x4, (0x80 << PMP1_CFG_SHIFT))
	csrw pmpcfg2, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 7 -- No Permissions given to the PMP Region 8

	LA(x5, STANDARD_REGION)
	csrw pmpaddr8, x5

    LI(x4, (0x80 << PMP0_CFG_SHIFT))
	csrw pmpcfg2, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 8 -- No Permissions given to the PMP Region 7

	LA(x5, STANDARD_REGION)
	csrw pmpaddr7, x5

    LI(x4, (0x80 << PMP3_CFG_SHIFT))
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 9 -- No Permissions given to the PMP Region 6

	LA(x5, STANDARD_REGION)
	csrw pmpaddr6, x5

    LI(x4, (0x80 << PMP2_CFG_SHIFT))
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 10 -- No Permissions given to the PMP Region 5

	LA(x5, STANDARD_REGION)
	csrw pmpaddr5, x5

    LI(x4, (0x80 << PMP1_CFG_SHIFT))
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 11 -- No Permissions given to the PMP Region 4

	LA(x5, STANDARD_REGION)
	csrw pmpaddr4, x5

    LI(x4, (0x80 << PMP0_CFG_SHIFT))
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 12 -- No Permissions given to the PMP Region 3

	LA(x5, STANDARD_REGION)
	csrw pmpaddr3, x5

    LI(x4, (0x80 << PMP3_CFG_SHIFT))
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 13 -- No Permissions given to the PMP Region 2

	LA(x5, STANDARD_REGION)
	csrw pmpaddr2, x5

    LI(x4, (0x80 << PMP2_CFG_SHIFT))
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 14 -- No Permissions given to the PMP Region 1

	LA(x5, STANDARD_REGION)
	csrw pmpaddr1, x5

    LI(x4, (0x80 << PMP1_CFG_SHIFT))
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

// Test Case: 15 -- No Permissions given to the PMP Region 0

	LA(x5, STANDARD_REGION)
	csrw pmpaddr0, x5

    LI(x4, (0x80 << PMP0_CFG_SHIFT))
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
	.rept (1<<RVMODEL_PMP_GRAIN)
	nop
	.endr
//We need to add a extra nop to complete the minimal NAPOT region i.e., 8 Byte in case of 4 Byte Grain
.if RVMODEL_PMP_GRAIN == 0
    nop
.endif

RETURN_INSTRUCTION:
	nop
	nop
	jr ra														// Get back to the point from where TEST_FOR_EXECUTION was called.

exit:
#endif
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
signature_x13_1:
    .fill 128*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 512*(XLEN/32),4,0xdeadbeef
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