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
//   UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_8|_16|_32|_64
#if defined(UDB_VECTOR_LS_INDEX_MAX_EEW_XLEN)
  #define MAXINDEXEEW UDB_MXLEN
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_64)
  #define MAXINDEXEEW 64
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_32)
  #define MAXINDEXEEW 32
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_16)
  #define MAXINDEXEEW 16
#elif defined(UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_8)
  #define MAXINDEXEEW 8
#endif

#endif // DERIVED_CONFIG_H
