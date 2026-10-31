// SPDX-License-Identifier: Apache-2.0
// Copyright (c) 2026 RISC-V International
//
// xlen_probe.S: print "# xlen: 32" or "# xlen: 64" on the DUT's console.
//
// Written by David Harris with assistance from Claude.
//
// make_config.py runs this before the extractor, which must be compiled for the hart's XLEN.  The
// code uses only instructions that RV32I and RV64I share with the same encoding, so the RV32 build
// runs on either kind of hart: 1 << 31 is negative on RV32 and positive on RV64.  It uses no CSR,
// since some harts (Wally rv32i, PicoRV32) have none.

#include "rvmodel_macros.h"

.section .text.init, "ax", @progbits
.globl rvtest_entry_point
rvtest_entry_point:
#ifdef RVMODEL_IO_INIT
    RVMODEL_IO_INIT(t0, t1, t2)
#endif
    li      t0, 1
    slli    t0, t0, 31
    la      a0, msg64
    bgez    t0, 1f
    la      a0, msg32
1:  RVMODEL_IO_WRITE_STR(t0, t1, t2, a0)
    RVMODEL_HALT_PASS

.section .data
msg32:  .string "# xlen: 32\n"
msg64:  .string "# xlen: 64\n"

#ifdef RVMODEL_DATA_SECTION
RVMODEL_DATA_SECTION
#endif
