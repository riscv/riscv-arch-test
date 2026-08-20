// derived_config.h
// Derived test configuration macros built from the UDB-generated rvtest_config.h.
// These represent values that are not directly emitted by UDB but are computed
// from UDB primitives.
// SPDX-License-Identifier: Apache-2.0

#ifndef DERIVED_CONFIG_H
#define DERIVED_CONFIG_H

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

#endif // DERIVED_CONFIG_H
