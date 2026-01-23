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
// Coverpoints : cp_cfg_L_modify for PMPM is partially covered in this test file.
//
// Test Cases  : Checking that pmpcfg and pmpaddr are unwritable when L = 1.
//               With pmpcfg_i.L ={0/1}, pmpcfg_i.A = TOR, pmpcfg_i.XWR = 111,
//               pmpaddr_i = 0x100, trying to change pmpcfg_i to 000000000,
//               and to change pmpaddr_i to 0s, and reading these back. 
//               When L = 1, should be unchanged because of lock.
//               When L = 0, changeable.
//
//               Checking that pmpcfg and pmpaddr of previous region are unwritable
//               when L=1. With pmpcfg_i.L ={0/1}, pmpcfg_i.A=TOR, pmpcfg_i.XWR=111,
//               pmpaddr_i=0x100, pmpcfg_i-1.L=0 trying to change pmpcfg_i-1 to
//               00000111, and to change pmpaddr_i-1 to 1s and reading these back.
//               pmpaddr_i-1 should be unchanged because of lock iff pmpcfg_i.A = TOR,
//               otherwise change. pmpcfg_i-1 is changable independent of pmpcfg_i.A.
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_L_modify)
RVTEST_CASE(2,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_L_modify)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc

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
		
#define PMP_REGION_GLOBAL	((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region

#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, (PMP_REGION_GLOBAL << PMP7_CFG_SHIFT))
	csrw pmpcfg2, x4

//											Verification Section
// Test Case 1 : Setting region 1 to be TOR with L->0, XWR->111 and pmpaddr->0x100

    addi x4, x0, 0x100
    csrw pmpaddr1, x4

    LI(x4, ((PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF) << PMP1_CFG_SHIFT)
    csrw pmpcfg0, x4

    // Now trying to change pmp0cfg0 to 000000111, and to change pmpaddr0 to 1s.

    addi x5, x4, 7
    csrw pmpcfg0, x5
    addi x4, x0,-1
    csrw pmpaddr0, x4

    // Now trying to change pmp1cfg0 to 000000000, and to change pmpaddr1 to 0s.

    csrw pmpaddr1, x0
    csrw pmpcfg0, x0

//--- Re-initialize the CSRs. ---
    csrw pmpaddr0, x0
    csrw pmpcfg0, x0
//-------------------------------

// Test Case 2 : Setting region 1 to be TOR with L->1, XWR->111 and pmpaddr->0x100

    addi x4, x0, 0x100
    csrw pmpaddr1, x4

    LI(x4, ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF) << PMP1_CFG_SHIFT)
    csrw pmpcfg0, x4

    // Now trying to change pmp0cfg0 to 000000111, and to change pmpaddr0 to 1s.

    addi x5, x4, 7
    csrw pmpcfg0, x5
    addi x4, x0,-1
    csrw pmpaddr0, x4

    // Now trying to change pmp1cfg0 to 000000000, and to change pmpaddr1 to 0s.

    csrw pmpaddr1, x0
    csrw pmpcfg0, x0

// ---------------------------------------------------------------------------

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
    RVTEST_SIGUPD(x13, a4)       								// Signature update
	j exit														// Verification Complete, exit the test

.align 10
.align (RVMODEL_PMP_GRAIN+2)

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