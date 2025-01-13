//
// In U-mode, the satp register and the sfence.vma instruction are not accessible regardless 
// of the mstatus.TVM value. Any attempt to access them in U-mode will raise an illegal 
// instruction exception as per privilege rules. 
//

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", mstatus_tvm)

RVTEST_SIGBASE( x13,signature_x13_1)

main:
#ifdef rvtest_mtrap_routine					                				// Verification of existance of rvtest_mtrap_routine
	LI a4, 0xceed
	RVTEST_SIGUPD(x13,a4)
#endif
#ifdef rvtest_strap_routine					                				// Verification of existance of rvtest_strap_routine
	LI a4, 0xbeed
	RVTEST_SIGUPD(x13,a4)
#endif


	ALL_MEM_PMP          		         // set the PMP permissions for the whole memory
	csrw satp, zero  		         // write satp with all zeros (bare mode)

	LI (t4, MSTATUS_TVM)    
	csrw mstatus, t4	// set mstatus with TVM bit
	
	csrr t3, mstatus
	RVTEST_SIGUPD(x13,t3)
	
	RVTEST_GOTO_LOWER_MODE Umode
	nop
	// the satp register and the sfence.vma instruction are not accessible regardless 
	// of the mstatus.TVM value.
	
	// Now use the satp and sfence.vma and it will generate illegal exception 
	li t1, 1																
	csrw satp, t1  		                   // writing satp exceptions will occur here
	nop
	
	LI a4, 0xffff
	RVTEST_SIGUPD(x13,a4)       

	sfence.vma      // using sfence.vma illegal exception will occur
	nop
	
	LI a4, 0xffff
	RVTEST_SIGUPD(x13,a4)  

	RVTEST_GOTO_MMODE

		                                        

#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 22

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
