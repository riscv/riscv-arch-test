// ---------------------------------------------------------------------------
// Title       	: Comprehensive PMP (Physical Memory Protection) Verification
// Authors     	: Muhammad Hammad Bashir, Umer Shahid, Allen Baum
// Contact	  	: https://github.com/MuhammadHammad001
//
// Description : 	This assembly file tests access of pmp registers in M, S, and U mode.
// 					pmp csrs are accessable only in M-mode so it should trap in S, and U mode.
//
// Notes       : - Ensure `model_test.h` is configured to match your PMP grain
//                 and PMP region count before running this test.
//               - Adjust PMP configurations for specific hardware if required.
//
// Test Cases  : 1. Full RWX permissions (Read, Write, Execute)
//               2. RX permissions (Read, Execute)
//               3. RW permissions (Read, Write)
//               4. R-only permissions (Read)
//               5. X-only permissions (Execute)
//
// Dependencies: model_test.h, arch_test.h
// Total expected faults: 2+5+3+6+8 = 24.
// ---------------------------------------------------------------------------
#define rvtest_strap_routine
#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV32I_Zicsr")
# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN
#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True",PMP_access_permission)
    RVTEST_CASE(2,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def TEST_CASE_1=True",PMP_access_permission)
RVTEST_SIGBASE( x13,signature_x13_1)
	.option nopic
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3
main:
#define PMPCFG0		0x3A0		// Address of pmpcfg0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
#define PMPADDR0	0x3B0		// Address of pmpaddr0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
main:
//////////////////////// INITIAL VALUES ////////////////////////////////
    	LI(a5, -1)		// SEtting up All locked bits (including everyother non-zero bit, which is redundent for this test)
    	LI(x5, 100)		// A rondom number, to check if pmp regs get update after lock bit enable
	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, PMPCFG0	// Initialize an iterating variable with the address of pmpcfg0
	.rept 4			// START OF LOOP
	csrc pmpcfgi , a5	// Set all pmpcfg regs to zero (initial value)
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
	// Loop to SET ALL pmpaddr REGs to zero
	// Loop to SET ALL pmpaddr REGs to zero
	.set pmpaddri, PMPADDR0	// Initialize an iterating variable with the address of pmpaddr0
	.rept 16		// START OF LOOP
	csrc pmpaddri, a5	// Set all pmpaddr regs to zero (initial value)
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
//////////////// VERIFICATION /////////////////////////////////////////
// READING pmpaddr in M-mode /////////////////////////////////////////
	.set pmpaddri, PMPADDR0		// Initialize an iterating variable with the address of pmpaddr0
	.rept 16			// START OF LOOP
	csrr a4, pmpaddri		// READING pmpaddri (i is from 0-15)
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)		// Storing into signature file
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
// WRITING pmpaddr in M-mode /////////////////////////////////////////
	LI(a4,0x01)			// RANDOM VALUE
	.set pmpaddri, PMPADDR0		// Initialize an iterating variable with the address of pmpaddr0
	.rept 16			// START OF LOOP
	csrw pmpaddri, a4		// WRITING pmpaddri (i is from 0-15)
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)		// Storing into signature file
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
// WRITING pmpcfg registers //////////////////////////////////////////
// Write in M-mode will be valid, Write in other modes will cause trap
	LI(a5, PMP_R| PMP_W | PMP_X | PMP_TOR)	// LOCKED BIT IS NOT SET
	// Loop to Write ALL pmpcfg regs
	.set pmpcfgi, PMPCFG0	// Initialize an iterating variable with the address of pmpcfg0
	.rept 4			// START OF LOOP
	csrw pmpcfgi, a5	// Write pmpcfgi
	nop			// Added nop in case of trap
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
//////////////// VERIFICATION /////////////////////////////////////////
// READING pmpcfg in M-mode /////////////////////////////////////////
	// Loop to verify the contents of pmpcfg regs
	.set pmpcfgi, PMPCFG0		// Initialize an iterating variable with the address of pmpcfg0
	.rept 4				// START OF LOOP
	csrr a4, pmpcfg0		// Read pmpcfg0
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
/////////////////// Switch to S-mode ////////////////////////////////////////////
	csrw satp, zero                // Disable address translation.
	LI(t2, -1)
	csrw pmpaddr0, t2		// Updated pmpaddr0 to define PMP region consisting
					// of whole physical memory
	csrr t0, pmpaddr0		// Verify its value by reading back
	nop				// Added nop in case of trap
	LI(a5, PMP_L| PMP_R| PMP_W | PMP_X | PMP_TOR)		// LOCKED BIT IS SET
	csrw pmpcfg0, a5

	RVTEST_GOTO_LOWER_MODE	Smode	// GO into S mode
