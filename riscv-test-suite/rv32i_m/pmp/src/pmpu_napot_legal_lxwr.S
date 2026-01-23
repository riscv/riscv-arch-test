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
// Coverpoints : cp_cfg_X and cp_cfg_RW from PMPU are partially covered in this
//			     test file. cp_cfg_A_napot is fully covered.
//
// Test Cases  : Checking XWR controls accesses in matching NAPOT region. Configuring
//               PMP in M mode and then switching to U mode. For a standard region with
//               pmpcfg_i.L = {0/1}, pmpcfg_i.A=NAPOT, all legal pmpcfg_i.XWR, making
//               {lw, sw, jalr} at that start of region, start - 4, start + 4, highest
//               word in region, just beyond top of the region. Observing proper access
//               faults for restricted regions, and accesses beyond and below the region
//               should succeed because of backgroung region with RWX permissions.
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

#if RVMODEL_PMP_GRAIN != 0
  #define g   (1 << (RVMODEL_PMP_GRAIN + 2))
#else
  #define g   (1 << (RVMODEL_PMP_GRAIN + 3))
#endif

RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_napot, cp_cfg_X, cp_cfg_RW)
RVTEST_CASE(2,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_napot, cp_cfg_X, cp_cfg_RW)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		0x13

.macro VERIFICATION_RWX ADDRESS  

	LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
	LA(x4, 1f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
1:
	nop

    addi a4, a4, -4                     // REGIONSTART - 4
	LA(x4, 2f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
2:
	nop

    addi a4, a4, 8                      // REGIONSTART + 4
	LA(x4, 3f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
3:
	nop

    LI(t0, (g-8))
    add a4, a4, t0                      // REGIONSTART + g - 4
	LA(x4, 4f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
4:
	nop

    addi a4, a4, 4                      // REGIONSTART + g
	LA(x4, 5f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
5:
	nop

    LI(a4, NOP)                  							// Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)             							// Address to be verified
    sb a4, 0(a5)
    nop
    sh a4, 0(a5)
    nop
    sw a4, 0(a5)
    nop

    addi a5, a5, -4                                         // REGIONSTART - 4
    sw a4, 0(a5)
    nop

    addi a5, a5, 8                                          // REGIONSTART + 4
    sw a4, 0(a5)
    nop

    LI(t0, (g-8))
    add a5, a5, t0                                          // REGIONSTART + g - 4
    sw a4, 0(a5)
    nop

    addi a5, a5, 4                                          // REGIONSTART + g
    sw a4, 0(a5)
    nop

    LA(a5, \ADDRESS)             							// Address to be verified
    lb a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update
    lbu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)                                  // Signature update
	lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update
	lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)                                  // Signature update
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LI(t0, (g-8))
    add a5, a5, t0                                          // REGIONSTART + g - 4
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, 4                                          // REGIONSTART + g
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

.endm

main:
	// Loop to SET pmpcfg REGs to zero
	.set pmpcfgi, CSR_PMPCFG0
	.rept RVMODEL_NUM_PMPS/4
	csrw pmpcfgi , x0
	.set pmpcfgi, pmpcfgi+1
	.endr

	// Loop to SET pmpaddr REGs to zero
	.set pmpaddri, CSR_PMPADDR0
	.rept RVMODEL_NUM_PMPS
	csrw pmpaddri, x0
	.set pmpaddri, pmpaddri+1
	.endr

#define PMP_REGION_GLOBAL	((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((                        PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((      PMP_R|            PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((      PMP_R|PMP_W	   |PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((      			  PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((      PMP_R		 |PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((      PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region									// Test section address
#define REGIONSTART			0x80002000	// RAM_BASE_ADDR + PROGRAM_SIZE
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
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg3, x4


//											Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 5

	LA(t0, STANDARD_REGION)
	csrw pmpaddr5, t0
    LI(t1, PMPREGION_LXWR_1000)
	csrw pmpcfg1, t1

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 4

	LA(t0, STANDARD_REGION)
	csrw pmpaddr4, t0
    LI(t1, PMPREGION_LXWR_1000|PMPREGION_LXWR_1001)
	csrw pmpcfg1, t1

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 3

	LA(t0, STANDARD_REGION)
	csrw pmpaddr3, t0
    LI(t1, PMPREGION_LXWR_1011)
	csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 2

	LA(t0, STANDARD_REGION)
	csrw pmpaddr2, t0
    LI(t1, PMPREGION_LXWR_1011|PMPREGION_LXWR_1100)
	csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region 1

	LA(t0, STANDARD_REGION)
	csrw pmpaddr1, t0
    LI(t1, PMPREGION_LXWR_1011|PMPREGION_LXWR_1100|PMPREGION_LXWR_1101)
	csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 0

	LA(t0, STANDARD_REGION)
	csrw pmpaddr0, t0
    LI(t1, PMPREGION_LXWR_1011|PMPREGION_LXWR_1100|PMPREGION_LXWR_1101|PMPREGION_LXWR_1111)
	csrw pmpcfg0, t1

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 13
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
    .fill 64*(XLEN/32),4,0xdeadbeef

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