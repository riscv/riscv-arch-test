// rvtest_pmp_macros.h
// PMP R/W/X verification macros for the PMP test suite (tests/priv/pmp/...).
// SPDX-License-Identifier: Apache-2.0
//
// Shared, centralized versions of the per-test PMP_VERIFICATION_* macros. Each macro
// probes how a PMP-protected region responds to execute / store / load accesses and
// records the outcome with RVTEST_SIGUPD. Defined here (instead of redefined in every
// test) so cross-cutting fixes — e.g. inserting RVTEST_FENCEI to sync the I-cache
// after writing executable code — are made in one place. RVTEST_FENCEI is
// self-disabling: fence.i only when Zifencei is supported, otherwise nop.
//
// Included from riscv_arch_test.h after rvtest_config.h / utils.h / signature.h, so
// UDB_PMP_GRANULARITY, NOP/DOUBLE_NOP, LA/LI and RVTEST_SIGUPD are all available.
//
// Contract for callers (must hold in each test that uses these):
//   - Signature pointer / temp registers x2, x5, x4 follow suite convention.
//   - The string labels test_<n>_str referenced below are defined in the test's
//     RVTEST_DATA section, with SIGUPD_COUNT sized accordingly.
//
// These are GAS (.macro) definitions; a test that uses one must NOT also define a
// local .macro of the same name (GAS errors on macro redefinition).
//==============================================================================

// PMP_NAPOT_REGION_PAD_WORDS: number of 4-byte filler words to emit before a NAPOT
// region-under-test so the region lands on the next g_napot-aligned boundary
// (0x80005008 at coverage grain 2). This makes the region's pmpaddr encode a *clean*
// NAPOT region that matches the coverage model's STANDARD_REGION / PMP_NAPOT_REGION_START
// and does NOT swallow the return-instruction pad (which would give a 16-byte region and
// hang execute probes). g_napot = (GRAN>3) ? 2^GRAN : 2^(GRAN+1); words = g_napot/4.
// (GAS .rept cannot evaluate a C ternary, so the branch is done with the preprocessor.)
#if UDB_PMP_GRANULARITY > 3
  #define PMP_NAPOT_REGION_PAD_WORDS (1 << (UDB_PMP_GRANULARITY - 2))
#else
  #define PMP_NAPOT_REGION_PAD_WORDS (1 << (UDB_PMP_GRANULARITY - 1))
#endif

// Background region helpers. The catch-all PMP entry must be the lowest-priority
// usable entry (highest usable PMP index). These macros compute the address CSR,
// config CSR, and config-byte shift from the UDB NUM_USABLE_PMP_ENTRIES parameter.
#define RVTEST_PMP_BACKGROUND_ENTRY (UDB_NUM_USABLE_PMP_ENTRIES - 1)
#define RVTEST_PMP_BACKGROUND_ADDR_CSR (CSR_PMPADDR0 + RVTEST_PMP_BACKGROUND_ENTRY)
#if UDB_MXLEN == 64
  #define RVTEST_PMP_BACKGROUND_CFG_CSR (CSR_PMPCFG0 + (2 * (RVTEST_PMP_BACKGROUND_ENTRY / 8)))
  #define RVTEST_PMP_BACKGROUND_CFG_SHIFT ((RVTEST_PMP_BACKGROUND_ENTRY % 8) * 8)
#else
  #define RVTEST_PMP_BACKGROUND_CFG_CSR (CSR_PMPCFG0 + (RVTEST_PMP_BACKGROUND_ENTRY / 4))
  #define RVTEST_PMP_BACKGROUND_CFG_SHIFT ((RVTEST_PMP_BACKGROUND_ENTRY % 4) * 8)
#endif
#define RVTEST_PMP_BACKGROUND_NAPOT_CFG \
  (((PMP_L | PMP_R | PMP_W | PMP_X | PMP_NAPOT) & 0xFF) << RVTEST_PMP_BACKGROUND_CFG_SHIFT)
#define RVTEST_PMP_BACKGROUND_TOR_CFG \
  (((PMP_L | PMP_R | PMP_W | PMP_X | PMP_TOR) & 0xFF) << RVTEST_PMP_BACKGROUND_CFG_SHIFT)

