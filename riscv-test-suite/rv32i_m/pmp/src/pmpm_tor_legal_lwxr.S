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
// Coverpoints : cp_cfg_A_tor for PMPM is fully covered in this test file.
//
// Test Cases  : Checking XWR controls accesses in matching TOR region. With 
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

RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I[^S]*Zicsr.*); def rvtest_mtrap_routine=True;                                verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor)
RVTEST_CASE(2,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",cp_cfg_A_tor)

#ifdef TEST_CASE_1
RVTEST_SIGBASE( x13,signature_x13_1)
	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	3   
  	.option norvc
#define NOP 		0x13
#define g    (1<<(RVMODEL_PMP_GRAIN+2))

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

    addi a4, a4, -4                     // REGIONSTART - 4
	LA(x4, 2f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
2:
	nop
	nop

    addi a4, a4, 8                      // REGIONSTART + 4
	LA(x4, 3f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
3:
	nop
	nop

    LI(t0, (g-8))
    add a4, a4, t0                      // REGIONSTART + g - 4
	LA(x4, 4f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
4:
	nop
	nop

    addi a4, a4, 4                      // REGIONSTART + g
	LA(x4, 5f)							// Store the return Address in x4
	jalr ra, 0(a4)
	nop
	nop
5:
	nop
	nop

    LI(a4, NOP)                  							// Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)             							// Address to be verified
    sw a4, 0(a5)
    nop
    nop

    addi a5, a5, -4                                         // REGIONSTART - 4
    sw a4, 0(a5)
    nop
    nop

    addi a5, a5, 8                                          // REGIONSTART + 4
    sw a4, 0(a5)
    nop
    nop

    LI(t0, (g-8))
    add a5, a5, t0                                          // REGIONSTART + g - 4
    sw a4, 0(a5)
    nop
    nop

    addi a5, a5, 4                                          // REGIONSTART + g
    sw a4, 0(a5)
    nop
    nop

    LA(a5, \ADDRESS)             							// Address to be verified
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    LI(t0, (g-8))
    add a5, a5, t0                                          // REGIONSTART + g - 4
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x13, a4)       							// Signature update

    addi a5, a5, 4                                          // REGIONSTART + g
    lw a4, 0(a5)
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

#define PMP_REGION_GLOBAL	((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R|            PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W	   |PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|			  PMP_X|PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|PMP_R		 |PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))

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
	csrw pmpcfg3, x4

	LA(x4, TEST_FOR_EXECUTION)
    LI(x5, g)
    add x5, x4, x5
	srl x4, x4, PMP_SHIFT
    srl x5, x5, PMP_SHIFT

	.set pmpaddri, CSR_PMPADDR0
	.rept 6
	csrw pmpaddri, x4
	.set pmpaddri, pmpaddri+1
    csrw pmpaddri, x5
    .set pmpaddri, pmpaddri+1
	.endr
//											Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 11

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr11, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr10, x5

    LI(x4, PMPREGION_LXWR_1000)
	csrw pmpcfg2, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 9

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr9, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr8, x5

    LI(x4, PMPREGION_LXWR_1001)
	csrw pmpcfg2, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 7

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr7, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr6, x5

    LI(x4, PMPREGION_LXWR_1011)
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 5

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr5, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr4, x5

    LI(x4, PMPREGION_LXWR_1100)
	csrw pmpcfg1, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 5 : L -> 1 and No Permissions given to the PMP Region 3

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr3, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr2, x5

    LI(x4, PMPREGION_LXWR_1101)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 1

	LA(x6, TOR_UPPER_BOUND)
	csrw pmpaddr1, x6
	LA(x5, TOR_LOWER_BOUND)
	csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1111)
	csrw pmpcfg0, x4

	VERIFICATION_RWX	TEST_FOR_EXECUTION

	li a4, 0xbeefcafe											// Clean Test exit verification signature.
	RVTEST_SIGUPD(x13, a4)										// Signature update
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