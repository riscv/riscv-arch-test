#include "encoding.h"

/*
 * Platform model macros (RVMODEL_BOOT, RVMODEL_HALT_PASS,
 * RVMODEL_HALT_FAIL, RVMODEL_DATA_SECTION) are injected via
 * ASFLAGS -include $(CONFIG_MODEL_HEADER) in Makefile.common.
 * If compiling outside the build system, ensure rvmodel_macros.h
 * from the target platform config directory is included first.
 */
#ifndef RVMODEL_HALT_PASS
#error "RVMODEL_* macros not defined. Include rvmodel_macros.h via -include or ASFLAGS."
#endif

#if __riscv_xlen == 64
    #define REGSIZE 8
    #define LOAD    ld
    #define STORE   sd
#else
    #define REGSIZE 4
    #define LOAD    lw
    #define STORE   sw
#endif

/* ===================================================================
 * CLEAR_GPRS - zero x1-x31
 *
 * The other register files are cleared in reg_init.S (_fp_reg_init).
 * The GPR clear has to stay here and be inlined: the first clear runs
 * before sp exists and must not clobber a return address, so it cannot
 * be turned into a function call.
 *
 * x0 is hardwired to zero and sp (x2) is owned by the caller, so both
 * are left alone. gp/tp are cleared as well: the framework builds with
 * -mno-relax and uses no TLS, so neither register is ever read.
 * =================================================================== */
.macro CLEAR_GPRS
    li      x1,  0
    li      x3,  0
    li      x4,  0
    li      x5,  0
    li      x6,  0
    li      x7,  0
    li      x8,  0
    li      x9,  0
    li      x10, 0
    li      x11, 0
    li      x12, 0
    li      x13, 0
    li      x14, 0
    li      x15, 0
    li      x16, 0
    li      x17, 0
    li      x18, 0
    li      x19, 0
    li      x20, 0
    li      x21, 0
    li      x22, 0
    li      x23, 0
    li      x24, 0
    li      x25, 0
    li      x26, 0
    li      x27, 0
    li      x28, 0
    li      x29, 0
    li      x30, 0
    li      x31, 0
.endm

    .section .text.init
    .global rvtest_entry_point
rvtest_entry_point:
    /* ---- Clear every general-purpose register ----
     *
     * Reset leaves the GPR contents undefined: real hardware can power
     * up with arbitrary values, so a test that happens to read an
     * uninitialized register would observe platform-dependent data.
     * Clear them first thing, on every hart, before any other boot
     * step can pick up a stale value.
     */
    CLEAR_GPRS

    /* ---- Only hart 0 continues; others spin ---- */
    csrr    a0, mhartid
    bnez    a0, _secondary_spin

    /* ---- Set up stack pointer (use full stack for hart 0) ---- */
    la      sp, __stack_end

#ifdef SMDBLTRP_SUPPORTED
    /* ---- Smdbltrp: clear MDT immediately ----
     *
     * When Smdbltrp is enabled, Spike sets mstatus.MDT=1 at reset.
     * If any synchronous trap occurs while MDT=1, it becomes a
     * double trap (critical error), causing an unrecoverable hang.
     *
     * We must clear MDT BEFORE any instruction that could potentially
     * trap. Use csrw mstatus (pure write, no read) to set MDT=0 while
     * keeping MPP=M-mode (0b11 at bits [12:11]).
     */
    li      t0, (3 << 11)       /* MPP=M, MDT=0, all other bits=0 */
    csrw    mstatus, t0
#endif

    /* ---- Set up early trap vectors ----
     *
     * Use the common m_trap_entry / s_trap_entry handlers at boot.
     * stvec is installed here (not only in reset_state) because the
     * delegation-first baseline below sends stimulus traps straight to the
     * S handler, which must therefore be reachable before main() starts.
     * Projects that need Smdbltrp-specific trap handling (e.g., Smdbltrp,
     * Ssdbltrp) should install smdbltrp_m_trap_entry in their main.c.
     */
    la      t0, m_trap_entry
    csrw    mtvec, t0
    la      t0, s_trap_entry
    csrw    stvec, t0

    /* ---- Clear BSS ---- */
    la      a0, _bss_start
    la      a1, _bss_end
_clear_bss:
    bgeu    a0, a1, _bss_done
    STORE   zero, 0(a0)
    addi    a0, a0, REGSIZE
    j       _clear_bss
_bss_done:

    /* ---- Platform-specific boot (earliest HW init) ---- */
#ifdef RVMODEL_BOOT
    RVMODEL_BOOT
