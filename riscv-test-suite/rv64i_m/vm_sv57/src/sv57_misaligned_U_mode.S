// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV57 based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1rZQbz8gJc3RRbTG4rbw9SoEGYkArA8ileVldBX_gxUc/edit?gid=1688601426#gid=1688601426
// Developed by: Umer Shahid & Muhammad Zain
// ----------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
// 1. A misaligned petapage is set up with RWX Permissions (Read, write, execute page):
//		Then, in U-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 2. A misaligned terapage is set up with RWX Permissions (Read, write, execute page):
//		Then, in U-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 3. A misaligned gigapage is set up with RWX Permissions (Read, write, execute page):
//		Then, in U-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault
// 4. A misaligned megapage is set up with RWX Permissions (Read, write, execute page):
//		Then, in U-Mode, the page is accessed --> required: Load-page-fault, Store-page-fault, Fetch-page-fault

// Total Expected Faults :: 12
// ----------------------------------------------------------------------------------------------------------------------

#define SKIP_MEPC
#define SKIP_MTVAL

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
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True", sv57_tests)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------
// Test the RWX permissions
.macro VERIFICATION_RWX ADDRESS, level	
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

.macro TEST_CASES_RUNNER LOWER_MODE, VA, level
	.if \LOWER_MODE == Mmode
		SET_REQ_MSTATUS_VAL
	.else
		RVTEST_GOTO_LOWER_MODE \LOWER_MODE   // Switch to the specified lower mode
	.endif
	.align 2

	//JUMP TO LOAD, STORE, EXECUTE CHECK MACRO (SEE ON TOP)
	VERIFICATION_RWX	\VA, \level
	nop
	nop

	RVTEST_GOTO_MMODE		            // Switching back to M mode
	
	// Signature Update
   	SREG a2, 0(x13)                     // Record store attempt
    nop
	addi x13, x13, REGWIDTH

   	SREG a4, 0(x13)                     // Record load attempt
    nop
	addi x13, x13, REGWIDTH
.endm


main:
#ifdef rvtest_mtrap_routine				// Verification of existance of rvtest_mtrap_routine
	LI a4, 0xceed
	RVTEST_SIGUPD(x13,a4)
#endif
#ifdef rvtest_strap_routine				// Verification of existance of rvtest_strap_routine
	LI a4, 0xbeed
	RVTEST_SIGUPD(x13,a4)
#endif
	
	ALL_MEM_PMP							// set the PMP permissions for the whole memory
	csrw satp, zero  		            // write satp with all zeros (bare mode)

//---------------------------------------------------------------------------------------------------------------------------------
//								Virtual addresses definition section for the code, data & test sections
//---------------------------------------------------------------------------------------------------------------------------------

	// Virtual Address of Test section 
	.set va_data,          		0x5000000000000				// Virtual Address of rvtest_data_1

	// Virtual Addresses for code & data regions
	.set va_rvtest_code_begin,  0x600008000039C
	.set va_rvtest_data_begin,  0x7000080004530
    
	// PetaPage must have PA[47:0] == 0 and TeraPage must have PA[38:0] == 0, but our PA range starts from 0x8000_0000
	// Therefore, we will setup these pages using a physical address of zero
    .set pa_zero,				0x0000000000000				// Physical Address for Peta & TeraPages

	// PTE setup for Code Region
    PTE_SETUP_SV57_New(pa_zero, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL4)
	sfence.vma

	// PTE setup for Data Region
	PTE_SETUP_SV57_New(pa_zero, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data_begin, LEVEL4)
	sfence.vma

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
	
//---------------------------------------------------------------------------------------------------------------------------------
//												Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

	SATP_SETUP_RV64(sv57)                                                  // Set SATP for virtualization
	sfence.vma                                                             // Flush the TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//													TESTS AT LEVEL 4
//---------------------------------------------------------------------------------------------------------------------------------
//					256TB PAGE	Region 1 under test at level 4 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 1: Test in U-Mode | Misaligned petapage | expected = RWX Fault
	PTE_SETUP_SV57_New(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL4)
	sfence.vma

	TEST_CASES_RUNNER Umode, va_data, LEVEL4

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//													TESTS AT LEVEL 3
//---------------------------------------------------------------------------------------------------------------------------------
//					512GB PAGE	Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 2: Test in U-Mode | Misaligned terapage | expected = RWX Fault
	PTE_SETUP_SV57_New(rvtest_slvl4_pg_tbl, (PTE_V), va_data, LEVEL4)
	PTE_SETUP_SV57_New(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL3)
	sfence.vma

	TEST_CASES_RUNNER Umode, va_data, LEVEL3

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//													TESTS AT LEVEL 2
//---------------------------------------------------------------------------------------------------------------------------------
//					1GB PAGE	Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 3: Test in U-Mode | Misaligned gigapage | expected = RWX Fault
	PTE_SETUP_SV57_New(rvtest_slvl4_pg_tbl, (PTE_V), va_data, LEVEL4)
	PTE_SETUP_SV57_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV57_New(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
	sfence.vma

	TEST_CASES_RUNNER Umode, va_data, LEVEL2

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//													TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//					2MB PAGE	Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 4: Test in U-Mode | Misaligned megapage | expected = RWX Fault 
	PTE_SETUP_SV57_New(rvtest_slvl4_pg_tbl, (PTE_V), va_data, LEVEL4)
	PTE_SETUP_SV57_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV57_New(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL2)
	PTE_SETUP_SV57_New(rvtest_data_1, (PTE_D | PTE_A | PTE_U | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
	sfence.vma

	TEST_CASES_RUNNER Umode, va_data, LEVEL1

#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

//---------------------------------------------------------------------------------------------------------------------------------
//											PHYSICAL ADDRESS REGIONS FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1, 2, 3 and 4

.align 12				// Misaligned (Peta/Tera/Giga/Mega) Page
rvtest_data_1:
	nop
	nop
	addi ra, ra, REGWIDTH
	jr ra
	nop
	.word 0xbeefcaf1				// Random word
	.word 0xbeefcaf2				// Random word
	jr ra	

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

#ifdef rvtest_strap_routine
.align 12
rvtest_slvl1_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 1, PTE_V | PTE_A | PTE_D | PTE_G)
.align 12
rvtest_slvl2_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 2, PTE_V | PTE_A | PTE_D | PTE_G)
.align 12
rvtest_slvl3_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 3, PTE_V | PTE_A | PTE_D | PTE_G)
.align 12
rvtest_slvl4_pg_tbl:
		RVTEST_PTE_IDENT_MAP(0, 3, PTE_V | PTE_A | PTE_D | PTE_G)
#endif

RVTEST_DATA_END                               
.align 12
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

// test signatures initialization
signature_x13_1:
    .fill 32*(XLEN/32),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
