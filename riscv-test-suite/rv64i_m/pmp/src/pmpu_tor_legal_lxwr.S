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
// Coverpoints : cp_cfg_A_tor for PMPU is fully covered in this test file.
//
// Test Cases  : Configuring PMP in M mode and then switching to U mode.
//               Checking XWR controls accesses in matching TOR region. With 
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR, 
//               default TOR region, address-g in pmpaddr_i-1: making {lw,sw,jalr}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
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

RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor)
RVTEST_CASE(2,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		(0x13<<32)+0x13
#define g      (1<<(RVMODEL_PMP_GRAIN+2))

.macro VERIFICATION_RWX ADDRESS  

	LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
	LA(x4, 1f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
1:
	nop

    addi a4, a4, -4                     // REGIONSTART - 4
	LA(x4, 2f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
2:
	nop

    addi a4, a4, 8                      // REGIONSTART + 4
	LA(x4, 3f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
3:
	nop

    LI(t0, (g-8))
    add a4, a4, t0                      // REGIONSTART + g - 4
	LA(x4, 4f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
4:
	nop

    addi a4, a4, 4                      // REGIONSTART + g
	LA(x4, 5f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
5:
	nop

    LI(a4, NOP)                  							// Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)             							// Address to be verified
    sw a4, 0(a5)
    nop

    addi a5, a5, -4                                         // REGIONSTART - 4
    sw a4, 0(a5)
    nop

    addi a5, a5, 8                                          // REGIONSTART + 4
    sw a4, 0(a5)
    nop

    li x0, (g-8)
    add a5, a5, t0                                          // REGIONSTART + g - 4ls
    sw a4, 0(a5)
    nop

    addi a5, a5, 4                                          // REGIONSTART + g
    sw a4, 0(a5)
    nop

    LA(a5, \ADDRESS)             							// Address to be verified
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LI(t0, (g-8))
    add a5, a5, t0                                          // REGIONSTART + g - 4
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, 4                                          // REGIONSTART + g
    lw a4, 0(a5)
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
#define PMPREGION_LXWR_0000 ((((                        PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0001 ((((      PMP_R|            PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_0011 ((((      PMP_R|PMP_W	   |PMP_TOR  )&0xFF) << PMP7_CFG_SHIFT))
#define PMPREGION_LXWR_0100 ((((      			  PMP_X|PMP_TOR  )&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_0101 ((((      PMP_R		 |PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_0111 ((((      PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL		-1												// All memory region
#define REGIONSTART			0x80002000		// RAM_BASE_ADDR + PROGRAM_SIZE
#define TOR_UPPER_BOUND		((REGIONSTART+g) >> PMP_SHIFT)
#define TOR_LOWER_BOUND		(REGIONSTART >> PMP_SHIFT)

#ifdef rvtest_strap_routine
	csrw satp, zero                // Disable address translation.
#endif

	LA(x4, PMPADDRESS_TOP_GLOBAL)
	csrw 	pmpaddr15, x4

	//Lock the Background region.
	LI(x4, PMP_REGION_GLOBAL)
	csrw pmpcfg2, x4

//											Verification Section
// Test Case: 1 : L -> 0 and No Permissions given to the PMP Region 11

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr11, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr10, x5
    LI(x4, PMPREGION_LXWR_0000)
	csrw pmpcfg2, x4

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 2 : L -> 0 and R Permissions given to the PMP Region 9

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr9, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr8, x5
    LI(x4, PMPREGION_LXWR_0001)
	csrw pmpcfg2, x4

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 3 : L -> 0 and WR Permissions given to the PMP Region 7

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr7, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr6, x5
    LI(x4, PMPREGION_LXWR_0011)
	csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 4 : L -> 0 and X Permissions given to the PMP Region 5

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr5, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr4, x5
    LI(x4, PMPREGION_LXWR_0100)
	csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 5 : L -> 0 and RX Permissions given to the PMP Region 3

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr3, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr2, x5
    LI(x4, PMPREGION_LXWR_0101)
	csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

// Test Case: 6 : L -> 0 and XWR Permissions given to the PMP Region 1

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr1, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr0, x5
    LI(x4, PMPREGION_LXWR_0111)
	csrw pmpcfg0, x4

    RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION
    RVTEST_GOTO_MMODE

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
	RVTEST_SIGUPD(x13, a4)										// Signature update
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
    .fill 32*(XLEN/32),4,0xdeadbeef

#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END