// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// extensions.h: the table of unprivileged extensions the feature extractor detects.
//
// Adapted by David Harris from the original by Jayant Malvi (riscv-arch-test #1655),
// with assistance from Claude.
//
// Every ratified unprivileged extension that defines at least one instruction or CSR is detected
// the same way: execute one instruction (or CSR access) that only that extension makes legal and
// see whether it traps.  On an implementation with Ssstrict, or any implementation that raises an
// illegal-instruction exception on unimplemented encodings, a trap means the extension is absent.
//
// Each row is
//     X(name, version, arch, insn)
//   name     the UDB extension name; also used to name the probe function
//   version  the UDB version string
//   arch     the extension(s) the assembler must accept for insn, as an `.option arch` addition
//            (the program itself is compiled for rv{32,64}e_zicsr, so nothing else is enabled)
//   insn     the instruction to execute; a sequence may be joined with "\n\t"
//
// Conventions inside insn:
//   a1        points at PROBE_SCRATCH_SIZE bytes of scratch memory, aligned to PROBE_SCRATCH_SIZE,
//             for loads, stores, atomics and cache-block operations
//   t1, t2, a2, a3, s0, s1, ft0-ft4, fs0 and every vector register may be written
//   nothing else may be modified, and the instruction must be harmless when it does execute
//
// To add an extension, add a row.  The probe function, the YAML output and the self-test pick it
// up automatically.  Extensions whose presence changes no instruction's legality (hints, memory
// model and behavioral extensions) cannot be detected this way; they are listed in
// NOT_DETECTABLE_EXTENSIONS so the output names them.

#ifndef EXTENSIONS_H
#define EXTENSIONS_H

// Vector probes set vtype first.  vsetivli with an unsupported SEW sets vtype.vill, after which
// the vector instruction that follows raises an illegal-instruction exception, so a vector probe
// also fails on an implementation that lacks that SEW.  The element-group instructions
// (Zvk*) use LMUL = EGS so they are legal on any VLEN >= 32.
#define VTYPE(vl, sew, lmul) "vsetivli x0, " #vl ", " #sew ", " #lmul ", ta, ma\n\t"

