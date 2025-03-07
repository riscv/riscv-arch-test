// -----------
// Copyright (c) 2020. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
//
// This test belongs to the test plan for RISC-V Privilege Arch Compliance developed by 10xEngineers
// which can be found here: https://docs.google.com/spreadsheets/d/1p13gic7BD6aq7n_dHrqti4QmlGpxY7FkF17RVbG4DC0/edit?usp=sharing
/*	Test Name: pmp-NA4-RX.S
//	PMP Test in NA4 address matching mode
//	Description:
=> Foreach mode in MPP (including M), for Load/store instruction, perform the instruction referencing an address where the associated pmpcfg.W=1 and observe an access fault or not. 
=> Foreach mode, perform instruction fetches to an address where the associated pmpcfg.X=0 and observe an access fault or not.
=> Foreach mode in MPP (including M), Perform the instruction referencing an address where the associated pmpcfg.R=1 and observe an access fault or not. Do the same for stores where pmpcfg.R=1 and pmpcfg.W=1 to make sure that the R bit only affects loads while W bit only affect store.
*/
/* COVERPOINTS: (Explanation of updates in /coverage/rv32i_priv.cgf)
    (pmpcfg0 >> 8) & 0x18 == 0x10 : 0		// CHECK pmp2cfg in NA4 mode?
    (pmpcfg0 >> 8) & 0x01 == 0x01 : 0		// CHECK R-bit in pmp2cfg was HIGH
    (pmpcfg0 >> 8) & 0x02 == 0x02 : 0		// CHECK W-bit in pmp2cfg was HIGH
    (pmpcfg0 >> 8) & 0x04 == 0x04 : 0		// CHECK X-bit in pmp2cfg was HIGH
// Details are given in /coverage/rv32i_priv.cgf
*/

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac PMP_MACROS; mac PMP_helper_Coverpoints",PMP_NA4_rx)
RVTEST_SIGBASE( x13,signature_x13_1)

	.attribute unaligned_access, 0
	.attribute stack_align, 16
  	.align	2   
  	.option norvc
#define PMPCFG0		0x3A0		// Address of pmpcfg0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
#define PMPADDR0	0x3B0		// Address of pmpaddr0 	(HAS BEEN USED WHILE ITERATING THE LOOP)
/* Define PMP Configuration Fields */
#define PMP0_CFG_SHIFT  0
#define PMP1_CFG_SHIFT  8
#define PMP2_CFG_SHIFT  16
#define PMP3_CFG_SHIFT  24
#define NOP 		0x13
.macro VERIFICATION_RWX		ADDRESS	
   	LA(a5, \ADDRESS)	// Fetch the address to be checked
		LI(a4, 	NOP)		// Load the new value (NOP Instruction ID)
		sb	a4,0(a5)	// Store the new value (NOT TRAP => W enabled)
		nop
		nop
		sh	a4,0(a5)	// Load data from it (CHECK FOR READ) ; (NOT TRAP => W enabled)
		nop
		nop
		sw	a4,0(a5)	// Load data from it (CHECK FOR READ) ; (NOT TRAP => W enabled)
		nop
		nop
 	  	lb	a4,0(a5)	// Load data from it (CHECK FOR READ) ; (NOT TRAP => W enabled)
    	nop
    	nop
		RVTEST_SIGUPD(x13,a4)															//verify that the data is stored successfuly
    	lh	a4,0(a5)	// Load data from it (CHECK FOR READ) ; (NOT TRAP => W enabled)
    	nop
    	nop
		RVTEST_SIGUPD(x13,a4)
    	lw	a4,0(a5)	// Load data from it (CHECK FOR READ) ; (NOT TRAP => W enabled)
    	nop
    	nop
		RVTEST_SIGUPD(x13,a4)
		jal	\ADDRESS	// Test for execution, an instruction is placed at this address
		nop
		nop
 
.endm

main:
//////////////////////// INITIAL VALUES //////////////////////////////// 
    	LI(a5, -1)		// SEtting up All locked bits (including everyother non-zero bit, which is redundent for this test)
    	LI(x5, 100)		// A rondom number, to check if pmp regs get update after lock bit enable
	// Loop to SET ALL pmpcfg REGs to zero
	.set pmpcfgi, PMPCFG0	// Initialize an iterating variable with the address of pmpcfg0
	.rept 4			// START OF LOOP
	csrw pmpcfgi , x0	// Set all pmpcfg regs to zero (initial value)
	.set pmpcfgi, pmpcfgi+1		// increment variable to next pmpcfg reg
	.endr			// END OF LOOP BODY
	// Loop to SET ALL pmpaddr REGs to zero
	.set pmpaddri, PMPADDR0	// Initialize an iterating variable with the address of pmpaddr0
	.rept 16		// START OF LOOP
	csrw pmpaddri, x0	// Set all pmpaddr regs to zero (initial value)
	.set pmpaddri, pmpaddri+1		// increment variable pmpaddri to the next pmpaddr reg
	.endr			// END OF LOOP BODY
		
