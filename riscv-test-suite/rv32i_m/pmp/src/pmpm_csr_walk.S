// --------------------------------------------------------------------------------
// Title       	: Comprehensive PMP (Physical Memory Protection) Verification
// Authors     	: Umer Shahid, Allen Baum, David Harris
//				  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It evaluates RWX permissions at different granularity
//               levels (byte, half-word, word, double word) and across various
//               PMP configurations. The test adheres to the RISC-V Privileged
//               Specification v1.12 and includes:
//               - Comprehensive RWX checks for multiple PMP regions.
//
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Coverpoints : cp_pmpcfg_walk and cp_pmpaddr_walk for PMPM is fully covered in 
//               this test file.
//
// Test Cases  : Test pmpaddr access. No background region, writing all 1s,
//               walking 1s, all 0s to all defined pmpaddr CSRs. Test pmpcfg access,
//               writing walking 1s from lsb to msb (XLEN-1) to pmpcfg CSRs 0, 2 and
//               writing 0 to pmpcfg 1, 3. If 64 CSRs are supported, doing same
//               with 4, 6, 8, 10, 12, 14; and 5, 7, 9, 11, 13, 15. 
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

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

RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_pmpaddr_walk,cp_pmpcfg_walk)
RVTEST_CASE(2,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_pmpaddr_walk,cp_pmpcfg_walk)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc

main:
    RVTEST_GOTO_MMODE

	// Loop to SET ALL pmpaddr REGs to zeros
	.set pmpaddri, CSR_PMPADDR0
	.rept RVMODEL_NUM_PMPS
	csrw pmpaddri, x0
	.set pmpaddri, pmpaddri+1
	.endr

    li t0, -1
	// Loop to SET ALL pmpaddr REGs to ones
	.set pmpaddri, CSR_PMPADDR0
	.rept RVMODEL_NUM_PMPS
	csrw pmpaddri, t0
	.set pmpaddri, pmpaddri+1
	.endr

	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, CSR_PMPCFG0
	.rept RVMODEL_NUM_PMPS/4
	csrw pmpcfgi , x0
	.set pmpcfgi, pmpcfgi+1
	.endr


    li t2, 1                     // walking one: 0x00000001

1:  // Outer loop for walking ones
    csrw pmpaddr0, t2
    csrw pmpaddr1, t2
    csrw pmpaddr2, t2
    csrw pmpaddr3, t2
    csrw pmpaddr4, t2
    csrw pmpaddr5, t2
    csrw pmpaddr6, t2
    csrw pmpaddr7, t2
    csrw pmpaddr8, t2
    csrw pmpaddr9, t2
    csrw pmpaddr10, t2
    csrw pmpaddr11, t2
    csrw pmpaddr12, t2
    csrw pmpaddr13, t2
    csrw pmpaddr14, t2
    csrw pmpaddr15, t2
    .if RVMODEL_NUM_PMPS == 64
        csrw pmpaddr16, t2
        csrw pmpaddr17, t2
        csrw pmpaddr18, t2
        csrw pmpaddr19, t2
        csrw pmpaddr20, t2
        csrw pmpaddr21, t2
        csrw pmpaddr22, t2
        csrw pmpaddr23, t2
        csrw pmpaddr24, t2
        csrw pmpaddr25, t2
        csrw pmpaddr26, t2
        csrw pmpaddr27, t2
        csrw pmpaddr28, t2
        csrw pmpaddr29, t2
        csrw pmpaddr30, t2
        csrw pmpaddr31, t2
        csrw pmpaddr32, t2
        csrw pmpaddr33, t2
        csrw pmpaddr34, t2
        csrw pmpaddr35, t2
        csrw pmpaddr36, t2
        csrw pmpaddr37, t2
        csrw pmpaddr38, t2
        csrw pmpaddr39, t2
        csrw pmpaddr40, t2
        csrw pmpaddr41, t2
        csrw pmpaddr42, t2
        csrw pmpaddr43, t2
        csrw pmpaddr44, t2
        csrw pmpaddr45, t2
        csrw pmpaddr46, t2
        csrw pmpaddr47, t2
        csrw pmpaddr48, t2
        csrw pmpaddr49, t2
        csrw pmpaddr50, t2
        csrw pmpaddr51, t2
        csrw pmpaddr52, t2
        csrw pmpaddr53, t2
        csrw pmpaddr54, t2
        csrw pmpaddr55, t2
        csrw pmpaddr56, t2
        csrw pmpaddr57, t2
        csrw pmpaddr58, t2
        csrw pmpaddr59, t2
        csrw pmpaddr60, t2
        csrw pmpaddr61, t2
        csrw pmpaddr62, t2
        csrw pmpaddr63, t2
    .endif

    slli t2, t2, 1               // Shift walking one to left
    bnez t2, 1b                  // Continue loop while t2 != 0

    li t2, 1                     // walking one: 0x00000001

2:  // Outer loop for walking ones
    csrw pmpcfg0, t2
    csrw pmpcfg2, t2
    .if RVMODEL_NUM_PMPS == 64
        csrw pmpcfg4, t2
        csrw pmpcfg6, t2
        csrw pmpcfg8, t2
        csrw pmpcfg10, t2
        csrw pmpcfg12, t2
        csrw pmpcfg14, t2
    .endif

    slli t2, t2, 1               // Shift walking one to left
    bnez t2, 2b                  // Continue loop while t2 != 0

	RVTEST_GOTO_MMODE
	li a4, 0xbeefcafe							// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       				// Signature update
	j exit										// Verification Complete, exit the test

.align 10
.align (RVMODEL_PMP_GRAIN+2)

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
    .fill 128*(XLEN/32),4,0xdeadbeef
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