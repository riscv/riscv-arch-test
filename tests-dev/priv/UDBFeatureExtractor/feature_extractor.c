// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// feature_extractor.c: detect the unprivileged extensions a hart implements and print them as
// the implemented_extensions section of a UDB configuration.
//
// Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
// with assistance from Claude.
//
// Every extension in extensions.h is detected by executing one instruction that only that
// extension makes legal.  The trap handler in start.S returns to the probe with a flag when the
// instruction traps, so an unimplemented extension shows up as a trap and an implemented one as
// the instruction retiring.  This relies on unimplemented encodings raising an illegal-instruction
// exception, which Ssstrict guarantees.

#include <stdbool.h>
#include <stdint.h>

#include "console.h"
#include "extensions.h"

#include "probe.h"

// Shared with start.S
volatile unsigned long probe_resume;
volatile unsigned long probe_cause;
volatile unsigned long probe_tval;
volatile unsigned long probe_epc;
unsigned char probe_scratch[PROBE_SCRATCH_SIZE] __attribute__((aligned(PROBE_SCRATCH_SIZE)));

void print_parameters(unsigned long vlen, unsigned long reset_vtype, unsigned long reset_vl);   // parameters.c

// Shared with parameters.c
unsigned long reset_mseccfg;           // mseccfg as found at boot, PROBE_TRAPPED if it does not exist
bool has_zdinx;

// One probe function per table row
#define DEFINE_PROBE(name, version, arch, insn) \
    static bool probe_##name(void) { return PROBE(arch, insn); }
EXTENSIONS(DEFINE_PROBE)

#define DEFINE_HELPER(name, arch, insn) \
    static bool probe_##name(void) { return PROBE(arch, insn); }
HELPER_PROBES(DEFINE_HELPER)

// Privileged probes succeed when the sequence neither traps nor leaves a3 zero
#define DEFINE_PRIV_PROBE(name, version, arch, insn)                                        \
    static bool probe_##name(void)                                                          \
    {                                                                                       \
        unsigned long v = PROBE_VALUE(arch, insn);                                          \
        return v != PROBE_TRAPPED && v != 0;                                                \
    }
PRIV_EXTENSIONS(DEFINE_PRIV_PROBE)

struct extension {
    const char *name;
    const char *version;
    bool (*probe)(void);
    bool supported;
};

#define TABLE_ROW(name, version, arch, insn) { #name, version, probe_##name, false },
static struct extension extensions[] = { EXTENSIONS(TABLE_ROW) };
static struct extension priv_extensions[] = { PRIV_EXTENSIONS(TABLE_ROW) };
#define COUNT(a) (sizeof(a) / sizeof((a)[0]))
#define NUM_EXTENSIONS COUNT(extensions)
#define NUM_PRIV_EXTENSIONS COUNT(priv_extensions)

static bool streq(const char *a, const char *b)
{
    while (*a && *a == *b) { a++; b++; }
    return *a == '\0' && *b == '\0';
}

bool have(const char *name)
{
    for (unsigned i = 0; i < NUM_EXTENSIONS; i++)
        if (streq(extensions[i].name, name))
            return extensions[i].supported;
    for (unsigned i = 0; i < NUM_PRIV_EXTENSIONS; i++)
        if (streq(priv_extensions[i].name, name))
            return priv_extensions[i].supported;
    return false;
}

static void print_extension(const char *name, const char *version)
{
    printf("  - { name: %s, version: \"= %s\" }\n", name, version);
}

// The watchdog.  A hart with a buggy implementation of an extension may hang on its probe
// instruction instead of retiring it or trapping.  When rvmodel_macros.h names the machine timer
// (RVMODEL_MTIME_ADDRESS and RVMODEL_MTIMECMP_ADDRESS), every probe that check() runs, and every
// lower-mode probe, is armed with a machine-timer interrupt: a probe still running when it fires
// is ended by the trap handler and its feature is reported as not implemented.  The timeout is
// calibrated against a counted loop at boot, so it means about the same number of instructions
// whatever rate mtime counts at, and the interrupt is tested before it is relied on.
extern unsigned long watchdog_mtime_addr, watchdog_mtimecmp_addr;    // start.S
unsigned long watchdog_ticks;
static const char *watchdog_none;      // why there is no watchdog
static bool watchdog_armed;
static volatile unsigned long wd_args[3];

