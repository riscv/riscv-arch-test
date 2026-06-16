// Page Table Macros

/* Set up the Page table entry for Sv32 Translation scheme
    Arguments:
    _PAR: Register containing Physical Address
    _PR: Register containing Permissions for Leaf PTE.
        (Note: No-leaf PTE (if-any) has only valid permission (pte.v) set)
    _TR0, _TR1, _TR2: Temporary registers used and modified by function
    VA: Virtual address
    level: Level at which PTE would be setup
        0: Two level translation
        1: Superpage
*/

#define LEVEL0 0x00
#define LEVEL1 0x01
#define LEVEL2 0x02
#define LEVEL3 0x03
#define LEVEL4 0x04

#define sv39 0x00
#define sv48 0x01
#define sv57 0x02

#define CODE code_bgn_off
#define DATA data_bgn_off
#define SIG  sig_bgn_off
#define VMEM vmem_bgn_off


//****NOTE: label `rvtest_Sroot_pg_tbl` must be declared after RVTEST_DATA_END
//          in the test aligned at 4kiB (use .align 12)
#define PTE_SETUP_COMMON(_PAR, _PR, _TR0, _TR1, _VAR, level)      ;\
    srli _VAR, _VAR, (RISCV_PGLEVEL_BITS * level + RISCV_PGSHIFT) ;\
    srli _PAR, _PAR, (RISCV_PGLEVEL_BITS * level + RISCV_PGSHIFT) ;\
    slli _PAR, _PAR, (RISCV_PGLEVEL_BITS * level + RISCV_PGSHIFT) ;\
    LI(_TR0, ((1 << RISCV_PGLEVEL_BITS) - 1))                     ;\
    and _VAR, _VAR, _TR0                                          ;\
    slli _VAR, _VAR, ((UDB_MXLEN >> 5)+1)                         ;\
    add _TR1, _TR1, _VAR                                          ;\
    srli _PAR, _PAR, 12                                           ;\
    slli _PAR, _PAR, 10                                           ;\
    or _PAR, _PAR, _PR                                            ;\
    SREG _PAR, 0(_TR1);

// Replaces page offset of VA with PA page offset (depending on
// the PAGE_LEVEL) and stores it to S save area. a0 must
// point to M save area. t0 and t1 are clobbered
#define SAVE_AREA_SETUP(VA, PA_LBL, _REG_NAME, PAGE_LEVEL)      ;\
    .if (__riscv_xlen == 32)                                    ;\
        .set PAGE_OFFSET_SHIFT, (PAGE_LEVEL*10)+12              ;\
    .else                                                       ;\
        .set PAGE_OFFSET_SHIFT, (PAGE_LEVEL*9)+12               ;\
    .endif                                                      ;\
    LI(  t0, VA)                                                ;\
    srli t0, t0, PAGE_OFFSET_SHIFT                              ;\
    slli t0, t0, PAGE_OFFSET_SHIFT                              ;\
    LA(  t1, PA_LBL)                                            ;\
    slli t1, t1, __riscv_xlen-PAGE_OFFSET_SHIFT                 ;\
    srli t1, t1, __riscv_xlen-PAGE_OFFSET_SHIFT                 ;\
    or   t0, t0, t1                                             ;\
    SREG t0, _REG_NAME##_bgn_off+1*sv_area_sz(a0)               ;

// Replaces page offset of VA with PA page offset (depending on
// the PAGE_LEVEL) and stores it to V save area. a0 must
// point to M save area. t0 and t1 are clobbered
#define GUEST_SAVE_AREA_SETUP(VA, PA_LBL, _REG_NAME, PAGE_LEVEL);\
    .if (__riscv_xlen == 32)                                    ;\
        .set PAGE_OFFSET_SHIFT, (PAGE_LEVEL*10)+12              ;\
    .else                                                       ;\
        .set PAGE_OFFSET_SHIFT, (PAGE_LEVEL*9)+12               ;\
    .endif                                                      ;\
    LI(  t0, VA)                                                ;\
    srli t0, t0, PAGE_OFFSET_SHIFT                              ;\
    slli t0, t0, PAGE_OFFSET_SHIFT                              ;\
    LA(  t1, PA_LBL)                                            ;\
    slli t1, t1, __riscv_xlen-PAGE_OFFSET_SHIFT                 ;\
    srli t1, t1, __riscv_xlen-PAGE_OFFSET_SHIFT                 ;\
    or   t0, t0, t1                                             ;\
    addi a0, a0, 2*sv_area_sz                                   ;\
    SREG t0, _REG_NAME##_bgn_off+1*sv_area_sz(a0)               ;\
    addi a0, a0, -2*sv_area_sz                                  ;

