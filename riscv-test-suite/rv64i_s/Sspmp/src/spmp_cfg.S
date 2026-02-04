// --------------------------------------------------------------------------------
// Title       : SPMP Configuration Register Test via Indirect Access
// Authors     : Ported from riscv-tests SPMP test suite
//
// Description : This test verifies the functionality of SPMP configuration
//               registers (spmpcfg*) via indirect access mechanism (Sscsrind).
//
//               According to SPMP specification:
//               - Each SPMP entry has an SXLEN-bit configuration register
//               - spmpcfg[i] layout (SXLEN bits):
//                 Bit 0: R (read)
//                 Bit 1: W (write)
//                 Bit 2: X (execute)
//                 Bits [4:3]: A (address matching: 00=OFF, 01=TOR, 10=NA4, 11=NAPOT)
//                 Bits [6:5]: Reserved (WPRI)
//                 Bit 7: L (lock)
//                 Bit 8: U (user mode)
//                 Bit 9: S (shared)
//                 Bits [SXLEN-1:10]: Reserved (WPRI)
//
//               Access via indirect mechanism:
//               - siselect = 0x100 + i selects SPMP entry i
//               - sireg2 accesses spmpcfg[i]
//
// Notes       : - Requires Sscsrind extension for indirect CSR access
//               - Requires Sspmp extension implementation
//
// Coverpoints : SPMP configuration register access and modes
//
// Test Cases  : - Basic read/write of spmpcfg via indirect access
//               - TOR/NAPOT/NA4/OFF mode configurations
//               - U (user mode) and S (shared) bit testing
//               - Multiple SPMP entry configurations
//               - CSR set/clear bit operations
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

RVTEST_CASE(0,"//check ISA:=regex(.*64.*); check ISA:=regex(.*I.*S.*Zicsr.*); def rvtest_mtrap_routine=True; def rvtest_strap_routine=True; verify (Sspmp['implemented']); verify (Sscsrind['implemented']); def TEST_CASE_1=True",spmp_cfg)

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
    // Test 1: Basic read/write of spmpcfg[0] via indirect access
    // =========================================================================
test1:
    // Select SPMP entry 0
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // Clear spmpcfg[0]
    csrw CSR_SIREG2, zero
    csrr t0, CSR_SIREG2

    // Store result - should read 0 after writing 0
    RVTEST_SIGUPD(x13, t0)

    // =========================================================================
    // Test 2: Write TOR mode with R permission to spmpcfg[0]
    // =========================================================================
test2:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // TOR mode (A=01) + R permission = 0x09
    LI(t0, (SPMP_A_TOR | SPMP_R))
    csrw CSR_SIREG2, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, 0x1F  // Mask to check R, W, X, A fields

    // Store result - expect 0x09
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 3: Write NAPOT mode with R+W permissions
    // =========================================================================
test3:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // NAPOT mode (A=11) + R + W = 0x1B
    LI(t0, (SPMP_A_NAPOT | SPMP_R | SPMP_W))
    csrw CSR_SIREG2, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, 0x1F

    // Store result - expect 0x1B
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 4: Write NA4 mode with R+W+X permissions
    // =========================================================================
test4:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // NA4 mode (A=10) + R + W + X = 0x17
    LI(t0, (SPMP_A_NA4 | SPMP_R | SPMP_W | SPMP_X))
    csrw CSR_SIREG2, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, 0x1F

    // Store result - expect 0x17
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 5: Test U (user mode) bit
    // =========================================================================
test5:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // NAPOT + R + U = 0x119
    LI(t0, (SPMP_A_NAPOT | SPMP_R | SPMP_U))
    csrw CSR_SIREG2, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, 0x1FF  // Check key bits including U

    // Store result - expect 0x119
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 6: Test S (shared) bit
    // =========================================================================
test6:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // NAPOT + R + S + U (shared region) = 0x319
    LI(t0, (SPMP_A_NAPOT | SPMP_R | SPMP_S | SPMP_U))
    csrw CSR_SIREG2, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, 0x3FF  // Check all key bits including S

    // Store result - expect 0x319
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 7: Test multiple SPMP entries (entry 0 and entry 1)
    // =========================================================================
test7:
    // Configure entry 0
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0
    LI(t0, (SPMP_A_TOR | SPMP_R))
    csrw CSR_SIREG2, t0

    // Configure entry 1
    LI(t0, (SPMP_SELECT_BASE + 1))
    csrw CSR_SISELECT, t0
    LI(t0, (SPMP_A_NAPOT | SPMP_R | SPMP_W | SPMP_X))
    csrw CSR_SIREG2, t0

    // Verify entry 0
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, 0x1F

    // Store entry 0 result - expect (SPMP_A_TOR | SPMP_R) = 0x09
    RVTEST_SIGUPD(x13, t1)

    // Verify entry 1
    LI(t0, (SPMP_SELECT_BASE + 1))
    csrw CSR_SISELECT, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, 0x1F

    // Store entry 1 result - expect (SPMP_A_NAPOT | SPMP_R | SPMP_W | SPMP_X) = 0x1F
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 8: Clear configuration
    // =========================================================================
test8:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0
    csrw CSR_SIREG2, zero
    csrr t1, CSR_SIREG2

    // Store result - expect 0
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 9: Test CSR set bits on spmpcfg[0]
    // =========================================================================
test9:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0
    csrw CSR_SIREG2, zero

    // Set R bit using csrs
    LI(t0, SPMP_R)
    csrs CSR_SIREG2, t0
    csrr t1, CSR_SIREG2
    andi t1, t1, SPMP_R

    // Store result - expect SPMP_R = 0x01
    RVTEST_SIGUPD(x13, t1)

    // =========================================================================
    // Test 10: Test CSR clear bits on spmpcfg[0]
    // =========================================================================
test10:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // Write all permission bits
    LI(t0, (SPMP_A_NAPOT | SPMP_R | SPMP_W | SPMP_X))
    csrw CSR_SIREG2, t0

    // Clear R bit using csrc
    LI(t1, SPMP_R)
    csrc CSR_SIREG2, t1
    csrr t2, CSR_SIREG2
    andi t2, t2, SPMP_R

    // Store result - expect 0 (R bit cleared)
    RVTEST_SIGUPD(x13, t2)

    // =========================================================================
    // Test 11: Verify OFF mode (A=00) disables entry
    // =========================================================================
test11:
    LI(t0, SPMP_SELECT_BASE)
    csrw CSR_SISELECT, t0

    // Set OFF mode with some permissions (should be null region)
    LI(t0, (SPMP_A_OFF | SPMP_R | SPMP_W))
    csrw CSR_SIREG2, t0
    csrr t1, CSR_SIREG2
    // A field should be 0 (OFF)
    andi t1, t1, SPMP_A

    // Store result - expect 0 (A field = OFF)
    RVTEST_SIGUPD(x13, t1)

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
