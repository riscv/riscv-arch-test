// derived_config.h
// Derived test configuration macros built from the UDB-generated rvtest_config.h.
// These represent values that are not directly emitted by UDB but are computed
// from UDB primitives.
// SPDX-License-Identifier: Apache-2.0

#ifndef DERIVED_CONFIG_H
#define DERIVED_CONFIG_H

// Emulate time/timeh reads from mtime.
#if defined(ZICNTR_SUPPORTED) && !defined(UDB_TIME_CSR_IMPLEMENTED)
  #define RVTEST_EMULATE_TIME_CSR
#endif

// MAXINDEXEEW: maximum supported index element width for indexed vector load/store.
// UDB exposes one of:
//   UDB_VECTOR_LS_INDEX_MAX_EEW_XLEN     -> MAXINDEXEEW = MXLEN
//   UDB_VECTOR_LS_INDEX_MAX_EEW_8|_16|_32|_64
#if defined(UDB_VECTOR_LS_INDEX_MAX_EEW_XLEN)
  #define MAXINDEXEEW UDB_MXLEN
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_64)
  #define MAXINDEXEEW 64
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_32)
  #define MAXINDEXEEW 32
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_16)
  #define MAXINDEXEEW 16
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_8)
  #define MAXINDEXEEW 8
#endif

// MSECCFG_SUPPORTED: the mseccfg / mseccfgh CSRs exist when at least one of
// Zkr, Smmpm, Zicfilp, or Smepmp are implemented.
#if defined(ZKR_SUPPORTED) || defined(SMMPM_SUPPORTED) || defined(ZICFILP_SUPPORTED) || defined(SMEPMP_SUPPORTED)
  #define MSECCFG_SUPPORTED
#endif

// Cumulative privileged ISA version defines
#if defined(S1P13P0_SUPPORTED)
  #define S1P12P0_OR_LATER_SUPPORTED
  #define S1P13P0_OR_LATER_SUPPORTED
#elif defined(S1P12P0_SUPPORTED)
  #define S1P12P0_OR_LATER_SUPPORTED
#endif

#if defined(SM1P13P0_SUPPORTED)
  #define SM1P12P0_OR_LATER_SUPPORTED
  #define SM1P13P0_OR_LATER_SUPPORTED
#elif defined(SM1P12P0_SUPPORTED)
  #define SM1P12P0_OR_LATER_SUPPORTED
#endif

// RVTEST_SGEI_INTR_IMPL: supervisor guest external interrupts exist when H is implemented with
// GEILEN (NUM_EXTERNAL_GUEST_INTERRUPTS) > 0. check_defines.h then requires
// RVMODEL_SET/CLR_GUEST_EXT_INT, since hgeip is read-only and only the platform can raise it.
#if defined(H_SUPPORTED) && defined(UDB_NUM_EXTERNAL_GUEST_INTERRUPTS)
  #if UDB_NUM_EXTERNAL_GUEST_INTERRUPTS > 0
    #define RVTEST_SGEI_INTR_IMPL
  #endif
#endif

// MENVCFG_CBIE_ENABLE: menvcfg with its 2-bit CBIE field (bits 5:4) set to the value that enables
// cbo.inval. It is positioned like MENVCFG_CBIE so it can be ORed with MENVCFG_CBCFE and MENVCFG_CBZE.
// Normally CBIE = 11 (invalidate). With FORCE_UPGRADE_CBO_INVAL_TO_FLUSH the only legal values are
// 00 and 01, so use CBIE = 01 (flush): writing 11 would leave the result to the implementation's
// legalization.
#ifdef UDB_FORCE_UPGRADE_CBO_INVAL_TO_FLUSH
  #define MENVCFG_CBIE_ENABLE (1 << 4)     // CBIE = 01
#else
  #define MENVCFG_CBIE_ENABLE MENVCFG_CBIE // CBIE = 11
#endif

#endif // DERIVED_CONFIG_H
