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

#if __riscv_xlen == 64
#define SREG "sd"
#else
#define SREG "sw"
#endif

// Shared with start.S
volatile unsigned long probe_resume;    // while nonzero, a trap resumes here instead of failing
volatile unsigned long probe_cause;     // mcause of the most recent probe trap
#define PROBE_SCRATCH_SIZE 4096
unsigned char probe_scratch[PROBE_SCRATCH_SIZE] __attribute__((aligned(PROBE_SCRATCH_SIZE)));

// Execute insn and return true if it retired without trapping.
//
// The resume address is stored before the instruction and cleared afterwards, so the trap handler
// knows the trap was expected and returns to label 1 whatever the instruction's length was.  Label
// 1 is aligned to 4 bytes because a 16-bit probe instruction leaves the code after it 2-byte
// aligned, and a hart without C cannot resume at such an address (mepc[1] reads as zero).  The
// clobber list is the register convention of extensions.h; t0 is used for the resume address and
// a1 for the scratch pointer.  Floating-point and vector registers need no clobbers because the
// compiled code never keeps values in them.
#define PROBE(arch, insn) ({                                                            \
    unsigned long ok;                                                                   \
    __asm__ volatile(                                                                   \
        "la    t0, 1f\n\t"                                                              \
        SREG " t0, %[resume]\n\t"                                                       \
        "la    a1, probe_scratch\n\t"                                                   \
        ".option push\n\t"                                                              \
        ".option arch, +" arch "\n\t"                                                   \
        insn "\n\t"                                                                     \
        ".option pop\n\t"                                                               \
        "li    %[ok], 1\n\t"                                                            \
        "j     2f\n\t"                                                                  \
        ".balign 4\n"                                                                   \
        "1:\n\t"                                                                        \
        "li    %[ok], 0\n"                                                              \
        "2:\n\t"                                                                        \
        SREG " zero, %[resume]\n\t"                                                     \
        : [ok] "=&r"(ok), [resume] "=m"(probe_resume)                                   \
        :                                                                               \
        : "memory", "t0", "t1", "t2", "a1", "a2", "a3", "s0", "s1");                     \
    (bool)ok;                                                                           \
})

// Like PROBE, but also return the value left in a3, or PROBE_TRAPPED if the instruction trapped
#define PROBE_TRAPPED (~0ul)
#define PROBE_VALUE(arch, insn) ({                                                      \
    unsigned long value;                                                                \
    __asm__ volatile(                                                                   \
        "la    t0, 1f\n\t"                                                              \
        SREG " t0, %[resume]\n\t"                                                       \
        "la    a1, probe_scratch\n\t"                                                   \
        ".option push\n\t"                                                              \
        ".option arch, +" arch "\n\t"                                                   \
        insn "\n\t"                                                                     \
        ".option pop\n\t"                                                               \
        "mv    %[value], a3\n\t"                                                        \
        "j     2f\n\t"                                                                  \
        ".balign 4\n"                                                                   \
        "1:\n\t"                                                                        \
        "li    %[value], -1\n"                                                          \
        "2:\n\t"                                                                        \
        SREG " zero, %[resume]\n\t"                                                     \
        : [value] "=&r"(value), [resume] "=m"(probe_resume)                             \
        :                                                                               \
        : "memory", "t0", "t1", "t2", "a1", "a2", "a3", "s0", "s1");                     \
    value;                                                                              \
})

#define CAUSE_ILLEGAL_INSTRUCTION 2

// One probe function per table row
#define DEFINE_PROBE(name, version, arch, insn) \
    static bool probe_##name(void) { return PROBE(arch, insn); }
EXTENSIONS(DEFINE_PROBE)

#define DEFINE_HELPER(name, arch, insn) \
    static bool probe_##name(void) { return PROBE(arch, insn); }
HELPER_PROBES(DEFINE_HELPER)

struct extension {
    const char *name;
    const char *version;
    bool (*probe)(void);
    bool supported;
};

#define TABLE_ROW(name, version, arch, insn) { #name, version, probe_##name, false },
static struct extension extensions[] = { EXTENSIONS(TABLE_ROW) };
#define NUM_EXTENSIONS (sizeof(extensions) / sizeof(extensions[0]))

static bool have(const char *name)
{
    for (unsigned i = 0; i < NUM_EXTENSIONS; i++) {
        const char *a = extensions[i].name, *b = name;
        while (*a && *a == *b) { a++; b++; }
        if (*a == '\0' && *b == '\0')
            return extensions[i].supported;
    }
    return false;
}

static void print_extension(const char *name, const char *version)
{
    printf("  - { name: %s, version: \"= %s\" }\n", name, version);
}

// Run one probe, report a trap that is not an illegal-instruction exception (which would mean the
// probe itself is wrong, for example a scratch address the implementation cannot access).
static bool check(const char *name, bool (*probe)(void))
{
    probe_cause = 0;
    bool ok = probe();
    if (!ok && probe_cause != CAUSE_ILLEGAL_INSTRUCTION)
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

static unsigned long read_vlenb(void)
{
    unsigned long v;
    __asm__ volatile("csrr %0, 0xC22" : "=r"(v));   // vlenb; only read once Zve32x is known
    return v;
}

// Called from the trap handler for a trap that no probe expected
void report_unexpected_trap(unsigned long cause, unsigned long epc, unsigned long tval)
{
    printf("# FATAL: unexpected trap: mcause = 0x%x, mepc = 0x%x, mtval = 0x%x\n", cause, epc, tval);
}

int main(void)
{
    bool has_i = check("I", probe_I);
    for (unsigned i = 0; i < NUM_EXTENSIONS; i++)
        extensions[i].supported = check(extensions[i].name, extensions[i].probe);

    bool fadd_s = check("fadd.s", probe_fadd_s);
    bool fadd_d = check("fadd.d", probe_fadd_d);
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

    // Zicfilp: set mseccfg.MLPE, read it back and clear it again.  Nothing between the set and
    // the clear jumps indirectly, so enabling landing pads for a moment cannot fault.
    unsigned long mlpe = PROBE_VALUE("zicsr", "li t1, 0x400\n\tcsrrs zero, 0x747, t1\n\tcsrr a3, 0x747\n\t"
                                              "csrrc zero, 0x747, t1\n\tand a3, a3, t1");
    bool zicfilp = mlpe != PROBE_TRAPPED && mlpe != 0;

    printf("# Generated by the riscv-arch-test UDB feature extractor (tests-dev/priv/UDBFeatureExtractor)\n");
    printf("# Extensions detected by executing an instruction that only the extension defines and\n");
    printf("# checking whether it traps.  Not detectable that way: " NOT_DETECTABLE_EXTENSIONS ".\n");
    printf("params:\n");
    printf("  MXLEN: %d\n", (long)__riscv_xlen);
    if (vlen)
        printf("  VLEN: %d\n", (long)vlen);
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

    return 0;
}