#define EXTENSIONS_COMMON(X)                                                                  \
    /* multiply and divide */                                                                 \
    X(Zmmul,    "1.0.0", "zmmul",              "mul t1, t2, t2")                              \
    X(M,        "2.0",   "m",                  "div t1, t2, t2")                              \
    /* atomics */                                                                             \
    X(Zaamo,    "1.0.0", "zaamo",              "amoadd.w t1, t2, 0(a1)")                      \
    X(Zalrsc,   "1.0.0", "zalrsc",             "lr.w t1, 0(a1)")                              \
    X(Zacas,    "1.0.0", "zaamo,+zacas",       "amocas.w t1, t2, 0(a1)")                      \
    X(Zabha,    "1.0.0", "zaamo,+zabha",       "amoadd.b t1, t2, 0(a1)")                      \
    X(Zawrs,    "1.0.0", "zawrs",              "wrs.nto")                                     \
    /* Zi*: CSRs, fences, conditional ops, may-be-ops, cache-block ops */                     \
    X(Zifencei, "2.0.0", "zifencei",           "fence.i")                                     \
    X(Zicntr,   "2.0",   "zicsr",              "csrr t1, cycle")                              \
    X(Zihpm,    "2.0.0", "zicsr",              "csrr t1, hpmcounter3")                        \
    X(Zicond,   "1.0",   "zicond",             "czero.eqz t1, t2, t2")                        \
    X(Zimop,    "1.0.0", "zimop",              "mop.r.0 t1, t2")                              \
    X(Zicfiss,  "1.0.0", "zicsr",              "csrr t1, 0x011") /* ssp; always readable in M-mode */ \
    X(Zicbom,   "1.0.0", "zicbom",             "cbo.clean 0(a1)")                             \
    X(Zicboz,   "1.0.0", "zicboz",             "cbo.zero 0(a1)")                              \
    /* floating point: the loads exist only with the F/D/Q/Zfhmin register-file extensions,   \
       so they tell those apart from Zfinx/Zdinx/Zhinx, which share the arithmetic encodings */ \
    X(F,        "2.2.0", "f",                  "flw ft0, 0(a1)")                              \
    X(D,        "2.2.0", "d",                  "fld ft0, 0(a1)")                              \
    X(Q,        "2.2.0", "q",                  "flq ft0, 0(a1)")                              \
    X(Zfhmin,   "1.0.0", "zfhmin",             "flh ft0, 0(a1)")                              \
    X(Zfa,      "1.0.0", "f,+zfa",             "fround.s ft0, ft2")                           \
    X(Zfbfmin,  "1.0.0", "zfbfmin",            "fcvt.s.bf16 ft0, ft2")                        \
    /* compressed */                                                                          \
    X(Zca,      "1.0.0", "zca",                "c.addi t1, 1")                                \
    X(Zcb,      "1.0.0", "zca,+zcb",           "c.zext.b a2")                                 \
    X(Zcd,      "1.0.0", "zca,+d,+zcd",        "c.fld fs0, 0(a1)")                            \
    X(Zcmt,     "1.0.0", "zicsr",              "csrr t1, 0x017")   /* jvt exists only with Zcmt */ \
    X(Zcmop,    "1.0.0", "zca,+zcmop",         "c.mop.1")                                     \
    /* bit manipulation and scalar crypto */                                                  \
    X(Zba,      "1.0.0", "zba",                "sh1add t1, t2, t2")                           \
    X(Zbb,      "1.0.0", "zbb",                "clz t1, t2")                                  \
    X(Zbs,      "1.0.0", "zbs",                "bset t1, t2, t2")                             \
    X(Zbc,      "1.0.0", "zbc",                "clmulr t1, t2, t2")                           \
    X(Zbkb,     "1.0.0", "zbkb",               "pack t1, t2, t2")                             \
    X(Zbkc,     "1.0.0", "zbkc",               "clmul t1, t2, t2")                            \
    X(Zbkx,     "1.0.0", "zbkx",               "xperm8 t1, t2, t2")                           \
    X(Zknh,     "1.0.0", "zknh",               "sha256sum0 t1, t2")                           \
    X(Zksed,    "1.0.0", "zksed",              "sm4ed t1, t2, t2, 0")                         \
    X(Zksh,     "1.0.0", "zksh",               "sm3p0 t1, t2")                                \
    X(Zkr,      "1.0.0", "zicsr",              "csrrw t1, 0x015, zero") /* seed: reads need a write */ \
    /* vector */                                                                              \
    X(Zve32x,   "1.0.0", "zve32x",             VTYPE(1, e32, m1) "vadd.vv v1, v2, v3")        \
    X(Zve64x,   "1.0.0", "zve64x",             VTYPE(1, e64, m1) "vadd.vv v1, v2, v3")        \
    X(Zve32f,   "1.0.0", "zve32f",             VTYPE(1, e32, m1) "vfadd.vv v1, v2, v3")       \
    X(Zve64d,   "1.0.0", "zve64d",             VTYPE(1, e64, m1) "vfadd.vv v1, v2, v3")       \
    X(Zvfhmin,  "1.0.0", "zve32f,+zvfhmin",    VTYPE(1, e16, m1) "vfwcvt.f.f.v v2, v1")       \
    X(Zvfh,     "1.0.0", "zve32f,+zfhmin,+zvfh", VTYPE(1, e16, m1) "vfadd.vv v1, v2, v3")     \
    X(Zvfbfmin, "1.0.0", "zve32f,+zvfbfmin",   VTYPE(1, e16, m1) "vfwcvtbf16.f.f.v v2, v1")   \
    X(Zvfbfwma, "1.0.0", "zve32f,+zvfbfwma",   VTYPE(1, e16, m1) "vfwmaccbf16.vv v2, v1, v4") \
    X(Zvbb,     "1.0.0", "zve32x,+zvbb",       VTYPE(1, e32, m1) "vbrev.v v1, v2")            \
    X(Zvkb,     "1.0.0", "zve32x,+zvkb",       VTYPE(1, e32, m1) "vandn.vv v1, v2, v3")       \
    X(Zvbc,     "1.0.0", "zve64x,+zvbc",       VTYPE(1, e64, m1) "vclmul.vv v1, v2, v3")      \
    X(Zvkg,     "1.0.0", "zve32x,+zvkg",       VTYPE(4, e32, m4) "vghsh.vv v0, v4, v8")       \
    X(Zvkned,   "1.0.0", "zve32x,+zvkned",     VTYPE(4, e32, m4) "vaesem.vv v0, v4")          \
    X(Zvknha,   "1.0.0", "zve32x,+zvknha",     VTYPE(4, e32, m4) "vsha2ms.vv v0, v4, v8")     \
    X(Zvknhb,   "1.0.0", "zve64x,+zvknhb",     VTYPE(4, e64, m8) "vsha2ms.vv v0, v8, v16")    \
    X(Zvksed,   "1.0.0", "zve32x,+zvksed",     VTYPE(4, e32, m4) "vsm4r.vv v0, v4")           \
    X(Zvksh,    "1.0.0", "zve32x,+zvksh",      VTYPE(8, e32, m8) "vsm3me.vv v0, v8, v16")