// pmpcfg0 [7:0] value to configure address 0->RAM_LOCATION_FOR_TEST in TOR Mode with RWX enabled
#define PMPREGION1      ((((PMP_R|PMP_W|PMP_X|PMP_L|PMP_TOR)&0xFF) << PMP0_CFG_SHIFT))
// ------------------------------------------------------------------------------------------------
// pmpcfg0[15:8] value to configure address (TEST_FOR_EXECUTION)->(RETURN_INSTRUCTION)
// in NA4 Mode with RX enabled =========> THIS IS OUR REGION UNDER OBSERVATION.
// THIS REGION CONSISTS OF ONLY ONE INSTRUCTION
#define PMPREGION2      ((((PMP_R|PMP_X|PMP_L|PMP_NA4)&0xFF) << PMP1_CFG_SHIFT))
// ------------------------------------------------------------------------------------------------
// pmpcfg0[31:24] value to configure address (RAM_LOCATION_FOR_TEST)->(rvtest_code_end)
// in TOR Mode with RWX enabled 
// ALSO NOTE THAT PMPREGION2 IS INSIDE THIS REGION, so this test will also check the priority order of PMP regions
#define PMPREGION3      ((((PMP_R|PMP_W|PMP_X|PMP_L|PMP_TOR)&0xFF) << PMP3_CFG_SHIFT))
// ------------------------------------------------------------------------------------------------
// pmpcfg1[7:0] value to configure address (rvtest_code_end)->(PMP_region_High)
// in TOR Mode with RWX enabled
#define PMPREGION4      ((((PMP_R|PMP_W|PMP_X|PMP_L|PMP_TOR)&0xFF) << PMP0_CFG_SHIFT))
// ------------------------------------------------------------------------------------------------
// MACROS TO DECLARE THE VALUES TO BE STORED IN PMPADDR registers
#define PMPADDRESS0	RAM_LOCATION_FOR_TEST // value to be loaded pmpaddr0 to declare region1
// PMPADDRESS1 = value to be loaded pmpaddr1 to declare lower address of region2
#define PMPADDRESS1	TEST_FOR_EXECUTION	
// PMPADDRESS2 = value to be loaded pmpaddr2 to declare lower address of region3
#define PMPADDRESS2	RAM_LOCATION_FOR_TEST
// PMPADDRESS3 = value to be loaded pmpaddr3 to declare upper address of region3
#define PMPADDRESS3	rvtest_code_end
// PMPADDRESS4 = value to be loaded pmpaddr4 to declare upper address of region4
#define PMPADDRESS4	PMP_region_High
                                                                  
    /* SET UP DATA IN THE MEMORY */
	csrw satp, x0			// Disable Address Translation
