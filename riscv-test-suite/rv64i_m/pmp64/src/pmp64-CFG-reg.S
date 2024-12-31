// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This test belongs to the test plan for RISC-V Privilege Arch Compliance developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1p13gic7BD6aq7n_dHrqti4QmlGpxY7FkF17RVbG4DC0/edit?usp=sharing
//
// This assembly file tests access of pmp registers in M, S, and U mode.
// pmp csrs are accessable only in M-mode so it should trap in S, and U mode.
//
// coverpoint definitions are given in coverage/pmp32_translated_coverpoints.cgf or coverage/pmp32_coverpoint_def_format.cgf
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV64I_Zicsr")
# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",pmp_cfg_locked_write_unrelated)
RVTEST_SIGBASE( x3,signature_x3_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3
  	.option norvc
#define PMPCFG0		0x3A0		// Address of pmpcfg0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
#define PMPADDR0	0x3B0		// Address of pmpaddr0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
main:
//////////////////////// INITIAL VALUES //////////////////////////////// 
    	LI(a5, -1)		// SEtting up All locked bits (including everyother non-zero bit, which is redundent for this test)
    	LI(x9,0)		// The register to carry offset value
    	LI(x5, 100)		// A rondom number, to check if pmp regs get update after lock bit enable
	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, PMPCFG0	// Initialize an iterating variable with the address of pmpcfg0
	.rept 2			// START OF LOOP
	csrc pmpcfgi , a5	// Set all pmpcfg regs to zero (initial value)
	.set pmpcfgi, pmpcfgi+2		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
	// Loop to SET ALL pmpaddr REGs to zero
	.set pmpaddri, PMPADDR0	// Initialize an iterating variable with the address of pmpaddr0
	.rept 16		// START OF LOOP
	csrc pmpaddri, a5	// Set all pmpaddr regs to zero (initial value)
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY

//////////////////// Locked bit TEST 1 /////////////////////////////////////////////	
	.set pmpcfgi, PMPCFG0	// Initialize an iterating variable with the address of pmpcfg0
	.rept 2			// START OF LOOP

	csrw pmpcfgi, a5	// WRITE pmpcfgi with ALL 1s, Locked the lock-bit [7,15,23,31]
	nop			// Added nop in case of trap
	csrr a4, pmpcfgi	// READ pmpcfgi
	// THIS READ WILL ALSO CONFIRM THE ZERO BITs OF PMPCFGi REG.		
	// BIT 5-6, BIT 13-14, BIT 21-22, BIT 29-30 must be hardwired to zero
	// Verify that LOCKED bits are HIGH, and ZERO bits are zero
	RVTEST_SIGUPD(x3,a4)
	// TRY TO WRITE CFG REGISTER AGAIN (TRAP in case of LOCKED bit is HIGH)
	csrw pmpcfgi, x5		// WRITE pmpcfgi with some other values
	nop				// Added nop in case of trap
	csrr a4, pmpcfgi		// READ pmpcfgi		
	// Since Locked bit is high, so this should return the old value!!!
	RVTEST_SIGUPD(x3,a4)
	
	.set pmpaddri, PMPADDR0+4*(pmpcfgi-PMPCFG0)	
// Initialize an iterating variable with the address of pmpaddr0 in 1st iteration (when pmpcfgi=pmpcfg0)
// Initialize an iterating variable with the address of pmpaddr4 in 2nd iteration (when pmpcfgi=pmpcfg1)
// Initialize an iterating variable with the address of pmpaddr8 in 3rd iteration (when pmpcfgi=pmpcfg2)
// Initialize an iterating variable with the address of pmpaddr12 in 4th iteration (when pmpcfgi=pmpcfg3)
	.rept 8				// START OF LOOP
	// TRY TO WRITE ADDRESS REGISTER.
	csrw pmpaddri, a5		// WRITE pmpaddri with some other values
	// The updated write will give a trap!!!
	nop				// Added nop in case of trap
	csrr a4, pmpaddri		// READ pmpaddr0, value should not have been changed		
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x3,a4)
	.set pmpaddri, pmpaddri+1	// increment variable pmpaddri to the next pmpaddr reg
	.endr				// END OF INNER LOOP BODY
		
	.set pmpcfgi, pmpcfgi+2		// increment variable to next pmpcfg reg	.endr			// END OF OUTER LOOP BODY
	.endr
#endif
 # ---------------------------------------------------------------------------------------------
    # HALT
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
signature_x3_1:
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
