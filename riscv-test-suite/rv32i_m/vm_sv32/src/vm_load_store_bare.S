	// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-32-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by:
// ----------------------------------------------------------------------------------------------------------------------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// ----------------------------------------------------------------------------------------------------------------------
// Test Explanation:
// RISC-V Privileged Architecture ISA Manual -- Section 10.3
// Note: This test is based on RISC-V Privileged ISA version 1.12, which does not include SVADE and SVADU support.
// Future updates will align with ISA version 1.13.

// ---------------------------------------------------------------------------------------------------------------------- 
// 	This test is for checking store and load in bare mode. 
//	coverage effects : mprv load and store bins with bare cross.
// 	Total Expected Faults :: ?
//-------------------------------------------------------------------------------------------------------------------

#define SKIP_MEPC
#define SKIP_MTVAL

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", MPRV_bit)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------
// Test the RWX permissions
.macro VERIFICATION_RWX ADDRESS, level, VM_MODE
   	LA(a5, \ADDRESS)														// Fetch the address to be checked
	addi a2, a2, 16															// 16 stored in a2 for starting point

	// Check store on the address.
	sw	a2, 20(a5)
	SREG a2, 0(s11)
	nop
	addi s11, s11, REGWIDTH

	lw	a4, 20(a5)															// Reload for verification (CHECK IF DATA HAS BEEN UPDATED SUCCESSFULLY)
	SREG a4, 0(s11)
	nop
	addi s11, s11, REGWIDTH

	//check if level is equal to zero, if it is then jump to the end of the 4KB to check the permissions
	//else jump to the end of the 4MB page to check the permissions
    // Check if level is equal to zero (4KB page)
	addi a2, a2, 16															// update the counter for execute
    LI( t1, \level)
    beqz t1, 1f  // Forward reference to avoid label redefinition
    
    // 4MB - 4 = 4,194,300 bytes
	// Access the last four byteM_mode,s which contain the jr instruction
    LI (t0, (0x400000 - 4))
	.if \VM_MODE == Mmode
	   	LA(a5, rvtest_data_1_l1)														// Fetch the address to be checked
	.endif
	srli a5, a5, 22
	slli a5, a5, 22															//Clear the lower 21 bits -- offset bits(10) + level 0 bits(12)
    add t0, a5, t0
    jalr ra, t0, 0
	SREG a2, 0(s11)
	nop
	addi s11, s11, REGWIDTH
    j 2f
    
1:  // 4KB - 4 = 4,092 bytes
    LI (t0, (0x1000-4))
	.if \VM_MODE == Mmode
	   	LA(a5, rvtest_data_1_l0)						//this test probably effects the loads in coverage. 								// Fetch the address to be checked
	.endif
	srli a5, a5, 12
	slli a5, a5, 12
    add t0, a5, t0
    jalr ra, t0, 0
	SREG a2, 0(s11)
	nop
	addi s11, s11, REGWIDTH

2:  // end_macro
    // execution test sig update
	nop
.endm

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level
    .if \LOWER_MODE == Mmode
		LI (s7, MSTATUS_MPRV)           
		csrs mstatus,s7                 
		LI (s7, 0x1800)	//clear previous mode
		csrc mstatus,s7                 
		LI (s7, 0x800)	//Smode
		csrs mstatus,s7                 
    .else
        RVTEST_GOTO_LOWER_MODE \LOWER_MODE   // Switch to the specified lower mode
    .endif

	.align 2

	//JUMP TO LOAD, STORE, EXECUTE CHECK MACRO (SEE ON TOP)
	VERIFICATION_RWX	\VA, \level, \LOWER_MODE
	nop
	nop

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode

.endm

main:
#ifdef rvtest_mtrap_routine					                				// Verification of existance of rvtest_mtrap_routine
	LI a4, 0xceed
	RVTEST_SIGUPD(x13,a4)
