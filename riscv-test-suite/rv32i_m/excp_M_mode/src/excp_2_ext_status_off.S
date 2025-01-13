//
// This test checks that if an extension is turned off (e.g., FS bits [13 and 14] in mstatus are 00), 
// trying to access it will cause an illegal instruction error. If the extension is turned on, the 
// instruction will work as expected.

#include "model_test.h"

#include "arch_test.h"

 RVTEST_ISA("RV32IF_Zicsr")
//RVTEST_ISA("RV32IF")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

#ifdef TEST_CASE_1
// RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", fs_off)
    
 // RVTEST_CASE(1, "//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*F.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", fs_off)

RVTEST_CASE(1,"//check ISA:=regex(.*32.*);check ISA:=regex(.*I.*F.*Zicsr.*);def TEST_CASE_1=True;",fs_off)


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
	RVTEST_FP_ENABLE()

	ALL_MEM_PMP                        
	csrw satp, zero                      // (bare mode)

//	RVTEST_FP_ENABLE()
	
	// Set FS bits to 11 (Enable FPU)
	csrr t3, mstatus                     
	RVTEST_SIGUPD(x13,t3)
//	RVTEST_FP_ENABLE()
//	TEST_FPR4_OP(fmadd.s, f16, f23, f16, f25, dyn, 0, 0, x3, 0*0 + 3*0*FLEN/8, x4, x1, x2)

	// Use a floating-point instruction (should work as FS = 11)
	li t0, 0x40000000  // Load value for 2.0 (single-precision float)
//        fmv.w.x f0, t0     // Move integer to float register
 //       fadd.s f1, f0, f0  // Add f0 to itself, result in f1

	// Set FS bits to 00 (Disable FPU)
	csrr t3, mstatus                     // Read mstatus
	li t4, 0xFFFF9FFF                    // Mask to clear FS bits (FS = 00)
	and t3, t3, t4                       // Clear FS bits
	csrw mstatus, t3                     // Write back to mstatus

	// Use a floating-point instruction (should cause illegal instruction exception)
//	fadd.s f2, f0, f1                    // Attempt another floating-point addition

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