#endif

    /* ---- Call platform-specific init (weak symbol, default=nop) ---- */
    call    _platform_init

    /* ---- Clear the floating-point register file (reg_init.S) ----
     *
     * Runs after BSS is cleared and mtvec is installed, so an FP access
     * that unexpectedly traps on a non-conforming DUT is reported by
     * m_trap_handler (UNEXPECTED TRAP + halt fail) instead of hanging.
     * The symbol is always linked in: it degenerates to a plain ret when
     * the platform config declares no FP extension.
     */
    call    _fp_reg_init

    /* ---- Clear the GPRs again before entering C ----
     *
     * The boot path above (BSS loop, RVMODEL_BOOT, _platform_init,
     * _fp_reg_init) necessarily uses scratch registers. Re-clearing
     * here means main() - and therefore every test - starts from an
     * all-zero register file instead of inheriting boot temporaries.
     * ra is reloaded by the call itself; sp is already live.
     */
    CLEAR_GPRS

    /* ================================================================
     * S-mode-normal execution model (tsbi_design_brief.md section 1)
     *
     * Tests run in S-mode as their normal state; anything that touches
     * M-mode goes through T-SBI.  Boot therefore finishes the M-mode-only
     * setup here and then drops to S before entering main().
     *
     * Build with -DTSBI_BOOT_MODE_M to keep the historical M-mode entry
     * (needed by suites that own the very early M environment or a custom
     * trap entry: Smdbltrp / smrnmi / ntrace / iopmp / clic ...).
     * ================================================================ */

    /* ---- PMP: allow S/U full access to the whole address space ----
     * Hoisted out of the individual main.c files so it is guaranteed to be
     * in place before we drop privilege (otherwise S-mode cannot even
     * fetch instructions).  NAPOT entry covering everything, R/W/X. */
    li      t0, -1
    csrw    pmpaddr0, t0
    li      t0, 0x1F
    csrw    pmpcfg0, t0

    /* ---- Delegation-first baseline (medeleg / mideleg / hedeleg) ----
     * Writes the baseline, then reads it back so the framework knows the
     * effective value (WARL / read-only-zero bits).  Runs after BSS clear
     * because it stores the snapshot in BSS. */
    call    tsbi_deleg_apply_baseline

#ifndef TSBI_BOOT_MODE_M
    /* ---- Drop to S-mode and enter main() there ----
     * Lowering privilege is a right, not a request: configure MPP=S and
     * mret directly (no T-SBI involved).  current_priv must be updated by
     * hand because we bypass the C helpers here.
     * ra is pointed at _s_main_return so that main()'s `ret` lands there
     * while still in S-mode. */
    la      t0, current_priv
    li      t1, 1                   /* PRIV_S */
    sw      t1, 0(t0)

    li      t0, (3 << 11)           /* MPP field mask */
    csrc    mstatus, t0
    li      t0, (1 << 11)           /* MPP = S */
    csrs    mstatus, t0

    la      ra, _s_main_return
    la      t0, main
    csrw    mepc, t0
    mret

_s_main_return:
    /* main() returned, still in S-mode.  Raising privilege IS a request,
     * so go back to M through T-SBI GOTO_MMODE before the halt sequence
     * (RVMODEL_HALT_* needs M-mode). */
    mv      s0, a0                  /* preserve main()'s exit status */
    li      a0, 1                   /* TSBI_GOTO_MMODE */
    ecall
    mv      a0, s0
    j       _halt
#else
    /* ---- Jump to C main (M-mode entry, legacy/exception suites) ---- */
    call    main
#endif

    /* ---- Halt after main returns ---- */
_halt:
    bnez    a0, _halt_fail
    j       _halt_pass
.global _halt_fail
/*
 * RVMODEL_HALT_PASS is expected to never return (self-loop or
 * simulator exit). If it unexpectedly falls through, execution
 * escalates into RVMODEL_HALT_FAIL so the failure is explicit
 * instead of hanging silently.
 */
.global _halt_pass
    /* .balign 16 inside RVMODEL_HALT_* is encoded as R_RISCV_ALIGN when
     * GAS relaxation is enabled; GAS may record less NOP slack than the
     * final layout needs, causing "can't relax section" link errors.
     * Assemble these macros with norelax so GAS fills the alignment
     * exactly here. clang is excluded: its integrated assembler fills
     * code alignment with zeros (illegal unimp) under norelax, which
     * would trap on the fall-through path before the semihost sequence;
     * clang/LLD do not have the GAS alignment-record bug. */
_halt_pass:
#ifndef __clang__
    .option push
    .option norelax
#endif
    RVMODEL_HALT_PASS
#ifndef __clang__
    .option pop
#endif
_halt_fail:
#ifndef __clang__
    .option push
    .option norelax
#endif
    RVMODEL_HALT_FAIL
#ifndef __clang__
    .option pop
#endif
_halt_loop:
    wfi
    j       _halt_loop

_secondary_spin:
    wfi
    j       _secondary_spin

    /* ---- Platform-specific data section (e.g., semihost exit codes, tohost) ---- */
    RVMODEL_DATA_SECTION
