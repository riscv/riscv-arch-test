// This test will check that in machine mode, a store address misaligned exception is raised when we try 
// to attempt to store data to a misaligned memory address. For this we will check the log file 
// that either it is giving the expected exception at that point and value of the mcause is "6" in M mode

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
    RVTEST_CASE(1,"//check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; def TEST_CASE_1=True; mac SV32_MACROS", inst_addr_misalign)

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
    ALL_MEM_PMP                // Set PMP permissions for the entire memory
    csrw satp, zero            // Write satp with all zeros (bare mode)
    
    RVTEST_GOTO_LOWER_MODE Smode

    la t0, aligned_label       // Load the address of an aligned label
    addi t0, t0, 2             // Add an offset to make it misaligned (e.g., 2 for halfword alignment)

    // indirect jump to misaligned address
    jalr x0, 0(t0)             // Should cause an instruction address misaligned exception
    nop

aligned_label:
    nop                        // Aligned instruction
    nop
    nop
    
    LI a4,0xffff
    RVTEST_SIGUPD(x13,a4)
    
    // Switching back to M mode
    RVTEST_GOTO_MMODE


#endif
//---------------------------------------------------------------------------------------------------------------------------------
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
    .fill 64*(XLEN/32),4,0xdeadbeef
#endif

sig_end_canary:
CANARY;
rvtest_sig_end:
RVMODEL_DATA_END
