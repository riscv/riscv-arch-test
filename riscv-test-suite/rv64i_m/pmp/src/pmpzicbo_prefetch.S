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
// Coverpoints : cp_prefetch for PMPZicbo is partially covered in this test file.
//
// Test Cases  : Check that XWR bits control access for prefetch.
//				 Attempt {prefetch.i/w/r} with pmpcfg_i.L=1, legal pmpcfg_i.XWR,
//				 at start of 4 KB region plenty long to encompass a cache line.
//				 No exceptions should be raised.
//
// Dependencies: model_test.h, arch_test.h
// ---------------------------------------------------------------------------

#define SKIP_MEPC
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV64I_Zicbop_Zicsr")
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:= regex(.*I[^S]*Zicbop.*Zicsr.*); def rvtest_mtrap_routine=True;								def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_prefetch)
RVTEST_CASE(2,"//check ISA:=regex(.*64.*); check ISA:= regex(.*I.*S.*Zicbop.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_prefetch)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 			0x13

.macro VERIFICATION_RWX ADDRESS

	// Address must be aligned to the cache block
	LA(t0, \ADDRESS)
	prefetch.i 0(t0) 
	nop
	prefetch.r 0(t0) 
	nop
	prefetch.w 0(t0) 

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
		

#define PMP_REGION_GLOBAL				((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 			((((PMP_L|                  PMP_TOR)&0xFF) << PMP6_CFG_SHIFT))
#define PMPREGION_LXWR_1001 			((((PMP_L|PMP_R|            PMP_TOR)&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1011 			((((PMP_L|PMP_R|PMP_W	   |PMP_TOR)&0xFF) << PMP4_CFG_SHIFT))
#define PMPREGION_LXWR_1100 			((((PMP_L|			  PMP_X|PMP_TOR)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1101 			((((PMP_L|PMP_R		 |PMP_X|PMP_TOR)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1111 			((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF) << PMP1_CFG_SHIFT))

#define MENVCFG							0xF0 															// menvcfg.CBIE, CBCFE, CBZE = 1
#define PMPADDRESS_TOP_GLOBAL			-1			// All memory region

#define REGIONSTART			0x80002000
#define REGIONEND			0x80003000

#define LOWER_BOUND		(REGIONSTART >> PMP_SHIFT) 		
#define UPPER_BOUND		(REGIONEND   >> PMP_SHIFT)

#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg2, x4	

	li t0, MENVCFG
	csrrs zero, menvcfg, t0

//											    Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region
	
	LA(x4, LOWER_BOUND)
	csrw pmpaddr5, x4

	LA(x4, UPPER_BOUND)
	csrw pmpaddr6, x4

	LI(x4, PMPREGION_LXWR_1000)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region
	
	LA(x4, LOWER_BOUND)
	csrw pmpaddr4, x4

	LA(x4, UPPER_BOUND)
	csrw pmpaddr5, x4

	LI(x4, PMPREGION_LXWR_1001)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region
	
	LA(x4, LOWER_BOUND)
	csrw pmpaddr3, x4

	LA(x4, UPPER_BOUND)
	csrw pmpaddr4, x4

	LI(x4, PMPREGION_LXWR_1011)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region
	
	LA(x4, LOWER_BOUND)
	csrw pmpaddr2, x4

	LA(x4, UPPER_BOUND)
	csrw pmpaddr3, x4

	LI(x4, PMPREGION_LXWR_1100)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 5 : L -> 1 and XR Permissions given to the PMP Region
	
	LA(x4, LOWER_BOUND)
	csrw pmpaddr1, x4

	LA(x4, UPPER_BOUND)
	csrw pmpaddr2, x4

	LI(x4, PMPREGION_LXWR_1101)
	csrw pmpcfg0, x4
	
	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region

	LA(x4, LOWER_BOUND)
	csrw pmpaddr0, x4

	LA(x4, UPPER_BOUND)
	csrw pmpaddr1, x4

	LI(x4, PMPREGION_LXWR_1111)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	RVTEST_GOTO_MMODE
	li a4, 0xbeefcafe							// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       				// Signature update
	j exit										// Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
	.rept 1024
	nop
	.endr
.if RVMODEL_PMP_GRAIN == 0
    nop
.endif

RETURN_INSTRUCTION:
	nop
	nop
	jr ra										// Get back to the point from where TEST_FOR_EXECUTION was called.

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
