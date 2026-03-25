// rvtest_config.svh
// David_Harris@hmc.edu 7 September 2024
// SPDX-License-Identifier: Apache-2.0

// This file is needed in the config subdirectory for each config supporting coverage.
// It defines which extensions are enabled for that config.

// Define XLEN, used in covergroups
`define XLEN64
`define FLEN64
`define VLEN256

// Virtual Memory Modes
`define SV39
`define SV48
`define SV57

// PMP Grain (G)
// Set G as needed (e.g., 0, 1, 2, ...)
`define G 8

// Uncomment below if G = 0
// `define G_IS_0

// PMP mode selection
`define PMP_64     // Choose between PMP_16 or PMP_64 or None

// Base addresses specific for PMP
`define RAM_BASE_ADDR       32'h80000000  // PMP Region starts at RAM_BASE_ADDR + LARGEST_PROGRAM
`define LARGEST_PROGRAM     32'h00010000

// Define relevant addresses
`define RVMODEL_ACCESS_FAULT_ADDRESS 64'h00000000
`define CLINT_BASE 64'h02000000

//define extra supported extensions to collect full coverage in Privileged files
`define A_SUPPORTED
`define B_SUPPORTED
`define C_SUPPORTED
`define D_SUPPORTED
`define F_SUPPORTED
`define H_SUPPORTED
`define I_SUPPORTED
`define M_SUPPORTED
`define N_SUPPORTED
`define V_SUPPORTED
`define SDTRIG_SUPPORTED
`define SMAIA_SUPPORTED
`define SMDBLTRP_SUPPORTED
`define SMMPM_SUPPORTED
`define SMNPM_SUPPORTED
`define SMRNMI_SUPPORTED
`define SMSTATEEN_SUPPORTED
`define SSAIA_SUPPORTED
`define SSCOFPMF_SUPPORTED
`define SSNPM_SUPPORTED
`define SSQOSID_SUPPORTED
`define SSTC_SUPPORTED
`define SVADE_SUPPORTED
`define SVADU_SUPPORTED
`define SVINVAL_SUPPORTED
`define SVNAPOT_SUPPORTED
`define SVPBMT_SUPPORTED
`define SVVPTC_SUPPORTED
`define ZA64RS_SUPPORTED
`define ZAAMO_SUPPORTED
`define ZABHA_SUPPORTED
`define ZACAS_SUPPORTED
`define ZALASR_SUPPORTED
`define ZALRSC_SUPPORTED
`define ZAWRS_SUPPORTED
`define ZBA_SUPPORTED
`define ZBB_SUPPORTED
`define ZBC_SUPPORTED
`define ZBKB_SUPPORTED
`define ZBKC_SUPPORTED
`define ZBKX_SUPPORTED
`define ZBS_SUPPORTED
`define ZCA_SUPPORTED
`define ZCB_SUPPORTED
`define ZCD_SUPPORTED
`define ZCF_SUPPORTED
`define ZCLSD_SUPPORTED
`define ZCMOP_SUPPORTED
`define ZFA_SUPPORTED
`define ZFBFMIN_SUPPORTED
`define ZFH_SUPPORTED
`define ZFHMIN_SUPPORTED
`define ZIBI_SUPPORTED
`define ZIC64B_SUPPORTED
`define ZICBOM_SUPPORTED
`define ZICBOP_SUPPORTED
`define ZICBOZ_SUPPORTED
`define ZICCAMOA_SUPPORTED
`define ZICCIF_SUPPORTED
`define ZICCLSM_SUPPORTED
`define ZICCRSE_SUPPORTED
`define ZICFILP_SUPPORTED
`define ZICFISS_SUPPORTED
`define ZICNTR_SUPPORTED
`define ZICOND_SUPPORTED
`define ZICSR_SUPPORTED
`define ZIFENCEI_SUPPORTED
`define ZIHINTNTL_SUPPORTED
`define ZIHINTPAUSE_SUPPORTED
`define ZIHPM_SUPPORTED
`define ZILSD_SUPPORTED
`define ZIMOP_SUPPORTED
`define ZKND_SUPPORTED
`define ZKNE_SUPPORTED
`define ZKNH_SUPPORTED
`define ZKR_SUPPORTED
`define ZKSED_SUPPORTED
`define ZKSH_SUPPORTED
`define ZLSSEG_SUPPORTED
`define ZMMUL_SUPPORTED
`define ZVABD_SUPPORTED
`define ZVBB_SUPPORTED
`define ZVBC_SUPPORTED
`define ZVFBFMIN_SUPPORTED
`define ZVFBFWMA_SUPPORTED
`define ZVFH_SUPPORTED
`define ZVFHMIN_SUPPORTED
`define ZVKB_SUPPORTED
`define ZVKG_SUPPORTED
`define ZVKNED_SUPPORTED
`define ZVKNHA_SUPPORTED
`define ZVKNHB_SUPPORTED
`define ZVKSED_SUPPORTED
`define ZVKSH_SUPPORTED
`define ZVQDOT_SUPPORTED
`define ZVZIP_SUPPORTED

`define COUNTINHIBIT_EN_0
`define COUNTINHIBIT_EN_2
`define TIME_CSR_IMPLEMENTED
