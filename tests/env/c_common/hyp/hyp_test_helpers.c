/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * hyp_test_helpers.c - Shared helpers for Hypervisor Extension tests
 *
 * Provides VS/VU-mode trampoline functions for CSR access, instruction
 * execution, delegation configuration, and G-stage fault helpers.
 * =================================================================== */

#include "hyp_test_helpers.h"

/* ===================================================================
 * VS/VU-mode CSR access trampolines.
 *
 * These are passed to run_in_vs_mode() / run_in_vu_mode(). In V=1,
 * S-level CSR names map to their VS counterparts automatically.
 * =================================================================== */

uintptr_t vs_read_sstatus(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, sstatus" : "=r"(v));
    return v;
}

uintptr_t vs_write_sstatus(uintptr_t val) {
    asm volatile ("csrw sstatus, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_read_sie(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, sie" : "=r"(v));
    return v;
}

uintptr_t vs_read_sip(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, sip" : "=r"(v));
    return v;
}

uintptr_t vs_read_satp(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, satp" : "=r"(v));
    return v;
}

uintptr_t vs_read_stvec(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, stvec" : "=r"(v));
    return v;
}

uintptr_t vs_read_sscratch(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, sscratch" : "=r"(v));
    return v;
}

uintptr_t vs_read_sepc(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, sepc" : "=r"(v));
    return v;
}

uintptr_t vs_read_scause(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, scause" : "=r"(v));
    return v;
}

uintptr_t vs_read_stval(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, stval" : "=r"(v));
    return v;
}

