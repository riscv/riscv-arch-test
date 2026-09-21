// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// start.S: startup, trap handler and console output for the UDB feature extractor.
//
// Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
// with assistance from Claude.
//
// Only the DUT's rvmodel_macros.h is needed: the extractor runs entirely in machine mode with its
// own trap handler, so none of the riscv-arch-test boot or trap-handling framework is used.

#include "rvmodel_macros.h"

#if __riscv_xlen == 64
#define LREG ld
#define SREG sd
#define REGBYTES 8
#else
#define LREG lw
#define SREG sw
#define REGBYTES 4
#endif

// mstatus.FS = mstatus.VS = Dirty, so floating-point and vector probes may execute.
// Both fields are WARL and read as zero where the extensions are absent.
#define MSTATUS_FS_VS ((3 << 13) | (3 << 9))

.section .text.init, "ax", @progbits
.globl rvtest_entry_point
rvtest_entry_point:
    csrr    a0, mhartid
    bnez    a0, park                    // only hart 0 runs the extractor

    la      t0, trap_handler
    csrw    mtvec, t0
    li      t0, MSTATUS_FS_VS
    csrs    mstatus, t0
#ifdef RVMODEL_IO_INIT
    RVMODEL_IO_INIT(t0, t1, t2)
#endif

    la      t0, __bss_start             // clear .bss
    la      t1, __bss_end
1:  bgeu    t0, t1, 2f
    SREG    zero, 0(t0)
    addi    t0, t0, REGBYTES
    j       1b
2:  la      sp, __stack_top
    andi    sp, sp, -16
    call    main
halt_pass:
    RVMODEL_HALT_PASS
halt_fail:
    RVMODEL_HALT_FAIL
park:
    wfi
    j       park

// Trap handler.  A probe stores the address to resume at in probe_resume before executing its
// instruction; a trap while it is set records mcause and returns there, so the probe never needs
// to know the length of the instruction that trapped.  Any other trap is a fatal error: it is
// reported with its cause and the run fails.  t0-t2 may be clobbered here because every probe
// declares them clobbered.
.balign 4
trap_handler:
    li      t0, 1 << 17                 // clear mstatus.MPRV: a probe may have set it to take a
    csrc    mstatus, t0                 // fault, and the handler's own accesses must be M-mode ones
    la      t0, probe_resume
    LREG    t1, 0(t0)
    beqz    t1, unexpected_trap
    SREG    zero, 0(t0)
    csrr    t2, mcause
    la      t0, probe_cause
    SREG    t2, 0(t0)
    csrr    t2, mtval
    la      t0, probe_tval
    SREG    t2, 0(t0)
    csrr    t2, mepc
    la      t0, probe_epc
    SREG    t2, 0(t0)
    li      t0, 3 << 11                 // resume in M-mode even if the trap came from U or S
    csrs    mstatus, t0                 // (a probe may have entered a lower mode with mret)
    la      t0, cfi_active              // during the landing-pad probes: forget the expected
    LREG    t2, 0(t0)                   // landing pad (MPELP, which mret would restore into ELP)
    beqz    t2, 3f                      // and stop M-mode enforcement, or the resume would fault
#if __riscv_xlen == 64
    li      t0, 1 << 41
    csrc    mstatus, t0
#else
    li      t0, 1 << 9
    csrc    mstatush, t0
#endif
    li      t0, 1 << 10
    csrc    mseccfg, t0
3:  csrw    mepc, t1
    mret
unexpected_trap:
    csrr    a0, mcause
    csrr    a1, mepc
    csrr    a2, mtval
    la      sp, __stack_top             // a fresh stack, in case sp was the problem
    andi    sp, sp, -16
    call    report_unexpected_trap
    j       halt_fail

// Trap handler for S-mode and VS-mode probes.  parameters.c enters the lower mode with mret and
// delegates exceptions to it; this handler records the trap and returns to M-mode with an ecall,
// which the M-mode handler above resumes from.  In VS-mode the scause, stval and sepc names
// reach vscause, vstval and vsepc, so the same code serves both modes.
.balign 4
.globl hs_trap_handler
hs_trap_handler:                        // HS-mode variant: also record the hypervisor trap values
    csrr    t0, htval
    la      t1, s_htval
    SREG    t0, 0(t1)
    csrr    t0, htinst
    la      t1, s_htinst
    SREG    t0, 0(t1)
.globl s_trap_handler
s_trap_handler:
    csrr    t0, scause
    la      t1, s_cause
    SREG    t0, 0(t1)
    csrr    t0, stval
    la      t1, s_tval
    SREG    t0, 0(t1)
    csrr    t0, sepc
    la      t1, s_epc
    SREG    t0, 0(t1)
    ecall

// void console_write(const char *s): print a NUL-terminated string with the DUT's mechanism
.section .text
.globl console_write
.type console_write, @function
console_write:
    RVMODEL_IO_WRITE_STR(t0, t1, t2, a0)
    ret
.size console_write, . - console_write

#ifdef RVMODEL_DATA_SECTION
RVMODEL_DATA_SECTION
#endif
