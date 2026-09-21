// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// parameters.c: extract the UDB parameters that M-mode code can measure and print them as the
// params section of a UDB configuration.
//
// Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
// with assistance from Claude.
//
// Each parameter is measured by reading or writing the CSR field that defines it, or by
// executing an instruction and looking at whether and how it trapped (the trap handler records
// mcause, mtval and mepc).  A parameter is printed only when the extension that defines it was
// detected, and only when the measurement is conclusive; the README lists the parameters that
// cannot be measured this way.

#include <stdbool.h>

#include "console.h"
#include "extensions.h"
#include "probe.h"

bool have(const char *name);            // feature_extractor.c

#define COUNT(a) (sizeof(a) / sizeof((a)[0]))
#define BIT(n) (1ul << (n))

// ---------------------------------------------------------------------------------------------
// Output helpers

static void param_bool(const char *name, bool v)
{
    printf("  %s: %s\n", name, v ? "true" : "false");
}

static void param_int(const char *name, unsigned long v)
{
    printf("  %s: %u\n", name, v);
}

static void param_str(const char *name, const char *v)
{
    printf("  %s: %s\n", name, v);
}

// A list of booleans from a bit mask, lowest bit first
static void param_bools(const char *name, unsigned long mask, unsigned count)
{
    printf("  %s: [", name);
    for (unsigned i = 0; i < count; i++)
        printf("%s%s", i ? ", " : "", (mask >> i) & 1 ? "true" : "false");
    printf("]\n");
}

static void param_ints(const char *name, const unsigned long *v, unsigned count)
{
    printf("  %s: [", name);
    for (unsigned i = 0; i < count; i++)
        printf("%s%u", i ? ", " : "", v[i]);
    printf("]\n");
}

static unsigned popcount(unsigned long v)
{
    unsigned n = 0;
    for (; v; v >>= 1)
        n += v & 1;
    return n;
}

static unsigned ctz(unsigned long v)
{
    unsigned n = 0;
    for (; v && !(v & 1); v >>= 1)
        n++;
    return n;
}

static int msb(unsigned long v)     // index of the highest set bit, -1 if none
{
    int n = -1;
    for (; v; v >>= 1)
        n++;
    return n;
}

// ---------------------------------------------------------------------------------------------
// CSR accessors.  *_wr writes, reads back and restores; *_rd reads; *_set writes and leaves the
// value in place, returning the read-back.  All return PROBE_TRAPPED when the CSR does not exist.

