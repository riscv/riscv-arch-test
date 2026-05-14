// derived_config.svh
// Derived test configuration macros built from the UDB-generated rvtest_config.svh.
// SystemVerilog `define forms; mirrors derived_config.h plus extra coverpoint flags
// (SEW<N>_SUPPORTED, LMULf<N>_SUPPORTED, MAXINDEXEEW<N>) needed by .svh consumers.
// SPDX-License-Identifier: Apache-2.0

`ifndef DERIVED_CONFIG_SVH
`define DERIVED_CONFIG_SVH

// ---- SEW<N>_SUPPORTED ----
// SEW8 is always supported when V/Zve* is present (ELEN >= 8 is always true).
// Wider SEWs are gated on UDB_ELEN_<N>.
`ifdef V_SUPPORTED
  `define SEW8_SUPPORTED
`endif
`ifdef ZVE32X_SUPPORTED
  `define SEW8_SUPPORTED
`endif
`ifdef ZVE32F_SUPPORTED
  `define SEW8_SUPPORTED
`endif
`ifdef ZVE64X_SUPPORTED
  `define SEW8_SUPPORTED
`endif
`ifdef ZVE64F_SUPPORTED
  `define SEW8_SUPPORTED
`endif
`ifdef ZVE64D_SUPPORTED
  `define SEW8_SUPPORTED
`endif
`ifdef SEW8_SUPPORTED
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

// ---- LMULf<N>_SUPPORTED: VLEN >= 8*N ----
`ifdef UDB_VLEN_16
  `define LMULf2_SUPPORTED
`endif
`ifdef UDB_VLEN_32
  `define LMULf2_SUPPORTED
  `define LMULf4_SUPPORTED
`endif
`ifdef UDB_VLEN_64
  `define LMULf2_SUPPORTED
  `define LMULf4_SUPPORTED
  `define LMULf8_SUPPORTED
`endif
`ifdef UDB_VLEN_128
  `define LMULf2_SUPPORTED
  `define LMULf4_SUPPORTED
  `define LMULf8_SUPPORTED
`endif
`ifdef UDB_VLEN_256
  `define LMULf2_SUPPORTED
  `define LMULf4_SUPPORTED
  `define LMULf8_SUPPORTED
`endif
`ifdef UDB_VLEN_512
  `define LMULf2_SUPPORTED
  `define LMULf4_SUPPORTED
  `define LMULf8_SUPPORTED
`endif
`ifdef UDB_VLEN_1024
  `define LMULf2_SUPPORTED
  `define LMULf4_SUPPORTED
  `define LMULf8_SUPPORTED
`endif
`ifdef UDB_VLEN_2048
  `define LMULf2_SUPPORTED
  `define LMULf4_SUPPORTED
  `define LMULf8_SUPPORTED
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

`endif // DERIVED_CONFIG_SVH
