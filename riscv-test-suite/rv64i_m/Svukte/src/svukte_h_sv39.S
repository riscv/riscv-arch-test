// -----------
// Copyright (c) 2025. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This assembly file tests the Svukte extension with Sv39 paging enabled for a
// guest. Check that an exception is raised/not raised for UKTE 
// qualified/unqualified U accesses to the kernel pages above 2^(SXLEN-1),
// independent of PTE data. It also tests the HLS instructions HLV, HLVX, HSV.

#define SKIP_MEPC
#define SKIP_MTVAL

#include "model_test.h"
#include "arch_test.h"

RVTEST_ISA("RV64IH_Zicsr_Svukte")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT

nop
.align 10
j starting_point

//---------------------------------------------------------------------------------------------------------------------------------
//											PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------

// Physical Address region under testing for LEVEL 0, 1 and 2
rvtest_data:
	nop
	addi ra, ra, REGWIDTH
	jr ra
	nop
	.word 0xbeefcaf1					// Random word
	.word 0xbeefcaf2					// Random word
	nop
	jr ra

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

starting_point:
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def rvtest_vtrap_routine=True; def TEST_CASE_1=True;",)

RVTEST_SIGBASE(x13, signature_x13_1)

# --------------------------------------------------------------------------------------------------
// Test the RWX permissions
.macro VMODE_RWX ADDRESS
   	LI(a5, \ADDRESS)                    // Load virtual address
    addi a2, a2, 16                     // Test pattern initialization

    // Test store permission
    sw  a2, 20(a5)               		// Store test data
    nop

    // Test load permission
    lw  a4, 20(a5)        				// Load back data
    nop

   // Test Execute Permission
   LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
   LA(x4, 1f)							// Store the return Address in x4
   jalr ra, a5, 0
   nop
   nop
1:
   nop
.endm

.macro VTEST QUAL, VA
    // If this access is SVUKTE-qualitied, set the UKTE bit in senvcfg.
	LI(t0, SENVCFG_UKTE)
    .if (\QUAL == Qualified)
	  csrs CSR_SENVCFG, t0
	.else
	  csrc CSR_SENVCFG, t0
	.endif

    // Switch to the specified lower mode
    RVTEST_GOTO_LOWER_MODE VUmode

	.align 2

	VMODE_RWX \VA
	nop
	nop

	// Switching back to M mode
	RVTEST_GOTO_MMODE

	// Signature Update
   	SREG a2, 0(x13)                     // Record store attempt
    nop
    addi x13, x13, REGWIDTH

   	SREG a4, 0(x13)                     // Record load attempt
    nop
	addi x13, x13, REGWIDTH

   	SREG a5, 0(x13)                     // Record load attempt
    nop
	addi x13, x13, REGWIDTH
.endm


// Test the RWX permissions
.macro HMODE_RWX ADDRESS
   	LI(a5, \ADDRESS+20)                    // Load virtual address
    addi a2, a2, 16                     // Test pattern initialization

    // Test store permission
    hsv.w  a2, (a5)               		// Store test data
    nop

    // Test load permission
    hlv.w  a4, (a5)        				// Load back data
    nop

   // Test Execute Permission
   hlvx.wu  a5, (a5)        			   // Load back data
   nop
.endm

.macro HTEST QUAL, VA
    // If this access is SVUKTE-qualitied, set the UKTE bit in senvcfg.
	LI(t0, HSTATUS_HUKTE)
    .if (\QUAL == Qualified)
	  csrs hstatus, t0
	.else
	  csrc hstatus, t0
	.endif

    // Switch to the specified lower mode
    RVTEST_GOTO_LOWER_MODE HSmode

	.align 2

	HMODE_RWX \VA
	nop
	nop

	// Switching back to M mode
	RVTEST_GOTO_MMODE

	// Signature Update
   	SREG a2, 0(x13)                     // Record store attempt
    nop
    addi x13, x13, REGWIDTH

   	SREG a4, 0(x13)                     // Record load attempt
    nop
	addi x13, x13, REGWIDTH
