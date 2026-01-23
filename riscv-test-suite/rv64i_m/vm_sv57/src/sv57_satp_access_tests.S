// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV57 based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1rZQbz8gJc3RRbTG4rbw9SoEGYkArA8ileVldBX_gxUc/edit?gid=1688601426#gid=1688601426
// Developed by: Umer Shahid & Muhammad Zain
// ----------------------------------------------------------------------------------------------------------------------
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
//  1. Testing satp mode field (SV57 and Bare mode) -> Successful
//  2. All zeroes, all ones and walking ones in the PPN bitfield of satp  -> Successful
//	3. All zeroes and ones in satp[59:0] -> Successful
//	4. Walking ones in the ASID bitfield of satp -> Successful

// Total Expected Faults: 0
// ----------------------------------------------------------------------------------------------------------------------

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
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True", sv57_tests)

RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------

main:
#ifdef rvtest_mtrap_routine				// Verification of existance of rvtest_mtrap_routine
	LI a4, 0xceed
	RVTEST_SIGUPD(x13,a4)
#endif
#ifdef rvtest_strap_routine				// Verification of existance of rvtest_strap_routine
	LI a4, 0xbeed
	RVTEST_SIGUPD(x13,a4)
#endif
	
	ALL_MEM_PMP							// set the PMP permissions for the whole memory
	csrw satp, zero  		            // write satp with all zeros (bare mode)

//---------------------------------------------------------------------------------------------------------------------------------
//												Test Cases Start from here
//---------------------------------------------------------------------------------------------------------------------------------

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 1:  							  Mode Supported --- SV48 and Bare
//---------------------------------------------------------------------------------------------------------------------------------

	li t0, 0xA000000000000000  // Set t0 to have 1010 in [63:60] (SV57)
    csrw satp, t0              // Write satp
    csrr t1, satp              // Read back satp
    RVTEST_SIGUPD(x13, t1)     // Store read value in signature

    li t0, 0x0000000000000000  // Set t0 to have 0 in [63:60] (Bare mode)
    csrw satp, t0              // Write satp
    csrr t1, satp              // Read back satp
    RVTEST_SIGUPD(x13, t1)     // Store read value in signature
	
	RVTEST_GOTO_MMODE

//---------------------------------------------------------------------------------------------------------------------------------
// Test case 2:				   PPN all zeros, all ones and walking ones in the PPN bitfield of satp
//---------------------------------------------------------------------------------------------------------------------------------

    li t0, 0xA000000000000000  // Ensure SV57 mode in [63:60]
    mv t3, t0                  // Start with all_zero case                   
    csrw satp, t3              // Write all_zero PPN to satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature

    li t1, 0x1                 // Walking ones
    li t4, 44                  // 43 shifts needed for full 44-bit walking 1 test

loop_walking:
    or t3, t0, t1              // Combine SV57 mode with PPN value
    csrw satp, t3              // Write satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature
    slli t1, t1, 1             // Shift left to prepare the next value
    addi t4, t4, -1            // Decrement loop counter
    bnez t4, loop_walking      // Repeat until all iterations are done

    li t1, 0xFFFFFFFFFFF       // All ones case (44-bit max)
    or t3, t0, t1              // Combine SV57 mode with all ones PPN
    csrw satp, t3              // Write satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature
	
//---------------------------------------------------------------------------------------------------------------------------------
// Test case 3: 								 All zeros and ones in Satp[59:0]
//---------------------------------------------------------------------------------------------------------------------------------

    li t0, 0xA000000000000000  // Ensure SV57 mode in [63:60]

    mv t3, t0                  // Keep lower 60 bits as zero                   
    csrw satp, t3              // Write all_zero case to satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature

    li t1, 0x0FFFFFFFFFFFFFFF  // Keep lower 60 bits as one
    or t3, t0, t1              // Combine with mode field
    csrw satp, t3              // Write to satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature
	
//---------------------------------------------------------------------------------------------------------------------------------
// Test case 4:                           	 Walking ones in the ASID bitfield of Satp
//---------------------------------------------------------------------------------------------------------------------------------

    li t0, 0x0000100000000000      // Start with satp.ASID[0] set
    li t3, 0xA000000000000000      // Ensure SV57 mode in [63:60]
    li t2, 16                      // Number of iterations (16 shifts)

satp_test_loop:
    or t4, t3, t0                  // Combine SV57 mode with current ASID value
    csrw satp, t4                  // Write satp
    csrr t1, satp                  // Read back the value
    RVTEST_SIGUPD(x13, t1)         // Store the value in signature
    slli t0, t0, 1                 // Shift ASID left to test the next value
    addi t2, t2, -1                // Decrement loop counter
    bnez t2, satp_test_loop        // Repeat until all iterations are done


#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

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
    .fill 32*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