#define DEFINE_CSR_SET(name, csr)                                                           \
    static unsigned long name(unsigned long value)                                          \
    {                                                                                       \
        return PROBE_VALUE_IN("zicsr", "csrw " #csr ", %[in]\n\tcsrr a3, " #csr, value);    \
    }

DEFINE_CSR_READ(misa_rd, misa)
DEFINE_CSR_WRITE_READ(misa_wr, misa)
DEFINE_CSR_READ(mvendorid_rd, mvendorid)
DEFINE_CSR_READ(marchid_rd, marchid)
DEFINE_CSR_READ(mimpid_rd, mimpid)
DEFINE_CSR_READ(mconfigptr_rd, 0xF15)
DEFINE_CSR_READ(mstatus_rd, mstatus)
DEFINE_CSR_WRITE_READ(mstatus_wr, mstatus)
DEFINE_CSR_SET(mstatus_set, mstatus)
DEFINE_CSR_READ(mtvec_rd, mtvec)
DEFINE_CSR_SET(mtvec_set, mtvec)
DEFINE_CSR_WRITE_READ(stvec_wr, stvec)
DEFINE_CSR_WRITE_READ(vstvec_wr, vstvec)
DEFINE_CSR_WRITE_READ(mtval_wr, mtval)
DEFINE_CSR_WRITE_READ(stval_wr, stval)
DEFINE_CSR_READ(mcountinhibit_rd, mcountinhibit)
DEFINE_CSR_WRITE_READ(mcountinhibit_wr, mcountinhibit)
DEFINE_CSR_WRITE_READ(mcounteren_wr, mcounteren)
DEFINE_CSR_WRITE_READ(scounteren_wr, scounteren)
DEFINE_CSR_WRITE_READ(hcounteren_wr, hcounteren)
DEFINE_CSR_WRITE_READ(satp_wr, satp)
DEFINE_CSR_WRITE_READ(hgatp_wr, hgatp)
DEFINE_CSR_WRITE_READ(vsatp_wr, vsatp)
DEFINE_CSR_WRITE_READ(hgeie_wr, hgeie)
DEFINE_CSR_WRITE_READ(srmcfg_wr, 0x181)
DEFINE_CSR_READ(mcontext_rd, 0x7A8)
DEFINE_CSR_WRITE_READ(mcontext_wr, 0x7A8)
DEFINE_CSR_READ(hcontext_rd, 0x6A8)
DEFINE_CSR_WRITE_READ(scontext_wr, 0x5A8)
DEFINE_CSR_READ(time_rd, time)
DEFINE_CSR_WRITE_READ(mie_wr, mie)
DEFINE_CSR_WRITE_READ(jvt_wr, 0x017)
DEFINE_CSR_SET(pmpaddr0_set, pmpaddr0)
DEFINE_CSR_READ(pmpcfg0_rd, pmpcfg0)
DEFINE_CSR_SET(pmpcfg0_set, pmpcfg0)

// Indexed CSRs: pmpaddr0-63 and mhpmcounter3-31
#define IDX10(X, b) X(b##0) X(b##1) X(b##2) X(b##3) X(b##4) X(b##5) X(b##6) X(b##7) X(b##8) X(b##9)
#define IDX64(X) X(0) X(1) X(2) X(3) X(4) X(5) X(6) X(7) X(8) X(9) IDX10(X, 1) IDX10(X, 2) IDX10(X, 3) \
                 IDX10(X, 4) IDX10(X, 5) X(60) X(61) X(62) X(63)
#define PMPADDR_FN(n) DEFINE_CSR_WRITE_READ(pmpaddr##n##_wr, 0x3B0 + n)
#define PMPADDR_ENTRY(n) pmpaddr##n##_wr,
IDX64(PMPADDR_FN)
static unsigned long (*const pmpaddr_wr[64])(unsigned long) = { IDX64(PMPADDR_ENTRY) };

#define IDX3_31(X) X(3) X(4) X(5) X(6) X(7) X(8) X(9) IDX10(X, 1) IDX10(X, 2) X(30) X(31)
#define HPM_FN(n) DEFINE_CSR_WRITE_READ(mhpmcounter##n##_wr, 0xB00 + n)
#define HPM_ENTRY(n) mhpmcounter##n##_wr,
IDX3_31(HPM_FN)
static unsigned long (*const mhpmcounter_wr[29])(unsigned long) = { IDX3_31(HPM_ENTRY) };

// Set a bit, read it back and restore; and the same clearing the bit.  Both return the bit.
#define BIT_SET_READ(csr, mask)                                                             \
    "csrr t2, " #csr "\n\tli t1, " #mask "\n\tor a2, t2, t1\n\tcsrw " #csr ", a2\n\t"      \
    "csrr a3, " #csr "\n\tcsrw " #csr ", t2\n\tand a3, a3, t1"
#define BIT_CLEAR_READ(csr, mask)                                                           \
    "csrr t2, " #csr "\n\tli t1, " #mask "\n\tnot a2, t1\n\tand a2, t2, a2\n\t"            \
    "csrw " #csr ", a2\n\tcsrr a3, " #csr "\n\tcsrw " #csr ", t2\n\tand a3, a3, t1"

// The same for a bit of hstateen0/sstateen0, which is writable only while the same bit of
// mstateen0 is set: set the mstateen0 bit around the test and restore it afterwards
#define GATED_SET_READ(mst, hst, mask)                                                      \
    "csrr s0, " #mst "\n\tli t1, " #mask "\n\tor a2, s0, t1\n\tcsrw " #mst ", a2\n\t"      \
    BIT_SET_READ(hst, mask) "\n\tcsrw " #mst ", s0"
#define GATED_CLEAR_READ(mst, hst, mask)                                                    \
    "csrr s0, " #mst "\n\tli t1, " #mask "\n\tor a2, s0, t1\n\tcsrw " #mst ", a2\n\t"      \
    BIT_CLEAR_READ(hst, mask) "\n\tcsrw " #mst ", s0"

// ---------------------------------------------------------------------------------------------
// Measurements that several parameters share

// A field's legal values, from writing each candidate and reading back.  Uses *_wr(value) on a
// CSR whose current value is orig.
static unsigned legal_values(unsigned long (*wr)(unsigned long), unsigned long orig, unsigned shift,
                             unsigned long mask, const unsigned long *candidates, unsigned n,
                             unsigned long *out)
{
    unsigned found = 0;
    for (unsigned i = 0; i < n; i++) {
        unsigned long v = wr((orig & ~(mask << shift)) | (candidates[i] << shift));
        if (v != PROBE_TRAPPED && ((v >> shift) & mask) == candidates[i])
            out[found++] = candidates[i];
    }
    return found;
}

// "little", "big" or "dynamic" from whether an endianness bit can be set and cleared
static void endianness(const char *name, unsigned long set, unsigned long clear)
{
    if (set == PROBE_TRAPPED || clear == PROBE_TRAPPED)
        return;
    param_str(name, set && !clear ? "dynamic" : set ? "big" : "little");
}

// The set of XLENs a mode supports, from an XL field accepting 1 (32) and 2 (64)
static void xlen_list(const char *name, unsigned long accepts_32, unsigned long accepts_64)
{
    unsigned long v[2];
    unsigned n = 0;
    if (accepts_32 != PROBE_TRAPPED && accepts_32)
        v[n++] = 32;
    if (accepts_64 != PROBE_TRAPPED && accepts_64)
        v[n++] = 64;
    if (n)
        param_ints(name, v, n);
}

// "rw", "read-only-0" or "read-only-1" for a stateen-style enable bit
static void bit_type(const char *name, unsigned long set, unsigned long clear)
{
    if (set == PROBE_TRAPPED || clear == PROBE_TRAPPED)
        return;
    param_str(name, set && !clear ? "rw" : set ? "read-only-1" : "read-only-0");
}

// Trap-vector CSR parameters: modes, base alignment and behavior on an illegal write.  The base
// written is probe_scratch, which is aligned to PROBE_SCRATCH_SIZE, so alignments up to that can
// be seen.  set() must leave the value in place; the original is restored at the end.
static void tvec_params(const char *prefix_modes, const char *align_direct, const char *align_vectored,
                        const char *illegal, const char *access, unsigned long orig,
                        unsigned long (*set)(unsigned long))
{
    unsigned long base = (unsigned long)probe_scratch;
    unsigned long modes[2], nmodes = 0;
    if (access) {
        unsigned long v = set(base);
        param_str(access, v == base ? "rw" : "ro");
        if (v != base) {
            set(orig);
            return;
        }
    }
    for (unsigned long m = 0; m < 2; m++) {
        unsigned long v = set(base | m);
        if ((v & 3) == m)
            modes[nmodes++] = m;
        const char *align = m ? align_vectored : align_direct;
        if ((v & 3) == m && align) {
            unsigned long low = set((base | (PROBE_SCRATCH_SIZE - 4)) | m) & (PROBE_SCRATCH_SIZE - 4);
            param_int(align, low ? BIT(ctz(low)) : PROBE_SCRATCH_SIZE);
        }
    }
    if (nmodes)
        param_ints(prefix_modes, modes, nmodes);
    if (illegal) {
        unsigned long before = set(base | modes[nmodes ? nmodes - 1 : 0]);
        unsigned long v = set(base | 2);            // MODE = 2 is reserved
        param_str(illegal, v == before ? "retain" : "custom");
    }
    set(orig);
}

// Whether writing mode leaves a translation CSR reading back mode
static bool atp_accepts(unsigned long (*wr)(unsigned long), unsigned long mode)
{
    return wr(mode) == mode;
}

// Whether Bare can be written after mode was
#define DEFINE_BARE_AFTER(name, csr)                                                        \
    static bool name(unsigned long mode)                                                    \
    {                                                                                       \
        unsigned long v = PROBE_VALUE_IN("zicsr", "csrw " #csr ", %[in]\n\tcsrw " #csr ", zero\n\t" \
                                                  "csrr a3, " #csr "\n\tseqz a3, a3", mode); \
        return v != PROBE_TRAPPED && v != 0;                                                \
    }
DEFINE_BARE_AFTER(satp_bare_after, satp)
DEFINE_BARE_AFTER(hgatp_bare_after, hgatp)
DEFINE_BARE_AFTER(vsatp_bare_after, vsatp)

#if __riscv_xlen == 64
#define ATP_MODE(m) ((unsigned long)(m) << 60)
#define ATP_MODE_MASK ATP_MODE(0xF)
static const struct { const char *sv; unsigned long mode; } atp_modes[] =
    { { "SV39", 8 }, { "SV48", 9 }, { "SV57", 10 } };
#else
#define ATP_MODE(m) ((unsigned long)(m) << 31)
#define ATP_MODE_MASK ATP_MODE(1)
static const struct { const char *sv; unsigned long mode; } atp_modes[] = { { "SV32", 1 } };
#endif

// ---------------------------------------------------------------------------------------------
// Probes run in U-, S- or VS-mode.  The mode is entered with mret into a stub that executes one
// instruction and then an ecall; the ecall (or the trap the instruction takes, when it is not
// delegated) comes back to the M-mode handler, which resumes the probe.  When the instruction's
// trap is delegated, s_trap_handler in start.S records it in s_cause, s_tval and s_epc and
// returns with its own ecall.

volatile unsigned long s_cause, s_tval, s_epc;   // written by s_trap_handler
volatile unsigned long s_htval, s_htinst;        // written by hs_trap_handler
extern char s_trap_handler[], hs_trap_handler[];
volatile unsigned long lower_stub;               // address the mret enters
volatile unsigned long fault_va;                 // address the page-fault stubs touch

#define DEFINE_STUB(name, arch, insn)                                                       \
    __asm__(".text\n.balign 4\n.globl " #name "\n" #name ":\n\t.option push\n\t.option arch, +" arch \
            "\n\t" insn "\n\t.option pop\n\t.balign 4\n\tecall\n1:\tj 1b");                       \
    extern char name[];
DEFINE_STUB(ecall_stub, "zicsr", "ecall\n\tebreak")     // ecall, then ebreak in case it did not trap
DEFINE_STUB(stub_illegal, "zicsr", ".word 0x00004073")
DEFINE_STUB(stub_ebreak, "zicsr", "ebreak")
DEFINE_STUB(stub_lw_misaligned, "zicsr", "lw t1, 1(a1)")
DEFINE_STUB(stub_sw_misaligned, "zicsr", "sw t1, 1(a1)")
DEFINE_STUB(stub_jump_misaligned, "zicsr", "jalr zero, 2(a1)")
DEFINE_STUB(stub_lw_scratch, "zicsr", "lw t1, 0(a1)")
DEFINE_STUB(stub_sw_scratch, "zicsr", "sw t1, 0(a1)")
DEFINE_STUB(stub_jump_scratch, "zicsr", "jalr zero, 0(a1)")
#if __riscv_xlen == 64
#define LOAD_FAULT_VA "la a2, fault_va\n\tld a2, 0(a2)\n\t"
#else
#define LOAD_FAULT_VA "la a2, fault_va\n\tlw a2, 0(a2)\n\t"
#endif
DEFINE_STUB(stub_load_fault_va, "zicsr", LOAD_FAULT_VA "lw t1, 0(a2)")
DEFINE_STUB(stub_store_fault_va, "zicsr", LOAD_FAULT_VA "sw t1, 0(a2)")
DEFINE_STUB(stub_jump_fault_va, "zicsr", LOAD_FAULT_VA "jalr zero, 0(a2)")

#if __riscv_xlen == 64
#define LREG_ASM "ld"
#else
#define LREG_ASM "lw"
#endif

// Enter privilege mode mpp (0 = U, 1 = S; with virt, VS) at stub and return the cause of the
// trap that ended it: s_cause if the lower-mode handler took it, else the cause the M-mode handler
// saw (CAUSE_ECALL_S or _U, or CAUSE_ECALL_VS = 10, when the stub ran to its ecall)
#define CAUSE_ECALL_VS 10
static unsigned long run_in_mode(char *stub, unsigned long mpp, bool virt, unsigned long mstatus)
{
    s_cause = CAUSE_NONE;
    lower_stub = (unsigned long)stub;
    unsigned long ms = (mstatus & ~(3ul << 11)) | (mpp << 11);
#if __riscv_xlen == 64
    if (virt)
        ms |= 1ul << 39;                                // MPV
#else
    if (virt)
        PROBE("zicsr", "li t1, 1 << 7\n\tcsrs mstatush, t1");
#endif
    PROBE_VALUE_IN("zicsr", "csrw mstatus, %[in]\n\tla a2, lower_stub\n\t" LREG_ASM " a2, 0(a2)\n\t"
                            "csrw mepc, a2\n\tmret\n\tli a3, 0", ms);
#if __riscv_xlen == 32
    if (virt)
        PROBE("zicsr", "li t1, 1 << 7\n\tcsrc mstatush, t1");
#endif
    return s_cause != CAUSE_NONE ? s_cause : probe_cause;
}

DEFINE_CSR_SET(medeleg_set, medeleg)
DEFINE_CSR_SET(hedeleg_set, hedeleg)
DEFINE_CSR_SET(stvec_set, stvec)
DEFINE_CSR_SET(vstvec_set, vstvec)
DEFINE_CSR_SET(satp_set, satp)
DEFINE_CSR_SET(vsatp_set, vsatp)
DEFINE_CSR_SET(hgatp_set, hgatp)
DEFINE_CSR_SET(pmpaddr1_set, pmpaddr1)
DEFINE_CSR_READ(stvec_rd, stvec)
DEFINE_CSR_READ(vstvec_rd, vstvec)

// Exceptions delegated to the lower mode: everything but the ecalls, which must reach M-mode.
// The guest-page-fault bits (20, 21, 23) only exist with H and are ignored otherwise.
#define PAGE_FAULTS ((1ul << 12) | (1ul << 13) | (1ul << 15))
#define GUEST_PAGE_FAULTS ((1ul << 20) | (1ul << 21) | (1ul << 23))
#define DELEGATED ((1ul << 0) | (1ul << 1) | (1ul << 2) | (1ul << 3) | (1ul << 4) | (1ul << 5) |   \
                   (1ul << 6) | (1ul << 7) | PAGE_FAULTS | GUEST_PAGE_FAULTS)

// PMP entry 0 grants everything to the lower modes ...
static void pmp_open(unsigned num_pmp)
{
    if (num_pmp) {
        pmpaddr0_set(~0ul);
        pmpcfg0_set((pmpcfg0_rd() & ~0xFFFFul) | 0x0F);    // entry 0 TOR R W X, entry 1 off
        pmpaddr1_set(0);
    }
}

// ... or entry 0 denies the scratch page and entry 1 grants everything else.  Entry 1 is a NAPOT
// region of all ones, which covers the whole address space; TOR would start at entry 0's address.
static void pmp_deny_scratch(void)
{
    pmpaddr0_set(((unsigned long)probe_scratch >> 2) | (PROBE_SCRATCH_SIZE / 8 - 1));  // NAPOT
    pmpaddr1_set(~0ul);
    pmpcfg0_set((pmpcfg0_rd() & ~0xFFFFul) | (0x1F << 8) | 0x18);
}

static void pmp_close(unsigned num_pmp)
{
    if (num_pmp) {
        pmpcfg0_set(pmpcfg0_rd() & ~0xFFFFul);
        pmpaddr0_set(0);
        pmpaddr1_set(0);
    }
}

static void concat(char *out, const char *a, const char *b, const char *c)
{
    for (; *a; a++) *out++ = *a;
    for (; *b; b++) *out++ = *b;
    for (; *c; c++) *out++ = *c;
    *out = '\0';
}

// A one-level page table in probe_scratch: the entry for the region holding the program maps it
// to itself, every other entry is invalid, so an access to fault_va (another region) page-faults
// while the stubs and handlers keep running.  For a G-stage table the leaf carries the U bit and
// the root is 16 KiB, which is why probe_scratch is that size.  Uses the first translation mode
// the CSR accepts; returns false if it accepts none.
// hfence.vvma zero, zero and hfence.gvma zero, zero; the assembler will not enable H on an E base
#define HFENCE_VVMA ".insn r 0x73, 0, 0x11, x0, x0, x0"
#define HFENCE_GVMA ".insn r 0x73, 0, 0x31, x0, x0, x0"
#define PTE_LEAF 0xCF          // V R W X A D
#define PTE_U 0x10
static const struct { unsigned long mode; unsigned shift; } atp_levels[] = {
#if __riscv_xlen == 64
    { 8, 30 }, { 9, 39 }, { 10, 48 }
#else
    { 1, 22 }
#endif
};

static bool build_page_table(unsigned long (*wr)(unsigned long), bool gstage, unsigned long *atp,
                             unsigned long *fault)
{
    for (unsigned i = 0; i < COUNT(atp_levels); i++) {
        if (!atp_accepts(wr, ATP_MODE(atp_levels[i].mode)))
            continue;
        unsigned shift = atp_levels[i].shift;
        unsigned long base = (unsigned long)probe_scratch;
        unsigned long idx = base >> shift, fault_idx = idx == 1 ? 2 : 1;
        volatile unsigned long *table = (volatile unsigned long *)probe_scratch;
        for (unsigned j = 0; j < PROBE_SCRATCH_SIZE / sizeof(unsigned long); j++)
            table[j] = 0;
        table[idx] = ((((idx << shift) >> 12)) << 10) | PTE_LEAF | (gstage ? PTE_U : 0);
        *atp = ATP_MODE(atp_levels[i].mode) | (base >> 12);
        *fault = fault_idx << shift;
        return true;
    }
    return false;
}

// The REPORT_VA_IN_<tval>_ON_*_PAGE_FAULT parameters for the mode entered with mpp/virt.  When the
// faults are delegated the lower mode's handler records them, otherwise the M-mode handler does.
static void page_fault_params(const char *tval, bool virt, bool delegated, unsigned long mstatus)
{
    static const struct { int stub; unsigned long cause; const char *suffix; } faults[] = {
        { 0, 13, "_ON_LOAD_PAGE_FAULT" }, { 1, 15, "_ON_STORE_AMO_PAGE_FAULT" }, { 2, 12, "_ON_INSTRUCTION_PAGE_FAULT" },
    };
    char *const stubs[] = { stub_load_fault_va, stub_store_fault_va, stub_jump_fault_va };
    char name[80];
    for (unsigned i = 0; i < COUNT(faults); i++) {
        unsigned long cause = run_in_mode(stubs[faults[i].stub], 1, virt, mstatus);
        if (cause != faults[i].cause)
            continue;
        concat(name, "REPORT_VA_IN_", tval, faults[i].suffix);
        param_bool(name, (delegated ? s_tval : probe_tval) == fault_va);
    }
}

// After a guest page fault: the GPA >> 2 the trap reported, from htval if the HS-mode handler
// took it, else from mtval2, which still holds it since nothing has trapped into M-mode since
static unsigned long guest_pa(void)
{
    return s_cause != CAUSE_NONE ? s_htval : PROBE_VALUE("zicsr", "csrr a3, mtval2");
}

// U-mode or S-mode ecall
static void ecall_from(const char *name, unsigned long mpp, bool virt, unsigned long mstatus)
{
    unsigned long cause = run_in_mode(ecall_stub, mpp, virt, mstatus);
    if (cause == (virt ? CAUSE_ECALL_VS : mpp ? CAUSE_ECALL_S : CAUSE_ECALL_U))
        param_bool(name, true);
    else if (cause == CAUSE_BREAKPOINT)           // the ecall did not trap, the ebreak after it did
        param_bool(name, false);
}

// The REPORT_*_IN_STVAL_ON_* (or VSTVAL) parameters: take each trap in S-mode (VS-mode) and
// compare what the mode's tval register holds with what the parameter says it should
static void lower_mode_tval_params(const char *tval, bool virt, unsigned usable_pmp, unsigned long mstatus)
{
    char name[80];
    unsigned long scratch = (unsigned long)probe_scratch, cause;
    unsigned long mpp = 1;

    cause = run_in_mode(stub_illegal, mpp, virt, mstatus);
    if (cause == CAUSE_ILLEGAL_INSTRUCTION) {
        concat(name, "REPORT_ENCODING_IN_", tval, "_ON_ILLEGAL_INSTRUCTION");
        param_bool(name, s_tval == 0x00004073);
    }
    cause = run_in_mode(stub_ebreak, mpp, virt, mstatus);
    if (cause == CAUSE_BREAKPOINT) {
        concat(name, "REPORT_VA_IN_", tval, "_ON_BREAKPOINT");
        param_bool(name, s_tval == s_epc);
    }
    cause = run_in_mode(stub_lw_misaligned, mpp, virt, mstatus);
    if (cause == CAUSE_LOAD_MISALIGNED) {
        concat(name, "REPORT_VA_IN_", tval, "_ON_LOAD_MISALIGNED");
        param_bool(name, s_tval == scratch + 1);
    }
    cause = run_in_mode(stub_sw_misaligned, mpp, virt, mstatus);
    if (cause == CAUSE_STORE_MISALIGNED) {
        concat(name, "REPORT_VA_IN_", tval, "_ON_STORE_AMO_MISALIGNED");
        param_bool(name, s_tval == scratch + 1);
    }
    if (!have("Zca")) {
        cause = run_in_mode(stub_jump_misaligned, mpp, virt, mstatus);
        if (cause == CAUSE_INSTRUCTION_MISALIGNED) {
            concat(name, "REPORT_VA_IN_", tval, "_ON_INSTRUCTION_MISALIGNED");
            param_bool(name, s_tval == scratch + 2);
        }
    }
    if (usable_pmp >= 2) {
        pmp_deny_scratch();
        cause = run_in_mode(stub_lw_scratch, mpp, virt, mstatus);
        if (cause == CAUSE_LOAD_ACCESS_FAULT) {
            concat(name, "REPORT_VA_IN_", tval, "_ON_LOAD_ACCESS_FAULT");
            param_bool(name, s_tval == scratch);
        }
        cause = run_in_mode(stub_sw_scratch, mpp, virt, mstatus);
        if (cause == CAUSE_STORE_ACCESS_FAULT) {
            concat(name, "REPORT_VA_IN_", tval, "_ON_STORE_AMO_ACCESS_FAULT");
            param_bool(name, s_tval == scratch);
        }
        cause = run_in_mode(stub_jump_scratch, mpp, virt, mstatus);
        if (cause == CAUSE_INSTRUCTION_ACCESS_FAULT) {
            concat(name, "REPORT_VA_IN_", tval, "_ON_INSTRUCTION_ACCESS_FAULT");
            param_bool(name, s_tval == scratch);
        }
        pmp_open(2);
    }
}

// ---------------------------------------------------------------------------------------------

void print_parameters(unsigned long vlen)
{
    bool has_s = have("S"), has_u = have("U"), has_h = have("H");
    unsigned long v;

    printf("params:\n");
    param_int("MXLEN", __riscv_xlen);

    // Identification CSRs
    v = mvendorid_rd();
    if (v != PROBE_TRAPPED) {
        param_int("VENDOR_ID_BANK", v >> 7);
        param_int("VENDOR_ID_OFFSET", v & 0x7F);
    }
    v = marchid_rd();
    if (v != PROBE_TRAPPED) {
        param_bool("MARCHID_IMPLEMENTED", v != 0);
        if (v)
            param_int("ARCH_ID_VALUE", v);
    }
    v = mimpid_rd();
    if (v != PROBE_TRAPPED) {
        param_bool("MIMPID_IMPLEMENTED", v != 0);
        if (v)
            param_int("IMP_ID_VALUE", v);
    }
    v = mconfigptr_rd();
    if (v != PROBE_TRAPPED)
        param_int("CONFIG_PTR_ADDRESS", v);

    // misa and which of its extension bits can be cleared
    unsigned long misa = misa_rd();
    if (misa != PROBE_TRAPPED) {
        param_bool("MISA_CSR_IMPLEMENTED", misa != 0);
        static const struct { char letter; const char *param; } mutable_misa[] = {
            { 'A', "MUTABLE_MISA_A" }, { 'B', "MUTABLE_MISA_B" }, { 'C', "MUTABLE_MISA_C" },
            { 'D', "MUTABLE_MISA_D" }, { 'F', "MUTABLE_MISA_F" }, { 'H', "MUTABLE_MISA_H" },
            { 'M', "MUTABLE_MISA_M" }, { 'Q', "MUTABLE_MISA_Q" }, { 'S', "MUTABLE_MISA_S" },
            { 'U', "MUTABLE_MISA_U" }, { 'V', "MUTABLE_MISA_V" },
        };
        for (unsigned i = 0; i < COUNT(mutable_misa); i++) {
            unsigned long bit = BIT(mutable_misa[i].letter - 'A');
            if (misa & bit)
                param_bool(mutable_misa[i].param, !(misa_wr(misa & ~bit) & bit));
        }
    }

    // mstatus: FS and VS legal values, endianness, XLEN choices
    unsigned long mstatus = mstatus_rd();
    static const unsigned long four[] = { 0, 1, 2, 3 };
    unsigned long legal[4];
    unsigned n;
    if (have("F") || has_s) {
        n = legal_values(mstatus_wr, mstatus, 13, 3, four, 4, legal);
        param_ints("MSTATUS_FS_LEGAL_VALUES", legal, n);
    }
    if (vlen || has_s) {
        n = legal_values(mstatus_wr, mstatus, 9, 3, four, 4, legal);
        param_ints("MSTATUS_VS_LEGAL_VALUES", legal, n);
    }
    if (have("F")) {
        // Hardware FS update: put FS in Initial, execute an FP instruction, see if it is Dirty
        v = PROBE_VALUE("f", "csrr t2, mstatus\n\tli t1, 3 << 13\n\tnot a2, t1\n\tand a2, t2, a2\n\t"
                             "li t1, 1 << 13\n\tor a2, a2, t1\n\tcsrw mstatus, a2\n\t"
                             "fadd.s ft0, ft2, ft4\n\tcsrr a3, mstatus\n\tcsrw mstatus, t2\n\t"
                             "srli a3, a3, 13\n\tandi a3, a3, 3");
        if (v != PROBE_TRAPPED)
            param_str("HW_MSTATUS_FS_DIRTY_UPDATE", v == 3 ? "precise" : "never");
    }
    if (vlen) {
        v = PROBE_VALUE("zve32x", "csrr t2, mstatus\n\tli t1, 3 << 9\n\tnot a2, t1\n\tand a2, t2, a2\n\t"
                                  "li t1, 1 << 9\n\tor a2, a2, t1\n\tcsrw mstatus, a2\n\t"
                                  "vsetivli x0, 1, e32, m1, ta, ma\n\tvadd.vv v1, v2, v3\n\t"
                                  "csrr a3, mstatus\n\tcsrw mstatus, t2\n\tsrli a3, a3, 9\n\tandi a3, a3, 3");
        if (v != PROBE_TRAPPED)
            param_str("HW_MSTATUS_VS_DIRTY_UPDATE", v == 3 ? "precise" : "never");
    }
#if __riscv_xlen == 64
    endianness("M_MODE_ENDIANNESS", PROBE_VALUE("zicsr", BIT_SET_READ(mstatus, 1 << 37)),
               PROBE_VALUE("zicsr", BIT_CLEAR_READ(mstatus, 1 << 37)));
    if (has_s) {
        endianness("S_MODE_ENDIANNESS", PROBE_VALUE("zicsr", BIT_SET_READ(mstatus, 1 << 36)),
                   PROBE_VALUE("zicsr", BIT_CLEAR_READ(mstatus, 1 << 36)));
        xlen_list("SXLEN", PROBE_VALUE("zicsr", CSR_FIELD(mstatus, 3 << 34, 1 << 34)),
                  PROBE_VALUE("zicsr", CSR_FIELD(mstatus, 3 << 34, 2 << 34)));
    }
    if (has_u)
        xlen_list("UXLEN", PROBE_VALUE("zicsr", CSR_FIELD(mstatus, 3 << 32, 1 << 32)),
                  PROBE_VALUE("zicsr", CSR_FIELD(mstatus, 3 << 32, 2 << 32)));
    if (has_h) {
        xlen_list("VSXLEN", PROBE_VALUE("zicsr", CSR_FIELD(hstatus, 3 << 32, 1 << 32)),
                  PROBE_VALUE("zicsr", CSR_FIELD(hstatus, 3 << 32, 2 << 32)));
        xlen_list("VUXLEN", PROBE_VALUE("zicsr", CSR_FIELD(vsstatus, 3 << 32, 1 << 32)),
                  PROBE_VALUE("zicsr", CSR_FIELD(vsstatus, 3 << 32, 2 << 32)));
    }
#else
    endianness("M_MODE_ENDIANNESS", PROBE_VALUE("zicsr", BIT_SET_READ(mstatush, 1 << 5)),
               PROBE_VALUE("zicsr", BIT_CLEAR_READ(mstatush, 1 << 5)));
    if (has_s) {
        endianness("S_MODE_ENDIANNESS", PROBE_VALUE("zicsr", BIT_SET_READ(mstatush, 1 << 4)),
                   PROBE_VALUE("zicsr", BIT_CLEAR_READ(mstatush, 1 << 4)));
        static const unsigned long thirty_two[] = { 32 };
        param_ints("SXLEN", thirty_two, 1);
        if (has_u)
            param_ints("UXLEN", thirty_two, 1);
        if (has_h) {
            param_ints("VSXLEN", thirty_two, 1);
            param_ints("VUXLEN", thirty_two, 1);
        }
    }
#endif
    if (has_u)
        endianness("U_MODE_ENDIANNESS", PROBE_VALUE("zicsr", BIT_SET_READ(mstatus, 1 << 6)),
                   PROBE_VALUE("zicsr", BIT_CLEAR_READ(mstatus, 1 << 6)));
    if (has_h) {
        endianness("VS_MODE_ENDIANNESS", PROBE_VALUE("zicsr", BIT_SET_READ(hstatus, 1 << 5)),
                   PROBE_VALUE("zicsr", BIT_CLEAR_READ(hstatus, 1 << 5)));
        endianness("VU_MODE_ENDIANNESS", PROBE_VALUE("zicsr", BIT_SET_READ(vsstatus, 1 << 6)),
                   PROBE_VALUE("zicsr", BIT_CLEAR_READ(vsstatus, 1 << 6)));
    }

    // Trap vectors and trap values
    tvec_params("MTVEC_MODES", "MTVEC_BASE_ALIGNMENT_DIRECT", "MTVEC_BASE_ALIGNMENT_VECTORED",
                "MTVEC_ILLEGAL_WRITE_BEHAVIOR", "MTVEC_ACCESS", mtvec_rd(), mtvec_set);
    v = mtval_wr(~0ul);
    if (PROBE_OK())
        param_int("MTVAL_WIDTH", popcount(v));
    if (has_s) {
        unsigned long modes[2], nmodes = 0;
        unsigned long base = (unsigned long)probe_scratch;
        for (unsigned long m = 0; m < 2; m++) {
            v = stvec_wr(base | m);
            if (v != PROBE_TRAPPED && (v & 3) == m)
                modes[nmodes++] = m;
        }
        if (nmodes)
            param_ints("STVEC_MODES", modes, nmodes);
        v = stvec_wr((base | (PROBE_SCRATCH_SIZE - 4)) | 1);
        if (v != PROBE_TRAPPED && (v & 3) == 1) {
            unsigned long low = v & (PROBE_SCRATCH_SIZE - 4);
            param_int("STVEC_BASE_ALIGNMENT_VECTORED", low ? BIT(ctz(low)) : PROBE_SCRATCH_SIZE);
        }
        v = stval_wr(~0ul);
        if (PROBE_OK())
            param_int("STVAL_WIDTH", popcount(v));
    }
    if (has_h) {
        unsigned long modes[2], nmodes = 0;
        unsigned long base = (unsigned long)probe_scratch;
        for (unsigned long m = 0; m < 2; m++) {
            v = vstvec_wr(base | m);
            if (v != PROBE_TRAPPED && (v & 3) == m)
                modes[nmodes++] = m;
        }
        if (nmodes)
            param_ints("VSTVEC_MODES", modes, nmodes);
    }

    // Interrupts: an interrupt is implemented when its mie bit is writable
    v = mie_wr(~0ul);
    if (PROBE_OK()) {
        param_bool("MEI_INTR_IMPL", (v >> 11) & 1);
        param_bool("MSI_INTR_IMPL", (v >> 3) & 1);
        param_bool("MTI_INTR_IMPL", (v >> 7) & 1);
        if (has_s) {
            param_bool("SEI_INTR_IMPL", (v >> 9) & 1);
            param_bool("SSI_INTR_IMPL", (v >> 1) & 1);
            param_bool("STI_INTR_IMPL", (v >> 5) & 1);
        }
        if (has_h) {
            param_bool("VSEI_INTR_IMPL", (v >> 10) & 1);
            param_bool("VSSI_INTR_IMPL", (v >> 2) & 1);
            param_bool("VSTI_INTR_IMPL", (v >> 6) & 1);
        }
    }

    // Zcmt: the jvt CSR
    if (have("Zcmt")) {
        unsigned long jvt = jvt_wr(0);              // *_wr restores, so this reads the original
        v = jvt_wr(~0ul & ~0x3Ful);                 // BASE all ones, MODE 0
        if (PROBE_OK()) {
            param_bool("JVT_READ_ONLY", v == jvt);
            if (v != jvt) {
                param_str("JVT_BASE_TYPE", "mask");
                param_int("JVT_BASE_MASK", v & ~0x3Ful);
            }
        }
    }

    // Counters
    if (have("Zicntr"))
        param_bool("TIME_CSR_IMPLEMENTED", time_rd() != PROBE_TRAPPED);
    unsigned long hpm = 0;
    for (unsigned i = 0; i < COUNT(mhpmcounter_wr); i++) {
        v = mhpmcounter_wr[i](1);
        if (v != PROBE_TRAPPED && v != 0)
            hpm |= BIT(i + 3);
    }
    param_bools("HPM_COUNTER_EN", hpm, 32);
    bool inhibit = mcountinhibit_rd() != PROBE_TRAPPED;
    param_bool("MCOUNTINHIBIT_IMPLEMENTED", inhibit);
    if (inhibit)
        param_bools("COUNTINHIBIT_EN", mcountinhibit_wr(~0ul), 32);
    v = mcounteren_wr(~0ul);
    param_bools("MCOUNTENABLE_EN", PROBE_OK() ? v : 0, 32);
    if (has_s) {
        v = scounteren_wr(~0ul);
        if (PROBE_OK())
            param_bools("SCOUNTENABLE_EN", v, 32);
    }
    if (has_h) {
        v = hcounteren_wr(~0ul);
        if (PROBE_OK())
            param_bools("HCOUNTENABLE_EN", v, 32);
    }

    // PMP: entries that exist, entries that are writable, granularity, address widths
    unsigned num_pmp = 0, usable_pmp = 0;
    for (unsigned i = 0; i < 64; i++) {
        v = pmpaddr_wr[i](~0ul);
        if (!PROBE_OK())
            break;
        num_pmp = i + 1;
        if (v != 0 && usable_pmp == i)
            usable_pmp = i + 1;
    }
    param_int("NUM_PMP_ENTRIES", num_pmp);
    if (num_pmp) {
        param_int("NUM_USABLE_PMP_ENTRIES", usable_pmp);
        if (usable_pmp) {
            unsigned long cfg0 = pmpcfg0_rd();
            bool na4 = false, napot, tor;
            if (!(cfg0 & 0x80)) {                       // entry 0 not locked: its A field is writable
                pmpcfg0_set(cfg0 & ~0xFFul);           // A = OFF for the granularity read
                unsigned long ones = pmpaddr_wr[0](~0ul);
                param_int("PHYS_ADDR_WIDTH", msb(ones) + 3);
                na4 = ((pmpcfg0_set((cfg0 & ~0xFFul) | 0x10) >> 3) & 3) == 2;
                napot = ((pmpcfg0_set((cfg0 & ~0xFFul) | 0x18) >> 3) & 3) == 3;
                tor = ((pmpcfg0_set((cfg0 & ~0xFFul) | 0x08) >> 3) & 3) == 1;
                pmpcfg0_set(cfg0);
                param_bool("PMP_NA4_SUPPORTED", na4);
                param_bool("PMP_NAPOT_SUPPORTED", napot);
                param_bool("PMP_TOR_SUPPORTED", tor);
                // With A = OFF, pmpaddr bits [G-2:0] read as zero; if bit 0 reads as one, G is 0
                // when NA4 is supported and 1 otherwise
                param_int("PMP_GRANULARITY", ones & 1 ? (na4 ? 0 : 1) : ctz(ones) + 2);
            }
        }
    }

    // Misaligned accesses, and what the trap values report
    unsigned long scratch = (unsigned long)probe_scratch;
    probe_cause = CAUSE_NONE;
    bool lw_ok = PROBE("zicsr", "lw t1, 1(a1)");
    param_bool("MISALIGNED_LDST", lw_ok);
    if (!lw_ok && probe_cause == CAUSE_LOAD_MISALIGNED)
        param_bool("REPORT_VA_IN_MTVAL_ON_LOAD_MISALIGNED", probe_tval == scratch + 1);
    probe_cause = CAUSE_NONE;
    bool sw_ok = PROBE("zicsr", "sw t1, 1(a1)");
    if (!sw_ok && probe_cause == CAUSE_STORE_MISALIGNED)
        param_bool("REPORT_VA_IN_MTVAL_ON_STORE_AMO_MISALIGNED", probe_tval == scratch + 1);
    if (have("Zaamo")) {
        probe_cause = CAUSE_NONE;
        bool amo_ok = PROBE("zaamo", "addi a2, a1, 2\n\tamoadd.w t1, t2, (a2)");
        param_bool("MISALIGNED_AMO", amo_ok);
        if (sw_ok && !amo_ok && probe_cause == CAUSE_STORE_MISALIGNED)
            param_bool("REPORT_VA_IN_MTVAL_ON_STORE_AMO_MISALIGNED", probe_tval == scratch + 2);
        if (!amo_ok && have("Zalrsc")) {
            probe_cause = CAUSE_NONE;
            if (!PROBE("zalrsc", "addi a2, a1, 2\n\tlr.w t1, (a2)\n\tsc.w t2, t1, (a2)")) {
                if (probe_cause == CAUSE_LOAD_MISALIGNED)
                    param_str("LRSC_MISALIGNED_BEHAVIOR", "always raise misaligned exception");
                else if (probe_cause == CAUSE_LOAD_ACCESS_FAULT)
                    param_str("LRSC_MISALIGNED_BEHAVIOR", "always raise access fault");
            }
        }
    }
    if (!have("Zca")) {
        // Without C, a jump to a 2-byte-aligned address must trap; the resume address is restored
        // by the trap handler, so the jump never lands
        probe_cause = CAUSE_NONE;
        if (!PROBE("zicsr", "jalr zero, 2(a1)") && probe_cause == CAUSE_INSTRUCTION_MISALIGNED)
            param_bool("REPORT_VA_IN_MTVAL_ON_INSTRUCTION_MISALIGNED", probe_tval == scratch + 2);
    }
    if (has_u && num_pmp) {
        // With MPRV set and MPP = U, loads and stores use U-mode permissions, and with no PMP
        // entry matching they fault; the trap handler clears MPRV
        probe_cause = CAUSE_NONE;
        bool ok = PROBE("zicsr", "csrr t2, mstatus\n\tli t1, 3 << 11\n\tnot a2, t1\n\tand a2, t2, a2\n\t"
                                 "li t1, 1 << 17\n\tor a2, a2, t1\n\tcsrw mstatus, a2\n\t"
                                 "lw t1, 0(a1)\n\tcsrw mstatus, t2");
        if (!ok && probe_cause == CAUSE_LOAD_ACCESS_FAULT)
            param_bool("REPORT_VA_IN_MTVAL_ON_LOAD_ACCESS_FAULT", probe_tval == scratch);
        probe_cause = CAUSE_NONE;
        ok = PROBE("zicsr", "csrr t2, mstatus\n\tli t1, 3 << 11\n\tnot a2, t1\n\tand a2, t2, a2\n\t"
                            "li t1, 1 << 17\n\tor a2, a2, t1\n\tcsrw mstatus, a2\n\t"
                            "sw t1, 0(a1)\n\tcsrw mstatus, t2");
        if (!ok && probe_cause == CAUSE_STORE_ACCESS_FAULT)
            param_bool("REPORT_VA_IN_MTVAL_ON_STORE_AMO_ACCESS_FAULT", probe_tval == scratch);
        mstatus_set(mstatus);                       // MPP back to M in case a probe left it at U
    }

    // Traps on ebreak, ecall, reserved instructions and unimplemented CSRs
    probe_cause = CAUSE_NONE;
    bool ebreak_traps = !PROBE("zicsr", "ebreak");
    param_bool("TRAP_ON_EBREAK", ebreak_traps && probe_cause == CAUSE_BREAKPOINT);
    if (ebreak_traps && probe_cause == CAUSE_BREAKPOINT)
        param_bool("REPORT_VA_IN_MTVAL_ON_BREAKPOINT", probe_tval == probe_epc);
    probe_cause = CAUSE_NONE;
    param_bool("TRAP_ON_ECALL_FROM_M", !PROBE("zicsr", "ecall") && probe_cause == CAUSE_ECALL_M);
    probe_cause = CAUSE_NONE;
    bool reserved_traps = !PROBE("zicsr", ".word 0x00004073");     // SYSTEM with funct3 = 100
    param_bool("TRAP_ON_RESERVED_INSTRUCTION", reserved_traps && probe_cause == CAUSE_ILLEGAL_INSTRUCTION);
    if (reserved_traps && probe_cause == CAUSE_ILLEGAL_INSTRUCTION)
        param_bool("REPORT_ENCODING_IN_MTVAL_ON_ILLEGAL_INSTRUCTION", probe_tval == 0x00004073);
    probe_cause = CAUSE_NONE;
    param_bool("TRAP_ON_UNIMPLEMENTED_CSR", !PROBE("zicsr", "csrr t1, 0x3FF") && probe_cause == CAUSE_ILLEGAL_INSTRUCTION);
    // Probes in U-, S- and VS-mode: PMP must let the lower modes run, the exceptions the probes
    // take are delegated so the lower mode's tval registers can be seen, and address translation
    // is Bare
    if (has_u || has_s) {
        pmp_open(num_pmp);
        if (has_u)
            ecall_from("TRAP_ON_ECALL_FROM_U", 0, false, mstatus);
        if (has_s) {
            unsigned long stvec = stvec_rd();
            ecall_from("TRAP_ON_ECALL_FROM_S", 1, false, mstatus);
            medeleg_set(DELEGATED);
            stvec_set((unsigned long)(has_h ? hs_trap_handler : s_trap_handler));
            satp_set(0);
            lower_mode_tval_params("STVAL", false, usable_pmp, mstatus);
            // Page faults, with a page table in the scratch area and satp pointing at it
            unsigned long atp, fva;
            bool have_table = build_page_table(satp_wr, false, &atp, &fva);
            if (have_table) {
                fault_va = fva;
                satp_set(atp);
                PROBE("zicsr", "sfence.vma");
                page_fault_params("STVAL", false, true, mstatus);
                medeleg_set(DELEGATED & ~PAGE_FAULTS);
                page_fault_params("MTVAL", false, false, mstatus);
                medeleg_set(DELEGATED);
                satp_set(0);
                PROBE("zicsr", "sfence.vma");
            } else {
                // satp accepts no translation mode: does sfence.vma trap?
                param_bool("TRAP_ON_SFENCE_VMA_WHEN_SATP_MODE_IS_READ_ONLY", !PROBE("zicsr", "sfence.vma"));
            }
            if (usable_pmp >= 2) {
                // An instruction access fault not delegated: the M-mode tval after a jump from S
                medeleg_set(DELEGATED & ~(1ul << CAUSE_INSTRUCTION_ACCESS_FAULT));
                pmp_deny_scratch();
                if (run_in_mode(stub_jump_scratch, 1, false, mstatus) == CAUSE_INSTRUCTION_ACCESS_FAULT)
                    param_bool("REPORT_VA_IN_MTVAL_ON_INSTRUCTION_ACCESS_FAULT", probe_tval == scratch);
                pmp_open(2);
                medeleg_set(DELEGATED);
            }
            if (has_h) {
                unsigned long vstvec = vstvec_rd();
                // Guest page faults must reach HS-mode: the spec makes their hedeleg bits
                // read-only zero, but Sail 0.14 lets them be set and delegates
                hedeleg_set(DELEGATED & ~GUEST_PAGE_FAULTS);
                vstvec_set((unsigned long)s_trap_handler);
                vsatp_set(0);
                hgatp_set(0);
                PROBE("zicsr", "li t1, 1 << 7\n\tcsrs hstatus, t1");     // SPV: mret enters VS
                ecall_from("TRAP_ON_ECALL_FROM_VS", 1, true, mstatus);
                lower_mode_tval_params("VSTVAL", true, usable_pmp, mstatus);
                // VS-stage page faults: the same table in vsatp with the G-stage Bare
                if (have_table && build_page_table(vsatp_wr, false, &atp, &fva)) {
                    fault_va = fva;
                    vsatp_set(atp);
                    PROBE("zicsr", HFENCE_VVMA);
                    page_fault_params("VSTVAL", true, true, mstatus);
                    vsatp_set(0);
                    PROBE("zicsr", HFENCE_VVMA);
                }
                // Guest page faults: a G-stage table in hgatp with the VS-stage Bare.  They cannot
                // be delegated to VS, so HS takes them and hs_trap_handler records htval.
                if (build_page_table(hgatp_wr, true, &atp, &fva)) {
                    fault_va = fva;
                    hgatp_set(atp);
                    PROBE("zicsr", HFENCE_GVMA);
                    // The GPA is in htval when HS-mode took the fault and in mtval2 when M-mode did
                    // (a hart may not let medeleg delegate guest page faults); UDB names both
                    if (run_in_mode(stub_load_fault_va, 1, true, mstatus) == 21) {
                        bool gpa_ok = guest_pa() == fva >> 2;
                        param_bool("REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT", gpa_ok);
                        param_bool("REPORT_GPA_IN_TVAL_ON_LOAD_GUEST_PAGE_FAULT", gpa_ok);
                    }
                    if (run_in_mode(stub_store_fault_va, 1, true, mstatus) == 23)
                        param_bool("REPORT_GPA_IN_TVAL_ON_STORE_AMO_GUEST_PAGE_FAULT", guest_pa() == fva >> 2);
                    if (run_in_mode(stub_jump_fault_va, 1, true, mstatus) == 20)
                        param_bool("REPORT_GPA_IN_TVAL_ON_INSTRUCTION_GUEST_PAGE_FAULT", guest_pa() == fva >> 2);
                    hgatp_set(0);
                    PROBE("zicsr", HFENCE_GVMA);
                }
                PROBE("zicsr", "li t1, 1 << 7\n\tcsrc hstatus, t1");
                hedeleg_set(0);
                vstvec_set(vstvec);
            }
            medeleg_set(0);
            stvec_set(stvec);
        }
        pmp_close(num_pmp);
    }

    // Address translation
    if (has_s) {
        bool any = false;
        unsigned long last = 0;
        for (unsigned i = 0; i < COUNT(atp_modes); i++)
            if (atp_accepts(satp_wr, ATP_MODE(atp_modes[i].mode))) {
                any = true;
                last = ATP_MODE(atp_modes[i].mode);
            }
        param_bool("SATP_MODE_BARE", !any || satp_bare_after(last));
        v = satp_wr(ATP_MODE_MASK == ATP_MODE(1) ? 0x7FC00000ul : 0x0FFFF00000000000ul);   // ASID all ones
        if (v != PROBE_TRAPPED)
            param_int("ASID_WIDTH", popcount(v & (__riscv_xlen == 64 ? 0x0FFFF00000000000ul : 0x7FC00000ul)));
        if (has_h) {
            bool gany = false, vany = false;
            unsigned long glast = 0, vlast = 0;
            char name[32];
            for (unsigned i = 0; i < COUNT(atp_modes); i++) {
                unsigned long m = ATP_MODE(atp_modes[i].mode);
                bool g = atp_accepts(hgatp_wr, m), vs = atp_accepts(vsatp_wr, m);
                // SV39X4_TRANSLATION and SV39_VSMODE_TRANSLATION, built from the mode name
                const char *sv = atp_modes[i].sv;
                unsigned k = 0;
                for (; sv[k]; k++) name[k] = sv[k];
                const char *tail = "X4_TRANSLATION";
                for (unsigned j = 0; tail[j]; j++) name[k + j] = tail[j];
                name[k + 14] = '\0';
                param_bool(name, g);
                tail = "_VSMODE_TRANSLATION";
                for (unsigned j = 0; tail[j]; j++) name[k + j] = tail[j];
                name[k + 19] = '\0';
                param_bool(name, vs);
                if (g) { gany = true; glast = m; }
                if (vs) { vany = true; vlast = m; }
            }
            param_bool("GSTAGE_MODE_BARE", !gany || hgatp_bare_after(glast));
            param_bool("VSSTAGE_MODE_BARE", !vany || vsatp_bare_after(vlast));
            v = hgatp_wr(__riscv_xlen == 64 ? 0x03FFF00000000000ul : 0x1FC00000ul);   // VMID all ones
            if (v != PROBE_TRAPPED)
                param_int("VMID_WIDTH", popcount(v & (__riscv_xlen == 64 ? 0x03FFF00000000000ul : 0x1FC00000ul)));
            // Writing a reserved mode to vsatp while V = 0: ignored (retained) or not
            unsigned long reserved = ATP_MODE(__riscv_xlen == 64 ? 2 : 1);
            if (__riscv_xlen == 64) {
                v = vsatp_wr(reserved);
                if (v != PROBE_TRAPPED)
                    param_bool("IGNORE_INVALID_VSATP_MODE_WRITES_WHEN_V_EQ_ZERO", v != reserved);
            }
            v = hgeie_wr(~0ul);
            if (PROBE_OK())
                param_int("NUM_EXTERNAL_GUEST_INTERRUPTS", popcount(v));
        }
    }

    // Cache-block size, from how many bytes cbo.zero clears
    if (have("Zicboz")) {
        for (unsigned i = 0; i < PROBE_SCRATCH_SIZE; i++)
            probe_scratch[i] = 0xFF;
        if (PROBE("zicboz", "cbo.zero 0(a1)")) {
            unsigned size = 0;
            while (size < PROBE_SCRATCH_SIZE && probe_scratch[size] == 0)
                size++;
            param_int("CACHE_BLOCK_SIZE", size);
        }
    }

    // Vector
    if (vlen) {
        param_int("VLEN", vlen);
        // ELEN: the widest SEW vsetivli accepts without setting vill (Zve32x guarantees 32)
        unsigned long vill64 = PROBE_VALUE("zve32x", "vsetivli x0, 1, e64, m1, ta, ma\n\tcsrr a3, vtype\n\t"
                                                     "srli a3, a3, " STR(__riscv_xlen) " - 1");
        unsigned long elen = vill64 == 0 ? 64 : 32;
        param_int("ELEN", elen);
        unsigned long vill8 = PROBE_VALUE("zve32x", "vsetivli x0, 1, e8, m1, ta, ma\n\tcsrr a3, vtype\n\t"
                                                    "srli a3, a3, " STR(__riscv_xlen) " - 1");
        param_int("SEW_MIN", vill8 == 0 ? 8 : 16);
        // A vtype with LMUL < SEW_MIN / ELEN is reserved: SEW = ELEN with LMUL = 1/8
        unsigned long vill_reserved = elen == 64
            ? PROBE_VALUE("zve32x", "vsetivli x0, 1, e64, mf8, ta, ma\n\tcsrr a3, vtype\n\tsrli a3, a3, " STR(__riscv_xlen) " - 1")
            : PROBE_VALUE("zve32x", "vsetivli x0, 1, e32, mf8, ta, ma\n\tcsrr a3, vtype\n\tsrli a3, a3, " STR(__riscv_xlen) " - 1");
        if (vill_reserved != PROBE_TRAPPED)
            param_bool("VILL_SET_ON_RESERVED_VTYPE", vill_reserved != 0);
        param_bool("VECTOR_LS_MISALIGNED_LEGAL",
                   PROBE("zve32x", "vsetivli x0, 1, e32, m1, ta, ma\n\taddi a2, a1, 1\n\tvle32.v v1, (a2)"));
        PROBE("zve32x", "vsetivli x0, 1, e32, m1, ta, ma");     // leave vtype legal
        if (has_h) {
            v = PROBE_VALUE("zicsr", BIT_SET_READ(vsstatus, 1 << 9));
            if (v != PROBE_TRAPPED)
                param_bool("VSSTATUS_VS_EXISTS", v != 0);
        }
    }

    // Smstateen: how each mstateen0 enable bit behaves
    if (have("Smstateen") || have("Ssstateen")) {
#if __riscv_xlen == 64
#define STATEEN_BIT(csr, n) PROBE_VALUE("zicsr", BIT_SET_READ(csr, 1 << (n))), PROBE_VALUE("zicsr", BIT_CLEAR_READ(csr, 1 << (n)))
#define HSTATEEN_BIT(n) PROBE_VALUE("zicsr", GATED_SET_READ(0x30C, 0x60C, 1 << (n))), \
                        PROBE_VALUE("zicsr", GATED_CLEAR_READ(0x30C, 0x60C, 1 << (n)))
#define MSTATEEN0 0x30C
#else
#define STATEEN_BIT(csr, n) PROBE_VALUE("zicsr", BIT_SET_READ(csr, 1 << ((n) - 32))), PROBE_VALUE("zicsr", BIT_CLEAR_READ(csr, 1 << ((n) - 32)))
#define HSTATEEN_BIT(n) PROBE_VALUE("zicsr", GATED_SET_READ(0x31C, 0x61C, 1 << ((n) - 32))), \
                        PROBE_VALUE("zicsr", GATED_CLEAR_READ(0x31C, 0x61C, 1 << ((n) - 32)))
#define MSTATEEN0 0x31C
#endif
        if (has_s)
            bit_type("MSTATEEN_ENVCFG_TYPE", STATEEN_BIT(MSTATEEN0, 62));
        if (have("Sscsrind"))
            bit_type("MSTATEEN_CSRIND_TYPE", STATEEN_BIT(MSTATEEN0, 60));
        if (have("Ssaia")) {
            bit_type("MSTATEEN_AIA_TYPE", STATEEN_BIT(MSTATEEN0, 59));
            bit_type("MSTATEEN_IMSIC_TYPE", STATEEN_BIT(MSTATEEN0, 58));
        }
        if (have("Sdtrig"))
            bit_type("MSTATEEN_CONTEXT_TYPE", STATEEN_BIT(MSTATEEN0, 57));
        if (have("Zcmt")) {
            bit_type("MSTATEEN_JVT_TYPE", PROBE_VALUE("zicsr", BIT_SET_READ(0x30C, 4)),
                     PROBE_VALUE("zicsr", BIT_CLEAR_READ(0x30C, 4)));
            if (has_s)
                bit_type("SSTATEEN_JVT_TYPE", PROBE_VALUE("zicsr", GATED_SET_READ(0x30C, 0x10C, 4)),
                         PROBE_VALUE("zicsr", GATED_CLEAR_READ(0x30C, 0x10C, 4)));
            if (has_h)
                bit_type("HSTATEEN_JVT_TYPE", PROBE_VALUE("zicsr", GATED_SET_READ(0x30C, 0x60C, 4)),
                         PROBE_VALUE("zicsr", GATED_CLEAR_READ(0x30C, 0x60C, 4)));
        }
        if (has_h && have("Ssstateen")) {
            bit_type("HSTATEEN_ENVCFG_TYPE", HSTATEEN_BIT(62));
            if (have("Sscsrind"))
                bit_type("HSTATEEN_CSRIND_TYPE", HSTATEEN_BIT(60));
            if (have("Ssaia")) {
                bit_type("HSTATEEN_AIA_TYPE", HSTATEEN_BIT(59));
                bit_type("HSTATEEN_IMSIC_TYPE", HSTATEEN_BIT(58));
            }
            if (have("Sdtrig"))
                bit_type("HSTATEEN_CONTEXT_TYPE", HSTATEEN_BIT(57));
        }
    }

    // Ssqosid: the ID field widths of srmcfg
    if (have("Ssqosid")) {
        v = srmcfg_wr(~0ul);
        if (PROBE_OK()) {
            param_int("RCID_WIDTH", popcount(v & 0xFFF));
            param_int("MCID_WIDTH", popcount((v >> 16) & 0xFFF));
        }
    }

    // Sdtrig: the context CSRs
    if (have("Sdtrig")) {
        bool mcontext = mcontext_rd() != PROBE_TRAPPED;
        param_bool("MCONTEXT_AVAILABLE", mcontext);
        if (mcontext) {
            v = mcontext_wr(~0ul);
            if (PROBE_OK())
                param_int("DBG_HCONTEXT_WIDTH", popcount(v));
        }
        if (has_h)
            param_bool("HCONTEXT_AVAILABLE", hcontext_rd() != PROBE_TRAPPED);
        if (has_s) {
            v = scontext_wr(~0ul);
            if (PROBE_OK())
                param_int("DBG_SCONTEXT_WIDTH", popcount(v));
        }
    }

    // Smctr: which mctrctl controls are implemented
#if __riscv_xlen == 64
    if (have("Smctr")) {
        static const struct { const char *param; unsigned bit; } ctr[] = {
            { "MCTRCTL_RASEMU_IMPLEMENTED", 7 },     { "MCTRCTL_STE_IMPLEMENTED", 8 },
            { "MCTRCTL_MTE_IMPLEMENTED", 9 },        { "MCTRCTL_EXCINH_IMPLEMENTED", 33 },
            { "MCTRCTL_INTRINH_IMPLEMENTED", 34 },   { "MCTRCTL_TRETINH_IMPLEMENTED", 35 },
            { "MCTRCTL_NTBREN_IMPLEMENTED", 36 },    { "MCTRCTL_TKBRINH_IMPLEMENTED", 37 },
            { "MCTRCTL_INDCALLINH_IMPLEMENTED", 40 }, { "MCTRCTL_DIRCALLINH_IMPLEMENTED", 41 },
            { "MCTRCTL_INDJMPINH_IMPLEMENTED", 42 }, { "MCTRCTL_DIRJMPINH_IMPLEMENTED", 43 },
            { "MCTRCTL_CORSWAPINH_IMPLEMENTED", 44 }, { "MCTRCTL_RETINH_IMPLEMENTED", 45 },
            { "MCTRCTL_INDLJMPINH_IMPLEMENTED", 46 }, { "MCTRCTL_DIRLJMPINH_IMPLEMENTED", 47 },
        };
        unsigned long writable = PROBE_VALUE_IN("zicsr", "csrrw t2, 0x34E, %[in]\n\tcsrr a3, 0x34E\n\tcsrw 0x34E, t2", ~0ul);
        if (PROBE_OK()) {
            for (unsigned i = 0; i < COUNT(ctr); i++)
                param_bool(ctr[i].param, (writable >> ctr[i].bit) & 1);
            param_bool("MCTRCTL_CUSTOM_IMPLEMENTED", (writable >> 60) != 0);
        }
    }
#endif
}
