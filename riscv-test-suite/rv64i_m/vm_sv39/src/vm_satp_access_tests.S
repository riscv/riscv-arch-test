// ----------------------------------------------------------------------------------------------------------------------
// This test is part of the test plan for the SV-39-based Virtual Memory System, available at:
// https://docs.google.com/spreadsheets/d/1rZQbz8gJc3RRbTG4rbw9SoEGYkArA8ileVldBX_gxUc/edit?gid=1688601426#gid=1688601426
// Developed by: Umer Shahid, Muhammad Abdullah, Muhammad Zain, Hamza Ali and Muhammad Ahmad
// ----------------------------------------------------------------------------------------------------------------------
// This test verifies the functionality of satp register in M, S and U Mode using csrrw, csrrs, csrrc.
// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
//  1. Accessing the satp register in M and S mode -> Successful
//  2. Accessing the satp register in U mode -> Illegal Instruction exception
//  3. Testing satp mode field (SV39 and Bare mode) -> Successful
//  4. All zeroes, ones and walking ones on the PPN field of satp  -> Successful
//	5. All zeroes and ones on the ASID of satp -> Successful
//	6. Walking ones on the ASID of satp -> Successful
//  7. Verifying Bare mode operation -> Successful

// Total Expected Faults: 3
// ----------------------------------------------------------------------------------------------------------------------

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
    RVTEST_CASE(1,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True",satp_access_all_modes)
RVTEST_SIGBASE( x13,signature_x13_1)
# ---------------------------------------------------------------------------------------------

main:
#ifdef rvtest_mtrap_routine					                				// Verification of existance of rvtest_mtrap_routine
	LI a4, 0xceed
	//RVTEST_SIGUPD(x13,a4)
#endif
#ifdef rvtest_strap_routine					                				// Verification of existance of rvtest_strap_routine
	LI a4, 0xbeed
	//RVTEST_SIGUPD(x13,a4)
#endif
	
	ALL_MEM_PMP          		                  	                      	// set the PMP permissions for the whole memory
	csrw satp, zero  		                                        		// write satp with all zeros (bare mode)
 
 // ------------------------------------------------------------------------------------------------------------
// 										satp access in M Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------


	li t0, 1																//initial value for t0 = 1
	csrw satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrs satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrc satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

// ------------------------------------------------------------------------------------------------------------
// 										satp access in S Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------

	//Go to S mode
	RVTEST_GOTO_LOWER_MODE Smode

	li t0, 1																//initial value for t0 = 1
	csrw satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrs satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	csrc satp, t0  		                                        			// write satp with some value
	//read back the value from the satp and store in the signature to make sure they match !
	csrr t1, satp
	RVTEST_SIGUPD(x13,t1)
	slli t0, t0, 1															//walking ones to have different values in each satp store

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode

// ------------------------------------------------------------------------------------------------------------
// 										satp access in U Mode using csrrw, csrrc, csrrs
// ------------------------------------------------------------------------------------------------------------

	RVTEST_GOTO_LOWER_MODE Umode

	li t0, 1																//initial value for t0 = 1
	csrw satp, t0  		                                        			// write satp with some value
	nop
	nop

	csrs satp, t0  		                                        			// write satp with some value
	nop
	nop

	csrc satp, t0  		                                        			// write satp with some value
	nop
	nop

	RVTEST_GOTO_MMODE		                                        		// Switching back to M mode
	
// ------------------------------------------------------------------------------------------------------------
// 										Mode Supported --- SV39 and Bare i.e., sat.2
// ------------------------------------------------------------------------------------------------------------

	li t0, 0x8000000000000000  // Set t0 to have 8 in [63:60] (SV39)
    csrw satp, t0              // Write satp
    csrr t1, satp              // Read back satp
    RVTEST_SIGUPD(x13, t1)     // Store read value in signature

    li t0, 0x0000000000000000  // Set t0 to have 0 in [63:60] (Bare mode)
    csrw satp, t0              // Write satp
    csrr t1, satp              // Read back satp
    RVTEST_SIGUPD(x13, t1)     // Store read value in signature
	
	RVTEST_GOTO_MMODE
	
// ------------------------------------------------------------------------------------------------------------
// 				PPN all zeros, ones and walking ones to the PPN bits of satp i.e., sat.4
// ------------------------------------------------------------------------------------------------------------	

    li t0, 0x8000000000000000  // Ensure SV39 mode in [63:60]
    mv t3, t0                  // Start with all_zero case                   
    csrw satp, t3              // Write all_zero PPN to satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature

    li t1, 0x1                 // Walking ones
    li t4, 44                  // 43 shifts needed for full 44-bit walking 1 test

loop_walking:
    or t3, t0, t1              // Combine SV39 mode with PPN value
    csrw satp, t3              // Write satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature
    slli t1, t1, 1             // Shift left to prepare the next value
    addi t4, t4, -1            // Decrement loop counter
    bnez t4, loop_walking      // Repeat until all iterations are done

    li t1, 0xFFFFFFFFFFF       // All ones case (44-bit max)
    or t3, t0, t1              // Combine SV39 mode with all ones PPN
    csrw satp, t3              // Write satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature
	
// ------------------------------------------------------------------------------------------------------------
// 										Satp_Asid_PPN all zeros and ones i.e., sat.4
// ------------------------------------------------------------------------------------------------------------

    li t0, 0x8000000000000000  // Ensure SV39 mode in [63:60]

    mv t3, t0                  // Keep lower 60 bits as zero                   
    csrw satp, t3              // Write all_zero case to satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature

    li t1, 0x0FFFFFFFFFFFFFFF  // Keep lower 60 bits as one
    or t3, t0, t1              // Set SATP[59:0] to a non-zero value
    csrw satp, t3              // Write to satp
    csrr t2, satp              // Read back satp
    RVTEST_SIGUPD(x13, t2)     // Store read value in signature
	
// ------------------------------------------------------------------------------------------------------------
//                                      Satp_Asid_Length i.e., sat.5
// ------------------------------------------------------------------------------------------------------------

    li t0, 0x0000100000000000      // Start ASID in bit 44
    li t3, 0x8000000000000000      // Ensure SV39 mode in [63:60]
    li t2, 15                      // Number of iterations (15 shifts)

satp_test_loop:
    or t4, t3, t0                  // Combine SV39 mode with current ASID value
    csrw satp, t4                  // Write satp
    csrr t1, satp                  // Read back the value
    RVTEST_SIGUPD(x13, t1)         // Store the value in signature
    slli t0, t0, 1                 // Shift ASID left to test the next value
    addi t2, t2, -1                // Decrement loop counter
    bnez t2, satp_test_loop        // Repeat until all iterations are done


// ------------------------------------------------------------------------------------------------------------
//                                      Bare_Mode Testing i.e, sat.3
// ------------------------------------------------------------------------------------------------------------

    li t3, 0                       // Ensure Bare mode (satp[63:60] = 0)
	
    csrw satp, t3                  // Write all_zero value to satp
    csrr t2, satp                  // Read back satp
    RVTEST_SIGUPD(x13, t2)         // Store read-back value in signature

    li t1, 0x123456789ABC           // Example nonzero value for remaining fields
    or t3, t3, t1                   // Keep Bare mode, set nonzero [59:0]
    csrw satp, t3                   // Write satp with nonzero value
    csrr t2, satp                   // Read back satp
    RVTEST_SIGUPD(x13, t2)          // Store read-back value in signature


#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

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