static bool mtime_read(unsigned long long *t)
{
    wd_args[0] = watchdog_mtime_addr;
#if __riscv_xlen == 64
    unsigned long v = PROBE_VALUE_IN("zicsr", "ld t1, 0(%[in])\n\tld a3, 0(t1)", wd_args);
    *t = v;
#else
    unsigned long v = PROBE_VALUE_IN("zicsr", "lw t1, 0(%[in])\n"
                                              "3:\tlw s0, 4(t1)\n\tlw a3, 0(t1)\n\tlw t2, 4(t1)\n\t"
                                              "bne s0, t2, 3b\n\tsw t2, 8(%[in])", wd_args);
    *t = ((unsigned long long)wd_args[2] << 32) | v;
#endif
    return PROBE_OK();
}

static bool mtimecmp_write(unsigned long long t)
{
    wd_args[0] = watchdog_mtimecmp_addr;
    wd_args[1] = (unsigned long)t;
#if __riscv_xlen == 64
    PROBE_VALUE_IN("zicsr", "ld t1, 0(%[in])\n\tld t2, 8(%[in])\n\tsd t2, 0(t1)", wd_args);
#else
    wd_args[2] = (unsigned long)(t >> 32);
    PROBE_VALUE_IN("zicsr", "lw t1, 0(%[in])\n\tlw t2, 4(%[in])\n\tlw s0, 8(%[in])\n\t"
                            "li a2, -1\n\tsw a2, 4(t1)\n\tsw t2, 0(t1)\n\tsw s0, 4(t1)", wd_args);
#endif
    return PROBE_OK();
}

// Count n down to zero: two instructions per iteration
static unsigned long spin(unsigned long n)
{
    PROBE_VALUE_IN("zicsr", "mv t1, %[in]\n3:\taddi t1, t1, -1\n\tbnez t1, 3b", n);
    return probe_cause;
}

void watchdog_arm(unsigned long ticks)
{
    unsigned long long now;
    if (!ticks || !mtime_read(&now) || !mtimecmp_write(now + ticks))
        return;
    watchdog_armed = true;
    __asm__ volatile("csrs mie, %0\n\tcsrs mstatus, %1" : : "r"(1ul << 7), "r"(1ul << 3));
}

void watchdog_disarm(void)
{
    if (!watchdog_armed)
        return;
    watchdog_armed = false;
    unsigned long cause = probe_cause;
    __asm__ volatile("csrc mstatus, %1\n\tcsrc mie, %0" : : "r"(1ul << 7), "r"(1ul << 3));
    mtimecmp_write(~0ull);
    probe_cause = cause;
}

#define WATCHDOG_CALIBRATE 4096        // loop iterations timed at boot
#define WATCHDOG_FACTOR 64             // the timeout, in multiples of that loop (about 0.5M instructions)

