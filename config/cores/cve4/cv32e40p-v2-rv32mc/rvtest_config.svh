// rvtest_config.svh
// SPDX-License-Identifier: Apache-2.0

`define XLEN32

// PMP not implemented in default cv32e40p configuration
// `define PMP_16

`define RAM_BASE_ADDR       32'h00000000
`define LARGEST_PROGRAM     32'h00040000

`define ACCESS_FAULT_ADDRESS 64'h00000000
`define CLINT_BASE 64'h02000000
