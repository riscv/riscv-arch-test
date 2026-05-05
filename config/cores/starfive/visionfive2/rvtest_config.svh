// SPDX-License-Identifier: Apache-2.0
// rvtest_config.svh — SystemVerilog coverage config for VisionFive 2 (JH7110)
// Note: No RTL simulation is used with this SBC target.
// This file is included for completeness and framework compatibility.

// XLEN and FLEN
`define XLEN64
`define FLEN64

// PMP grain (G=0 for JH7110)
`define G 0

// PMP mode — JH7110 has 8 PMP entries
`define PMP_16   // Using PMP_16 as closest available option

// Base addresses for VisionFive 2 DRAM layout
`define RAM_BASE_ADDR       32'h42000000   // ELF load address
`define LARGEST_PROGRAM     32'h00010000   // 64 KB max test size

// Access fault address (unmapped region below DRAM)
`define RVMODEL_ACCESS_FAULT_ADDRESS 64'h00000000

// CLINT base (managed by OpenSBI; not directly writable from S-mode)
`define CLINT_BASE 64'h02000000

// Supported extensions
`define F_SUPPORTED
`define D_SUPPORTED
`define ZBA_SUPPORTED
`define ZBB_SUPPORTED
`define ZBS_SUPPORTED
`define ZAAMO_SUPPORTED
`define ZALRSC_SUPPORTED
`define ZCA_SUPPORTED
`define ZCB_SUPPORTED
`define ZCD_SUPPORTED
`define SV39_SUPPORTED
`define SV48_SUPPORTED

// Timer CSR available via OpenSBI (read-only from S-mode)
`define TIME_CSR_IMPLEMENTED