.macro RVTEST_PMP_SET_BACKGROUND_NAPOT TMP_REG
    LI(\TMP_REG, -1)
    .set rvtest_pmp_background_addr_csr, RVTEST_PMP_BACKGROUND_ADDR_CSR
    csrw rvtest_pmp_background_addr_csr, \TMP_REG
    LI(\TMP_REG, RVTEST_PMP_BACKGROUND_NAPOT_CFG)
    .set rvtest_pmp_background_cfg_csr, RVTEST_PMP_BACKGROUND_CFG_CSR
    csrw rvtest_pmp_background_cfg_csr, \TMP_REG
.endm

.macro RVTEST_PMP_SET_BACKGROUND_TOR TMP_REG
    .if RVTEST_PMP_BACKGROUND_ENTRY > 0
      LI(\TMP_REG, 0)
      .set rvtest_pmp_background_prev_addr_csr, RVTEST_PMP_BACKGROUND_ADDR_CSR - 1
      csrw rvtest_pmp_background_prev_addr_csr, \TMP_REG
    .endif
    LI(\TMP_REG, -1)
    .set rvtest_pmp_background_addr_csr, RVTEST_PMP_BACKGROUND_ADDR_CSR
    csrw rvtest_pmp_background_addr_csr, \TMP_REG
    LI(\TMP_REG, RVTEST_PMP_BACKGROUND_TOR_CFG)
    .set rvtest_pmp_background_cfg_csr, RVTEST_PMP_BACKGROUND_CFG_CSR
    csrw rvtest_pmp_background_cfg_csr, \TMP_REG
.endm

.macro RVTEST_PMP_SET_BACKGROUND TMP_REG
  #ifdef UDB_PMP_NAPOT_SUPPORTED
    RVTEST_PMP_SET_BACKGROUND_NAPOT \TMP_REG
  #elif defined(UDB_PMP_TOR_SUPPORTED)
    RVTEST_PMP_SET_BACKGROUND_TOR \TMP_REG
  #else
    #error "PMP background region requires NAPOT or TOR support"
  #endif
  RVTEST_SFENCE_VMA_IF_SUPPORTED
.endm

//==============================================================================
// Verification macros.
//
// Every macro probes one region and records each probe with RVTEST_SIGUPD, using the
// suite's fixed register convention: x2/x5/x4 for the signature, a4/a5 for the probe
// address and data, ra for the execute-probe resume label, t0 as scratch. Execute
// probes set ra to the label that follows the jump, so the region's `jr ra` and the
// trap handler's resume after a fetch fault both land there. RVTEST_FENCEI precedes
// the first execute probe of a macro that contains one, so a store from an earlier
// probe cannot leave a stale instruction in the I-cache.
//
// Region granules:
//   PMP_TOR_REGION_BYTES    the smallest TOR region, one PMP granule
//   PMP_NAPOT_REGION_BYTES  the smallest NAPOT region, the coverage model's
//                           PMP_NAPOT_REGION_START granularity (8 bytes at grain <= 3)
// XLEN-dependent parts (the written value, doubleword accesses) are selected with .if.
//==============================================================================

#define PMP_TOR_REGION_BYTES   (1 << UDB_PMP_GRANULARITY)
#define PMP_NAPOT_REGION_BYTES (PMP_NAPOT_REGION_PAD_WORDS * 4)

// PMP_LI_RET REG: load the value a store probe writes, a `ret` (jalr x0, 0(ra)) in
// every word so that any word a probe overwrites still returns when executed.
.macro PMP_LI_RET REG
  .if (UDB_MXLEN == 64)
    LI(\REG, 0x0000806700008067)
  .else
    LI(\REG, 0x00008067)
  .endif
.endm

// PMP_PROBE_X ADDR_REG, LABEL, CASE, STR: execute probe. Jumps to ADDR_REG and records
// the outcome under CASE / STR; LABEL is the numeric resume label (1..9).
.macro PMP_PROBE_X ADDR_REG, LABEL, CASE, STR
    LA(ra, \LABEL\()f)
    \CASE:
    jalr x0, 0(\ADDR_REG)
    nop
\LABEL:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \CASE, \STR)
.endm

// PMP_PROBE INSN, DATA_REG, ADDR_REG, CASE, STR: one load or store probe; a4 is recorded.
.macro PMP_PROBE INSN, DATA_REG, ADDR_REG, CASE, STR
    \CASE:
    \INSN \DATA_REG, 0(\ADDR_REG)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \CASE, \STR)
.endm