static void watchdog_init(void)
{
    unsigned long long t0, t1;
#ifdef WATCHDOG_DISABLE
    watchdog_none = "built with WATCHDOG_DISABLE";
    return;
#endif
    if (!watchdog_mtime_addr || !watchdog_mtimecmp_addr) {
        watchdog_none = "rvmodel_macros.h defines no RVMODEL_MTIME_ADDRESS and RVMODEL_MTIMECMP_ADDRESS";
        return;
    }
    if (!mtime_read(&t0) || !mtimecmp_write(~0ull)) {
        watchdog_none = "mtime or mtimecmp cannot be accessed";
        return;
    }
    spin(WATCHDOG_CALIBRATE);
    mtime_read(&t1);
    unsigned long d = (unsigned long)(t1 - t0);
    if (d == 0) {                                   // a slow timer: time a loop 16 times longer
        spin(16 * WATCHDOG_CALIBRATE);
        mtime_read(&t0);
        d = (unsigned long)(t0 - t1) >> 4;
        if (d == 0 && t0 != t1)
            d = 1;
    }
    if (d == 0) {
        watchdog_none = "mtime does not advance";
        return;
    }
    unsigned long mie = PROBE_VALUE("zicsr", "li t1, 1 << 7\n\tcsrs mie, t1\n\tcsrr a3, mie\n\tcsrc mie, t1");
    if (mie == PROBE_TRAPPED || !(mie & (1ul << 7))) {
        watchdog_none = "mie.MTIE cannot be set";
        return;
    }
    // The interrupt must end a loop that runs for about eight timeouts of one calibration loop
    watchdog_arm(d);
    unsigned long cause = spin(8 * WATCHDOG_CALIBRATE);
    watchdog_disarm();
    if (cause != CAUSE_TIMEOUT) {
        watchdog_none = "the machine-timer interrupt did not arrive";
        return;
    }
    watchdog_ticks = d * WATCHDOG_FACTOR;
}

// Probes named in SKIP_PROBES (a comma-separated list, given by make_config.py after a probe
// stopped the simulation on an earlier run) are not run, and their features are reported absent
#ifndef SKIP_PROBES
#define SKIP_PROBES ""
#endif
static bool skipped(const char *name)
{
    for (const char *s = SKIP_PROBES; *s; ) {
        const char *n = name;
        while (*n && *s == *n) { s++; n++; }
        if (*n == '\0' && (*s == ',' || *s == '\0'))
            return true;
        while (*s && *s != ',') s++;
        if (*s == ',') s++;
    }
    return false;
}

// Run one probe, report a trap that is not an illegal-instruction exception (which would mean the
// probe itself is wrong, for example a scratch address the implementation cannot access).  Under
// the watchdog, a probe that times out is tried once more with a timeout 16 times longer, so that
// a simulator whose mtime follows the host's clock cannot fail a probe by being descheduled.
volatile unsigned long unimplemented_seen;      // some probe's instruction raised an illegal-instruction exception

static bool check(const char *name, bool (*probe)(void))
{
    if (skipped(name)) {
        printf("# warning: the %s probe was not run because it stopped the simulation on an earlier run;\n"
               "#          %s is reported as not implemented\n", name, name);
        return false;
    }
#ifdef TRACE_PROBES
    printf("# probe: %s\n", name);
#endif
    bool ok = false;
    for (unsigned attempt = 0; attempt < 2; attempt++) {
        watchdog_arm(watchdog_ticks << (4 * attempt));
        probe_cause = CAUSE_NONE;
        ok = probe();
        watchdog_disarm();
        if (probe_cause != CAUSE_TIMEOUT)
            break;
    }
    if (probe_cause == CAUSE_TIMEOUT) {
        printf("# warning: the %s probe did not finish within %u mtime ticks (twice), so the watchdog\n"
               "#          stopped it; %s is reported as not implemented\n", name, watchdog_ticks << 4, name);
        return false;
    }
    if (!ok && probe_cause == CAUSE_ILLEGAL_INSTRUCTION)
        unimplemented_seen = 1;
    if (!ok && probe_cause != CAUSE_NONE && probe_cause != CAUSE_ILLEGAL_INSTRUCTION)
        printf("# warning: the %s probe trapped with mcause %d, not an illegal-instruction exception\n",
               name, (long)probe_cause);
    return ok;
}

// I versus E: x16 is the first register E does not have.  Written as a raw encoding
// (addi x16, x16, 0) because the assembler does not know x16 for an E build.
static bool probe_I(void)
{
    return PROBE("zicsr", ".word 0x00080813");
}