#endif
#ifdef rvtest_strap_routine					                				// Verification of existance of rvtest_strap_routine
	LI a4, 0xbeed
	RVTEST_SIGUPD(x13,a4)
#endif
	
	ALL_MEM_PMP          		                  	                      	// set the PMP permissions for the whole memory
	csrw satp, zero  		                                        		// write satp with all zeros (bare mode)

//---------------------------------------------------------------------------------------------------------------------------------
//								Virtual addresses definition section for the code, data, sig, vmem, test sections
//---------------------------------------------------------------------------------------------------------------------------------

	// test section VAs
	.set va_data,          0x91400000                                  		// virtual address of rvtest_data_1_l1 and rvtest_data_1_l0
	.set va_return_page_l1,     0x91800000                                  // virtual address of return_page for the rvtest_data_1_l1
	.set va_return_page_l0,     0x91401000                                  // virtual address of return_page for the rvtest_data_1_l0

	// code, data, sig, vmem section VAs	li t0,1																   //initial value for t0 = 1
	#successful access
	csrr t0, mstatush       												   //Read the current value of mstatus into t0
	li t1, 0x10      												  	      // Load the mask for the SBE bit (bit 4)
	or t0, t0, t1          												     // Set the SBE bit to 1
	csrw mstatush, t0 
	csrr t3, mstatush       											     // Write the updated value of t0 back to mstatus
	RVTEST_SIGUPD(x13,t3)
	.set va_rvtest_code_begin,  0x9000036c                             		// virtual address of rvtest_code_begin
	.set va_rvtest_data_begin, 	0x910003fc									// virtual address of rvtest_data_begin (for save area)
	.set va_rvtest_sig_begin,   0x93014510                                  // virtual address of signature_x13_1
	.set  va_rvtest_vmem_begin, 0x940003F0									// virtual address of rvtest_vmem_begin

//													PTE setup for Code Region
	PTE_SETUP_RV32_New(rvtest_code_begin, (PTE_D | PTE_A  | PTE_X |PTE_R | PTE_V), va_rvtest_code_begin, LEVEL1)
	sfence.vma
