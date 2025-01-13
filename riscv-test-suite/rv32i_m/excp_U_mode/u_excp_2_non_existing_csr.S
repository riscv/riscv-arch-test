//
// If we try to access the non existinfg CSR and the instruction is csrr  
// 0xfff in U mode so it will cause the illegal instruction and will update the mcause 
// with the exception code 2, mepc will point to the address of the illegal 
// instruction, mtval will contain the binary representation of illegal instruction
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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", excp_2_U_non_exstn_csr)

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
	
 	ALL_MEM_PMP          		  // set the PMP permissions for the whole memory
	csrw satp, zero  		  // write satp with all zeros (bare mode)

	csrr t3, mstatus           // read mstatus value 
	RVTEST_SIGUPD(x13,t3)

	RVTEST_GOTO_LOWER_MODE Umode
	nop
	nop
	
	li t1,0xabcd   // accessing non existing CSR will generate the illegal instruction exception
	csrw 0xFFF,t1
	nop
	nop
	
	RVTEST_GOTO_MMODE
	nop 
	
	csrr a4,mcause     //it will read value 2 for mcause in a4
	RVTEST_SIGUPD(x13, a4)
	
	csrr a4,mtval      // mtval will have the instruction that cause the illegal instruction
	RVTEST_SIGUPD(x13, a4)
	
	nop
	nop
#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 22

//---------------------------------------------------------------------------------------------------------------------------------
//---------------------------------------------------------------------------------------------------------------------------------
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

#ifdef rvtest_strap_routine
strap_sigptr:
    .fill 64*(XLEN/32),4,0xaaaabeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