#define PTE_SETUP_RV32(_PAR, _PR, _TR0, _TR1, VA, level)        ;\
    srli _PAR, _PAR, 12                                         ;\
    slli _PAR, _PAR, 10                                         ;\
    or _PAR, _PAR, _PR                                          ;\
    .if (level==1)                                              ;\
        LA(_TR1, rvtest_Sroot_pg_tbl)                           ;\
        LI(_TR0, ((VA>>22)&0x3FF)<<2)                           ;\
    .endif                                                      ;\
    .if (level==0)                                              ;\
        LA(_TR1, rvtest_slvl0_pg_tbl)                           ;\
        LI(_TR0, ((VA>>12)&0x3FF)<<2)                           ;\
    .endif                                                      ;\
    add _TR1, _TR1, _TR0                                        ;\
    SREG _PAR, 0(_TR1)                                          ;

#define PTE_SETUP_RV64(_PAR, _PR, _TR0, _TR1, VA, level, mode)  ;\
    srli _PAR, _PAR, 12                                         ;\
    slli _PAR, _PAR, 10                                         ;\
    or _PAR, _PAR, _PR                                          ;\
    .if (mode == sv39)                                          ;\
        .if (level == 2)                                        ;\
            LA(_TR1, rvtest_Sroot_pg_tbl)                       ;\
            .set vpn, ((VA >> 30) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 1)                                        ;\
            LA(_TR1, rvtest_slvl1_pg_tbl)                       ;\
            .set vpn, ((VA >> 21) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 0)                                        ;\
            LA(_TR1, rvtest_slvl0_pg_tbl)                       ;\
            .set vpn, ((VA >> 12) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
    .endif                                                      ;\
    .if (mode == sv48)                                          ;\
        .if (level == 3)                                        ;\
            LA(_TR1, rvtest_Sroot_pg_tbl)                       ;\
            .set vpn, ((VA >> 39) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 2)                                        ;\
            LA(_TR1, rvtest_slvl2_pg_tbl)                       ;\
            .set vpn, ((VA >> 30) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 1)                                        ;\
            LA(_TR1, rvtest_slvl1_pg_tbl)                       ;\
            .set vpn, ((VA >> 21) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 0)                                        ;\
            LA(_TR1, rvtest_slvl0_pg_tbl)                       ;\
            .set vpn, ((VA >> 12) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
    .endif                                                      ;\
    .if (mode == sv57)                                          ;\
        .if (level == 4)                                        ;\
            LA(_TR1, rvtest_Sroot_pg_tbl)                       ;\
            .set vpn, ((VA >> 48) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 3)                                        ;\
            LA(_TR1, rvtest_slvl3_pg_tbl)                       ;\
            .set vpn, ((VA >> 39) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 2)                                        ;\
            LA(_TR1, rvtest_slvl2_pg_tbl)                       ;\
            .set vpn, ((VA >> 30) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 1)                                        ;\
            LA(_TR1, rvtest_slvl1_pg_tbl)                       ;\
            .set vpn, ((VA >> 21) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
        .if (level == 0)                                        ;\
            LA(_TR1, rvtest_slvl0_pg_tbl)                       ;\
            .set vpn, ((VA >> 12) & 0x1FF) << 3                 ;\
        .endif                                                  ;\
    .endif                                                      ;\
    LI(_TR0, vpn)                                               ;\
    add _TR1, _TR1, _TR0                                        ;\
    SREG _PAR, 0(_TR1)                                          ;

#define PTE_SETUP_SV32(PA_LBL, PERMS, VA, level)                ;\
    LA(a0, PA_LBL)                                              ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV32(a0, a1, t0, t1, VA, level)                   ;

#define SUPERPAGE_PTE_SETUP_SV32(PA_LBL, PERMS, VA, level)      ;\
    LA(a0, (PA_LBL))                                            ;\
    srli a0, a0, 22                                             ;\
    slli a0, a0, 22                                             ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV32(a0, a1, t0, t1, VA, level)                   ;

#define PTE_SETUP_SV39(PA_LBL, PERMS, VA, level)                ;\
    LA(a0, PA_LBL)                                              ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV64(a0, a1, t0, t1, VA, level, sv39)             ;

#define SUPERPAGE_PTE_SETUP_SV39(PA_LBL, PERMS, VA, level)      ;\
    .set PA_SHIFT, (level*9)+12                                 ;\
    LA(a0, (PA_LBL))                                            ;\
    srli a0, a0, PA_SHIFT                                       ;\
    slli a0, a0, PA_SHIFT                                       ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV64(a0, a1, t0, t1, VA, level, sv39)             ;

#define PTE_SETUP_SV48(PA_LBL, PERMS, VA, level)                ;\
    LA(a0, PA_LBL)                                              ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV64(a0, a1, t0, t1, VA, level, sv48)             ;

#define SUPERPAGE_PTE_SETUP_SV48(PA_LBL, PERMS, VA, level)      ;\
    .set PA_SHIFT, (level*9)+12                                 ;\
    LA(a0, (PA_LBL))                                            ;\
    srli a0, a0, PA_SHIFT                                       ;\
    slli a0, a0, PA_SHIFT                                       ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV64(a0, a1, t0, t1, VA, level, sv48)             ;

#define PTE_SETUP_SV57(PA_LBL, PERMS, VA, level)                ;\
    LA(a0, PA_LBL)                                              ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV64(a0, a1, t0, t1, VA, level, sv57)             ;

#define SUPERPAGE_PTE_SETUP_SV57(PA_LBL, PERMS, VA, level)      ;\
    .set PA_SHIFT, (level*9)+12                                 ;\
    LA(a0, (PA_LBL))                                            ;\
    srli a0, a0, PA_SHIFT                                       ;\
    slli a0, a0, PA_SHIFT                                       ;\
    LI(a1, PERMS)                                               ;\
    PTE_SETUP_RV64(a0, a1, t0, t1, VA, level, sv57)             ;

#define PTE_PERMUPD_RV32(_PR, _TR0, _TR1, VA, level)            ;\
    .if (level==1)                                              ;\
        LA(_TR1, rvtest_Sroot_pg_tbl)                           ;\
        .set vpn, ((VA>>22)&0x3FF)<<2                           ;\
    .endif                                                      ;\
    .if (level==0)                                              ;\
        LA(_TR1, rvtest_slvl1_pg_tbl)                           ;\
        .set vpn, ((VA>>12)&0x3FF)<<2                           ;\
    .endif                                                      ;\
    LI(_TR0, vpn)                                               ;\
    add _TR1, _TR1, _TR0                                        ;\
    LREG _TR0, 0(_TR1)                                          ;\
    srli _TR0, _TR0, 10                                         ;\
    slli _TR0, _TR0, 10                                         ;\
    or _TR0, _TR0, _PR                                          ;\
    SREG _TR0, 0(_TR1)                                          ;

#define SATP_SETUP_SV32                                         ;\
    LA(t6, rvtest_Sroot_pg_tbl)                                 ;\
    LI(t5, SATP32_MODE)                                         ;\
    srli t6, t6, 12                                             ;\
    or t6, t6, t5                                               ;\
    csrw satp, t6                                               ;

#define SATP_SETUP_RV64(MODE)                                   ;\
    LA(t6, rvtest_Sroot_pg_tbl)                                 ;\
    .if (MODE == sv39)                                          ;\
    LI(t5, (SATP64_MODE) & (SATP_MODE_SV39 << 60))              ;\
    .endif                                                      ;\
    .if (MODE == sv48)                                          ;\
    LI(t5, (SATP64_MODE) & (SATP_MODE_SV48 << 60))              ;\
    .endif                                                      ;\
    .if (MODE == sv57)                                          ;\
    LI(t5, (SATP64_MODE) & (SATP_MODE_SV57 << 60))              ;\
    .endif                                                      ;\
    srli t6, t6, 12                                             ;\
    or t6, t6, t5                                               ;\
    csrw satp, t6                                               ;

//==============================================================================
// PMP R/W/X verification macros
//
// Shared, centralized versions of the per-test VERIFICATION_* macros used by
// the PMP test suite (tests/priv/pmp/...). Each macro probes how a PMP-protected
// region responds to execute / store / load accesses and records the outcome
// with RVTEST_SIGUPD.
//
// Defined here (instead of redefined in every test) so that cross-cutting fixes
// — e.g. inserting RVMODEL_FENCEI to sync the I-cache after writing executable
// code — are made in one place. RVMODEL_FENCEI is self-disabling: it expands to
// fence.i only when Zifencei is supported, otherwise to nop, so it is always
// safe to include.
//
// Contract for callers (must hold in each test that uses these):
//   - The signature pointer / temp registers x2, x5, x4 follow suite convention.
//   - The string label(s) test_<n>_str referenced below are defined in the
//     test's RVTEST_DATA section.
//   - `g` (PMP granule, 1<<UDB_PMP_GRANULARITY) is defined where a macro uses it.
//
// These are GAS (.macro) definitions; a test that uses one must NOT also define
// a local .macro of the same name (GAS errors on macro redefinition).
//==============================================================================

// rvtest_macros.h is included before rvtest_trap_handler.h (where RVMODEL_FENCEI is
// normally defined), so define it here too. The #ifndef guard makes the later
// definition in rvtest_trap_handler.h a no-op; ZIFENCEI_SUPPORTED comes from the
// already-included derived_config.h. Keep this in sync with rvtest_trap_handler.h.
#ifndef   RVMODEL_FENCEI
  #ifndef ZIFENCEI_SUPPORTED
       #define RVMODEL_FENCEI nop                // no Zifencei: assume coherent I-cache
  #else
       #define RVMODEL_FENCEI fence.i            // Zifencei available: use fence.i
  #endif
#endif

// VERIFICATION_X_C: compressed execute-only check.
// Jumps (c.jalr) to ADDRESS and records whether execution was permitted.
// No store occurs, so no RVMODEL_FENCEI is required.
//   ADDRESS   - region label to execute from
//   TEST_CASE - prefix for the local result label (TEST_CASE_1)
.macro VERIFICATION_X_C ADDRESS, TEST_CASE
    \TEST_CASE\()_1:
    LA(x15, \ADDRESS)               // Address to be verified
    c.jalr x15
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
.endm

// VERIFICATION_CBO: cache-block-operation permission check (the Zicbo cbo_wr family).
// Runs cbo.zero/clean/flush/inval on ADDRESS and records each outcome. No jump and no
// ordinary store, so no RVMODEL_FENCEI is required. XLEN-independent.
//   ADDRESS   - cache-block-aligned region label
//   TEST_CASE - prefix for the local result labels (TEST_CASE_1 .. _4)
.macro VERIFICATION_CBO ADDRESS, TEST_CASE
    // Address must be aligned to the cache block
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

// VERIFICATION_RWX_ALL_RV32 / _RV64: all-access-width R/W/X check (the cfg_XWR_all
// family). Execute-first: probe execution, then every store width, then every load
// width, recording each outcome. RVMODEL_FENCEI syncs the I-cache before the jump in
// case a prior invocation's store updated this executable region.
// XLEN-suffixed because RV64 additionally exercises doubleword accesses (sd/lwu/ld)
// and uses DOUBLE_NOP; RV32 uses NOP. Each referenced test_<n>_str must be defined
// in the test, and SIGUPD_COUNT sized accordingly (RV32: 9 cases, RV64: 12).
//   ADDRESS   - region label to probe
//   TEST_CASE - prefix for the local result labels
.macro VERIFICATION_RWX_ALL_RV32 ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x1, 1f)                            // Store the return Address in x1
    RVMODEL_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_9:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    LI(a4, NOP)                                              // Value to write (NOP)
    \TEST_CASE\()_1:
    sb a4, 0(a5)                                             // Byte-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
    \TEST_CASE\()_2:
    sh a4, 0(a5)                                             // Half-word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)
    \TEST_CASE\()_3:
    sw a4, 0(a5)                                             // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    // Load Access Check
    \TEST_CASE\()_4:
    lb a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)                                   // Signature update
    \TEST_CASE\()_5:
    lbu a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                  // Signature update
    \TEST_CASE\()_6:
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                   // Signature update
    \TEST_CASE\()_7:
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                  // Signature update
    \TEST_CASE\()_8:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update
.endm

.macro VERIFICATION_RWX_ALL_RV64 ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x1, 1f)                            // Store the return Address in x1
    RVMODEL_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_12:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    \TEST_CASE\()_1:
    sb a4, 0(a5)                                             // Byte-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
    \TEST_CASE\()_2:
    sh a4, 0(a5)                                             // Half-word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)
    \TEST_CASE\()_3:
    sw a4, 0(a5)                                             // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)
    \TEST_CASE\()_4:
    sd a4, 0(a5)                                             // Doubleword store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    // Load Access Check
    \TEST_CASE\()_5:
    lb a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                   // Signature update
    \TEST_CASE\()_6:
    lbu a4, 0(a5)                                             // Byte-level load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                  // Signature update
    \TEST_CASE\()_7:
    lh a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                   // Signature update
    \TEST_CASE\()_8:
    lhu a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                  // Signature update
    \TEST_CASE\()_9:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update
    \TEST_CASE\()_10:
    lwu a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update
    \TEST_CASE\()_11:
    ld a4, 0(a5)                                             // Doubleword load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)                                   // Signature update
.endm