// REPEATING THE SAME TEST //////////////////////////////////////////
// IN Smode now
/////////////////// TEST 01 ////////////////////////////////////////////
// READING pmpaddr in S-mode /////////////////////////////////////////
	.set pmpaddri, PMPADDR0		// Initialize an iterating variable with the address of pmpaddr0
	.rept 4			// START OF LOOP
	csrr a4, pmpaddri		// READING pmpaddri (i is from 0-15)
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)		// Storing into signature file
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
// WRITING pmpaddr in S-mode /////////////////////////////////////////
	LI(a4,0x01)			// RANDOM VALUE
	.set pmpaddri, PMPADDR0		// Initialize an iterating variable with the address of pmpaddr0
	.rept 4			// START OF LOOP
	csrw pmpaddri, a4		// WRITING pmpaddri (i is from 0-15)
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)		// Storing into signature file
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
// WRITING pmpcfg registers //////////////////////////////////////////
// Write in M-mode will be valid, Write in other modes will cause trap
	LI(a5, PMP_R| PMP_W | PMP_X | PMP_TOR)	// LOCKED BIT IS NOT SET
	// Loop to Write ALL pmpcfg regs
	.set pmpcfgi, PMPCFG0	// Initialize an iterating variable with the address of pmpcfg0
	.rept 4			// START OF LOOP
	csrw pmpcfgi, a5	// Write pmpcfgi
	nop			// Added nop in case of trap
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
//////////////// VERIFICATION /////////////////////////////////////////
// READING pmpcfg in S-mode /////////////////////////////////////////
	// Loop to verify the contents of pmpcfg regs
	.set pmpcfgi, PMPCFG0		// Initialize an iterating variable with the address of pmpcfg0
	.rept 4				// START OF LOOP
	csrr a4, pmpcfg0		// Read pmpcfg0
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
/////////////////// Switch back to M-mode ////////////////////////////////////////////
	RVTEST_GOTO_MMODE
  	csrr a4, mstatus		// VERIFICATION of M-mode
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)
/////////////////// Switch to U-mode ////////////////////////////////////////////
	csrw satp, zero                 // Disable address translation.
	LI(t2, -1)
	csrw pmpaddr0, t2		// Updated pmpaddr0 to define PMP region consisting
					// of whole physical memory
	csrr t0, pmpaddr0		// Verify its value by reading back
	nop				// Added nop in case of trap
	LI(a5, PMP_L| PMP_R| PMP_W | PMP_X | PMP_TOR)		// LOCKED BIT IS SET
	csrw pmpcfg0, a5
// These steps are repeated and can be removed but it will make sure that you will switch mode
// with full access on physical memory
	RVTEST_GOTO_LOWER_MODE	Umode
// REPEATING THE SAME TEST //////////////////////////////////////////
// IN U-mode now
// READING pmpaddr in U-mode /////////////////////////////////////////
	.set pmpaddri, PMPADDR0		// Initialize an iterating variable with the address of pmpaddr0
	.rept 4				// START OF LOOP
	csrr a4, pmpaddri		// READING pmpaddri (i is from 0-15)
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)		// Storing into signature file
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
// WRITING pmpaddr in U-mode /////////////////////////////////////////
	LI(a4,0x01)			// RANDOM VALUE
	.set pmpaddri, PMPADDR0		// Initialize an iterating variable with the address of pmpaddr0
	.rept 4			// START OF LOOP
	csrw pmpaddri, a4		// WRITING pmpaddri (i is from 0-15)
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)		// Storing into signature file
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
// WRITING pmpcfg registers //////////////////////////////////////////
// Write in M-mode will be valid, Write in other modes will cause trap
	LI(a5, PMP_R| PMP_W | PMP_X | PMP_TOR)	// LOCKED BIT IS NOT SET
	// Loop to Write ALL pmpcfg regs
	.set pmpcfgi, PMPCFG0	// Initialize an iterating variable with the address of pmpcfg0
	.rept 4			// START OF LOOP
	csrw pmpcfgi, a5	// Write pmpcfgi
	nop			// Added nop in case of trap
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
//////////////// VERIFICATION /////////////////////////////////////////
// READING pmpcfg in U-mode /////////////////////////////////////////
	// Loop to verify the contents of pmpcfg regs
	.set pmpcfgi, PMPCFG0		// Initialize an iterating variable with the address of pmpcfg0
	.rept 4				// START OF LOOP
	csrr a4, pmpcfg0		// Read pmpcfg0
	nop				// Added nop in case of trap
	RVTEST_SIGUPD(x13,a4)
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY

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
