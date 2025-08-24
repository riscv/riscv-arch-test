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
// Coverpoints : cp_cfg_A_tor_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking A = TOR works in each region. Preconfigure all 
//				 (PMP_writable_regs-1) PMP regions in with pmpcfg.L = 1,
//				 pmpcfg.A = TOR, pmpcfg.XWR=00(i%2), starting with default
//				 TOR region and moving up by g*i (each region getting larger by g).
//				 Attempt lw at at start of region.  Odd regions should allow lw,
//				 and all others should trap.
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

RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor_all)
RVTEST_CASE(2,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor_all)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		0x13

.macro VERIFICATION_RWX ADDRESS 

    LA(a5, \ADDRESS)             							// Address to be ve
    lw a4, 0(a5)                 							// Word load test
    nop
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

#define PMP_REGION_GLOBAL	(((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT)  // Background region with RWX enable.
#define DEFAULT_TOR_REGION  (((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF) << PMP0_CFG_SHIFT)
#define PMPREGION0_XWR_000  (((PMP_L|                  PMP_TOR)&0xFF) << PMP0_CFG_SHIFT)
#define PMPREGION1_XWR_001  (((PMP_L|PMP_R|            PMP_TOR)&0xFF) << PMP1_CFG_SHIFT)
#define PMPREGION2_XWR_000  (((PMP_L|                  PMP_TOR)&0xFF) << PMP2_CFG_SHIFT)
#define PMPREGION3_XWR_001  (((PMP_L|PMP_R|            PMP_TOR)&0xFF) << PMP3_CFG_SHIFT)
	
#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, -1)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, (PMP_REGION_GLOBAL))
	csrw pmpcfg3, x4

	LA(x4, TEST_FOR_EXECUTION_0)
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr0, x4

	LA(x4, (TEST_FOR_EXECUTION_1))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr1, x4

	LA(x4, (TEST_FOR_EXECUTION_2))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr2, x4

	LA(x4, (TEST_FOR_EXECUTION_3))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr3, x4

	LA(x4, (TEST_FOR_EXECUTION_4))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr4, x4

	LA(x4, (TEST_FOR_EXECUTION_5))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr5, x4

	LA(x4, (TEST_FOR_EXECUTION_6))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr6, x4

	LA(x4, (TEST_FOR_EXECUTION_7))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr7, x4

	LA(x4, (TEST_FOR_EXECUTION_8))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr8, x4

	LA(x4, (TEST_FOR_EXECUTION_9))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr9, x4

	LA(x4, (TEST_FOR_EXECUTION_10))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr10, x4

	LA(x4, (TEST_FOR_EXECUTION_11))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr11, x4

	LA(x4, (TEST_FOR_EXECUTION_12))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr12, x4

	LA(x4, (TEST_FOR_EXECUTION_13))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr13, x4

	LA(x4, (TEST_FOR_EXECUTION_14))
	srl x4, x4, PMP_SHIFT
    csrw pmpaddr14, x4

//											Verification Section
// Test Case: 1 : Preconfigure all (PMP_writable_regs-1) PMP regions in with pmpcfg.L = 1, pmpcfg.A = TOR, pmpcfg.XWR=00(i%2)

    LI(x4, (PMPREGION3_XWR_001|PMPREGION2_XWR_000|PMPREGION1_XWR_001|DEFAULT_TOR_REGION))
	csrw pmpcfg0, x4
    LI(x4, (PMPREGION3_XWR_001|PMPREGION2_XWR_000|PMPREGION1_XWR_001|PMPREGION0_XWR_000))
	csrw pmpcfg1, x4
    LI(x4, (PMPREGION3_XWR_001|PMPREGION2_XWR_000|PMPREGION1_XWR_001|PMPREGION0_XWR_000))
	csrw pmpcfg2, x4
    LI(x4, (PMPREGION2_XWR_000|PMPREGION1_XWR_001|PMPREGION0_XWR_000))
	csrw pmpcfg3, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION_0
	VERIFICATION_RWX	TEST_FOR_EXECUTION_1
	VERIFICATION_RWX	TEST_FOR_EXECUTION_2
	VERIFICATION_RWX	TEST_FOR_EXECUTION_3
	VERIFICATION_RWX	TEST_FOR_EXECUTION_4
	VERIFICATION_RWX	TEST_FOR_EXECUTION_5
	VERIFICATION_RWX	TEST_FOR_EXECUTION_6
	VERIFICATION_RWX	TEST_FOR_EXECUTION_7
	VERIFICATION_RWX	TEST_FOR_EXECUTION_8
	VERIFICATION_RWX	TEST_FOR_EXECUTION_9
	VERIFICATION_RWX	TEST_FOR_EXECUTION_10
	VERIFICATION_RWX	TEST_FOR_EXECUTION_11
	VERIFICATION_RWX	TEST_FOR_EXECUTION_12
	VERIFICATION_RWX	TEST_FOR_EXECUTION_13

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION_0:						// Adding nops in TOR Region from 0x80001000 to 0x80001000 + g 
	.rept (1<<RVMODEL_PMP_GRAIN)
	nop
	.endr

TEST_FOR_EXECUTION_1:						// Adding nops in TOR Region from 0x80001000 + g to 0x80001000 + 3g
	.rept (2*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_2:						// Adding nops in TOR Region from 0x80001000 + 3g to 0x80001000 + 6g
	.rept (3*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_3:						// Adding nops in TOR Region from 0x80001000 + 6g to 0x80001000 + 10g
	.rept (4*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_4:						// Adding nops in TOR Region from 0x80001000 + 10g to 0x80001000 + 15g
	.rept (5*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr
	
TEST_FOR_EXECUTION_5:						// Adding nops in TOR Region from 0x80001000 + 15g to 0x80001000 + 21g
	.rept (6*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_6:						// Adding nops in TOR Region from 0x80001000 + 21g to 0x80001000 + 28g
	.rept (7*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_7:						// Adding nops in TOR Region from 0x80001000 + 28g to 0x80001000 + 36g
	.rept (8*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_8:						// Adding nops in TOR Region from 0x80001000 + 36g to 0x80001000 + 45g
	.rept (9*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_9:						// Adding nops in TOR Region from 0x80001000 + 45g to 0x80001000 + 55g
	.rept (10*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr
	
TEST_FOR_EXECUTION_10:						// Adding nops in TOR Region from 0x80001000 + 55g to 0x80001000 + 66g
	.rept (11*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_11:						// Adding nops in TOR Region from 0x80001000 + 66g to 0x80001000 + 78g
	.rept (12*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_12:						// Adding nops in TOR Region from 0x80001000 + 78g to 0x80001000 + 91g
	.rept (13*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_13:						// Adding nops in TOR Region from 0x80001000 + 91g to 0x80001000 + 105g
	.rept (14*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

TEST_FOR_EXECUTION_14:						// Adding nops in TOR Region from 0x80001000 + 105g to 0x80001000 + 120g
	.rept (15*(1<<RVMODEL_PMP_GRAIN))
	nop
	.endr

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