// PMP_VERIFICATION_X_C: compressed execute probe (c.jalr). Records TEST_CASE_1.
.macro PMP_VERIFICATION_X_C ADDRESS, TEST_CASE
    \TEST_CASE\()_1:
    LA(x15, \ADDRESS)
    c.jalr x15
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
.endm

// PMP_VERIFICATION_CBO: cbo.zero/clean/flush/inval at ADDRESS. Records _1.._4.
.macro PMP_VERIFICATION_CBO ADDRESS, TEST_CASE
    LA(a4, \ADDRESS)
    \TEST_CASE\()_1:
    cbo.zero  (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
    \TEST_CASE\()_2:
    cbo.clean (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)
    \TEST_CASE\()_3:
    cbo.flush (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)
    \TEST_CASE\()_4:
    cbo.inval (a4)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)
.endm

// PMP_VERIFICATION_PREFETCH: prefetch.i/r/w at ADDRESS. Records _1.._3.
.macro PMP_VERIFICATION_PREFETCH ADDRESS, TEST_CASE
    LA(t0, \ADDRESS)
    \TEST_CASE\()_1:
    prefetch.i 0(t0)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
    \TEST_CASE\()_2:
    prefetch.r 0(t0)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)
    \TEST_CASE\()_3:
    prefetch.w 0(t0)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)
.endm

// PMP_VERIFICATION_RWX: execute, word store and word load at ADDRESS.
// Records jalr _1, sw _2, lw _3.
.macro PMP_VERIFICATION_RWX ADDRESS, TEST_CASE
    RVTEST_FENCEI
    LA(a4, \ADDRESS)
    PMP_PROBE_X a4, 1, \TEST_CASE\()_1, test_1_str
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_2, test_2_str
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_3, test_3_str
.endm

// PMP_VERIFICATION_RWX_MPRV: PMP_VERIFICATION_RWX with mstatus.MPRV/MPP re-armed to
// MSTATUS_BITS before every probe, since the trap handler leaves MPP = M on return.
.macro PMP_VERIFICATION_RWX_MPRV ADDRESS, TEST_CASE, MSTATUS_BITS
    RVTEST_FENCEI
    LA(a4, \ADDRESS)
    PMP_ARM_MPRV \MSTATUS_BITS
    PMP_PROBE_X a4, 1, \TEST_CASE\()_1, test_1_str
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    PMP_ARM_MPRV \MSTATUS_BITS
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_2, test_2_str
    PMP_ARM_MPRV \MSTATUS_BITS
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_3, test_3_str
    PMP_ARM_MPRV 0
.endm

// PMP_ARM_MPRV MSTATUS_BITS: clear mstatus.MPRV and MPP, then set MSTATUS_BITS.
.macro PMP_ARM_MPRV MSTATUS_BITS
    LI(t0, (1 << 17) | (3 << 11))
    csrc mstatus, t0
    LI(t0, \MSTATUS_BITS)
    csrs mstatus, t0
.endm

// PMP_VERIFICATION_LW: one word load at ADDRESS. Records _1.
.macro PMP_VERIFICATION_LW ADDRESS, TEST_CASE
    LA(a5, \ADDRESS)
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_1, test_1_str
.endm

// PMP_VERIFICATION_LW_BOUNDS: word loads at ADDRESS, ADDRESS-4 and ADDRESS+BEYOND, the
// first word past a region of BEYOND bytes. Records _1.._3.
.macro PMP_VERIFICATION_LW_BOUNDS ADDRESS, TEST_CASE, BEYOND
    LA(a5, \ADDRESS)
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_1, test_1_str
    addi a5, a5, -4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_2, test_2_str
    LI(t0, (\BEYOND) + 4)
    add a5, a5, t0
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_3, test_3_str
.endm

