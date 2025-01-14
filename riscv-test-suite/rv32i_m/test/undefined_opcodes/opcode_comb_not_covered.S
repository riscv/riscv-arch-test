/* // 
//  This test is to check the behavior when accessing opcodes that are not assigned to any instruction.
//  
//    Developed by: Maria Rehman
//

// */

#include "model_test.h"

#include "arch_test.h"

RVTEST_ISA("RV32IF_Zicsr")

# Test code region
.section .text.init
.globl rvtest_entry_point
.option norvc

rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN


#ifdef TEST_CASE_1
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True;  def TEST_CASE_1=True ", cp_S_ecall) 

RVTEST_SIGBASE( x13,signature_x13_1)

main:
#ifdef rvtest_mtrap_routine	// Verification of existance of rvtest_mtrap_routine
	LI (a4, 0xceed)
	RVTEST_SIGUPD(x13,a4)
#endif

	ALL_MEM_PMP          		  // set the PMP permissions for the whole memory
	csrw satp, zero  		  // write satp with all zeros (bare mode)
	
// nop operations
	.word 0x00000013     // nop
	.word 0x00000013     // nop
	.word 0x00000013     // nop
	.word 0x00000013     // nop
	
// instruction with add opcode
	// .word 0x00000033     // add (opcode 0010011)
	add x0,x0,x0
	
	
	.word 0x00000013     // nop
	nop
	
	// Here below are the some opcode combinations that are not defined for any instruction 
	// so when we use such opcodes they give the illegal instruction exception
	
	// "111_1110" //
	.word 0x01029071     // opcode not defined for any instruction
	nop
	nop
	
	
	// "100_0001" //
	.word 0x0102a042     // opcode not defined for any instruction
	nop
	nop
	
	// "101_0001" //
	.word 0x0102a052     // opcode not defined for any instruction
	nop
	nop
	
	
	// "101_1001" //
	.word 0x0102a05a     // opcode not defined for any instruction
	nop
	nop
	
	// "101_1011" //
	.word 0x0102a05b     // opcode not defined for any instruction
	nop
	nop
	
#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 4
// -------------------------------------------------------------------------------------------------------------------------------
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
