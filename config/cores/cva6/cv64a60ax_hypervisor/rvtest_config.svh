// rvtest_config.svh
// cv64a60ax configuration
// SPDX-License-Identifier: Apache-2.0

// Define XLEN, used in covergroups
`define XLEN64
`define FLEN64

// PMP Grain (G)
// Set G as needed (e.g., 0, 1, 2, ...)
`define G 1

// Uncomment below if G = 0
// `define G_IS_0

// PMP mode selection
`define PMP_16     // Choose between PMP_16 or PMP_64 or None

// Base addresses specific for PMP
`define RAM_BASE_ADDR       32'h80000000  // PMP Region starts at RAM_BASE_ADDR + LARGEST_PROGRAM
`define LARGEST_PROGRAM     32'h00001000

// Define relevant addresses
`define RVMODEL_ACCESS_FAULT_ADDRESS 64'h00000000
`define CLINT_BASE 64'h02000000

//define extra supported extensions to collect full coverage in Privileged files
`define D_SUPPORTED
`define F_SUPPORTED
`define ZBB_SUPPORTED
`define ZBA_SUPPORTED
`define ZBS_SUPPORTED
`define ZIHPM_SUPPORTED
`define ZCA_SUPPORTED
`define ZCB_SUPPORTED
`define ZCD_SUPPORTED
`define ZAAMO_SUPPORTED
`define ZALRSC_SUPPORTED
`define S_SUPPORTED
`define U_SUPPORTED
`define H_SUPPORTED
`define SV39_SUPPORTED

`define COUNTINHIBIT_EN_0
`define COUNTINHIBIT_EN_2
`define TIME_CSR_IMPLEMENTED