// PMP_VERIFICATION_RWX_ALL: execute, then every store width, then every load width at
// ADDRESS. Records sb _1, sh _2, sw _3, [sd _4,] lb, lbu, lh, lhu, lw, [lwu, ld,] and the
// jalr last: _9 on RV32, _12 on RV64.
.macro PMP_VERIFICATION_RWX_ALL ADDRESS, TEST_CASE
    RVTEST_FENCEI
    LA(a4, \ADDRESS)
  .if (UDB_MXLEN == 64)
    PMP_PROBE_X a4, 1, \TEST_CASE\()_12, test_12_str
  .else
    PMP_PROBE_X a4, 1, \TEST_CASE\()_9, test_9_str
  .endif
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    PMP_PROBE sb, a4, a5, \TEST_CASE\()_1, test_1_str
    PMP_PROBE sh, a4, a5, \TEST_CASE\()_2, test_2_str
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_3, test_3_str
  .if (UDB_MXLEN == 64)
    PMP_PROBE sd, a4, a5, \TEST_CASE\()_4, test_4_str
    PMP_PROBE lb, a4, a5, \TEST_CASE\()_5, test_5_str
    PMP_PROBE lbu, a4, a5, \TEST_CASE\()_6, test_6_str
    PMP_PROBE lh, a4, a5, \TEST_CASE\()_7, test_7_str
    PMP_PROBE lhu, a4, a5, \TEST_CASE\()_8, test_8_str
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_9, test_9_str
    PMP_PROBE lwu, a4, a5, \TEST_CASE\()_10, test_10_str
    PMP_PROBE ld, a4, a5, \TEST_CASE\()_11, test_11_str
  .else
    PMP_PROBE lb, a4, a5, \TEST_CASE\()_4, test_4_str
    PMP_PROBE lbu, a4, a5, \TEST_CASE\()_5, test_5_str
    PMP_PROBE lh, a4, a5, \TEST_CASE\()_6, test_6_str
    PMP_PROBE lhu, a4, a5, \TEST_CASE\()_7, test_7_str
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_8, test_8_str
  .endif
.endm

// PMP_VERIFICATION_RWX_NA4: execute, word store and word load at ADDRESS, ADDRESS-4 and
// ADDRESS+4, the three words around a 4-byte region. Records jalr _1.._3, then
// sw/lw pairs _4/_5 at ADDRESS, _6/_7 at ADDRESS-4, _8/_9 at ADDRESS+4.
.macro PMP_VERIFICATION_RWX_NA4 ADDRESS, TEST_CASE
    RVTEST_FENCEI
    LA(a4, \ADDRESS)
    PMP_PROBE_X a4, 1, \TEST_CASE\()_1, test_1_str
    addi a4, a4, -4
    PMP_PROBE_X a4, 2, \TEST_CASE\()_2, test_2_str
    addi a4, a4, 8
    PMP_PROBE_X a4, 3, \TEST_CASE\()_3, test_3_str
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_4, test_4_str
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_5, test_5_str
    addi a5, a5, -4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_6, test_6_str
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_7, test_7_str
    addi a5, a5, 8
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_8, test_8_str
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_9, test_9_str
.endm

// PMP_VERIFICATION_RWX_LEGAL: execute, word store and word load at the five words
// around a TOR region of PMP_TOR_REGION_BYTES at ADDRESS: start, start-4, start+4,
// the highest word in the region and the first word beyond it. Records jalr _1.._5,
// sw _6.._10, lw _11.._15, each group in that offset order.
.macro PMP_VERIFICATION_RWX_LEGAL ADDRESS, TEST_CASE
    RVTEST_FENCEI
    LI(t0, PMP_TOR_REGION_BYTES - 8)
    LA(a4, \ADDRESS)
    PMP_PROBE_X a4, 1, \TEST_CASE\()_1, test_1_str
    addi a4, a4, -4
    PMP_PROBE_X a4, 2, \TEST_CASE\()_2, test_2_str
    addi a4, a4, 8
    PMP_PROBE_X a4, 3, \TEST_CASE\()_3, test_3_str
    add a4, a4, t0
    PMP_PROBE_X a4, 4, \TEST_CASE\()_4, test_4_str
    addi a4, a4, 4
    PMP_PROBE_X a4, 5, \TEST_CASE\()_5, test_5_str
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_6, test_6_str
    addi a5, a5, -4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_7, test_7_str
    addi a5, a5, 8
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_8, test_8_str
    add a5, a5, t0
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_9, test_9_str
    addi a5, a5, 4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_10, test_10_str
    LA(a5, \ADDRESS)
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_11, test_11_str
    addi a5, a5, -4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_12, test_12_str
    addi a5, a5, 8
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_13, test_13_str
    add a5, a5, t0
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_14, test_14_str
    addi a5, a5, 4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_15, test_15_str
.endm

