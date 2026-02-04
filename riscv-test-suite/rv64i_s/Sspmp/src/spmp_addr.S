// --------------------------------------------------------------------------------
// Title       : SPMP Address Register Test via Indirect Access
// Authors     : Ported from riscv-tests SPMP test suite
//
// Description : This test verifies the functionality of SPMP address registers
//               (spmpaddr*) via indirect access mechanism (Sscsrind).
//
//               According to SPMP specification:
//               - SPMP registers are accessed ONLY via indirect access mechanism
//               - siselect = 0x100 + i selects SPMP entry i (i = 0..63)
//               - sireg accesses spmpaddr[i]
//               - sireg2 accesses spmpcfg[i]
//
//               This test verifies:
//               - Indirect access to spmpaddr registers works correctly
//               - Address granularity detection
//               - Read/write behavior of spmpaddr via sireg
//               - Address bit behavior in different modes (OFF vs NAPOT)
//
// Notes       : - Requires Sscsrind extension for indirect CSR access
//               - Requires Sspmp extension implementation
//
// Coverpoints : SPMP address register access and granularity
//
// Test Cases  : - siselect write verification
//               - Granularity detection via spmpaddr
//               - Address bit behavior in NAPOT mode
//               - Address bit behavior in OFF mode
//               - Mode switching effects on address bits
//
// Dependencies: model_test.h, arch_test.h
// --------------------------------------------------------------------------------

#include "model_test.h"
#include "arch_test.h"
RVTEST_ISA("RV64I_Zicsr_Sscsrind_Sspmp")

# Test code region
.section .text.init
.globl rvtest_entry_point
rvtest_entry_point:
RVMODEL_BOOT
RVTEST_CODE_BEGIN