// PMP Configuration
/* PMP is configure in the following order:
1. Address 0x0000 0000 to Address RAM_LOCATION_FOR_TEST => PMP TOR Region with RWX enabled. This region is the part of the code memory containing our code. For this purpose, pmpaddr0 has been given the value of RAM_LOCATION_FOR_TEST to declare the region from 0->RAM_LOCATION_FOR_TEST into a single PMP region.

2. Address TEST_FOR_EXECUTION to Address RETURN_INSTRUCTION =====> This is the PMP region under test (A 4byte region == Granularity of Sail. This region has been declared by entering TEST_FOR_EXECUTION into pmpaddr1 and RETURN_INSTRUCTION into pmpaddr2. Then a PMP region is configure into NA4 mode by setting pmpcfg0[15:8]=PMPREGION2

3. Address RAM_LOCATION_FOR_TEST to Address rvtest_code_end => Another PMP region under test. This region has been declared by entering rvtest_code_end into pmpaddr3 and RAM_LOCATION_FOR_TEST into pmpaddr2. configure pmpaddr2(RAM_LOCATION_FOR_TEST) to pmpaddr3(rvtest_code_end) into TOR mode by setting pmpcfg0[31:24]=((((PMP_R|PMP_W|PMP_X|PMP_L|PMP_TOR)&0xFF) << PMP3_CFG_SHIFT))

4. Address rvtest_code_end to address PMP_region_High => PMP TOR Region with RWX enabled. This region is the part of the code memory containing trap handler, epilogs, and other important macro definitions. For this purpose, configure pmpaddr3(rvtest_code_end) to pmpaddr4(PMP_region_High) into TOR mode by setting pmpcfg1[7:0]=((((PMP_R|PMP_W|PMP_X|PMP_L|PMP_TOR)&0xFF) << PMP0_CFG_SHIFT)). This PMP Region is mandatory to access signature area in S,U mode	*/
    /* Assigning addresses to PMP address registers */
    	LA(x4, PMPADDRESS0)		// Value to be stored in pmpaddr0
	srl x4, x4, PMP_SHIFT		// Shift right by 2 times
	csrw 	pmpaddr0, x4		// Updated pmpaddr0
	nop				// Added nop in case of trap
    	LA(x4, PMPADDRESS1)		// Value to be stored in pmpaddr1
	srl x4, x4, PMP_SHIFT		// Shift right by 2 times
	csrw 	pmpaddr1, x4		// Updated pmpaddr1
	nop				// Added nop in case of trap
    	LA(x4, PMPADDRESS2)		// Value to be stored in pmpaddr2
	srl x4, x4, PMP_SHIFT		// Shift right by 2 times
	csrw 	pmpaddr2, x4		// Updated pmpaddr2
	nop				// Added nop in case of trap
    	LA(x4, PMPADDRESS3)		// Value to be stored in pmpaddr3
	srl x4, x4, PMP_SHIFT		// Shift right by 2 times
	csrw 	pmpaddr3, x4		// Updated pmpaddr3
	nop				// Added nop in case of trap
    	LA(x4, PMPADDRESS4)		// Value to be stored in pmpaddr4
	srl x4, x4, PMP_SHIFT		// Shift right by 2 times
	csrw 	pmpaddr4, x4		// Updated pmpaddr4
	nop				// Added nop in case of trap
    /* Decalring pmp configuration register */
	LI(x4, PMPREGION1 | PMPREGION2 |  PMPREGION3)	
	// Value to be stored in pmpcfg register ;  Setting Up PMP Region-1,2,3
	csrs pmpcfg0, x4		// Updated pmpcfg0
	nop				// Added nop in case of trap
	LI(x4, PMPREGION4)	
	// Value to be stored in pmpcfg1 register ; Setting up PMP Region-4
	csrs pmpcfg1, x4		// Updated pmpcfg1
	nop				// Added nop in case of trap
//////////// ALL PMP REGIONS DECLARED //////////////////////////////////////////////
    /* VERIFICATION in M-mode  */    
	VERIFICATION_RWX	TEST_FOR_EXECUTION	
// VERIFICATION IN S-Mode	
	RVTEST_GOTO_LOWER_MODE	Smode		// SWITCH TO S-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION	

/////////////////// Switch back to M-mode ////////////////////////////////////////////
	RVTEST_GOTO_MMODE
  	csrr a4, mstatus		// VERIFICATION of M-mode
	nop				// Added nop in case of trap
// VERIFICATION IN U-Mode
	RVTEST_GOTO_LOWER_MODE	Umode		// SWITCH TO U-mode
	VERIFICATION_RWX	TEST_FOR_EXECUTION	
	j exit

RAM_LOCATION_FOR_TEST:
	.fill 3*(XLEN/32),4,0x12345678
TEST_FOR_EXECUTION:
	addi x9,x9,0x01		// A TEST INSTRUCTION TO TEST THE EXECUTION CHECK ON PMP REGION
RETURN_INSTRUCTION:
	nop				// Added nop in case of trap
	nop				// Added nop in case of trap
	nop				// Added nop in case of trap
	nop				// Added nop in case of trap
	jr ra			
// AN instruction to bring back PC to the address where TEST_FOR_EXECUTION was called to check for execution.
exit:
#endif
 # ---------------------------------------------------------------------------------------------
    # HALT
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN
.align 4

rvtest_data:
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
.word 0xbabecafe
RVTEST_DATA_END


RVMODEL_DATA_BEGIN
rvtest_sig_begin:
sig_begin_canary:
CANARY;
signature_x13_1:
    .fill 32*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 64*(XLEN/32),4,0xdeadbeef
tsig_end_canary:
CANARY;

#endif

#ifdef rvtest_gpr_save

gpr_save:
    .fill 32*(XLEN/32),4,0xdeadbeef

#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
PMP_region_High:
RVMODEL_DATA_END