// PMP_VERIFICATION_RWX_NAPOT: every store and load width at ADDRESS plus execute, word
// store and word load at the five words around a NAPOT region of PMP_NAPOT_REGION_BYTES.
// Records sb _1, sh _2, sw _3 at start, sw _4.._7 at start-4/start+4/highest/beyond,
// lb _8, lbu _9, lh _10, lhu _11, lw _12 at start, lw _13.._16 at the four offsets,
// jalr _17.._21 at start and the four offsets; on RV64 also sd _22, ld _23, lwu _24 at start.
.macro PMP_VERIFICATION_RWX_NAPOT ADDRESS, TEST_CASE
    RVTEST_FENCEI
    LI(t0, PMP_NAPOT_REGION_BYTES - 8)
    LA(a4, \ADDRESS)
    PMP_PROBE_X a4, 1, \TEST_CASE\()_17, test_17_str
    addi a4, a4, -4
    PMP_PROBE_X a4, 2, \TEST_CASE\()_18, test_18_str
    addi a4, a4, 8
    PMP_PROBE_X a4, 3, \TEST_CASE\()_19, test_19_str
    add a4, a4, t0
    PMP_PROBE_X a4, 4, \TEST_CASE\()_20, test_20_str
    addi a4, a4, 4
    PMP_PROBE_X a4, 5, \TEST_CASE\()_21, test_21_str
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    PMP_PROBE sb, a4, a5, \TEST_CASE\()_1, test_1_str
    PMP_PROBE sh, a4, a5, \TEST_CASE\()_2, test_2_str
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_3, test_3_str
    addi a5, a5, -4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_4, test_4_str
    addi a5, a5, 8
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_5, test_5_str
    add a5, a5, t0
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_6, test_6_str
    addi a5, a5, 4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_7, test_7_str
    LA(a5, \ADDRESS)
    PMP_PROBE lb, a4, a5, \TEST_CASE\()_8, test_8_str
    PMP_PROBE lbu, a4, a5, \TEST_CASE\()_9, test_9_str
    PMP_PROBE lh, a4, a5, \TEST_CASE\()_10, test_10_str
    PMP_PROBE lhu, a4, a5, \TEST_CASE\()_11, test_11_str
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_12, test_12_str
    addi a5, a5, -4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_13, test_13_str
    addi a5, a5, 8
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_14, test_14_str
    add a5, a5, t0
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_15, test_15_str
    addi a5, a5, 4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_16, test_16_str
  .if (UDB_MXLEN == 64)
    LA(a5, \ADDRESS)
    PMP_PROBE sd, a4, a5, \TEST_CASE\()_22, test_22_str
    PMP_PROBE ld, a4, a5, \TEST_CASE\()_23, test_23_str
    PMP_PROBE lwu, a4, a5, \TEST_CASE\()_24, test_24_str
  .endif
.endm

// PMP_VERIFICATION_RWX_TOR_BOT: word store, word load and execute at the four words
// bounding a TOR region [ADDRESS, ADDRESS+PMP_TOR_REGION_BYTES): ADDRESS-4, ADDRESS,
// top-4 and top. Records sw _1.._4, lw _5.._8, jalr _9.._12.
.macro PMP_VERIFICATION_RWX_TOR_BOT ADDRESS, TEST_CASE
    RVTEST_FENCEI
    LI(t0, PMP_TOR_REGION_BYTES - 8)
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    addi a5, a5, -4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_1, test_1_str
    addi a5, a5, 4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_2, test_2_str
    add a5, a5, t0
    addi a5, a5, 4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_3, test_3_str
    addi a5, a5, 4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_4, test_4_str
    LA(a5, \ADDRESS)
    addi a5, a5, -4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_5, test_5_str
    addi a5, a5, 4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_6, test_6_str
    add a5, a5, t0
    addi a5, a5, 4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_7, test_7_str
    addi a5, a5, 4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_8, test_8_str
    LA(a4, \ADDRESS)
    addi a4, a4, -4
    PMP_PROBE_X a4, 1, \TEST_CASE\()_9, test_9_str
    addi a4, a4, 4
    PMP_PROBE_X a4, 2, \TEST_CASE\()_10, test_10_str
    add a4, a4, t0
    addi a4, a4, 4
    PMP_PROBE_X a4, 3, \TEST_CASE\()_11, test_11_str
    addi a4, a4, 4
    PMP_PROBE_X a4, 4, \TEST_CASE\()_12, test_12_str
.endm