#ifdef WATCHDOG_SELFTEST
static bool probe_hang(void)
{
    return PROBE("zicsr", "3:\tj 3b");
}
#endif

static unsigned long read_vlenb(void)
{
    unsigned long v;
    __asm__ volatile("csrr %0, 0xC22" : "=r"(v));   // vlenb; only read once Zve32x is known
    return v;
}

DEFINE_CSR_WRITE_READ(write_read_satp, satp)
DEFINE_CSR_WRITE_READ(write_read_hgatp, hgatp)
DEFINE_CSR_WRITE_READ(write_read_vsatp, vsatp)
DEFINE_CSR_WRITE_READ(write_read_mcounteren, mcounteren)
DEFINE_CSR_WRITE_READ(write_read_medeleg, medeleg)
DEFINE_CSR_WRITE_READ(write_read_scounteren, scounteren)
DEFINE_CSR_WRITE_READ(write_read_hcounteren, hcounteren)

// Write a translation mode to satp/hgatp/vsatp, then Bare, and report whether Bare stuck
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

// Address translation modes: satp.MODE values; hgatp uses the same values for the x4 modes
#if __riscv_xlen == 64
#define ATP_MODE(m) ((unsigned long)(m) << 60)
static const struct { const char *name; unsigned long mode; } atp_modes[] =
    { { "Sv39", 8 }, { "Sv48", 9 }, { "Sv57", 10 } };
#else
#define ATP_MODE(m) ((unsigned long)(m) << 31)
static const struct { const char *name; unsigned long mode; } atp_modes[] = { { "Sv32", 1 } };
#endif
#define NUM_ATP_MODES COUNT(atp_modes)

// Entered from start.S instead of main() when a CSR written with a value does not read it back:
// the hart ignores CSR instructions rather than trapping on them, so it has no Zicsr and takes no
// exceptions, and no probe can tell an implemented instruction from an ignored one.  All that
// can be reported is the base ISA, from whether x16 holds a value (E has no x16).
void main_no_zicsr(void)
{
    unsigned long x16;
    __asm__ volatile(".word 0x05a00813\n\t"      // addi x16, x0, 0x5a
                     ".word 0x00080693\n\t"      // addi a3, x16, 0
                     "mv %0, a3" : "=r"(x16) : : "a3");
    bool has_i = x16 == 0x5a;
    printf("# Generated by the riscv-arch-test UDB feature extractor (tests-dev/priv/UDBFeatureExtractor)\n");
    printf("# note: CSR instructions neither trap nor reach a CSR, so this hart has no Zicsr and takes\n"
           "#       no exceptions.  Nothing beyond the base ISA can be probed; Sm is listed because UDB\n"
           "#       requires it.\n");
    printf("implemented_extensions:\n");
    print_extension(has_i ? "I" : "E", has_i ? "2.1" : "2.0");
    print_extension("Sm", "1.11.0");
    printf("params:\n");
    printf("  MXLEN: %u\n", (unsigned long)__riscv_xlen);
    printf("# end of extractor output\n");
}

// Called from the trap handler for a trap that no probe expected
void report_unexpected_trap(unsigned long cause, unsigned long epc, unsigned long tval)
{
    printf("# FATAL: unexpected trap: mcause = 0x%x, mepc = 0x%x, mtval = 0x%x\n", cause, epc, tval);
}

