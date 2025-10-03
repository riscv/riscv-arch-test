// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-48-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1rZQbz8gJc3RRbTG4rbw9SoEGYkArA8ileVldBX_gxUc/edit?gid=1688601426#gid=1688601426
// Developed by: Umer Shahid & Muhammad Zain
// ----------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
//	1. satp and sfence.vma accessed in M Mode with mstatus.tvm bit set -> Successful
//	2. satp and sfence.vma accessed in S Mode with mstatus.tvm bit set -> illegal instruction exception
//
// Total Expected Faults: 4
// -------------------------------------------------------------------------------------------------------------------

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
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True", sv48_tests)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------

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

    # Set the TVM bit in mstatus
	LI (t4, MSTATUS_TVM)
	csrw mstatus, t4
	csrr t3, mstatus
	RVTEST_SIGUPD(x13,t3)

// ------------------------------------------------------------------------------------------------------------
// 												satp access in M Mode
// ------------------------------------------------------------------------------------------------------------
    
    li t0, 1																
	csrw satp, t0  		                                        			// Write satp with some value
	csrr t3, satp
	RVTEST_SIGUPD(x13,t3)

	sfence.vma
	nop
	nop

// ------------------------------------------------------------------------------------------------------------
// 										satp access in S Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------

	RVTEST_GOTO_LOWER_MODE Smode

	li t0, 1																
	csrw satp, t0  		                                        			
	nop
	
	li t0, 1
    csrrc t1, satp, t0  
    nop

    li t0, 1           
    csrrs t1, satp, t0
    nop

	sfence.vma
	nop
	nop

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode


#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

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
