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
// Coverpoints : cp_cfg_A_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A is writable in each region. For each standard
//               region, attempt to write pmpcfg.A={OFF, TOR, NA4, NAPOT} with
//               pmpcfg.L=0, pmpcfg.RWX = 000.  Only able to write NA4 if grain
//       		 G = 0. Other pmpcfg bits are writable.
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_all)
RVTEST_CASE(2,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_all)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		0x13

main:
	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, CSR_PMPCFG0
	.rept RVMODEL_NUM_PMPS/8
	csrw pmpcfgi , x0
	.set pmpcfgi, pmpcfgi+2
	.endr

#define PMP_REGION_GLOBAL	((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
#define NAPOT   (PMP_NAPOT & 0xFF)
#define TOR     (PMP_TOR   & 0xFF)
#define NA4     (PMP_NA4   & 0xFF)

#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, (PMP_REGION_GLOBAL << PMP7_CFG_SHIFT))
	csrw pmpcfg2, x4

//											Verification Section
// Test Case 1 : Setting region 0-14 to be NA4, NAPOT, TOR and OFF with L->0, XWR->000

    LI(x4, (NA4   << PMP7_CFG_SHIFT|NA4   << PMP6_CFG_SHIFT|NA4   << PMP5_CFG_SHIFT|NA4   << PMP4_CFG_SHIFT|NA4   << PMP3_CFG_SHIFT|NA4   << PMP2_CFG_SHIFT|NA4   << PMP1_CFG_SHIFT|NA4  ))
    csrw pmpcfg0, x4
    csrw pmpcfg2, x4

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, x4
    csrw pmpcfg6, x4
    csrw pmpcfg8, x4
    csrw pmpcfg10, x4
    csrw pmpcfg12, x4
    csrw pmpcfg14, x4
.endif

    LI(x4, (NAPOT << PMP7_CFG_SHIFT|NAPOT << PMP6_CFG_SHIFT|NAPOT << PMP5_CFG_SHIFT|NAPOT << PMP4_CFG_SHIFT|NAPOT << PMP3_CFG_SHIFT|NAPOT << PMP2_CFG_SHIFT|NAPOT << PMP1_CFG_SHIFT|NAPOT))
    csrw pmpcfg0, x4
    csrw pmpcfg2, x4

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, x4
    csrw pmpcfg6, x4
    csrw pmpcfg8, x4
    csrw pmpcfg10, x4
    csrw pmpcfg12, x4
    csrw pmpcfg14, x4
.endif

    LI(x4, (TOR   << PMP7_CFG_SHIFT|TOR   << PMP6_CFG_SHIFT|TOR   << PMP5_CFG_SHIFT|TOR    << PMP4_CFG_SHIFT|TOR   << PMP3_CFG_SHIFT|TOR   << PMP2_CFG_SHIFT|TOR  << PMP1_CFG_SHIFT|TOR  ))
    csrw pmpcfg0, x4
    csrw pmpcfg2, x4

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, x4
    csrw pmpcfg6, x4
    csrw pmpcfg8, x4
    csrw pmpcfg10, x4
    csrw pmpcfg12, x4
    csrw pmpcfg14, x4
.endif

    csrw pmpcfg0, zero
    csrw pmpcfg2, zero

.if RVMODEL_NUM_PMPS == 64
    csrw pmpcfg4, zero
    csrw pmpcfg6, zero
    csrw pmpcfg8, zero
    csrw pmpcfg10, zero
    csrw pmpcfg12, zero
    csrw pmpcfg14, zero
.endif

// ---------------------------------------------------------------------------

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 12
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
    .fill 64*(XLEN/32),4,0xdeadbeef

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