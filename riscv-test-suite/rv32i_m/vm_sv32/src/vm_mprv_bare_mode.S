// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
// ------------------------------------------Virtualization is not enabled---------------------------------------------------
// 1. MPRV is set and MPP is set to S-Mode:
//		Then, in M-Mode, the page is accessed --> required: successful load, store and execute without translation
// 1. MPRV is set and MPP is set to U-Mode:
//		Then, in M-Mode, the page is accessed --> required: successful load, store and execute without translation

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", MPRV_bit)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------
// Test the RWX permissions
.macro VERIFICATION_RWX
	// As we are in bare mode, we will test on physical address
   	LA(a5, rvtest_data_1_l0)												// Fetch the address to be checked
	addi a2, a2, 16															// 16 stored in a2 for starting point

	// Check store on the address.
	sw	a2, 20(a5)
	RVTEST_SIGUPD(x13, a2)
	nop

	lw	a4, 20(a5)															// Reload for verification (CHECK IF DATA HAS BEEN UPDATED SUCCESSFULLY)
	RVTEST_SIGUPD(x13, a4)
	nop

    // 4KB - 4 = 4,092 bytes
    LI (t0, (0x1000-4))
	srli a5, a5, 12
	slli a5, a5, 12
    add t0, a5, t0
    jalr ra, t0, 0
	RVTEST_SIGUPD(x13, a2)
	nop

	// end_macro
    // execution test sig update
	nop
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
//												Set MPRV and set MPP to S Mode
//---------------------------------------------------------------------------------------------------------------------------------

	LI (s7, MSTATUS_MPRV)           
	csrs mstatus,s7                 
	LI (s7, 0x1800)	//clear previous mode
	csrc mstatus,s7                 
	LI (s7, 0x800)	//Smode
	csrs mstatus,s7 

	.align 2
	// Check load, store and execute in bare mode
	VERIFICATION_RWX
	nop
	nop
	RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
//												Set MPRV and set MPP to U Mode
//---------------------------------------------------------------------------------------------------------------------------------

	LI (s7, MSTATUS_MPRV)           
	csrs mstatus,s7                 
	LI (s7, 0x1800)	// Set to Umode
	csrc mstatus,s7                 

	.align 2
	// Check load, store and execute in bare mode
	VERIFICATION_RWX
	nop
	nop
	RVTEST_GOTO_MMODE

#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 12

//---------------------------------------------------------------------------------------------------------------------------------
//											PHYSICAL ADDRESS REGIONS FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
//Physical Address region under testing for LEVEL 0 -- Aligned by 12
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