#ifdef ONLY_PROBE
// make_config.py builds with -DONLY_PROBE='"NAME"' to run one probe by itself: when a run stopped
// in that probe but the probe alone finishes, the run ran into a cycle or time limit instead
static void run_only(void)
{
    static const struct { const char *name; bool (*probe)(void); } named[] = {
        { "I", probe_I }, { "fadd.s", probe_fadd_s }, { "fadd.d", probe_fadd_d }, { "fadd.h", probe_fadd_h },
        { "fcvt.s.h", probe_fcvt_s_h }, { "Zcmp", probe_cm_mvsa01 },
    };
    for (unsigned i = 0; i < COUNT(named); i++)
        if (streq(named[i].name, ONLY_PROBE))
            printf("# only: %s %d\n", ONLY_PROBE, (long)check(named[i].name, named[i].probe));
    for (unsigned i = 0; i < NUM_EXTENSIONS; i++)
        if (streq(extensions[i].name, ONLY_PROBE))
            printf("# only: %s %d\n", ONLY_PROBE, (long)check(extensions[i].name, extensions[i].probe));
    for (unsigned i = 0; i < NUM_PRIV_EXTENSIONS; i++)
        if (streq(priv_extensions[i].name, ONLY_PROBE))
            printf("# only: %s %d\n", ONLY_PROBE, (long)check(priv_extensions[i].name, priv_extensions[i].probe));
    printf("# end of extractor output\n");
}
#endif