// PMP_VERIFICATION_RWX_TOR_ZERO: word store, word load and execute at ADDRESS and
// ADDRESS-4, for a TOR region 0 that spans [0, pmpaddr0). Records sw _1/_2, lw _3/_4,
// jalr _5/_6. The same three accesses are also made at address 0 but not recorded,
// since whether address 0 is memory is platform-defined; a `ret` is stored there first
// so that where it is RAM the execute probe returns.
.macro PMP_VERIFICATION_RWX_TOR_ZERO ADDRESS, TEST_CASE
    LA(a5, \ADDRESS)
    PMP_LI_RET a4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_1, test_1_str
    addi a5, a5, -4
    PMP_PROBE sw, a4, a5, \TEST_CASE\()_2, test_2_str
    LI(a4, 0x00008067)
    LI(a5, 0)
    LA(ra, 7f)
    sw a4, 0(a5)
    nop
7:
    nop
    LA(a5, \ADDRESS)
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_3, test_3_str
    addi a5, a5, -4
    PMP_PROBE lw, a4, a5, \TEST_CASE\()_4, test_4_str
    LI(a5, 0)
    LA(ra, 8f)
    lw a4, 0(a5)
    nop
8:
    nop
    RVTEST_FENCEI
    LA(a4, \ADDRESS)
    PMP_PROBE_X a4, 1, \TEST_CASE\()_5, test_5_str
    addi a4, a4, -4
    PMP_PROBE_X a4, 2, \TEST_CASE\()_6, test_6_str
    LI(a5, 0)
    LA(ra, 9f)
    jalr x0, 0(a5)
    nop
9:
    nop
.endm

// PMP_VERIFICATION_F: every floating-point store and load width at ADDRESS.
// Records fsh _1, fsw _2, fsd _3, flh _4, flw _5, fld _6.
.macro PMP_VERIFICATION_F ADDRESS, TEST_CASE
    LA(a5, \ADDRESS)
    PMP_PROBE fsh, f14, a5, \TEST_CASE\()_1, test_1_str
    PMP_PROBE fsw, f14, a5, \TEST_CASE\()_2, test_2_str
    PMP_PROBE fsd, f14, a5, \TEST_CASE\()_3, test_3_str
    PMP_PROBE flh, f14, a5, \TEST_CASE\()_4, test_4_str
    PMP_PROBE flw, f14, a5, \TEST_CASE\()_5, test_5_str
    PMP_PROBE fld, f14, a5, \TEST_CASE\()_6, test_6_str
.endm

// PMP_AMO_PROBE AMO, WIDTH, CASE, STR: one atomic memory operation on (a5).
.macro PMP_AMO_PROBE AMO, WIDTH, CASE, STR
    \CASE:
    \AMO\().\WIDTH a4, a6, (a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \CASE, \STR)
.endm

// PMP_VERIFICATION_AMO: every Zaamo operation at ADDRESS, word width on RV32 and word
// then doubleword on RV64. Records amoadd, amoand, amoor, amoxor, amomax, amomaxu,
// amomin, amominu, amoswap in that order: _1.._9 on RV32, _1.._18 (w, d pairs) on RV64.
.macro PMP_VERIFICATION_AMO ADDRESS, TEST_CASE
    PMP_LI_RET a6
    LA(a5, \ADDRESS)
  .if (UDB_MXLEN == 64)
    PMP_AMO_PROBE amoadd, w, \TEST_CASE\()_1, test_1_str
    PMP_AMO_PROBE amoadd, d, \TEST_CASE\()_2, test_2_str
    PMP_AMO_PROBE amoand, w, \TEST_CASE\()_3, test_3_str
    PMP_AMO_PROBE amoand, d, \TEST_CASE\()_4, test_4_str
    PMP_AMO_PROBE amoor, w, \TEST_CASE\()_5, test_5_str
    PMP_AMO_PROBE amoor, d, \TEST_CASE\()_6, test_6_str
    PMP_AMO_PROBE amoxor, w, \TEST_CASE\()_7, test_7_str
    PMP_AMO_PROBE amoxor, d, \TEST_CASE\()_8, test_8_str
    PMP_AMO_PROBE amomax, w, \TEST_CASE\()_9, test_9_str
    PMP_AMO_PROBE amomax, d, \TEST_CASE\()_10, test_10_str
    PMP_AMO_PROBE amomaxu, w, \TEST_CASE\()_11, test_11_str
    PMP_AMO_PROBE amomaxu, d, \TEST_CASE\()_12, test_12_str
    PMP_AMO_PROBE amomin, w, \TEST_CASE\()_13, test_13_str
    PMP_AMO_PROBE amomin, d, \TEST_CASE\()_14, test_14_str
    PMP_AMO_PROBE amominu, w, \TEST_CASE\()_15, test_15_str
    PMP_AMO_PROBE amominu, d, \TEST_CASE\()_16, test_16_str
    PMP_AMO_PROBE amoswap, w, \TEST_CASE\()_17, test_17_str
    PMP_AMO_PROBE amoswap, d, \TEST_CASE\()_18, test_18_str
  .else
    PMP_AMO_PROBE amoadd, w, \TEST_CASE\()_1, test_1_str
    PMP_AMO_PROBE amoand, w, \TEST_CASE\()_2, test_2_str
    PMP_AMO_PROBE amoor, w, \TEST_CASE\()_3, test_3_str
    PMP_AMO_PROBE amoxor, w, \TEST_CASE\()_4, test_4_str
    PMP_AMO_PROBE amomax, w, \TEST_CASE\()_5, test_5_str
    PMP_AMO_PROBE amomaxu, w, \TEST_CASE\()_6, test_6_str
    PMP_AMO_PROBE amomin, w, \TEST_CASE\()_7, test_7_str
    PMP_AMO_PROBE amominu, w, \TEST_CASE\()_8, test_8_str
    PMP_AMO_PROBE amoswap, w, \TEST_CASE\()_9, test_9_str
  .endif