RVTEST_CASE(0,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (Sspmp['implemented']); verify (Sscsrind['implemented']); def TEST_CASE_1=True",spmp_addr)

#ifdef TEST_CASE_1
RVTEST_SIGBASE(x13, signature_x13_1)
    .attribute unaligned_access, 0
    .attribute stack_align, 16
    .align 3
    .option norvc

main:
    RVTEST_GOTO_MMODE

#ifdef rvtest_strap_routine
    csrw satp, zero                // Disable address translation.
#endif

    // =========================================================================
    // Test 1: Select SPMP entry 0 and verify siselect write
    // =========================================================================
test1:
    // Select SPMP entry 0 (siselect = 0x100)
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // Verify siselect was written correctly
    csrr t1, CSR_SISELECT

    // Store siselect readback value
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 2: Detect SPMP granularity
    // =========================================================================
    // Software may determine the SPMP granularity by:
    // 1. Writing zero to spmpcfg[i] (via sireg2)
    // 2. Writing all ones to spmpaddr[i] (via sireg)
    // 3. Reading back spmpaddr[i]
    // If G is the index of the least-significant bit set, the granularity is 2^(G+2) bytes.
test2:
    // Clear spmpcfg[0] via sireg2
    csrw CSR_SIREG2, zero

    // Write all ones to spmpaddr[0] via sireg
    li t0, -1
    csrw CSR_SIREG, t0

    // Read back spmpaddr[0] via sireg
    csrr t0, CSR_SIREG

    // Store spmpaddr readback value (will show implemented bits)
    RVTEST_SIGUPD(x13, t0)

    // Isolate the least significant bit set
    neg t1, t0
    and a7, t0, t1

    // a7 now contains only the lowest 1 that was set in spmpaddr[0]
    // Store granularity indicator
    RVTEST_SIGUPD(x13, a7)

    // =========================================================================
    // Test 3: Verify granularity is valid (not >= XLEN)
    // =========================================================================
test3:
    // If a7 is 0 then G is >= XLEN which this test does not support.
    // Store a7 value for verification
    RVTEST_SIGUPD(x13, a7)

    // If granularity is 0, skip to pass (test cannot continue)
    beqz a7, test_complete

    // Shift so the G-1 bit is set.
    srl a7, a7, 1

    // Store shifted granularity mask
    RVTEST_SIGUPD(x13, a7)

    // If no bits are set now then G is 0, which trivially passes.
    beqz a7, test_complete

    // a7 is now SPMPADDR_Gm1_MASK (G-1 bit mask)

    // =========================================================================
    // Test 4: Bit is writable in NAPOT mode - clear it
    // =========================================================================
test4:
    // Set NAPOT mode
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    LI(t5, SPMP_A_NAPOT)
    csrw CSR_SIREG2, t5

    // Clear the G-1 bit
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    csrc CSR_SIREG, a7

    // Read back and check
    csrr t6, CSR_SIREG
    and t6, t6, a7

    // Store result - should be 0 (bit cleared)
    RVTEST_SIGUPD(x13, t6)

    // =========================================================================
    // Test 5: Bit is writable in NAPOT mode - set it
    // =========================================================================
test5:
    // Set the G-1 bit
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    csrs CSR_SIREG, a7

    // Read back and check
    csrr t6, CSR_SIREG
    and t6, t6, a7

    // Store result - should be non-zero (bit set)
    RVTEST_SIGUPD(x13, t6)

    // =========================================================================
    // Test 6: Bit reads as 0 in OFF mode
    // =========================================================================
test6:
    // Switch to OFF mode
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    csrw CSR_SIREG2, zero

    // Read spmpaddr and check G-1 bit
    csrr t6, CSR_SIREG
    and t6, t6, a7

    // Store result - should be 0 in OFF mode
    RVTEST_SIGUPD(x13, t6)

    // =========================================================================
    // Test 7: Switch back to NAPOT, bit should be readable again
    // =========================================================================
test7:
    // Switch back to NAPOT mode
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    LI(t5, SPMP_A_NAPOT)
    csrw CSR_SIREG2, t5

    // Read back and check
    csrr t6, CSR_SIREG
    and t6, t6, a7

    // Store result - should still have the bit set
    RVTEST_SIGUPD(x13, t6)

    // =========================================================================
    // Test 8: Writing the bit while in OFF mode (read-as-zero)
    // =========================================================================
test8:
    // First clear the bit in NAPOT mode
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    LI(t5, SPMP_A_NAPOT)
    csrw CSR_SIREG2, t5
    csrc CSR_SIREG, a7

    // Switch to OFF mode
    csrw CSR_SIREG2, zero

    // Set the bit while in OFF mode
    csrs CSR_SIREG, a7

    // Switch back to NAPOT mode
    LI(t5, SPMP_A_NAPOT)
    csrw CSR_SIREG2, t5

    // Read and check - bit should be set
    csrr t6, CSR_SIREG
    and t6, t6, a7

    // Store result
    RVTEST_SIGUPD(x13, t6)

    // =========================================================================
    // Test 9: csrs/csrc from zero register should have no side effects
    // =========================================================================
test9:
    // Switch to OFF mode with bit still set
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    csrw CSR_SIREG2, zero

    // csrs and csrc from zero register should not modify the value
    csrc CSR_SIREG, zero
    csrs CSR_SIREG, zero

    // Switch back to NAPOT mode
    LI(t5, SPMP_A_NAPOT)
    csrw CSR_SIREG2, t5

    // Check bit is still set
    csrr t6, CSR_SIREG
    and t6, t6, a7

    // Store result - should still be set
    RVTEST_SIGUPD(x13, t6)

    // =========================================================================
    // Test 10: Setting other bits in OFF mode clears the read-as-zero bit
    // =========================================================================
test10:
    // Switch to OFF mode
    LI(t5, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t5
    csrw CSR_SIREG2, zero

    // Set other bits (all except G-1 bit)
    not t0, a7
    csrs CSR_SIREG, t0

    // Switch back to NAPOT mode
    LI(t5, SPMP_A_NAPOT)
    csrw CSR_SIREG2, t5

    // Check G-1 bit - should be cleared
    csrr t6, CSR_SIREG
    and t6, t6, a7

    // Store result - should be 0
    RVTEST_SIGUPD(x13, t6)

test_complete:
    // =========================================================================
    // Test complete - store final marker
    // =========================================================================
    LI(a4, 0xbeefcafe)
    RVTEST_SIGUPD(x13, a4)

    j exit

exit:
#endif
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
    .fill 64*(XLEN/32),4,0xdeadbeef

#ifdef rvtest_mtrap_routine

tsig_begin_canary:
CANARY;
mtrap_sigptr:
    .fill 256*(XLEN/32),4,0xdeadbeef
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
RVMODEL_DATA_END
