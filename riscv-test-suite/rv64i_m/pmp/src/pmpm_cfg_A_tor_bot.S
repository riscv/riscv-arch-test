// --------------------------------------------------------------------------------
// Title       	: Comprehensive PMP (Physical Memory Protection) Verification
// Authors     	: Umer Shahid, Allen Baum, David Harris
//				  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description  :This test verifies the functionality and enforcement of
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
// Coverpoints : cp_cfg_A_tor_bot for PMPM is fully covered in this test file. 
//
// Test cases  : In this test, we check that region 1 extends from pmpaddr0 to
//				pmpaddr1. We set up a default TOR region, then make accesses
//				{lw,sw,jalr} at addresses {pmpadr0-4, pmpadr0, pmpadr1-4, pmpadr1}.
//
//				Test case 1: pmpcfg1.L=1, pmpcfg1.A = TOR, pmpcfg1.XWR=101, 
//               pmpcfg0.L = 0, pmpcfg0.A = OFF, pmpcfg0.XWR = 000 
//
//              Test case 2: pmpcfg1.L=1, pmpcfg1.A = TOR, pmpcfg1.XWR=101, 
//               pmpcfg0.L = 1, pmpcfg0.A = OFF, pmpcfg0.XWR = 000
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor_bot)
RVTEST_CASE(2,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor_bot)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		(0x13<<32)+0x13
#define g 		(1<<(RVMODEL_PMP_GRAIN+2))

.macro VERIFICATION_RWX ADDRESS    

    LI(a4, NOP)                  							// Value to write (NOP)

    LA(a5, (\ADDRESS-4))             						// Address to be verified
    sw a4, 0(a5)                 							// word-level store test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA(a5, (\ADDRESS))             						    // Address to be verified
    sw a4, 0(a5)                 							// word-level store test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA(a5, ((\ADDRESS+g)-4))             				    // Address to be verified
    sw a4, 0(a5)                 							// word-level store test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA(a5, (\ADDRESS+g))             				        // Address to be verified
    sw a4, 0(a5)                 							// word-level store test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA(a5, (\ADDRESS-4))             						// Address to be verified
    lw a4, 0(a5)                 							// Word load test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update
  
    LA(a5, (\ADDRESS))             						    // Address to be verified
    lw a4, 0(a5)                 							// Word load test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update
    
    LA(a5, ((\ADDRESS+g)-4))             						// Address to be verified
    lw a4, 0(a5)                 							// Word load test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA(a5, (\ADDRESS+g))             						// Address to be verified
    lw a4, 0(a5)                 							// Word load test
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LA (a4, (\ADDRESS-4))
	LI(x3, 0xACCE)						                    // Store a value which is to be checked in trap handler
	LA(x4, 1f)							                    // Store the return Address in x4
	jalr ra, 0(a4)
	nop
1:
	nop

    LA (a4, (\ADDRESS))
	LA(x4, 2f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
2:
	nop

    LA (a4, ((\ADDRESS+g)-4))
	LA(x4, 3f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
3:
	nop

    LA (a4, (\ADDRESS+g))
	LA(x4, 4f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
4:
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
		

#define PMP_REGION_GLOBAL			((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_UPPER_BOUND      	((((PMP_L|PMP_R		 |PMP_X|PMP_TOR)  &0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LOWER_BOUND       ((((PMP_L)      					  &0xFF) << PMP0_CFG_SHIFT))

#ifdef rvtest_strap_routine
	csrw satp, zero             // Disable address translation.
#endif

	LA(x4, -1)		   			// All memory region
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg2, x4

    LA(x4, TEST_FOR_EXECUTION)
	LI(x5, g)
	add    x5, x4, x5
    srl x4, x4, PMP_SHIFT
    srl x5, x5, PMP_SHIFT
    
    csrw 	pmpaddr0, x4
    csrw 	pmpaddr1, x5

//											Verification Section
// Test Case: 1

	LI(x4, PMPREGION_UPPER_BOUND)
	csrw pmpcfg0, x4
    
	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 2

	LI(x4, PMPREGION_UPPER_BOUND)
	csrw pmpcfg0, x4
    LI(x4, PMPREGION_LOWER_BOUND)
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