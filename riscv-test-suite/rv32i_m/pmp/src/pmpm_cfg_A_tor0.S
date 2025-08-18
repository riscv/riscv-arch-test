//// ---------------------------------------------------------------------------
// Title       	: Comprehensive PMP (Physical Memory Protection) Verification
// Authors     	: Umer Shahid, Muhammad Abdullah, Muhammad Zain, Hamza Ali
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It checks that region 0 extends from 0 to pmpaddr0
//               in TOR mode.
//
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Test Cases  : 1. Full RWX permissions (Read, Write, Execute)
//
// Dependencies: model_test.h, arch_test.h
// Total expected faults: 0
// ---------------------------------------------------------------------------

#define SKIP_MEPC
#define SKIP_MTVAL
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
	#define RVMODEL_PMP_GRAIN 4
#endif

#ifndef RVMODEL_NUM_PMPS
	#define RVMODEL_NUM_PMPS 16
#endif

#define PMP_REGION_SIZE 	(1 << (RVMODEL_PMP_GRAIN - 1)) - 1
#define g (1<<(RVMODEL_PMP_GRAIN+2))

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",PMP_NAPOT)
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define PMPCFG0		0x3A0		// Address of pmpcfg0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
#define PMPADDR0	0x3B0		// Address of pmpaddr0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
/* Define PMP Configuration Fields */
#define PMP0_CFG_SHIFT  0
#define PMP1_CFG_SHIFT  8
#define PMP2_CFG_SHIFT  16
#define PMP3_CFG_SHIFT  24
#define NOP 			0x13

.macro VERIFICATION_RWX ADDRESS

   	LI(a4, NOP)                  							// Value to write (NOP)
   
    LA(a5, (\ADDRESS))             							// Address to be verified
    sw a4, 0(a5)                 							// word-level store test
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA(a5, (\ADDRESS-4))             						// Address to be verified
    sw a4, 0(a5)                 							// word-level store test
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update   

	LI(x3, 0xACCE)
	li a5, 0
	LA(x4, 4f)           				    				// Address to be verified
    sw a4, 0(a5)                 							// word-level store test
    nop
4:	
    nop
    RVTEST_SIGUPD(x13, a4)									// Signature update						
    
	LA(a5, (\ADDRESS))             							// Address to be verified
    lw a4, 0(a5)                 							// Word load test
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA(a5, (\ADDRESS-4))             						    // Address to be verified
    lw a4, 0(a5)                 							// Word load test
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

	LA(x4, 5f)
	li a5, 0           				    					// Address to be verified
    lw a4, 0(a5)                 							// word-level store test
    nop

5:
    nop
    RVTEST_SIGUPD(x13, a4)									// Signature update


	LA (a4, (\ADDRESS)) 
	LA(x4, 1f)							                    // Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
1:
	nop
	nop

	LA (a4, (\ADDRESS-4))
	LA(x4, 2f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
2:
	nop
	nop

    li a5, 0
	LA(x4, 3f)							// Store the return Address in x4
	jalr ra, 0(a5)
	nop
	nop
3:
	nop
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

#define PMP_REGION_GLOBAL	       ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_TOR      		   ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF)   << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
#define PMPADDRESS0			TEST_FOR_EXECUTION 										// Test section address
#define PMP_MASK			~(1 << (RVMODEL_PMP_GRAIN - 1))
	
	csrw satp, x0																	// Disable Address Translation

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4
	
	LA(x4, TEST_FOR_EXECUTION)
	srl x4, x4, PMP_SHIFT

	csrw 	pmpaddr0, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg3, x4

//											Verification Section
// Test Case 1: Default TOR region with XWR permissions

    LI(x4, PMPREGION_TOR)
    csrw pmpcfg0, x4

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
//We need to add a extra nop to complete the minimul NAPOT region i.e., 8 Byte in case of 4 Byte Grain
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
    .fill 64*(XLEN/32),4,0xdeadbeef

#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
PMP_region_High:
RVMODEL_DATA_END