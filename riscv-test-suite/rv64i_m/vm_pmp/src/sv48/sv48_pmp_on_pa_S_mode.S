// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-48-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1rZQbz8gJc3RRbTG4rbw9SoEGYkArA8ileVldBX_gxUc/edit?gid=1688601426#gid=1688601426
// Developed by: Umer Shahid & Muhammad Zain
// ----------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
// Configure test data region as NAPOT with RX permissions (pmp1cfg0)
// 1-4. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: 4 Store access faults
// ----------------------------------------------------------------------------------------------------------------------
// Configure test data region as NAPOT with RW permissions (pmp1cfg0)
// 5-8. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: 4 Instruction access faults
// ----------------------------------------------------------------------------------------------------------------------
// Configure test data region as NAPOT with X permission (pmp1cfg0)
// 9-12. Setup a PTE at Level (3/2/1/0) with RWX permissions
//      → Then, in S-Mode, the page is accessed --> required: 4 Store access faults, 4 Load access faults
//
// Total Expected Faults :: 16
// ----------------------------------------------------------------------------------------------------------------------

#define SKIP_MEPC
#define SKIP_MTVAL

#include "model_test.h"

#include "arch_test.h"

#ifndef RVMODEL_PMP_GRAIN
	#define RVMODEL_PMP_GRAIN 0
#endif

RVTEST_ISA("RV64I_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT												// This test supports max 255 words for RVMODEL_BOOT

j starting_point											// Skip test region
.align 10													// Aligning so that RVMODEL_BOOT doesn't change address of rvtest_data_1

//---------------------------------------------------------------------------------------------------------------------------------
//											PHYSICAL ADDRESS REGION FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
// Physical Address region under testing for LEVEL 0, 1, 2 and 3
rvtest_data_1:
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

.align 11
// The preceding test region is 2KB by default. If G increases, adjusting alignment to expand the test region accordingly.
.align (RVMODEL_PMP_GRAIN+2)
starting_point:
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (PMP['implemented']); verify (PMP['pmp-grain'] <= 4); def TEST_CASE_1=True; mac SV48_MACROS", sv48_tests)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------
// Test the RWX permissions
.macro VERIFICATION_RWX ADDRESS, level	
   	LI(a5, \ADDRESS)                    // Load virtual address
    addi a2, a2, 16                     // Test pattern initialization
	
    // Test store permission
    sw  a2, 20(a5)
    nop

    // Test load permission
    lw  a4, 20(a5)
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
	
	csrw satp, zero  		            // write satp with all zeros (bare mode)

// PMP Macros
#define PMP_GLOBAL_RWX		(((PMP_TOR | PMP_X | PMP_W | PMP_R) & 0xFF) << PMP3_CFG_SHIFT)
#define PMP1CFG_RX			(((PMP_NAPOT | PMP_X | PMP_R) & 0xFF) << PMP1_CFG_SHIFT)
#define PMP1CFG_RW			(((PMP_NAPOT | PMP_W | PMP_R) & 0xFF) << PMP1_CFG_SHIFT)
#define PMP1CFG_X			(((PMP_NAPOT | PMP_X) & 0xFF) << PMP1_CFG_SHIFT)

//---------------------------------------------------------------------------------------------------------------------------------
//													Setup pmpaddr registers
//---------------------------------------------------------------------------------------------------------------------------------

	li t2, 0							// Set PMP permission for all memory in pmp3cfg0 (TOR)
	csrw pmpaddr2, t2
	li t2, -1
	csrw pmpaddr3, t2

	LI (t2, 0x80000000)					// Configure test region as NAPOT, Start = 0x8000_0000
	srl t2, t2, 2

	.if (RVMODEL_PMP_GRAIN < 10)
		LI (t1, 0xFF)								// Range = 2^(8+3) = 2048 Bytes
	.else
		LI (t1, ((1<<RVMODEL_PMP_GRAIN)-1)>>1)		// Range = 2^(G+3) Bytes
	.endif

	or t2, t2, t1						
	csrw pmpaddr1, t2

//---------------------------------------------------------------------------------------------------------------------------------
//								Virtual addresses definition section for the code, data & test sections
//---------------------------------------------------------------------------------------------------------------------------------

	// Virtual Address of Test section 
	.set va_data,          		0x028000000400              	// Virtual Address of rvtest_data_1

	// Virtual Addresses for code & data regions
	// If G increases more than 9, size of test region increases. Therefore, adjust address of rvtest_code_begin accordingly
	.if (RVMODEL_PMP_GRAIN < 10)
		.set va_rvtest_code_begin,  0x030080000B9C
	.else
		.set va_rvtest_code_begin,  0x03008000039C | (1<<(RVMODEL_PMP_GRAIN+2))
	.endif
	.set va_rvtest_data_begin,  0x038080005530	
    
	// TeraPage must have PA bits [38:0] equal to zero, but our PA range starts from 0x8000_0000
	// Therefore, we will setup TeraPage using this imm value
    .set terapage_pa,           0x000000000000    				// Physical Address for TeraPage
	.set va_data_l3,			0x028080000400					// Virtual Address of rvtest_data_1 (In case of Level3)

//	PTE setup for Code Region
    PTE_SETUP_SV48_New(terapage_pa, (PTE_D | PTE_A | PTE_X | PTE_R | PTE_V), va_rvtest_code_begin, LEVEL3)
	sfence.vma

//	PTE setup for Data Region
	PTE_SETUP_SV48_New(terapage_pa, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data_begin, LEVEL3)
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

	SATP_SETUP_RV64(sv48)                                                  	// Set SATP for virtualization
	sfence.vma                                                            	// Flush the TLB

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
// 							Configure test data region as NAPOT with RX permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
	
	LI (t2, PMP_GLOBAL_RWX | PMP1CFG_RX)							
	csrw pmpcfg0, t2

//---------------------------------------------------------------------------------------------------------------------------------
//					512GB PAGE	Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 1: Test in S-Mode | RWX bit set | expected = Store access fault
	PTE_SETUP_SV48_New(terapage_pa, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l3, LEVEL3)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data_l3, LEVEL3

//---------------------------------------------------------------------------------------------------------------------------------
//					1GB PAGE	Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 2: Test in S-Mode | RWX bit set | expected = Store access fault
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL2

//---------------------------------------------------------------------------------------------------------------------------------
//					2MB PAGE	Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 3: Test in S-Mode | RWX bit set | expected = Store access fault
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL2)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL1

