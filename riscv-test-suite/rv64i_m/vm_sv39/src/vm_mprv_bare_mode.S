// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-39-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1Y8fEu2PnT69w-h8hZc2QQSNKi7DBI0pbXHu2IB8soaQ/edit#gid=0
// Developed by: Umer Shahid, Muhammad Zain, Hamza Ali, Muhammad Abdullah and Muhammad Ahmed
// ----------------------------------------------------------------------------------------------------------------------
// Test Explanation:
// RISC-V Privileged Architecture ISA Manual -- Section 10.3
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
// 1. MPRV bit set with S mode permission and virtualization is not enabled (Bare Mode): 
//		Then, in M-Mode, Load, Store & Execute is performed --> required: No Fault

// Total Expected Faults :: 0
//-------------------------------------------------------------------------------------------------------------------

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
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV39_MACROS",sv39_template)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------
// Test the RWX permissions
.macro VERIFICATION_RWX	
	// As we are in bare mode, we will test on physical address
   	LA(a5, rvtest_data_1)            	// Load address
    addi a2, a2, 16                     // Test pattern initialization

    // Test store permission
    sw  a2, 20(a5)               		// Store test data
	RVTEST_SIGUPD(x13, a2)
    nop

    // Test load permission
    lw  a4, 20(a5)        				// Load back data
	RVTEST_SIGUPD(x13, a4)
    nop

    // Test Execute Permission
    LI(x3, 0xACCE)						// Store a value which is to be checked in trap handler
    LA(x4, 1f)							// Store the return Address in x4
    jalr ra, a5, 0
    RVTEST_SIGUPD(x13, a2)
    nop
    nop
1:
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
	LI (s7, 0x1800)	// clear previous mode
	csrc mstatus,s7                 
	LI (s7, 0x800)	// Smode
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

//---------------------------------------------------------------------------------------------------------------------------------
//											PHYSICAL ADDRESS REGIONS FOR TESTING
//---------------------------------------------------------------------------------------------------------------------------------
//Physical Address region under testing for LEVEL 0, 1 and 2
.align 12
rvtest_data_1:
	nop
	addi ra, ra, REGWIDTH
	jr ra																	
	nop
	.word 0xbeefcaf1				// Random word
	.word 0xbeefcaf2				// Random word
	nop
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