// Instructions whose mnemonics differ between RV32 and RV64, and RV32-only extensions
#if __riscv_xlen == 32
#define EXTENSIONS_XLEN(X)                                                                    \
    X(Zknd,     "1.0.0", "zknd",               "aes32dsi t1, t2, t2, 0")                      \
    X(Zkne,     "1.0.0", "zkne",               "aes32esi t1, t2, t2, 0")                      \
    X(Zilsd,    "1.0.0", "zilsd",              "ld a2, 0(a1)")
#else
#define EXTENSIONS_XLEN(X)                                                                    \
    X(Zknd,     "1.0.0", "zknd",               "aes64ds t1, t2, t2")                          \
    X(Zkne,     "1.0.0", "zkne",               "aes64es t1, t2, t2")
#endif

#define EXTENSIONS(X) EXTENSIONS_COMMON(X) EXTENSIONS_XLEN(X)

// Probes that are not extensions themselves but feed the derived ones below: the floating-point
// arithmetic encodings execute under either the register-file extension (F, D, Zfh, Zfhmin) or
// its x-register twin (Zfinx, Zdinx, Zhinx, Zhinxmin).  Even-numbered registers keep the
// RV32 Zdinx register-pair rule satisfied.
//
// Some extensions reuse encodings of another extension they are incompatible with, so their
// probe instruction executes as something else on a hart that has the other extension.  Those
// are handled in feature_extractor.c rather than the table:
//   Zcmp and Zcmt use the c.fsdsp/c.fldsp space of Zcd, so cm.mvsa01 is a stack store on a Zcd
//     hart; Zcmp is probed only when Zcd is absent
//   Zclsd's c.ld/c.sd are Zcf's c.flw/c.fsw, so the encoding is executed and the extension
//     decided by whether it wrote an x register (Zclsd) or not (Zcf)
//   Zicfilp's only instruction, lpad, is a hint until landing pads are enabled, so it is detected
//     by whether the MLPE bit it adds to mseccfg can be set
#define HELPER_PROBES(X)                                                                      \
    X(fadd_s,   "f",      "fadd.s ft0, ft2, ft4")                                             \
    X(fadd_d,   "d",      "fadd.d ft0, ft2, ft4")                                             \
    X(fadd_h,   "zfh",    "fadd.h ft0, ft2, ft4")                                             \
    X(fcvt_s_h, "zfhmin", "fcvt.s.h ft0, ft2")                                                \
    X(cm_mvsa01, "zca,+zcmp", "cm.mvsa01 s0, s1")

// Extensions defined only as a combination of others, reported when every member is present:
//   A = Zaamo + Zalrsc              B = Zba + Zbb + Zbs
//   C = Zca (+ Zcf with F on RV32) (+ Zcd with D)
//   Zkn = Zbkb + Zbkc + Zbkx + Zkne + Zknd + Zknh      Zks = Zbkb + Zbkc + Zbkx + Zksed + Zksh
//   Zve64f = Zve64x + Zve32f       V = Zve64d with VLEN >= 128       Zvl<n>b for each n <= VLEN
//   Zfh = Zfhmin and fadd.h executes (Zfh has no load of its own; Zhinx shares its arithmetic)
//   Zfinx, Zdinx, Zhinx, Zhinxmin = the arithmetic executes but the load does not
//   Zcmp = cm.mvsa01 executes and Zcd is absent      Zcf / Zclsd / Zicfilp = see above
// They are computed in feature_extractor.c.

// Ratified unprivileged extensions that add no instruction or CSR whose legality could be tested,
// so a trap-based probe cannot see them.  They are reported as a comment.
#define NOT_DETECTABLE_EXTENSIONS                                                             \
    "Zihintpause, Zihintntl, Zicbop (hints that execute everywhere), "                        \
    "Zicclsm, Ztso, Zkt, Zvkt, Zic64b, Ziccif, Ziccamoa, Ziccamoc, Ziccrse, Za64rs, Za128rs, " \
    "Zama16b (behavioral guarantees), Zk, Zvkn, Zvks and their variants (need Zkt or Zvkt)"

#endif