//---------------------------------------------------------------------------------------------------------------------------------
//					4KB PAGE	Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 4: Test in S-Mode | RWX bit set | expected = Store access fault
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL2)
	PTE_SETUP_SV48_New(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL1)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL0


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
// 							Configure test data region as NAPOT with RW permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

	LI (t2, PMP_GLOBAL_RWX | PMP1CFG_RW)							
	csrw pmpcfg0, t2

//---------------------------------------------------------------------------------------------------------------------------------
//					512GB PAGE	Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 5: Test in S-Mode | RWX bit set | expected = Instruction access fault
	PTE_SETUP_SV48_New(terapage_pa, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l3, LEVEL3)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data_l3, LEVEL3

//---------------------------------------------------------------------------------------------------------------------------------
//					1GB PAGE	Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 6: Test in S-Mode | RWX bit set | expected = Instruction access fault 
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL2

//---------------------------------------------------------------------------------------------------------------------------------
//					2MB PAGE	Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 7: Test in S-Mode | RWX bit set | expected = Instruction access fault 
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL2)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL1

//---------------------------------------------------------------------------------------------------------------------------------
//					4KB PAGE	Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 8: Test in S-Mode | RWX bit set | expected = Instruction access fault
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL2)
	PTE_SETUP_SV48_New(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL1)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL0


//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
// 							Configure test data region as NAPOT with X permissions (pmp1cfg0)
//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------

	LI (t2, PMP_GLOBAL_RWX | PMP1CFG_X)							
	csrw pmpcfg0, t2

//---------------------------------------------------------------------------------------------------------------------------------
//					512GB PAGE	Region 1 under test at level 3 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 9: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
	PTE_SETUP_SV48_New(terapage_pa, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data_l3, LEVEL3)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data_l3, LEVEL3

//---------------------------------------------------------------------------------------------------------------------------------
//					1GB PAGE	Region 1 under test at level 2 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 10: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL2)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL2

//---------------------------------------------------------------------------------------------------------------------------------
//					2MB PAGE	Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 11: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL2)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL1

//---------------------------------------------------------------------------------------------------------------------------------
//					4KB PAGE	Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	
	// Test case 12: Test in S-Mode | RWX bit set | expected = Store access fault, Load access fault
	PTE_SETUP_SV48_New(rvtest_slvl3_pg_tbl, (PTE_V), va_data, LEVEL3)
	PTE_SETUP_SV48_New(rvtest_slvl2_pg_tbl, (PTE_V), va_data, LEVEL2)
	PTE_SETUP_SV48_New(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL1)
	PTE_SETUP_SV48_New(rvtest_data_1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL0)
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL0


#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

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
#endif

RVTEST_DATA_END                               
.align 12
RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;

// test signatures initialization
signature_x13_1:
    .fill 64*(XLEN/32),4,0xcafebeef

// trap signatures initialization
#ifdef rvtest_mtrap_routine
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
