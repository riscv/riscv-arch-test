// Test cases are as follows:
// ----------------------------------------------------------------------------------------------------------------------
// 1. Walking ones are stored in ASID bitfield of satp register
// 2. Then satp register is accessed S Mode using csrrw, csrrc, csrrs -> Successful
// Total Expected Faults :: 0
// ----------------------------------------------------------------------------------------------------------------------


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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", vm_satp_asid_walking_ones)

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
	
	ALL_MEM_PMP          		                  	                      	// set the PMP permissions for the whole memory
	csrw satp, zero  		                                        		// write satp with all zeros (bare mode)


// ------------------------------------------------------------------------------------------------------------
// 										SATP_ASID_Length 
// ------------------------------------------------------------------------------------------------------------

	li t1, 0                // Temporary storage for read-back
	li t0, 0x400000         // Initial value

	// Loop for multiple satp writes and reads
	li t2, 8                // Number of iterations (8 shifts)
	satp_test_loop:
    csrw satp, t0     		// Write satp with the current value
    csrr t1, satp     		// Read back the value from satp
    RVTEST_SIGUPD(x13, t1) 	// Update the signature with the read-back value
    slli t0, t0, 1    		// Shift left to prepare the next value
    addi t2, t2, -1   		// Decrement loop counter
    bnez t2, satp_test_loop // Repeat until all iterations are done

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

#endif
//---------------------------------------------------------------------------------------------------------------------------------
RVTEST_CODE_END
RVMODEL_HALT
RVTEST_DATA_BEGIN

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