.endm

// PMP_LRSC_PROBE WIDTH, LR_CASE, LR_STR, SC_CASE, SC_STR: one LR/SC pair on (a5),
// each half recorded separately. For a region that forbids the access.
.macro PMP_LRSC_PROBE WIDTH, LR_CASE, LR_STR, SC_CASE, SC_STR
    \LR_CASE:
    lr.\WIDTH a2, (a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a2, \LR_CASE, \LR_STR)
    \SC_CASE:
    sc.\WIDTH a2, a2, (a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a2, \SC_CASE, \SC_STR)
.endm

// PMP_LRSC_RETRY_PROBE WIDTH, TAG, LR_CASE, LR_STR, SC_CASE, SC_STR: one LR/SC pair on
// (a5) retried up to 100 times until the SC succeeds. For a region that allows the
// access, where a constrained loop is the only way to make the SC outcome deterministic.
.macro PMP_LRSC_RETRY_PROBE WIDTH, TAG, LR_CASE, LR_STR, SC_CASE, SC_STR
    LI(t2, 100)
\TAG\()_retry:
    \LR_CASE:
    lr.\WIDTH a3, (a5)
    \SC_CASE:
    sc.\WIDTH a2, a3, (a5)
    beqz a2, \TAG\()_success
    addi t2, t2, -1
    bnez t2, \TAG\()_retry
\TAG\()_success:
    RVTEST_SIGUPD(x2, x5, x4, a3, \LR_CASE, \LR_STR)
    RVTEST_SIGUPD(x2, x5, x4, a2, \SC_CASE, \SC_STR)
.endm

// PMP_VERIFICATION_LRSC: LR/SC at ADDRESS where the region forbids the access.
// Records lr.w _1, sc.w _2 and on RV64 lr.d _3, sc.d _4.
.macro PMP_VERIFICATION_LRSC ADDRESS, TEST_CASE
    LA(a5, \ADDRESS)
    PMP_LRSC_PROBE w, \TEST_CASE\()_1, test_1_str, \TEST_CASE\()_2, test_2_str
  .if (UDB_MXLEN == 64)
    PMP_LRSC_PROBE d, \TEST_CASE\()_3, test_3_str, \TEST_CASE\()_4, test_4_str
  .endif
.endm

// PMP_VERIFICATION_LRSC_SUCCESS: the same probes for a region that allows the access.
.macro PMP_VERIFICATION_LRSC_SUCCESS ADDRESS, TEST_CASE
    LA(a5, \ADDRESS)
    PMP_LRSC_RETRY_PROBE w, \TEST_CASE\()_w, \TEST_CASE\()_1, test_1_str, \TEST_CASE\()_2, test_2_str
  .if (UDB_MXLEN == 64)
    PMP_LRSC_RETRY_PROBE d, \TEST_CASE\()_d, \TEST_CASE\()_3, test_3_str, \TEST_CASE\()_4, test_4_str
  .endif
.endm

