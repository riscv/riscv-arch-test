// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
// SBE (Supervisor Big Endian) Bit is set
// ----------------------------------------------------------------------------------------------------------------------
// 1. PTE is configured in big endian format at level 1 with RWX Permissions (Read, write, execute page):
//		Then, in S-Mode, the page is accessed --> required: No fault
// 2. PTE is configured in big endian format at level 0 with RWX Permissions (Read, write, execute page):
//		Then, in S-Mode, the page is accessed --> required: No fault
// Total Expected Faults :: 0
//-------------------------------------------------------------------------------------------------------------------

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS",mstatus_sbe_set)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------
// Test the RWX permissions
.macro VERIFICATION_RWX ADDRESS, level	
   	LA(a5, \ADDRESS)														// Fetch the address to be checked
	addi a2, a2, 16															// 16 stored in a2 for starting point
	// Check store on the address.
	sw	a2, 0(a5)
	SREG a2, 0(s11)
	nop
	addi s11, s11, REGWIDTH

	lw	a4, 0(a5)															// Reload for verification (CHECK IF DATA HAS BEEN UPDATED SUCCESSFULLY)
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
	// Access the last four bytes which contain the jr instruction
    LI (t0, (0x400000 - 4))
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
	RVTEST_GOTO_LOWER_MODE	\LOWER_MODE		                                // Switching to S mode
	.align 2

	//JUMP TO LOAD, STORE, EXECUTE CHECK MACRO (SEE ON TOP)
	VERIFICATION_RWX	\VA, \level
	nop
	nop

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode

.endm

// Address translation with SBE high will give PTE in big endian
// PTE_SETUP_RV32 sets up the PTE in little endian, so we need to change it to big endian for proper translation
.macro CHANGE_PTE_TO_BE 
	// After PTE_SETUP_RV32 completes, a0 has the PTE (PPN and Permission bits) while t1 has the PTE address
	add  t2, zero, zero			
    andi t2, a0, 0xFF			
    slli t2, t2, 24
    srli t3, a0, 8
    andi t3, t3, 0xFF
    slli t3, t3, 16
    or   t2, t2, t3
    srli t3, a0, 16
    andi t3, t3, 0xFF
    slli t3, t3, 8
    or   t2, t2, t3
    srli t3, a0, 24
    andi t3, t3, 0xFF
    or   t2, t2, t3
	SREG t2, 0(t1)	
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

	// code, data, sig, vmem section VAs
	.set va_rvtest_code_begin,  0x9000036c                             		// virtual address of rvtest_code_begin
	.set va_rvtest_data_begin, 	0x910003fc									// virtual address of rvtest_data_begin (for save area)
	.set va_rvtest_sig_begin,   0x93014510                                  // virtual address of signature_x13_1
	.set  va_rvtest_vmem_begin, 0x940003F0									// virtual address of rvtest_vmem_begin

//													PTE setup for Code Region
	PTE_SETUP_RV32_New(rvtest_code_begin, (PTE_D | PTE_A | PTE_X |PTE_R | PTE_V), va_rvtest_code_begin, LEVEL1)
	CHANGE_PTE_TO_BE
	sfence.vma
//													PTE setup for Data Region
	PTE_SETUP_RV32_New(rvtest_data_begin, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_rvtest_data_begin, LEVEL1)
	CHANGE_PTE_TO_BE
	sfence.vma
//													PTE setup for Signature Region
	PTE_SETUP_RV32_New(rvtest_slvl1_pg_tbl, (PTE_V), va_rvtest_sig_begin, LEVEL1)
	CHANGE_PTE_TO_BE
	PTE_SETUP_RV32_New(rvtest_sig_begin,  (PTE_D | PTE_A | PTE_R | PTE_W | PTE_V), va_rvtest_sig_begin, LEVEL0)
	CHANGE_PTE_TO_BE
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
//												Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

	SATP_SETUP_SV32                                                         // set the SATP for virtualization
	sfence.vma                                                              // flush the TLB

//---------------------------------------------------------------------------------------------------------------------------------

	csrrsi t0, mstatush, 0x10												// Set SBE (Supervisor Big Endian)

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//													TESTS AT LEVEL 1
//---------------------------------------------------------------------------------------------------------------------------------
//					4MB PAGE	Region 1 under test at level 1 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	// Test case 1: Test in S-Mode | RWX set | expected = successful page access
	PTE_SETUP_RV32_New(rvtest_data_1_l1, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V), va_data, LEVEL1)
	CHANGE_PTE_TO_BE
	sfence.vma

	//return page PTE
	PTE_SETUP_RV32_New(rvtest_data_1_l1, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V), va_return_page_l1, LEVEL1)
	CHANGE_PTE_TO_BE
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL1

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
//													TESTS AT LEVEL 0
//---------------------------------------------------------------------------------------------------------------------------------
//					4KB PAGE	Region 1 under test at level 0 -- RWX permissions given to the region
//---------------------------------------------------------------------------------------------------------------------------------
	// Test case 2: Test in S-Mode | RWX set | expected = successful page access
	PTE_SETUP_RV32_New(rvtest_slvl1_pg_tbl, (PTE_V), va_data, LEVEL1)
	CHANGE_PTE_TO_BE
	PTE_SETUP_RV32_New(rvtest_data_1_l0, (PTE_D | PTE_A | PTE_X | PTE_W | PTE_R | PTE_V | PTE_SOFT), va_data, LEVEL0)
	CHANGE_PTE_TO_BE
	sfence.vma

	//return page PTE
	PTE_SETUP_RV32_New(rvtest_slvl1_pg_tbl, (PTE_V), va_return_page_l0, LEVEL1)
	CHANGE_PTE_TO_BE
	PTE_SETUP_RV32_New(rvtest_data_1_l0, (PTE_D | PTE_A | PTE_R | PTE_W | PTE_X | PTE_V), va_return_page_l0, LEVEL0)
	CHANGE_PTE_TO_BE
	sfence.vma

	TEST_CASES_RUNNER Smode, va_data, LEVEL0

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
		RVTEST_PTE_IDENT_MAP(0,1,PTE_V | PTE_A | PTE_D | PTE_G)
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