uintptr_t vs_write_satp(uintptr_t val) {
    asm volatile ("csrw satp, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_write_sie(uintptr_t val) {
    asm volatile ("csrw sie, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_write_sip_ssip(uintptr_t val) {
    uintptr_t bit = val ? (1UL << 1) : 0;
    asm volatile ("csrw sip, %0" :: "r"(bit));
    return 0;
}

uintptr_t vs_write_sscratch(uintptr_t val) {
    asm volatile ("csrw sscratch, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_write_sepc(uintptr_t val) {
    asm volatile ("csrw sepc, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_write_scause(uintptr_t val) {
    asm volatile ("csrw scause, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_write_stval(uintptr_t val) {
    asm volatile ("csrw stval, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_write_stvec(uintptr_t val) {
    asm volatile ("csrw stvec, %0" :: "r"(val));
    return 0;
}

uintptr_t vs_read_senvcfg(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x10A" : "=r"(v));  /* senvcfg */
    return v;
}

uintptr_t vs_write_senvcfg(uintptr_t val) {
    asm volatile ("csrw 0x10A, %0" :: "r"(val));  /* senvcfg */
    return 0;
}

uintptr_t vs_read_scounteren(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x106" : "=r"(v));  /* scounteren */
    return v;
}

uintptr_t vs_write_scounteren(uintptr_t val) {
    asm volatile ("csrw 0x106, %0" :: "r"(val));  /* scounteren */
    return 0;
}

/* ===================================================================
 * VS/VU-mode instruction execution trampolines.
 * =================================================================== */

uintptr_t vs_exec_sret(uintptr_t arg) {
    (void)arg;
    /* Set sepc (= vsepc when V=1) to the instruction after sret,
     * so that if VTSR=0 and sret actually executes, it lands safely
     * at the return path instead of jumping to address 0. */
    asm volatile (
        "la   t0, 1f\n\t"
        "csrw sepc, t0\n\t"
        "sret\n\t"
        "1:\n\t"
        ::: "t0", "memory"
    );
    return 0;
}

uintptr_t vu_exec_sret(uintptr_t arg) {
    (void)arg;
    /* VU-mode variant: execute sret directly without writing sepc first,
     * since VU-mode cannot access S-level CSRs (csrw sepc would itself
     * trap and consume the armed state before sret is reached). */
    asm volatile ("sret" ::: "memory");
    return 0;
}

uintptr_t vu_nop(uintptr_t arg) {
    /* Simple identity function safe for VU-mode (no CSR access). */
    return arg;
}

uintptr_t vs_exec_wfi(uintptr_t arg) {
    (void)arg;
    asm volatile ("wfi");
    return 0;
}

uintptr_t vs_exec_sfence_vma(uintptr_t arg) {
    (void)arg;
    asm volatile ("sfence.vma x0, x0");
    return 0;
}

uintptr_t vs_exec_sinval_vma(uintptr_t arg) {
    (void)arg;
    /* sinval.vma x0, x0 encoding: 0x16000073 */
    asm volatile (".4byte 0x16000073");
    return 0;
}

uintptr_t vs_exec_ecall(uintptr_t arg) {
    (void)arg;
    /* We want a RAW ecall stimulus, i.e. one the handler records instead of
     * interpreting.  Zeroing the legacy ecall_args[] tag used to achieve that;
     * under T-SBI the opcode travels in a0, which we do not control here, so
     * the escape hatch has to be armed explicitly (consume-once). */
    tsbi_arm_raw_ecall(true);
    asm volatile ("ecall" ::: "memory");
    return 0;
}

uintptr_t vs_exec_ebreak(uintptr_t arg) {
    (void)arg;
    asm volatile ("ebreak");
    return 0;
}

uintptr_t vs_exec_illegal(uintptr_t arg) {
    (void)arg;
    /* 0xC0001073: SYSTEM opcode with reserved funct3 — guaranteed
     * illegal on all implementations. A full 4-byte encoding is used
     * (NOT the all-zeros word, which the trap handler would mistake
     * for a 2-byte compressed instruction and skip incorrectly). */
    asm volatile (".word 0xC0001073");
    return 0;
}

uintptr_t vs_nop_fn(uintptr_t arg) {
    (void)arg;
    return 0;
}

/* fadd.s f0, f0, f0 — modifies f0 to trigger FS dirty.
 * Raw .4byte encoding avoids -march dependency on F extension. */
uintptr_t vs_exec_fp_inst(uintptr_t arg) {
    (void)arg;
    asm volatile (".4byte 0x00000053" ::: "memory");
    return 0;
}

/* vsetvli t0, zero, e8, m1, ta, ma — touches vector config state.
 * Raw .4byte encoding avoids -march dependency on V extension. */
uintptr_t vs_exec_vector_inst(uintptr_t arg) {
    (void)arg;
    asm volatile (".4byte 0x0C0072D7" ::: "memory");
    return 0;
}

/* ===================================================================
 * VS/VU-mode H-CSR access trampolines (should cause virtual-inst).
 * =================================================================== */

uintptr_t vs_read_hstatus(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x600" : "=r"(v));  /* hstatus */
    return v;
}

uintptr_t vs_read_hedeleg(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x602" : "=r"(v));  /* hedeleg */
    return v;
}

uintptr_t vs_read_hgatp(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x680" : "=r"(v));  /* hgatp */
    return v;
}

uintptr_t vs_read_hgeip(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0xE12" : "=r"(v));  /* hgeip (read-only) */
    return v;
}

uintptr_t vs_read_hgeie(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x607" : "=r"(v));  /* hgeie */
    return v;
}

uintptr_t vs_read_htval(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x643" : "=r"(v));  /* htval */
    return v;
}

uintptr_t vs_read_htinst(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x64A" : "=r"(v));  /* htinst */
    return v;
}

uintptr_t vs_read_vsstatus_direct(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x200" : "=r"(v));  /* vsstatus addr */
    return v;
}

uintptr_t vs_exec_hlv_w(uintptr_t arg) {
    uintptr_t v;
    /* hlv.w rd, (rs1): .insn r 0x73, 0x4, 0x34, rd, rs1, x0 */
    asm volatile (".insn r 0x73, 0x4, 0x34, %0, %1, x0"
                  : "=r"(v) : "r"(arg));
    return v;
}

uintptr_t vs_exec_hsv_w(uintptr_t arg) {
    /* hsv.w rs2, (rs1): .insn r 0x73, 0x4, 0x35, x0, rs1, rs2 */
    asm volatile (".insn r 0x73, 0x4, 0x35, x0, %0, x0"
                  :: "r"(arg));
    return 0;
}

uintptr_t vs_exec_hlvx_wu(uintptr_t arg) {
    uintptr_t v;
    /* hlvx.wu rd, (rs1): .insn r 0x73, 0x4, 0x34, rd, rs1, x3 */
    asm volatile (".insn r 0x73, 0x4, 0x34, %0, %1, x3"
                  : "=r"(v) : "r"(arg));
    return v;
}

uintptr_t vs_exec_hfence_vvma(uintptr_t arg) {
    (void)arg;
    asm volatile (".4byte 0x22000073");  /* hfence.vvma x0, x0 */
    return 0;
}

uintptr_t vs_exec_hfence_gvma(uintptr_t arg) {
    (void)arg;
    asm volatile (".4byte 0x62000073");  /* hfence.gvma x0, x0 */
    return 0;
}

/* ===================================================================
 * Additional H-CSR access trampolines.
 *
 * Each attempts to read an HS-only CSR by its raw address.
 * All should trigger virtual-instruction exception when V=1.
 * =================================================================== */

uintptr_t vs_read_hideleg(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x603" : "=r"(v));  /* hideleg */
    return v;
}

uintptr_t vs_read_hcounteren(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x606" : "=r"(v));  /* hcounteren */
    return v;
}

uintptr_t vs_read_htimedelta(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x605" : "=r"(v));  /* htimedelta */
    return v;
}

uintptr_t vs_read_hip(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x644" : "=r"(v));  /* hip */
    return v;
}

uintptr_t vs_read_hie(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x604" : "=r"(v));  /* hie */
    return v;
}

uintptr_t vs_read_hvip(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x645" : "=r"(v));  /* hvip */
    return v;
}

uintptr_t vs_read_henvcfg(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0x60A" : "=r"(v));  /* henvcfg */
    return v;
}

uintptr_t vs_write_hstatus(uintptr_t val) {
    asm volatile ("csrw 0x600, %0" :: "r"(val));  /* hstatus */
    return 0;
}

/* ===================================================================
 * Additional HLV/HSV width-variant trampolines.
 *
 * Each should trigger virtual-instruction exception when V=1.
 * =================================================================== */

uintptr_t vs_exec_hlv_b(uintptr_t arg) {
    uintptr_t v;
    /* hlv.b rd, (rs1): funct7=0x30, funct3=4 */
    asm volatile (".insn r 0x73, 0x4, 0x30, %0, %1, x0"
                  : "=r"(v) : "r"(arg));
    return v;
}

uintptr_t vs_exec_hlv_h(uintptr_t arg) {
    uintptr_t v;
    /* hlv.h rd, (rs1): funct7=0x32, funct3=4 */
    asm volatile (".insn r 0x73, 0x4, 0x32, %0, %1, x0"
                  : "=r"(v) : "r"(arg));
    return v;
}

uintptr_t vs_exec_hlv_d(uintptr_t arg) {
    uintptr_t v;
    /* hlv.d rd, (rs1): funct7=0x36, funct3=4 */
    asm volatile (".insn r 0x73, 0x4, 0x36, %0, %1, x0"
                  : "=r"(v) : "r"(arg));
    return v;
}

uintptr_t vs_exec_hlvx_bu(uintptr_t arg) {
    uintptr_t v;
    /* hlvx.bu rd, (rs1): funct7=0x30, funct3=4, rs2=3 */
    asm volatile (".insn r 0x73, 0x4, 0x30, %0, %1, x3"
                  : "=r"(v) : "r"(arg));
    return v;
}

uintptr_t vs_exec_hlvx_hu(uintptr_t arg) {
    uintptr_t v;
    /* hlvx.hu rd, (rs1): funct7=0x32, funct3=4, rs2=3 */
    asm volatile (".insn r 0x73, 0x4, 0x32, %0, %1, x3"
                  : "=r"(v) : "r"(arg));
    return v;
}

uintptr_t vs_exec_hsv_b(uintptr_t arg) {
    /* hsv.b rs2, (rs1): funct7=0x31, funct3=4 */
    asm volatile (".insn r 0x73, 0x4, 0x31, x0, %0, x0"
                  :: "r"(arg));
    return 0;
}

uintptr_t vs_exec_hsv_h(uintptr_t arg) {
    /* hsv.h rs2, (rs1): funct7=0x33, funct3=4 */
    asm volatile (".insn r 0x73, 0x4, 0x33, x0, %0, x0"
                  :: "r"(arg));
    return 0;
}

uintptr_t vs_exec_hsv_d(uintptr_t arg) {
    /* hsv.d rs2, (rs1): funct7=0x37, funct3=4 */
    asm volatile (".insn r 0x73, 0x4, 0x37, x0, %0, x0"
                  :: "r"(arg));
    return 0;
}

/* ===================================================================
 * Counter access trampolines.
 * =================================================================== */

uintptr_t vs_read_cycle(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, cycle" : "=r"(v));
    return v;
}

uintptr_t vs_read_time(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, time" : "=r"(v));
    return v;
}

uintptr_t vs_read_instret(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, instret" : "=r"(v));
    return v;
}

/* ===================================================================
 * U-mode HLV trampoline (for HU bit testing).
 *
 * Executed via run_in_priv(PRIV_U, ...) in V=0 U-mode.
 * With hstatus.HU=0 this triggers illegal-instruction (cause=2).
 * With hstatus.HU=1 the HLV.W executes (may fault on translation).
 * =================================================================== */

uintptr_t u_exec_hlv_w(uintptr_t addr) {
    uintptr_t v;
    /* hlv.w rd, (rs1): .insn r 0x73, 0x4, 0x34, rd, rs1, x0 */
    asm volatile (".insn r 0x73, 0x4, 0x34, %0, %1, x0"
                  : "=r"(v) : "r"(addr));
    return v;
}

/* ===================================================================
 * Delegation configuration helpers.
 * =================================================================== */

void setup_deleg_to_vs(uintptr_t exc_mask, uintptr_t int_mask) {
    /* First-level (M->HS) delegation via the M-safe primitive: medeleg/mideleg
     * are M-level and this helper is called from S(HS)-mode test context. */
    tsbi_deleg_or(exc_mask, int_mask);

    /* Second-level (HS->VS) via hedeleg/hideleg - HS-level, direct. */
    uintptr_t hedeleg = hedeleg_read();
    hedeleg |= exc_mask;
    hedeleg_write(hedeleg);

    uintptr_t hideleg = hideleg_read();
    hideleg |= int_mask;
    hideleg_write(hideleg);
}

void setup_deleg_to_hs(uintptr_t exc_mask) {
    /* Delegate from M to HS via medeleg only (M-safe primitive). */
    tsbi_deleg_or(exc_mask, 0);

    /* Clear hedeleg so trap stays at HS-mode. */
    uintptr_t hedeleg = hedeleg_read();
    hedeleg &= ~exc_mask;
    hedeleg_write(hedeleg);
}

void clear_all_deleg(void) {
    /* medeleg/mideleg are M-level; clear every delegatable bit via the M-safe
     * primitive (raises to M under S-mode-normal). */
    tsbi_deleg_clear((uintptr_t)-1, (uintptr_t)-1);
    hedeleg_write(0);
    hideleg_write(0);
}

/* G-stage fault helpers that depend on the __vm_test_region linker
 * region live in hyp_test_helpers_region.c (linked per suite). */

/* ===================================================================
 * Trap-value probe helpers (Group 15 TINST / Group 18 MTVAL).
 * =================================================================== */

/* .option norvc keeps the probe bodies free of compressed
 * instructions: the trapping instruction must be a deterministic
 * 32-bit ld/sd so its SPEC transformed value is unambiguous
 * (bits 1:0 = 11 in htinst/mtinst).
 * aligned(16): tests fetch the trapping instruction from mepc; a
 * 4-byte-aligned address avoids misaligned-fetch issues on strict
 * implementations and keeps the golden check simple. */
uintptr_t vs_load_probe(uintptr_t addr) __attribute__((naked, aligned(16)));
uintptr_t vs_load_probe(uintptr_t addr) {
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "ld a0, 0(a0)\n\t"
        ".option pop\n\t"
        "ret\n\t"
        ::: "memory"
    );
}

uintptr_t vs_store_probe(uintptr_t addr) __attribute__((naked, aligned(16)));
uintptr_t vs_store_probe(uintptr_t addr) {
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "sd zero, 0(a0)\n\t"
        ".option pop\n\t"
        "li a0, 0\n\t"
        "ret\n\t"
        ::: "memory"
    );
}

/* Compressed-load variant for TINST-08: exactly one 2-byte `c.lw`
 * (encoding 0x4108, `c.lw a0, 0(a0)`, equivalent to `lw a0, 0(a0)`)
 * against arg. The trapping instruction is compressed, so the SPEC
 * transformed value is derived from the UNCOMPRESSED equivalent with
 * bit 1 replaced by 0 (bits 1:0 = 01 mark a compressed source,
 * norm:H_trap_xtinst_exception). */
uintptr_t vs_load_probe_c(uintptr_t addr) __attribute__((naked, aligned(16)));
uintptr_t vs_load_probe_c(uintptr_t addr) {
    asm volatile (
        ".option push\n\t"
        ".option rvc\n\t"
        "c.lw a0, 0(a0)\n\t"
        ".option pop\n\t"
        "ret\n\t"
        ::: "memory"
    );
}

uintptr_t hyp_transform_mem_inst(uintptr_t inst, uintptr_t addr_offset)
{
    uintptr_t opcode = inst & 0x7FUL;
    uintptr_t off5   = (addr_offset & 0x1FUL) << 15;

    if (opcode == 0x03UL) {
        /* Basic load (LB..LD/FLW..FLQ): keep funct3/rd/opcode (bits
         * 14:0), zero the immediate (bits 31:20), rs1 field <-
         * Addr. Offset. */
        return (inst & 0x00007FFFUL) | off5;
    }
    if (opcode == 0x23UL) {
        /* Basic store (SB..SD/FSW..FSQ): keep rs2/funct3/opcode, zero
         * both immediate halves (bits 31:25 and 11:7), rs1 field <-
         * Addr. Offset. */
        return (inst & 0x01F0707FUL) | off5;
    }
    if (opcode == 0x2FUL) {
        /* Atomic (LR/SC/AMO): all fields kept except bits 19:15. */
        return (inst & ~(0x1FUL << 15)) | off5;
    }
    if (opcode == 0x73UL && ((inst >> 12) & 0x7UL) == 0x4UL &&
        (inst & (0x7FUL << 25)) != 0) {
        /* HLV/HLVX/HSV (SYSTEM opcode, funct3=4, nonzero funct7 —
         * distinguishes them from CSR instructions): all fields kept
         * except bits 19:15. */
        return (inst & ~(0x1FUL << 15)) | off5;
    }
    return 0;
}