int main(void)
{
    reset_mseccfg = PROBE_VALUE("zicsr", "csrr a3, 0x747");

    // Two reset states would turn the first probe's trap into something else, so undo them before
    // any probe.  Smdbltrp sets mstatus.MDT at reset, and a trap while it is set is a double
    // trap.  Smrnmi clears mnstatus.NMIE at reset, and an exception taken while it is clear goes
    // to the RNMI vector instead of mtvec.  Both are done as probes so that a hart without the
    // CSR (mstatush needs privileged 1.12, mnstatus needs Smrnmi) just takes an ordinary trap.
#if __riscv_xlen == 64
    PROBE("zicsr", "li t1, 1 << 42\n\tcsrc mstatus, t1");
#else
    PROBE("zicsr", "li t1, 1 << 10\n\tcsrc mstatush, t1");
#endif
    PROBE("zicsr", "li t1, 8\n\tcsrs 0x744, t1");

    watchdog_init();
    if (watchdog_ticks)
        printf("# watchdog: a probe that runs for %u mtime ticks is stopped and its feature reported absent\n",
               watchdog_ticks);
    else
        printf("# watchdog: none (%s); a probe that hangs stops the run\n", watchdog_none);
#ifdef ONLY_PROBE
    run_only();
    return 0;
#endif

    // vtype and vl as left by reset, before any probe touches the vector unit
    unsigned long reset_vtype = PROBE_VALUE("zicsr", "csrr a3, vtype");
    unsigned long reset_vl = PROBE_VALUE("zicsr", "csrr a3, vl");

#ifdef WATCHDOG_SELFTEST
    // make ... EXTRA_CFLAGS=-DWATCHDOG_SELFTEST: a probe that never finishes, for the watchdog to stop
    check("WatchdogSelftest", probe_hang);
#endif
    bool has_i = check("I", probe_I);
    for (unsigned i = 0; i < NUM_EXTENSIONS; i++)
        extensions[i].supported = check(extensions[i].name, extensions[i].probe);

    bool fadd_s = check("fadd.s", probe_fadd_s);
    bool fadd_d = check("fadd.d", probe_fadd_d);
    has_zdinx = fadd_d && !have("D");
    bool fadd_h = check("fadd.h", probe_fadd_h);
    bool fcvt_s_h = check("fcvt.s.h", probe_fcvt_s_h);

    unsigned long vlen = have("Zve32x") ? read_vlenb() * 8 : 0;

    // Zcmp shares encodings with Zcd's c.fsdsp, so its probe would store to the stack on a Zcd
    // hart; the two are incompatible, so only probe when Zcd is absent
    bool zcmp = !have("Zcd") && check("Zcmp", probe_cm_mvsa01);

    // On RV32, Zclsd's c.ld is the same encoding as Zcf's c.flw.  Execute it with a2 cleared and
    // nonzero data in scratch memory: an x-register write means Zclsd, a float write means Zcf.
    bool zcf = false, zclsd = false;
#if __riscv_xlen == 32
    for (unsigned i = 0; i < 8; i++)
        probe_scratch[i] = 0x11;      // an earlier cbo.zero may have cleared it
    unsigned long c_ld = PROBE_VALUE("zca,+zilsd,+zclsd", "li a2, 0\n\tli a3, 0\n\tc.ld a2, 0(a1)\n\tmv a3, a2");
    if (c_ld != PROBE_TRAPPED) {
        zclsd = c_ld != 0 && have("Zilsd");
        zcf = c_ld == 0 && have("F");
    }
#endif

    // Zicfilp: mseccfg.MLPE can be set.  Nothing between the set and the restore jumps
    // indirectly, so enabling landing pads for a moment cannot fault.
    unsigned long mlpe = PROBE_VALUE("zicsr", CSR_BIT(0x747, 10));
    bool zicfilp = mlpe != PROBE_TRAPPED && mlpe != 0;

    // Privileged extensions
    for (unsigned i = 0; i < NUM_PRIV_EXTENSIONS; i++)
        priv_extensions[i].supported = check(priv_extensions[i].name, priv_extensions[i].probe);
    bool has_s = have("S"), has_h = have("H");
    // Probed individually only to explain a missing Zicntr: the extension needs all three.
    bool cycle_ok   = PROBE_VALUE("zicsr", CSR_EXISTS(cycle))   != PROBE_TRAPPED;
    bool time_ok    = PROBE_VALUE("zicsr", CSR_EXISTS(time))    != PROBE_TRAPPED;
    bool instret_ok = PROBE_VALUE("zicsr", CSR_EXISTS(instret)) != PROBE_TRAPPED;
    // Privileged 1.12 added mconfigptr, which every 1.12 hart has (menvcfg exists only with
    // U-mode), and on RV32 mstatush.  A hart with 1.12 CSRs but no mstatush matches neither
    // version: a configuration declaring 1.12 makes the test environment read mstatush
    // unconditionally, and on a hart without it every trap then takes a nested trap.  VeeR EL2 is
    // such a hart - it implements menvcfg, mcounteren and mseccfg but not mstatush - and declaring
    // 1.12 for it made every privileged test die.  Report the lower version, which is the one
    // such a hart actually works under, and say so.
    bool has_menvcfg = PROBE_VALUE("zicsr", CSR_EXISTS(menvcfg)) != PROBE_TRAPPED;
    bool has_mconfigptr = PROBE_VALUE("zicsr", CSR_EXISTS(0xF15)) != PROBE_TRAPPED;
    bool has_mstatush = __riscv_xlen != 32 ||
                        PROBE_VALUE("zicsr", CSR_EXISTS(0x310)) != PROBE_TRAPPED;
    const char *sm_version = has_mconfigptr && has_mstatush ? "1.12.0" : "1.11.0";
    // Privileged 1.13 added medelegh on RV32, and the hardware-error exception (19) and, without
    // Zicfilp or Zicfiss, the software-check exception (18), whose medeleg bits are reserved
    // before 1.13; a hart that lets either be delegated is 1.13
    if (has_mconfigptr && has_mstatush) {
        unsigned long deleg = has_s ? write_read_medeleg(~0ul) : 0;
        if (deleg == PROBE_TRAPPED)
            deleg = 0;
        bool v113 = (deleg >> 19) & 1 || ((deleg >> 18) & 1 && !zicfilp && !have("Zicfiss"));
#if __riscv_xlen == 32
        v113 = v113 || PROBE_VALUE("zicsr", CSR_EXISTS(0x312)) != PROBE_TRAPPED;
#endif
        if (v113)
            sm_version = "1.13.0";
    }

    // Address translation: which modes satp accepts, and whether hgatp and vsatp accept the same
    bool atp_ok[NUM_ATP_MODES], any_atp = false;
    unsigned long last_atp = 0;
    bool shgatpa = has_h, shvsatpa = has_h;
    for (unsigned i = 0; i < NUM_ATP_MODES; i++) {
        unsigned long m = ATP_MODE(atp_modes[i].mode);
        atp_ok[i] = has_s && write_read_satp(m) == m;
        if (atp_ok[i]) {
            any_atp = true;
            last_atp = m;
            shgatpa = shgatpa && write_read_hgatp(m) == m;
            shvsatpa = shvsatpa && write_read_vsatp(m) == m;
        }
    }
    bool svbare = has_s && (!any_atp || satp_bare_after(last_atp));
    if (any_atp) {
        shgatpa = shgatpa && hgatp_bare_after(last_atp);
        shvsatpa = shvsatpa && vsatp_bare_after(last_atp);
    }

    // Ssccfg: scountinhibit is accessible only while menvcfg.CDE is set, so set it, try the
    // access, and clear it again afterwards whether or not the access trapped
    bool ssccfg = false;
    if (have("Smcdeleg")) {
#if __riscv_xlen == 64
#define CDE_CSR menvcfg
#define CDE_BIT 60
#else
#define CDE_CSR menvcfgh
#define CDE_BIT 28
#endif
        unsigned long v = PROBE_VALUE("zicsr", "li t1, 1 << " STR(CDE_BIT) "\n\tcsrs " STR(CDE_CSR) ", t1\n\t"
                                               "csrr a3, 0x120\n\tli a3, 1");
        PROBE_VALUE("zicsr", "li t1, 1 << " STR(CDE_BIT) "\n\tcsrc " STR(CDE_CSR) ", t1\n\tli a3, 1");
        ssccfg = v != PROBE_TRAPPED && v != 0;
    }

    // Counter enables: every bit writable in mcounteren must be writable in scounteren/hcounteren
    unsigned long m_writable = write_read_mcounteren(~0ul);
    // (both are defined only with Zihpm)
    bool sscounterenw = has_s && have("Zihpm") && (write_read_scounteren(~0ul) & m_writable) == m_writable;
    bool shcounterenw = has_h && have("Zihpm") && (write_read_hcounteren(~0ul) & m_writable) == m_writable;

    printf("# Generated by the riscv-arch-test UDB feature extractor (tests-dev/priv/UDBFeatureExtractor)\n");
    printf("# Extensions are detected by executing an instruction or CSR access that only the extension\n");
    printf("# makes legal, or by writing a CSR field it adds.  These are not looked for (see the README):\n");
    printf("# untested: " UNTESTED_EXTENSIONS " " UNTESTED_PRIV_EXTENSIONS "%s%s\n",
           have("Svadu") ? "" : " Svade", __riscv_xlen == 32 ? " Ssu32xl" : "");
    if ((has_mconfigptr || has_menvcfg) && !has_mstatush)
        printf("# note: privileged 1.12 CSRs are implemented but mstatush is not, so this hart matches neither\n"
               "#       privileged 1.11 nor 1.12.  Sm is reported as 1.11.0 because that is the\n"
               "#       version it works under; declaring 1.12 makes the trap handler read\n"
               "#       mstatush and every trap then takes a nested trap.\n");
    if (!have("Zicntr") && cycle_ok && instret_ok && !time_ok)
        printf("# note: cycle and instret are implemented but time is not, so Zicntr is not\n"
               "#       reported.  If the platform supplies time some other way, set\n"
               "#       TIME_CSR_IMPLEMENTED to false and claim Zicntr by hand.\n");
    printf("implemented_extensions:\n");
    print_extension(has_i ? "I" : "E", has_i ? "2.1" : "2.0");
    print_extension("Zicsr", "2.0");   // the extractor itself needs it to run

    for (unsigned i = 0; i < NUM_EXTENSIONS; i++)
        if (extensions[i].supported)
            print_extension(extensions[i].name, extensions[i].version);

    // Extensions defined as combinations of the ones above
    if (have("Zaamo") && have("Zalrsc"))
        print_extension("A", "2.1.0");
    if (have("Zba") && have("Zbb") && have("Zbs"))
        print_extension("B", "1.0.0");
    if (zcmp)
        print_extension("Zcmp", "1.0.0");
    if (zcf)
        print_extension("Zcf", "1.0.0");
    if (zclsd)
        print_extension("Zclsd", "1.0.0");
    if (zicfilp)
        print_extension("Zicfilp", "1.0.0");
    bool c_fp_ok = (!have("D") || have("Zcd")) && (__riscv_xlen != 32 || !have("F") || zcf);
    if (have("Zca") && c_fp_ok)
        print_extension("C", "2.0");
    if (have("Zfhmin") && fadd_h)
        print_extension("Zfh", "1.0.0");
    if (have("Zbkb") && have("Zbkc") && have("Zbkx") && have("Zkne") && have("Zknd") && have("Zknh"))
        print_extension("Zkn", "1.0.0");
    if (have("Zbkb") && have("Zbkc") && have("Zbkx") && have("Zksed") && have("Zksh"))
        print_extension("Zks", "1.0.0");
    if (have("Zve64x") && have("Zve32f"))
        print_extension("Zve64f", "1.0.0");
    if (have("Zve64d") && vlen >= 128)
        print_extension("V", "1.0.0");
    static const char *const zvl[] = { "Zvl32b", "Zvl64b", "Zvl128b", "Zvl256b", "Zvl512b", "Zvl1024b",
                                       "Zvl2048b", "Zvl4096b", "Zvl8192b", "Zvl16384b", "Zvl32768b", "Zvl65536b" };
    for (unsigned i = 0; i < sizeof(zvl) / sizeof(zvl[0]) && (32ul << i) <= vlen; i++)
        print_extension(zvl[i], "1.0.0");
    // The x-register floating-point extensions share encodings with F/D/Zfh/Zfhmin but have no
    // floating-point loads, so they are the arithmetic working without the load
    if (fadd_s && !have("F"))
        print_extension("Zfinx", "1.0.0");
    if (fadd_d && !have("D"))
        print_extension("Zdinx", "1.0.0");
    if (fadd_h && !have("Zfhmin"))
        print_extension("Zhinx", "1.0.0");
    if (fcvt_s_h && !have("Zfhmin"))
        print_extension("Zhinxmin", "1.0.0");

    // Privileged extensions
    print_extension("Sm", sm_version);
    for (unsigned i = 0; i < NUM_PRIV_EXTENSIONS; i++)
        if (priv_extensions[i].supported)
            print_extension(priv_extensions[i].name,
                            streq(priv_extensions[i].name, "S") ? sm_version : priv_extensions[i].version);
    for (unsigned i = 0; i < NUM_ATP_MODES; i++)
        if (atp_ok[i])
            print_extension(atp_modes[i].name, "1.0");
    if (svbare)
        print_extension("Svbare", "1.0.0");
    if (have("Svadu"))
        print_extension("Svade", "1.0.0");    // menvcfg.ADUE = 0 is defined as Svade behavior
    if (sscounterenw)
        print_extension("Sscounterenw", "1.0.0");
    if (shcounterenw)
        print_extension("Shcounterenw", "1.0.0");
    if (shgatpa)
        print_extension("Shgatpa", "1.0.0");
    if (shvsatpa)
        print_extension("Shvsatpa", "1.0.0");
    if (has_s && have("Smnpm"))
        print_extension("Sspm", "1.0.0");
    if (has_s ? have("Ssnpm") : have("Smnpm"))
        print_extension("Supm", "1.0.0");
    if (ssccfg)
        print_extension("Ssccfg", "1.0.0");
    if (has_h && shcounterenw && shgatpa && shvsatpa && have("Shvstvecd"))
        print_extension("Sha", "1.0.0");      // Shtvala and Shvstvala are assumed

    print_parameters(vlen, reset_vtype, reset_vl);
    printf("# end of extractor output\n");    // make_config.py's sign that the run finished
    return 0;
}