//													PTE setup for Data Region
	PTE_SETUP_RV32_New(rvtest_data_begin, ( PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data_begin, LEVEL1)
	sfence.vma
//													PTE setup for Signature Region
	PTE_SETUP_RV32_New(rvtest_slvl1_pg_tbl, (PTE_V), va_rvtest_sig_begin, LEVEL1)
	PTE_SETUP_RV32_New(rvtest_sig_begin,  (PTE_D | PTE_A | PTE_R | PTE_W  | PTE_V), va_rvtest_sig_begin, LEVEL0)
	sfence.vma
//								register setup for the signature save in virtualization mode
	LI (t0, va_rvtest_sig_begin)                                                     
	LA (t1, rvtest_sig_begin)                                                      
	sub t0, t0, t1 					        								// (VA-PA) Note: VA > PA 
	add s11, x13, t0				        								// Translation of Signature reg

//---------------------------------------------------------------------------------------------------------------------------------
//													Save area logic
//---------------------------------------------------------------------------------------------------------------------------------
	LI (t0, va_rvtest_data_begin) 
	LA (t1, rvtest_data_begin) 
	sub t0, t0, t1         
	addi t3, t0, sv_area_sz
	csrr sp, mscratch      
	add t1,sp,t3           
	csrw sscratch, t1      
	csrr sp, mscratch

	//save area setup for code region
	SAVE_AREA_SETUP(va_rvtest_code_begin, rvtest_code_begin, code)
	//save area setup for data region
	SAVE_AREA_SETUP(va_rvtest_data_begin, rvtest_data_begin, data)
	//save area setup for sig region
	SAVE_AREA_SETUP(va_rvtest_sig_begin, rvtest_sig_begin, sig)	
	//save area setup for vmem region
	SAVE_AREA_SETUP(va_rvtest_vmem_begin, rvtest_data_begin, vmem)

//---------------------------------------------------------------------------------------------------------------------------------
//					Test Cases Start from here, the machine is in bare mode, so all the addresses used are treated as physical addresses
//---------------------------------------------------------------------------------------------------------------------------------

	sfence.vma                                                              // flush the TLB


//													TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//					4MB PAGE	Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	// Test case 1: MPRV bit set | Test in M-Mode | RWX&U bit set | expected = All Faults 
	PTE_SETUP_RV32_New(rvtest_data_1_l1, (PTE_D | PTE_U | PTE_A  | PTE_X | PTE_W | PTE_R| PTE_V), va_data, LEVEL1)
	sfence.vma


	// Load address of va_data into t1
	la t1, va_data

	// Load and Store Instructions
	lw t0, 0(t1)         // Load from va_data (address in t1)
	sw t0, 4(t1)         // Store to va_data + 4 (offset 4 from t1)

	//return page PTE
	PTE_SETUP_RV32_New(rvtest_data_1_l1, (PTE_D | PTE_A  | PTE_R | PTE_W | PTE_X | PTE_V), va_return_page_l1, LEVEL1)
	sfence.vma

	//setting the sum bit here

	LI (s7, MSTATUS_SUM)           
	csrs mstatus,s7                 

	TEST_CASES_RUNNER Mmode, va_data, LEVEL1

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//													TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//					4MB PAGE	Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	// Test case 2: MPRV bit set | Test in M-Mode | RWX&U bit set | expected = All faults
	PTE_SETUP_RV32_New(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL1)
	PTE_SETUP_RV32_New(rvtest_data_1_l0, (PTE_D | PTE_U | PTE_A  | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
	sfence.vma


	// Load address of va_data into t1
	la t1, va_data

	// Load and Store Instructions
	lw t0, 0(t1)         // Load from va_data (address in t1)
	sw t0, 4(t1)         // Store to va_data + 4 (offset 4 from t1)


	//return page PTE
	PTE_SETUP_RV32_New(rvtest_slvl1_pg_tbl, (PTE_V), va_return_page_l0, LEVEL1)
	PTE_SETUP_RV32_New(rvtest_data_1_l0, (PTE_D | PTE_A  | PTE_R | PTE_W | PTE_X | PTE_V), va_return_page_l0, LEVEL0)
	sfence.vma

	TEST_CASES_RUNNER Mmode, va_data, LEVEL0


#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 22

//---------------------------------------------------------------------------------------------------------------------------------
//											PHYSICAL ADDRESS REGIONS FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
//Physical Address region under testing for LEVEL 1 -- Aligned by 22
rvtest_data_1_l1:
	nop																		//nops are added so if there is a trap
	addi ra, ra, REGWIDTH
	jr ra																	// return back if the access fault
	nop
	.word 0xbeefcaf1														// Random word
	.word 0xbeefcaf2														// Random word
	.rept ((1 << 20) - 7)													// (2^22 - 7) nops
    nop
	.endr
	jr ra																	// return back if successful access

//Physical Address region under testing for LEVEL 0 -- Aligned by 10
rvtest_data_1_l0:
	nop																		// trap return back skip
	addi ra, ra, REGWIDTH
	jr ra																	//jump back for the trap on level 1
	nop
	.word 0xbeefcaf1														// Random word
	.word 0xbeefcaf2														// Random word
	.rept ((1 << 10) - 7)													// (2^12 - 7) nops
    nop
	.endr
	jr ra

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

#ifdef rvtest_strap_routine
.align 12                       //complete the 4KB permission memory range
rvtest_slvl1_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0,1,PTE_V | PTE_A | PTE_D  | PTE_G)
#endif

RVTEST_DATA_END                               
.align 12
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

// test signatures initialization
signature_x13_1:
    .fill 128*(XLEN/32),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 128*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END