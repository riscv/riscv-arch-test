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
`define A_SUUPORTED
`define B_SUUPORTED
`define C_SUUPORTED
`define D_SUUPORTED
`define F_SUUPORTED
`define H_SUUPORTED
`define I_SUUPORTED
`define M_SUUPORTED
`define N_SUUPORTED
`define V_SUUPORTED
`define SDTRIG_SUUPORTED
`define SMAIA_SUUPORTED
`define SMDBLTRP_SUUPORTED
`define SMMPM_SUUPORTED
`define SMNPM_SUUPORTED
`define SMRNMI_SUUPORTED
`define SMSTATEEN_SUUPORTED
`define SSAIA_SUUPORTED
`define SSCOFPMF_SUUPORTED
`define SSNPM_SUUPORTED
`define SSQOSID_SUUPORTED
`define SSTC_SUUPORTED
`define SVADE_SUUPORTED
`define SVADU_SUUPORTED
`define SVINVAL_SUUPORTED
`define SVNAPOT_SUUPORTED
`define SVPBMT_SUUPORTED
`define SVVPTC_SUUPORTED
`define ZA64RS_SUUPORTED
`define ZAAMO_SUUPORTED
`define ZABHA_SUUPORTED
`define ZACAS_SUUPORTED
`define ZALASR_SUUPORTED
`define ZALRSC_SUUPORTED
`define ZAWRS_SUUPORTED
`define ZBA_SUUPORTED
`define ZBB_SUUPORTED
`define ZBC_SUUPORTED
`define ZBKB_SUUPORTED
`define ZBKC_SUUPORTED
`define ZBKX_SUUPORTED
`define ZBS_SUUPORTED
`define ZCA_SUUPORTED
`define ZCB_SUUPORTED
`define ZCD_SUUPORTED
`define ZCF_SUUPORTED
`define ZCLSD_SUUPORTED
`define ZCMOP_SUUPORTED
`define ZFA_SUUPORTED
`define ZFBFMIN_SUUPORTED
`define ZFH_SUUPORTED
`define ZFHMIN_SUUPORTED
`define ZIBI_SUUPORTED
`define ZIC64B_SUUPORTED
`define ZICBOM_SUUPORTED
`define ZICBOP_SUUPORTED
`define ZICBOZ_SUUPORTED
`define ZICCAMOA_SUUPORTED
`define ZICCIF_SUUPORTED
`define ZICCLSM_SUUPORTED
`define ZICCRSE_SUUPORTED
`define ZICFILP_SUUPORTED
`define ZICFISS_SUUPORTED
`define ZICNTR_SUUPORTED
`define ZICOND_SUUPORTED
`define ZICSR_SUUPORTED
`define ZIFENCEI_SUUPORTED
`define ZIHINTNTL_SUUPORTED
`define ZIHINTPAUSE_SUUPORTED
`define ZIHPM_SUUPORTED
`define ZILSD_SUUPORTED
`define ZIMOP_SUUPORTED
`define ZKND_SUUPORTED
`define ZKNE_SUUPORTED
`define ZKNH_SUUPORTED
`define ZKR_SUUPORTED
`define ZKSED_SUUPORTED
`define ZKSH_SUUPORTED
`define ZLSSEG_SUUPORTED
`define ZMMUL_SUUPORTED
`define ZVABD_SUUPORTED
`define ZVBB_SUUPORTED
`define ZVBC_SUUPORTED
`define ZVFBFMIN_SUUPORTED
`define ZVFBFWMA_SUUPORTED
`define ZVFH_SUUPORTED
`define ZVFHMIN_SUUPORTED
`define ZVKB_SUUPORTED
`define ZVKG_SUUPORTED
`define ZVKNED_SUUPORTED
`define ZVKNHA_SUUPORTED
`define ZVKNHB_SUUPORTED
`define ZVKSED_SUUPORTED
`define ZVKSH_SUUPORTED
`define ZVQDOT_SUUPORTED
`define ZVZIP_SUUPORTED

`define COUNTINHIBIT_EN_0
`define COUNTINHIBIT_EN_2
`define TIME_CSR_IMPLEMENTED
