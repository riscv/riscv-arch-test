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
// Coverpoints : cp_mprv for PMPS is partially covered in this file.
//
// Test Cases  : Checking L bit doesn't matter with MPRV setting to lower privilege
//				 mode. Configuring PMP in M-mode. Setting mstatus.MPRV = {0/1},
//				 mstatus.MPP = {11 / 01}. While staying in M-mode doing {lw/sw/jalr}
//				 with pmpcfg_i.L={0/1}, XWR = 111. Observing access faults for 
//				 restricted execution regions even with L = 0 in effective S mode.
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#define SKIP_MEPC
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV64I_Zicsr")
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_mprv)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		(0x13<<32)+0x13									// Encoded Instruction of nop (64 bit case)

.macro VERIFICATION_X ADDRESS  

	LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
	LA(x4, 1f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
1:
	nop

.endm

.macro VERIFICATION_W ADDRESS  

    LI(a4, NOP)                  							// Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)             							// Address to be verified
    sw a4, 0(a5)
    nop

.endm

.macro VERIFICATION_R ADDRESS  

    LA(a5, \ADDRESS)             							// Address to be verified
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

.endm

main:
	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, CSR_PMPCFG0
	.rept RVMODEL_NUM_PMPS/8
	csrw pmpcfgi , x0
	.set pmpcfgi, pmpcfgi+2
	.endr

	// Loop to SET ALL pmpaddr REGs to zero
	.set pmpaddri, CSR_PMPADDR0
	.rept RVMODEL_NUM_PMPS
	csrw pmpaddri, x0
	.set pmpaddri, pmpaddri+1
	.endr

#define PMP_REGION_GLOBAL	  ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPREGION_LXWR_1111   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMPREGION_LXWR_0111   ((      PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT

#define MPRV					(1 << 17)
#define S_MODE					(1 << 11)
#define M_MODE					(3 << 11)

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
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
	LI(x4, PMP_REGION_GLOBAL << PMP7_CFG_SHIFT)
	csrw pmpcfg2, x4

//-------------------------------------
	LA(x4, STANDARD_REGION)
	csrw pmpaddr0, x4

    LI(x4, PMPREGION_LXWR_0111)
	csrw pmpcfg0, x4
//-------------------------------------

//											Verification Section
// Test Case: 1 : mstatus.MPRV = 0, L = 0, mstatus.MPP = 01 and XWR Permissions given to the PMP Region 0

	li t0, (MPRV|M_MODE)		// Initialize mstatus.MPRV & mstatus.MPP
	csrc mstatus, t0

	li t0, (S_MODE)
	csrs mstatus, t0

	VERIFICATION_X	TEST_FOR_EXECUTION

	li t0, (S_MODE)
	csrs mstatus, t0

	VERIFICATION_W	TEST_FOR_EXECUTION

	li t0, (S_MODE)
	csrs mstatus, t0

	VERIFICATION_R	TEST_FOR_EXECUTION

// Test Case: 2 : mstatus.MPRV = 1, L = 0, mstatus.MPP = 01 and XWR Permissions given to the PMP Region 0

	li t0, (M_MODE|MPRV)		// Initialize mstatus.MPRV & mstatus.MPP
	csrc mstatus, t0

	li t0, (MPRV|S_MODE)
	csrs mstatus, t0

	VERIFICATION_X	TEST_FOR_EXECUTION

	li t0, (MPRV|S_MODE)
	csrs mstatus, t0

	VERIFICATION_W	TEST_FOR_EXECUTION

	li t0, (MPRV|S_MODE)
	csrs mstatus, t0

	VERIFICATION_R	TEST_FOR_EXECUTION

//-------------------------------------
	LA(x4, STANDARD_REGION)
	csrw pmpaddr0, x4

    LI(x4, PMPREGION_LXWR_1111)
	csrw pmpcfg0, x4
//-------------------------------------

// Test Case: 1 : mstatus.MPRV = 0, L = 1, mstatus.MPP = 01 and XWR Permissions given to the PMP Region 0

	li t0, (MPRV|M_MODE)		// Initialize mstatus.MPRV & mstatus.MPP
	csrc mstatus, t0

	li t0, (S_MODE)
	csrs mstatus, t0

	VERIFICATION_X	TEST_FOR_EXECUTION

	li t0, (S_MODE)
	csrs mstatus, t0

	VERIFICATION_W	TEST_FOR_EXECUTION

	li t0, (S_MODE)
	csrs mstatus, t0

	VERIFICATION_R	TEST_FOR_EXECUTION

// Test Case: 2 : mstatus.MPRV = 1, L = 1, mstatus.MPP = 01 and XWR Permissions given to the PMP Region 0

	li t0, (M_MODE|MPRV)		// Initialize mstatus.MPRV & mstatus.MPP
	csrc mstatus, t0

	li t0, (MPRV|S_MODE)
	csrs mstatus, t0

	VERIFICATION_X	TEST_FOR_EXECUTION

	li t0, (MPRV|S_MODE)
	csrs mstatus, t0

	VERIFICATION_W	TEST_FOR_EXECUTION

	li t0, (MPRV|S_MODE)
	csrs mstatus, t0

	VERIFICATION_R	TEST_FOR_EXECUTION


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
    .fill 128*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 256*(XLEN/32),4,0xdeadbeef
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