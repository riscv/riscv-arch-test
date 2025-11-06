// ---------------------------------------------------------------------------
// Title       	: Comprehensive PMP (Physical Memory Protection) Verification
// Authors     	: Umer Shahid, Muhammad Abdullah, Muhammad Zain, Hamza Ali
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
// Coverpoints : cp_cret_napot for PMPZca is fully covered in this test file.
//
// Test Cases  : Check that 16-bit fetches adjacent to a NAPOT PMP boundary succeed.
//				 Set up a standard NAPOT PMP region with L=1, XWR = 111.
//				 Place four c.ret = c.jr ra statements just below, at bottom, 
//				 at top, and just above PMP region, half of which are on 16-bit
//				 boundaries. Attempt jalr to each c.ret.  
//				 
// Dependencies: model_test.h, arch_test.h
// ---------------------------------------------------------------------------
#define SKIP_MEPC
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV64IC_Zicsr")
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*C[^S]*Zicsr.*); def rvtest_mtrap_routine=True;								   verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cret_napot)
RVTEST_CASE(2,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*C.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cret_napot)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
#define NOP 	(0x13<<32)+0x13

.macro VERIFICATION_RWX ADDRESS  

    LA(x15, \ADDRESS)             							// Address to be verified
	c.jalr x15
    nop

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

#define PMP_REGION_GLOBAL	((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMP0CFG 			((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
#define REGIONSTART			0x80002000
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
	csrw pmpcfg2, x4

//											Verification Section
// Test Case: NAPOT Region with L->1 and XWR->111

	LA(x5, STANDARD_REGION)
	csrw pmpaddr0, x5

	LA(x4, PMP0CFG)
	csrw pmpcfg0, x4

	VERIFICATION_RWX 	TEST_FOR_EXECUTION_0
	VERIFICATION_RWX 	TEST_FOR_EXECUTION_1
    VERIFICATION_RWX 	TEST_FOR_EXECUTION_3
	VERIFICATION_RWX 	TEST_FOR_EXECUTION_4

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)
.skip (0x1000 -2)
TEST_FOR_EXECUTION_0:
	ret															// Comrpessed return just before the start of region

TEST_FOR_EXECUTION_1:
    ret                                                         // Compressed return inside the region
	.rept (1<<(RVMODEL_PMP_GRAIN)-1)
	nop
    .endr
.if RVMODEL_PMP_GRAIN == 0
    nop
.endif

TEST_FOR_EXECUTION_2:
	.rept ((1<<(RVMODEL_PMP_GRAIN))-1)
	nop
    .endr
.if RVMODEL_PMP_GRAIN == 0
    nop
.endif

TEST_FOR_EXECUTION_3:
    ret                       									// Compressed return at the bottom of the region                                  

TEST_FOR_EXECUTION_4:
    ret                                             			// Comrpessed return just below the region          
	nop

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
    .fill 32*(XLEN/32),4,0xdeadbeef

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