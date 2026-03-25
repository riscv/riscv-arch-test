///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ARCHUPPER
`ifdef ELENEFFEW
    `define SEW_EFFEW_EQ_ELEN
`endif
`ifdef ELENTWOEFFEW
    `define SEW_EFFEW_EQ_ELEN_DIV_2
`endif
