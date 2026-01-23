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
// Coverpoints :  cp_priority for PMPM is fully covered in this file.
//
// Test Cases  :  Testing that first matching region has priority to determing
//                XWR. Set up 7 even/odd pairs of TOR regions, where each pair
//                starts (even) at the standard location and has pair i has size
//                i*g (in odd reg) so the regions partially overlap. Set the even
//                pmpcfg to 0 (OFF). Set the odd pmpcfg to TOR and cycle through
//                the 6 legal XWR values for each pair. Make {lw, sw, jalr} to
//                each of (PMP_writable_regs-1) addresses at end of each region. 
//                Access fault if the relevant (highest priority) region prohibits
//                access.
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_priority)
RVTEST_CASE(2,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_priority)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		(0x13<<32)+0x13
#define g   (1 << (RVMODEL_PMP_GRAIN + 2))

.macro VERIFICATION_RWX ADDRESS  

	LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
	LA(x4, 1f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
1:
	nop
	nop

    LI(a4, NOP)                  							// Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)             							// Address to be verified
    sw a4, 0(a5)
    nop
    nop

    LA(a5, \ADDRESS)             							// Address to be verified
    lw a4, 0(a5)
    nop
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

#define PMP_REGION_GLOBAL	((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|      PMP_R|PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W|      PMP_TOR  )&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|            PMP_X|PMP_TOR  )&0xFF) << PMP7_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R            |PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))

#ifdef rvtest_strap_routine
	csrw satp, zero                 // Disable address translation.
#endif

	LA(x4, -1)                      // All memory region
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg2, x4

    LA(x4, TEST_FOR_EXECUTION)
    srl x4, x4, PMP_SHIFT
    LI(x5, g)
    add x5, x0, x5

    // REGIONSTART in even PMPADDR
    .set pmpaddri, CSR_PMPADDR0
    .rept 7
    csrw pmpaddri, x4
    .set pmpaddri, pmpaddri+2
    .endr

    // REGIONSTART + i*g in odd PMPADDR
    LA(x5, TEST_FOR_EXECUTION)
    .set pmpaddri, CSR_PMPADDR0+1
    .rept 7
    LI(t0, g)
    add x5, x5, t0
    srl x6, x5, PMP_SHIFT
    csrw pmpaddri, x6
    .set pmpaddri, pmpaddri+2
    .endr

	// Setting the even pmpcfg to 0 and odd pmpcfg to TOR & and rotating through the 6 legal XWR values.
    LI(x4, (PMPREGION_LXWR_1100|PMPREGION_LXWR_1011|PMPREGION_LXWR_1101|PMPREGION_LXWR_1000))
    csrw pmpcfg0, x4
    LI(x4, (PMPREGION_LXWR_1000 << PMP4_CFG_SHIFT|PMPREGION_LXWR_1111|PMPREGION_LXWR_1001))
    csrw pmpcfg2, x4

//											Verification Section
// Test Case: 1 : Accessing at end of region with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + g - 4)

// Test Case: 2 : Accessing at end of region with XR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 2*g - 4)

// Test Case: 3 : Accessing at end of region with WR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 3*g - 4)

// Test Case: 4 : Accessing at end of region with X Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 4*g - 4)

// Test Case: 5 : Accessing at end of region with R Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 5*g - 4)

// Test Case: 6 : Accessing at end of region with XWR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 6*g - 4)

// Test Case: 6 : Accessing at end of region with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 7*g - 4)

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:     // Largest Region of size 7*g
	.rept 7*(1<<RVMODEL_PMP_GRAIN)
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