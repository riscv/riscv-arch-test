// rvtest_config.svh 
// cv32a65x configuration
// SPDX-License-Identifier: Apache-2.0

// Define XLEN, used in covergroups
`define XLEN32

// PMP Grain (G)
// CVA6 typically uses G=0 (4-byte granularity) unless specified otherwise
`define G 0
// `define G_IS_0

// PMP mode selection
// Per parameters: NrPMPEntries = 8 (but minimum we can select is 16)
`define PMP_16

// Base addresses 
`define RAM_BASE_ADDR       32'h80000000
`define LARGEST_PROGRAM     32'h00001000

// Define relevant addresses
`define RVMODEL_ACCESS_FAULT_ADDRESS 32'h00000000
`define CLINT_BASE 32'h02000000 

