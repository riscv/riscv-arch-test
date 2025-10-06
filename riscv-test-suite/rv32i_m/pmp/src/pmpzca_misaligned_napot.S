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
// Coverpoints : cp_misaligned_napot for PMPZca is partially covered
//				 in this test file.
//
// Test Cases  : Check that misaligned 32-bit fetches that cross a NAPOT PMP boundary fail.
//				 Setting up 3 standard consecutive NAPOT PMP regions with L=1, XWR=111 
//				 (XWR = 000 for region 3).Place an uncompressed ret = jalr straddling the
//				 start and end of the second regions. Attempt jalr to each ret. 
//				 
// Dependencies: model_test.h, arch_test.h
// ---------------------------------------------------------------------------

#define SKIP_MEPC
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32IC_Zicsr")
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

RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*C[^S]*Zicsr.*); def rvtest_mtrap_routine=True; 							   verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_misaligned_napot)
RVTEST_CASE(2,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*C.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_misaligned_napot)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
#define NOP 		0x13

.macro VERIFICATION_RWX ADDRESS  

    LA(x15, \ADDRESS)             							// Address to be verified
	c.jalr x15
    nop

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
#define PMP0CFG 			((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))
#define PMP1CFG 			((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMP2CFG 			((((PMP_L|                  PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
#define REGIONSTART			0x80002000	// RAM_BASE_ADDR + PROGRAM_SIZE

#define PMP_NAPOT_ONES      ((g >> 3) - 1)
#define NEWREGION1			(REGIONSTART)
#define NEWREGION2			(REGIONSTART+g)
#define NEWREGION3			(REGIONSTART+(2*g))

#define STANDARD_REGION1        (((NEWREGION1 >> PMP_SHIFT) + PMP_NAPOT_ONES))
#define STANDARD_REGION2        (((NEWREGION2 >> PMP_SHIFT) + PMP_NAPOT_ONES))
#define STANDARD_REGION3        (((NEWREGION3 >> PMP_SHIFT) + PMP_NAPOT_ONES))
	
#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg3, x4

//											Verification Section
// Test Case: Three NAPOT regions with L=1 and XWR = 111 for first 2 regions, and XWR = 000 for third region.

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

	VERIFICATION_RWX 	TEST_FOR_EXECUTION_2
	VERIFICATION_RWX 	TEST_FOR_EXECUTION_4

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION_1:												
	.rept (1<<RVMODEL_PMP_GRAIN)
	nop
	.endr
	.rept ((1<<RVMODEL_PMP_GRAIN)-1)
	nop
	.endr
.if RVMODEL_PMP_GRAIN == 0
    nop
.endif

TEST_FOR_EXECUTION_2:
    jalr x0, x1, 0												//uncompressed return straddling the start of the second region

TEST_FOR_EXECUTION_3:											
	.rept ((1<<RVMODEL_PMP_GRAIN)-1)
	nop
	.endr
	.rept ((1<<RVMODEL_PMP_GRAIN)-1)
	nop
	.endr
.if RVMODEL_PMP_GRAIN == 0
    nop
.endif

TEST_FOR_EXECUTION_4:
    jalr x0, x1, 0												// Uncompressed return straddling the end of the second region

TEST_FOR_EXECUTION_5:
	.rept (1<<RVMODEL_PMP_GRAIN)
	nop
	.endr
	.rept (1<<RVMODEL_PMP_GRAIN)
	nop
	.endr
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
