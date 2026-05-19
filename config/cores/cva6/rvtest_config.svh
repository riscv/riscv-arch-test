// rvtest_config.svh
// cv32a65x configuration
// SPDX-License-Identifier: Apache-2.0

`define XLEN32

// PMP not supported in CV32A65X
// `define PMP_16

// Base addresses
`define RAM_BASE_ADDR       32'h80000000
`define LARGEST_PROGRAM     32'h00010000

// `define RVMODEL_ACCESS_FAULT_ADDRESS 32'h50000000
`define CLINT_BASE 32'h02000000
