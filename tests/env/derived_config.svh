// derived_config.svh
// Derived test configuration macros built from the UDB-generated rvtest_config.svh.
// SystemVerilog `define forms; mirrors derived_config.h plus extra coverpoint flags
// (SEW<N>_SUPPORTED, LMULf<N>_SUPPORTED, MAXINDEXEEW<N>) needed by .svh consumers.
// SPDX-License-Identifier: Apache-2.0

`ifndef DERIVED_CONFIG_SVH
`define DERIVED_CONFIG_SVH

// ---- SEW<N>_SUPPORTED ----
// Per the V spec, every power-of-two SEW between SEW_MIN and ELEN inclusive
// must be supported. So SEW<N>_SUPPORTED iff SEW_MIN <= N <= ELEN.
`ifdef UDB_SEW_MIN_8
  `define SEW8_SUPPORTED
  `ifdef UDB_ELEN_16
    `define SEW16_SUPPORTED
  `endif
  `ifdef UDB_ELEN_32
    `define SEW16_SUPPORTED
    `define SEW32_SUPPORTED
  `endif
  `ifdef UDB_ELEN_64
    `define SEW16_SUPPORTED
    `define SEW32_SUPPORTED
    `define SEW64_SUPPORTED
  `endif
`endif
`ifdef UDB_SEW_MIN_16
  `ifdef UDB_ELEN_16
    `define SEW16_SUPPORTED
  `endif
  `ifdef UDB_ELEN_32
    `define SEW16_SUPPORTED
    `define SEW32_SUPPORTED
  `endif
  `ifdef UDB_ELEN_64
    `define SEW16_SUPPORTED
    `define SEW32_SUPPORTED
    `define SEW64_SUPPORTED
  `endif
`endif
`ifdef UDB_SEW_MIN_32
  `ifdef UDB_ELEN_32
    `define SEW32_SUPPORTED
  `endif
  `ifdef UDB_ELEN_64
    `define SEW32_SUPPORTED
    `define SEW64_SUPPORTED
  `endif
`endif
`ifdef UDB_SEW_MIN_64
  `ifdef UDB_ELEN_64
    `define SEW64_SUPPORTED
  `endif
`endif

// ---- LMULf<N>_SUPPORTED ----
// Smallest fractional LMUL is SEW_MIN/ELEN. LMULf<N> means LMUL = 1/N is
// supported, which requires SEW_MIN * N <= ELEN.
`ifdef UDB_SEW_MIN_8
  `ifdef UDB_ELEN_16
    `define LMULf2_SUPPORTED
  `endif
  `ifdef UDB_ELEN_32
    `define LMULf2_SUPPORTED
    `define LMULf4_SUPPORTED
  `endif
  `ifdef UDB_ELEN_64
    `define LMULf2_SUPPORTED
    `define LMULf4_SUPPORTED
    `define LMULf8_SUPPORTED
  `endif
`endif
`ifdef UDB_SEW_MIN_16
  `ifdef UDB_ELEN_32
    `define LMULf2_SUPPORTED
  `endif
  `ifdef UDB_ELEN_64
    `define LMULf2_SUPPORTED
    `define LMULf4_SUPPORTED
  `endif
`endif
`ifdef UDB_SEW_MIN_32
  `ifdef UDB_ELEN_64
    `define LMULf2_SUPPORTED
  `endif
`endif

// ---- MAXINDEXEEW<N> ----
// One-of selector consumed by RISCV_coverage_common.svh, which derives both
// the numeric `MAXINDEXEEW` and the `MAXINDEXEEW_GE<N>` ladder from this.
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_XLEN
  `ifdef UDB_MXLEN_32
    `define MAXINDEXEEW32
  `endif
  `ifdef UDB_MXLEN_64
    `define MAXINDEXEEW64
  `endif
`endif
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_64
  `define MAXINDEXEEW64
`endif
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_32
  `define MAXINDEXEEW32
`endif
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_16
  `define MAXINDEXEEW16
`endif
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_EXPLICIT_8
  `define MAXINDEXEEW8
`endif

// ---- MSECCFG_SUPPORTED ----
// The mseccfg / mseccfgh CSRs exist when at least one of Zkr, Smmpm, Zicfilp, or Smepmp are implemented.
`ifdef ZKR_SUPPORTED
  `define MSECCFG_SUPPORTED
`elsif SMMPM_SUPPORTED
  `define MSECCFG_SUPPORTED
`elsif ZICFILP_SUPPORTED
  `define MSECCFG_SUPPORTED
`elsif SMEPMP_SUPPORTED
  `define MSECCFG_SUPPORTED
`endif

`endif // DERIVED_CONFIG_SVH
