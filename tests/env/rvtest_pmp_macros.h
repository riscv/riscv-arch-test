// rvtest_pmp_macros.h
// PMP setup constants and background-region macros.
// SPDX-License-Identifier: Apache-2.0
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
// Region constants
//==============================================================================

#define PMP_TOR_REGION_BYTES   (1 << UDB_PMP_GRANULARITY)
#define PMP_NAPOT_REGION_BYTES (PMP_NAPOT_REGION_PAD_WORDS * 4)

#if UDB_MXLEN == 64
  #define RVTEST_PMP_RET_ENCODING 0x0000806700008067
#else
  #define RVTEST_PMP_RET_ENCODING 0x00008067
#endif
