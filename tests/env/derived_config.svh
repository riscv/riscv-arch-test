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
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_64
  `define MAXINDEXEEW64
`endif
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_32
  `define MAXINDEXEEW32
`endif
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_16
  `define MAXINDEXEEW16
`endif
`ifdef UDB_VECTOR_LS_INDEX_MAX_EEW_8
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

// Cumulative privileged ISA version defines
`ifdef S1P13P0_SUPPORTED
  `define S1P12P0_OR_LATER_SUPPORTED
  `define S1P13P0_OR_LATER_SUPPORTED
`elsif S1P12P0_SUPPORTED
  `define S1P12P0_OR_LATER_SUPPORTED
`endif

`ifdef SM1P13P0_SUPPORTED
  `define SM1P12P0_OR_LATER_SUPPORTED
  `define SM1P13P0_OR_LATER_SUPPORTED
`elsif SM1P12P0_SUPPORTED
  `define SM1P12P0_OR_LATER_SUPPORTED
`endif

// ---- UDB_VLEN ----
// UDB defines UDB_VLEN only when the DUT implements a vector extension. Default it to 0, as
// tests/env/utils.h does, so code that sizes vector registers also elaborates without one.
`ifndef UDB_VLEN
  `define UDB_VLEN 0
`endif

// RVTEST_SGEI_INTR_IMPL: mirrors derived_config.h (H with GEILEN > 0). Configs without H do not
// emit UDB_NUM_EXTERNAL_GUEST_INTERRUPTS at all; GEILEN = 0 emits the _0 form.
`ifdef H_SUPPORTED
  `ifdef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS
    `ifndef UDB_NUM_EXTERNAL_GUEST_INTERRUPTS_0
      `define RVTEST_SGEI_INTR_IMPL
    `endif
  `endif
`endif

// PMP_ENTRY<n>_BELOW_BACKGROUND: PMP entry n lies below the background entry
// (NUM_USABLE_PMP_ENTRIES - 1), so PMP tests can configure and probe it. Most uses guard
// individual bins, which only the preprocessor can remove, and `ifdef cannot compare
// UDB_NUM_USABLE_PMP_ENTRIES with n, so the range is spelled out over the one-hot
// UDB_NUM_USABLE_PMP_ENTRIES_<n> macros.
// check_defines.h requires at least 8 usable entries, so entries 0-6 always qualify; coverage of
// entries above 15 uses numeric bins on UDB_NUM_USABLE_PMP_ENTRIES instead.
// Each level holds when NUM_USABLE_PMP_ENTRIES > n + 1, so the checks nest.
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_8
  `define PMP_ENTRY7_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_9
  `define PMP_ENTRY8_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_10
  `define PMP_ENTRY9_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_11
  `define PMP_ENTRY10_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_12
  `define PMP_ENTRY11_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_13
  `define PMP_ENTRY12_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_14
  `define PMP_ENTRY13_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_15
  `define PMP_ENTRY14_BELOW_BACKGROUND
`ifndef UDB_NUM_USABLE_PMP_ENTRIES_16
  `define PMP_ENTRY15_BELOW_BACKGROUND
`endif
`endif
`endif
`endif
`endif
`endif
`endif
`endif
`endif

`endif // DERIVED_CONFIG_SVH
