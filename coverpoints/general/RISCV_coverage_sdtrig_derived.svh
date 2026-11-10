///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Sdtrig Derived Defines
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Defines derived from the Sdtrig UDB parameters, included by the Sdtrig*_coverage.svh files
//
///////////////////////////////////////////
`ifndef RISCV_COVERAGE_SDTRIG_DERIVED_SVH
`define RISCV_COVERAGE_SDTRIG_DERIVED_SVH

// SDTRIG_TESTED_TRIGGERS: the triggers the Sdtrig tests exercise, tselect 0 to 15 (the generator's maximum).
// SDTRIG_<TYPE>_ANY: a tested trigger supports the type (UDB_SDTRIG_<TYPE>_SUPPORTED_TRIGGERS_<n>).
// SDTRIG_CHAIN_PAIR_<n>: triggers n-1 and n support mcontrol6 and chains of 2 are allowed (SDTRIG_CHAIN_ANY_PAIR: any n).
// SDTRIG_CHAIN_<n>: triggers 0 to n-1 support mcontrol6 and UDB_SDTRIG_MAX_CHAIN_LENGTH >= n. The integer parameter
//   also defines UDB_SDTRIG_MAX_CHAIN_LENGTH_<value>, so MAX_CHAIN_LENGTH >= n is "not any of 1 to n-1".
`ifdef SDTRIG_SUPPORTED
  `define SDTRIG_TESTED_TRIGGERS ((`UDB_SDTRIG_NUM_TRIGGERS < 16) ? `UDB_SDTRIG_NUM_TRIGGERS : 16)
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_0
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_1
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_2
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_3
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_4
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_5
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_6
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_7
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_8
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_9
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_10
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_11
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_12
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_13
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_14
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_15
    `define SDTRIG_MCONTROL6_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_0
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_1
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_2
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_3
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_4
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_5
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_6
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_7
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_8
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_9
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_10
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_11
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_12
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_13
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_14
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_15
    `define SDTRIG_ICOUNT_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_0
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_1
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_2
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_3
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_4
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_5
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_6
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_7
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_8
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_9
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_10
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_11
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_12
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_13
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_14
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_15
    `define SDTRIG_ITRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_0
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_1
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_2
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_3
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_4
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_5
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_6
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_7
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_8
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_9
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_10
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_11
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_12
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_13
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_14
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_15
    `define SDTRIG_ETRIGGER_ANY
  `endif
  `ifdef UDB_SDTRIG_MAX_CHAIN_LENGTH
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_0
      `define SDTRIG_CHAIN_1
    `endif
    `ifdef SDTRIG_CHAIN_1
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_1
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_1
          `define SDTRIG_CHAIN_2
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_2
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_2
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_2
          `define SDTRIG_CHAIN_3
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_3
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_3
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_3
          `define SDTRIG_CHAIN_4
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_4
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_4
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_4
          `define SDTRIG_CHAIN_5
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_5
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_5
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_5
          `define SDTRIG_CHAIN_6
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_6
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_6
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_6
          `define SDTRIG_CHAIN_7
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_7
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_7
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_7
          `define SDTRIG_CHAIN_8
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_8
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_8
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_8
          `define SDTRIG_CHAIN_9
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_9
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_9
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_9
          `define SDTRIG_CHAIN_10
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_10
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_10
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_10
          `define SDTRIG_CHAIN_11
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_11
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_11
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_11
          `define SDTRIG_CHAIN_12
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_12
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_12
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_12
          `define SDTRIG_CHAIN_13
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_13
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_13
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_13
          `define SDTRIG_CHAIN_14
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_14
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_14
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_14
          `define SDTRIG_CHAIN_15
        `endif
      `endif
    `endif
    `ifdef SDTRIG_CHAIN_15
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_15
        `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_15
          `define SDTRIG_CHAIN_16
        `endif
      `endif
    `endif
    `ifndef UDB_SDTRIG_MAX_CHAIN_LENGTH_1
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_0
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_1
          `define SDTRIG_CHAIN_PAIR_1
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_1
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_2
          `define SDTRIG_CHAIN_PAIR_2
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_2
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_3
          `define SDTRIG_CHAIN_PAIR_3
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_3
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_4
          `define SDTRIG_CHAIN_PAIR_4
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_4
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_5
          `define SDTRIG_CHAIN_PAIR_5
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_5
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_6
          `define SDTRIG_CHAIN_PAIR_6
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_6
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_7
          `define SDTRIG_CHAIN_PAIR_7
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_7
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_8
          `define SDTRIG_CHAIN_PAIR_8
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_8
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_9
          `define SDTRIG_CHAIN_PAIR_9
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_9
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_10
          `define SDTRIG_CHAIN_PAIR_10
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_10
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_11
          `define SDTRIG_CHAIN_PAIR_11
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_11
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_12
          `define SDTRIG_CHAIN_PAIR_12
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_12
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_13
          `define SDTRIG_CHAIN_PAIR_13
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_13
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_14
          `define SDTRIG_CHAIN_PAIR_14
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
      `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_14
        `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_15
          `define SDTRIG_CHAIN_PAIR_15
          `define SDTRIG_CHAIN_ANY_PAIR
        `endif
      `endif
    `endif
  `endif
`endif

// mcontrol6 match and size values that select a group of cases
`ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_1
    `define SDTRIG_MATCH_NAPOT
`endif
`ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_9
    `define SDTRIG_MATCH_NAPOT
`endif
`ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_4
    `define SDTRIG_MATCH_MASK
`endif
`ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_5
    `define SDTRIG_MATCH_MASK
`endif
`ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_12
    `define SDTRIG_MATCH_MASK
`endif
`ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_13
    `define SDTRIG_MATCH_MASK
`endif
`ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_1
    `define SDTRIG_SIZE_DATA
`endif
`ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2
    `define SDTRIG_SIZE_DATA
`endif
`ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3
    `define SDTRIG_SIZE_DATA
`endif
`ifdef UDB_MXLEN_64
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_5
        `define SDTRIG_SIZE_DATA
    `endif
`endif
// cp_mcontrol6_execute_adr_size: a legal size the generator writes on an execute address trigger (sizes above XLEN
// are never written; size 2 has only a c.nop case)
`ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_1
    `define SDTRIG_EXEC_ADR_SIZE
`endif
`ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3
    `define SDTRIG_EXEC_ADR_SIZE
`endif
`ifdef ZCA_SUPPORTED
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2
        `define SDTRIG_EXEC_ADR_SIZE
    `endif
`endif
`ifdef UDB_MXLEN_64
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_4
        `define SDTRIG_EXEC_ADR_SIZE
    `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_5
        `define SDTRIG_EXEC_ADR_SIZE
    `endif
`endif
// cp_mcontrol6_match_size_*: select = 1 triggers on stores, loads (any data size) and execution (sizes 2 and 3)
`ifdef UDB_SDTRIG_MCONTROL6_SELECT_WRITABLE
    `ifdef SDTRIG_SIZE_DATA
        `ifdef UDB_SDTRIG_MCONTROL6_STORE_WRITABLE
            `define SDTRIG_MATCH_SIZE_STORE
        `endif
        `ifdef UDB_SDTRIG_MCONTROL6_LOAD_WRITABLE
            `define SDTRIG_MATCH_SIZE_LOAD
        `endif
    `endif
    `ifdef UDB_SDTRIG_MCONTROL6_EXECUTE_WRITABLE
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3
            `define SDTRIG_MATCH_SIZE_EXEC
        `endif
        `ifdef ZCA_SUPPORTED
            `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2
                `define SDTRIG_MATCH_SIZE_EXEC
                `define SDTRIG_MATCH_SIZE_EXEC16
            `endif
        `endif
    `endif
`endif
// textra context matches with value bits to compare (the generator's _MCONTEXT_MATCH_GATE, _SCONTEXT_MATCH_GATE)
`ifdef UDB_SDTRIG_TEXTRA_MHSELECT_MCONTEXT_MATCH
    `ifndef UDB_SDTRIG_TEXTRA_MHVALUE_LEN_0
        `define SDTRIG_TEXTRA_MCONTEXT
    `endif
`endif
`ifdef UDB_SDTRIG_TEXTRA_SSELECT_SCONTEXT_MATCH
    `ifndef UDB_SDTRIG_TEXTRA_SVALUE_LEN_0
        `define SDTRIG_TEXTRA_SCONTEXT
    `endif
`endif

`endif // RISCV_COVERAGE_SDTRIG_DERIVED_SVH
