// rvtest_config.svh
// David_Harris@hmc.edu 7 September 2024
// SPDX-License-Identifier: Apache-2.0

// This file is needed in the config subdirectory for each config supporting coverage.
// It defines which extensions are enabled for that config.

// Define XLEN, used in covergroups
`define XLEN64
`define FLEN64
`define VLEN512

// PMP Grain (G)
// Set G as needed (e.g., 0, 1, 2, ...)
`define G 4

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
`define ZFA_SUPPORTED
`define F_SUPPORTED
`define ZFH_SUPPORTED
`define ZBB_SUPPORTED
`define ZBA_SUPPORTED
`define ZBS_SUPPORTED
`define ZIHPM_SUPPORTED
`define ZCA_SUPPORTED
`define ZCB_SUPPORTED
`define ZCD_SUPPORTED
`define ZAAMO_SUPPORTED
`define ZABHA_SUPPORTED
`define ZALRSC_SUPPORTED
`define ZICBOZ_SUPPORTED
`define ZICBOM_SUPPORTED
`define ZICBOP_SUPPORTED

`define COUNTINHIBIT_EN_0
`define COUNTINHIBIT_EN_2
`define TIME_CSR_IMPLEMENTED