// PMP_C_PROBE INSN, DATA_REG, ADDR_REG, CASE, STR: one compressed load or store probe.
.macro PMP_C_PROBE INSN, DATA_REG, ADDR_REG, CASE, STR
    \CASE:
    \INSN \DATA_REG, 0(\ADDR_REG)
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \CASE, \STR)
.endm

// PMP_C_SP_PROBES STORE, LOAD, DATA_REG: the stack-pointer forms of a compressed
// store/load pair against the address in x8, not recorded.
.macro PMP_C_SP_PROBES STORE, LOAD, DATA_REG
    mv t0, sp
    addi sp, x8, 0
    \STORE \DATA_REG, 0(sp)
    c.nop
    c.nop
    \LOAD \DATA_REG, 0(sp)
    c.nop
    c.nop
    mv sp, t0
.endm

// PMP_VERIFICATION_ZCA: compressed word store/load, execute, and on RV64 doubleword
// store/load at ADDRESS, each also issued through sp. Records c.sw _1, c.lw _2,
// c.jalr _3, and on RV64 c.sd _4, c.ld _5.
.macro PMP_VERIFICATION_ZCA ADDRESS, TEST_CASE
    RVTEST_FENCEI
    LA(x15, \ADDRESS)
    LA(ra, 1f)
    \TEST_CASE\()_3:
    c.jalr x15
    c.nop
    c.nop
1:
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)
    LI(x15, 0x00010001)
    LA(x8, \ADDRESS)
    PMP_C_PROBE c.sw, x15, x8, \TEST_CASE\()_1, test_1_str
    PMP_C_PROBE c.lw, x15, x8, \TEST_CASE\()_2, test_2_str
    PMP_C_SP_PROBES c.swsp, c.lwsp, x15
  .if (UDB_MXLEN == 64)
    LI(x15, 0x0001000100010001)
    PMP_C_PROBE c.sd, x15, x8, \TEST_CASE\()_4, test_4_str
    PMP_C_PROBE c.ld, x15, x8, \TEST_CASE\()_5, test_5_str
    PMP_C_SP_PROBES c.sdsp, c.ldsp, x15
  .endif
.endm

// PMP_VERIFICATION_ZCB: the Zcb compressed byte and halfword loads and stores at
// ADDRESS. Records c.sb _1, c.lbu _2, c.sh _3, c.lhu _4, c.sh _5, c.lh _6.
.macro PMP_VERIFICATION_ZCB ADDRESS, TEST_CASE
    LI(x15, NOP)
    LA(x8, \ADDRESS)
    PMP_C_PROBE c.sb, x15, x8, \TEST_CASE\()_1, test_1_str
    PMP_C_PROBE c.lbu, x15, x8, \TEST_CASE\()_2, test_2_str
    PMP_C_PROBE c.sh, x15, x8, \TEST_CASE\()_3, test_3_str
    PMP_C_PROBE c.lhu, x15, x8, \TEST_CASE\()_4, test_4_str
    PMP_C_PROBE c.sh, x15, x8, \TEST_CASE\()_5, test_5_str
    PMP_C_PROBE c.lh, x15, x8, \TEST_CASE\()_6, test_6_str
.endm

// PMP_VERIFICATION_ZCD: c.fsd / c.fld at ADDRESS, also through sp. Records _1, _2.
.macro PMP_VERIFICATION_ZCD ADDRESS, TEST_CASE
    li x15, 0x3f800000
    fmv.w.x f8, x15
    LA(x8, \ADDRESS)
    PMP_C_PROBE c.fsd, f8, x8, \TEST_CASE\()_1, test_1_str
    PMP_C_PROBE c.fld, f8, x8, \TEST_CASE\()_2, test_2_str
    PMP_C_SP_PROBES c.fsdsp, c.fldsp, f8
.endm

// PMP_VERIFICATION_ZCF: c.fsw / c.flw at ADDRESS, also through sp. Records _1, _2.
.macro PMP_VERIFICATION_ZCF ADDRESS, TEST_CASE
    li x15, 0x3f800000
    fmv.w.x f8, x15
    LA(x8, \ADDRESS)
    PMP_C_PROBE c.fsw, f8, x8, \TEST_CASE\()_1, test_1_str
    PMP_C_PROBE c.flw, f8, x8, \TEST_CASE\()_2, test_2_str
    PMP_C_SP_PROBES c.fswsp, c.flwsp, f8
.endm