.endm

main:
#ifdef rvtest_mtrap_routine             // Verification of existance of rvtest_mtrap_routine
	LI(a4, 0xceed)
	RVTEST_SIGWRITE(x13,a4)
#endif
#ifdef rvtest_strap_routine             // Verification of existance of rvtest_strap_routine
	LI(a4, 0xbeed)
	RVTEST_SIGWRITE(x13,a4)
#endif

	ALL_MEM_PMP                         // Set the PMP permissions for the whole memory
	csrw satp, zero                     // Write satp with all zeros (bare mode)
	csrw vsatp, zero                    // Write satp with all zeros (bare mode)

//---------------------------------------------------------------------------------------------------------------------------------
//								Virtual addresses definition section for the code, data, sig, vmem, test sections
//---------------------------------------------------------------------------------------------------------------------------------

	// Virtual Address of Test section
    .set va_rvtest_data, 0xFFFFFFC000000404

	// Virtual Addresses for code & data regions
	.set va_rvtest_code_begin,  0x18000091c
	.set va_rvtest_data_begin,  0x1c00007c8

    // PTE setup for Code Region
	V_PTE_SETUP_RV39_New(rvtest_code_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL2)
	sfence.vma

    // PTE setup for Data Region
	V_PTE_SETUP_RV39_New(rvtest_data_begin, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data_begin, LEVEL2)
	sfence.vma

    // Set the SATP for virtualization
	VSATP_SETUP_RV64(sv39)

//---------------------------------------------------------------------------------------------------------------------------------
//													Save area logic
//---------------------------------------------------------------------------------------------------------------------------------

	LI (t0, va_rvtest_data_begin)
	LA (t1, rvtest_data_begin)
	sub t0, t0, t1
	addi t3, t0, sv_area_sz
	csrr sp, mscratch
	add t1, sp, t3
	csrw sscratch, t1
	csrr sp, mscratch
	// After sscratch setup, add:
	addi t3, t0, 2*sv_area_sz    // Calculate VS-mode save area offset
	csrr sp, mscratch
	add t1, sp, t3
	csrw vsscratch, t1           // Set up vsscratch for VS-mode
	csrr sp, mscratch

	// Save area setup for code region
    V_SAVE_AREA_SETUP(va_rvtest_code_begin, 0x8000091c, rvtest_code_begin, code)
	// Save area setup for data region
	V_SAVE_AREA_SETUP(va_rvtest_data_begin, 0xc00007c8, rvtest_data_begin, data)

//---------------------------------------------------------------------------------------------------------------------------------
//												Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

	sfence.vma

//---------------------------------------------------------------------------------------------------------------------------------
//					1GB PAGE	Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------

	VTEST Unqualified, va_rvtest_data
	HTEST Unqualified, va_rvtest_data
	VTEST Qualified, va_rvtest_data
	HTEST Qualified, va_rvtest_data

	// Set up the page table for the data region.
	V_PTE_SETUP_RV39_New(rvtest_data, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data, LEVEL2)
	sfence.vma

	VTEST Unqualified, va_rvtest_data
	HTEST Unqualified, va_rvtest_data
	VTEST Qualified, va_rvtest_data
	HTEST Qualified, va_rvtest_data

#endif

//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

#ifdef rvtest_strap_routine
// TODO: we don't use these in this test.
.align 12
rvtest_slvl1_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 1, PTE_V | PTE_A | PTE_D | PTE_G)
.align 12
rvtest_slvl2_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 2, PTE_V | PTE_A | PTE_D | PTE_G)
#endif

#ifdef rvtest_vtrap_routine
// TODO: 
.align 12
rvtest_vlvl1_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 1, PTE_V | PTE_A | PTE_D | PTE_G)
.align 12
rvtest_vlvl2_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 2, PTE_V | PTE_A | PTE_D | PTE_G)
#endif

RVTEST_DATA_END
.align 12
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

// test signatures initialization
signature_x13_1:
    .fill 256*(XLEN/32),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 128*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
