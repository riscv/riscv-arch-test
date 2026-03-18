// rvtest_config.svh
// SPDX-License-Identifier: Apache-2.0
// STUB: Copied from cv32e40p. Update PMP count when filling.

`define XLEN32

// cv32e40s has 16 PMP regions (TBC — verify NUM_PMP_ENTRIES in rtl/cv32e40s_pkg.sv)
// `define PMP_16

`define RAM_BASE_ADDR       32'h00000000
`define LARGEST_PROGRAM     32'h00040000

`define ACCESS_FAULT_ADDRESS 64'h00000000
`define CLINT_BASE 64'h02000000
