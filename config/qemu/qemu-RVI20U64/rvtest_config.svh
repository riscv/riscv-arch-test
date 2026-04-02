// rvtest_config.svh
// David_Harris@hmc.edu 7 September 2024
// SPDX-License-Identifier: Apache-2.0

// This file is needed in the config subdirectory for each config supporting coverage.
// It defines which extensions are enabled for that config.

// Define XLEN, used in covergroups
`define XLEN64
`define FLEN64

// Define relevant addresses
`define CLINT_BASE 64'h02000000

// PMP Grain (G) — QEMU default grain is 0
`define G 0
`define G_IS_0

// PMP mode selection
`define PMP_16

// Base addresses specific for PMP
`define RAM_BASE_ADDR       64'h80000000
`define LARGEST_PROGRAM     64'h00001000

`define RVMODEL_ACCESS_FAULT_ADDRESS 64'h00000000

//define extra supported extensions to collect full coverage in Privileged files
`define D_SUPPORTED
`define F_SUPPORTED
`define ZIHPM_SUPPORTED
`define ZCA_SUPPORTED
`define ZCD_SUPPORTED
`define ZAAMO_SUPPORTED
`define ZALRSC_SUPPORTED

`define COUNTINHIBIT_EN_0
`define COUNTINHIBIT_EN_2
`define TIME_CSR_IMPLEMENTED
