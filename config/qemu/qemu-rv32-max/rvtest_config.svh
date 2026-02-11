// rvtest_config.svh
// Ported for QEMU Virt Machine
// Feb 2026
// SPDX-License-Identifier: Apache-2.0

// Define XLEN, used in covergroups
`define XLEN32
`define FLEN32       // QEMU 'virt' typically aligns FLEN with XLEN unless specified
`define VLEN128      // Standard QEMU VLEN is 128 (can be higher, but 1024 is rare for default)

// PMP Grain (G)
`define G 0          // QEMU defaults to G=0 (4-byte granularity)
`define G_IS_0       // Uncommented because G = 0

// PMP mode selection
`define PMP_64       // QEMU virt supports the full 64 regions

// Base addresses specific for PMP
`define RAM_BASE_ADDR       32'h80000000  
`define LARGEST_PROGRAM     32'h00200000  // Increased: QEMU tests often need more headroom

// Define relevant addresses
`define ACCESS_FAULT_ADDRESS 64'h00001000  // Reserved ROM area in QEMU
`define CLINT_BASE 64'h02000000           // Standard for QEMU virt

// Extensions (Keep these as-is, they are well-supported in QEMU)
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
`define ZALRSC_SUPPORTED

`define COUNTINHIBIT_EN_0
`define COUNTINHIBIT_EN_2
`define TIME_CSR_IMPLEMENTED