///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Configuration
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written: Jordan Carlin jcarlin@hmc.edu February 2024
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// Unprivileged extensions
`ifdef I_COVERAGE
  `include "I_coverage.svh"
`endif
`ifdef M_COVERAGE
  `include "M_coverage.svh"
`endif
`ifdef F_COVERAGE
  `include "F_coverage.svh"
`endif
`ifdef D_COVERAGE
  `include "D_coverage.svh"
`endif
`ifdef VX8_COVERAGE
  `include "Vx8_coverage.svh"
`endif
`ifdef VX16_COVERAGE
  `include "Vx16_coverage.svh"
`endif
`ifdef VX32_COVERAGE
  `include "Vx32_coverage.svh"
`endif
`ifdef VX64_COVERAGE
  `include "Vx64_coverage.svh"
`endif
`ifdef VLS8_COVERAGE
  `include "Vls8_coverage.svh"
`endif
`ifdef VLS16_COVERAGE
  `include "Vls16_coverage.svh"
`endif
`ifdef VLS32_COVERAGE
  `include "Vls32_coverage.svh"
`endif
`ifdef VLS64_COVERAGE
  `include "Vls64_coverage.svh"
`endif
`ifdef VF16_COVERAGE
  `include "Vf16_coverage.svh"
`endif
`ifdef VF32_COVERAGE
  `include "Vf32_coverage.svh"
`endif
`ifdef VF64_COVERAGE
  `include "Vf64_coverage.svh"
`endif
`ifdef ZBA_COVERAGE
  `include "Zba_coverage.svh"
`endif
`ifdef ZBB_COVERAGE
  `include "Zbb_coverage.svh"
`endif
`ifdef ZBC_COVERAGE
  `include "Zbc_coverage.svh"
`endif
`ifdef ZBS_COVERAGE
  `include "Zbs_coverage.svh"
`endif
`ifdef ZFAF_COVERAGE
  `include "ZfaF_coverage.svh"
`endif
`ifdef ZFAD_COVERAGE
  `include "ZfaD_coverage.svh"
`endif
`ifdef ZFAZFH_COVERAGE
  `include "ZfaZfh_coverage.svh"
`endif
`ifdef ZFAZFHD_COVERAGE
  `include "ZfaZfhD_coverage.svh"
`endif
`ifdef ZFH_COVERAGE
  `include "Zfh_coverage.svh"
`endif
`ifdef ZFHD_COVERAGE
  `include "ZfhD_coverage.svh"
`endif
`ifdef ZFHMIN_COVERAGE
  `include "Zfhmin_coverage.svh"
`endif
`ifdef ZFHMIND_COVERAGE
  `include "ZfhminD_coverage.svh"
`endif
`ifdef ZMMUL_COVERAGE
  `include "Zmmul_coverage.svh"
`endif
`ifdef ZICOND_COVERAGE
  `include "Zicond_coverage.svh"
`endif
`ifdef ZIFENCEI_COVERAGE
  `include "Zifencei_coverage.svh"
`endif
`ifdef ZIHINTPAUSE_COVERAGE
  `include "Zihintpause_coverage.svh"
`endif
`ifdef ZCA_COVERAGE
  `include "Zca_coverage.svh"
`endif
`ifdef ZCB_COVERAGE
  `include "Zcb_coverage.svh"
`endif
`ifdef ZCBM_COVERAGE
  `include "ZcbM_coverage.svh"
`endif
`ifdef ZCBZBB_COVERAGE
  `include "ZcbZbb_coverage.svh"
`endif
`ifdef ZCBZBA_COVERAGE
  `include "ZcbZba_coverage.svh"
`endif
`ifdef ZCD_COVERAGE
  `include "Zcd_coverage.svh"
`endif
`ifdef ZCF_COVERAGE
  `include "Zcf_coverage.svh"
`endif
`ifdef ZICSR_COVERAGE
  `include "Zicsr_coverage.svh"
`endif
`ifdef ZBKB_COVERAGE
  `include "Zbkb_coverage.svh"
`endif
`ifdef ZBKC_COVERAGE
  `include "Zbkc_coverage.svh"
`endif
`ifdef ZBKX_COVERAGE
  `include "Zbkx_coverage.svh"
`endif
`ifdef ZKND_COVERAGE
  `include "Zknd_coverage.svh"
`endif
`ifdef ZKNE_COVERAGE
  `include "Zkne_coverage.svh"
`endif
`ifdef ZKNH_COVERAGE
  `include "Zknh_coverage.svh"
`endif
`ifdef ZAAMO_COVERAGE
  `include "Zaamo_coverage.svh"
`endif
`ifdef ZALRSC_COVERAGE
  `include "Zalrsc_coverage.svh"
`endif
`ifdef SVINVAL_COVERAGE
  `include "Svinval_coverage.svh"
`endif

// Privileged extensions
`ifdef VM_COVERAGE
  `include "VM_coverage.svh"
`endif
`ifdef VM_PMP_COVERAGE
  `include "VM_PMP_coverage.svh"
`endif
`ifdef VM_CBO_COVERAGE
  `include "VM_CBO_coverage.svh"
`endif
`ifdef VM_PMP_CBO_COVERAGE
  `include "VM_PMP_CBO_coverage.svh"
`endif
`ifdef SVADE_COVERAGE
  `include "Svade_coverage.svh"
`endif
`ifdef SVADU_COVERAGE
  `include "Svadu_coverage.svh"
`endif
`ifdef SVADU_PMP_COVERAGE
  `include "Svadu_PMP_coverage.svh"
`endif
`ifdef SVNAPOT_COVERAGE
  `include "Svnapot_coverage.svh"
`endif
`ifdef SVPBMT_COVERAGE
  `include "Svpbmt_coverage.svh"
`endif
`ifdef RV64PMP_COVERAGE
  `include "PMPM_coverage.svh"
  `include "PMPU_coverage.svh"
  `include "PMPS_coverage.svh"
  `include "PMPF_coverage.svh"
  `include "PMPZaamo_coverage.svh"
  `include "PMPZalrsc_coverage.svh"
  `include "PMPZca_coverage.svh"
  `include "PMPZicbo_coverage.svh"
`endif
`ifdef RV32PMP_COVERAGE
  `include "PMPM_coverage.svh"
  `include "PMPU_coverage.svh"
  `include "PMPS_coverage.svh"
  `include "PMPF_coverage.svh"
  `include "PMPZaamo_coverage.svh"
  `include "PMPZalrsc_coverage.svh"
  `include "PMPZca_coverage.svh"
  `include "PMPZicbo_coverage.svh"
`endif
`ifdef RV64CBO_PMP_COVERAGE
  `include "RV64CBO_PMP_coverage.svh"
`endif
`ifdef RV32CBO_PMP_COVERAGE
  `include "RV32CBO_PMP_coverage.svh"
`endif
`ifdef ZICSRM_COVERAGE
  `include "ZicsrM_coverage.svh"
`endif
`ifdef ZICSRS_COVERAGE
  `include "ZicsrS_coverage.svh"
`endif
`ifdef ZICSRU_COVERAGE
  `include "ZicsrU_coverage.svh"
`endif
`ifdef ZICSRV_COVERAGE
  `include "ZicsrV_coverage.svh"
`endif
`ifdef ZICSRVF_COVERAGE
  `include "ZicsrVF_coverage.svh"
`endif
`ifdef ZICSRHV_COVERAGE
  `include "ZicsrHV_coverage.svh"
`endif
`ifdef ZICSRF_COVERAGE
  `include "ZicsrF_coverage.svh"
`endif
`ifdef ENDIANU_COVERAGE
  `include "EndianU_coverage.svh"
`endif
`ifdef ENDIANS_COVERAGE
  `include "EndianS_coverage.svh"
`endif
`ifdef ENDIANM_COVERAGE
  `include "EndianM_coverage.svh"
`endif
`ifdef EXCEPTIONSM_COVERAGE
  `include "ExceptionsM_coverage.svh"
`endif
`ifdef EXCEPTIONSS_COVERAGE
  `include "ExceptionsS_coverage.svh"
`endif
`ifdef EXCEPTIONSU_COVERAGE
  `include "ExceptionsU_coverage.svh"
`endif
`ifdef EXCEPTIONSV_COVERAGE
  `include "ExceptionsV_coverage.svh"
`endif
`ifdef EXCEPTIONSHV_COVERAGE
  `include "ExceptionsHV_coverage.svh"
`endif
`ifdef EXCEPTIONSZC_COVERAGE
  `include "ExceptionsZc_coverage.svh"
`endif
`ifdef EXCEPTIONSF_COVERAGE
  `include "ExceptionsF_coverage.svh"
`endif
`ifdef ZICNTRU_COVERAGE
  `include "ZicntrU_coverage.svh"
`endif
`ifdef ZICNTRS_COVERAGE
  `include "ZicntrS_coverage.svh"
`endif
`ifdef ZICNTRM_COVERAGE
  `include "ZicntrM_coverage.svh"
`endif
`ifdef INTERRUPTSM_COVERAGE
  `include "InterruptsM_coverage.svh"
`endif
`ifdef INTERRUPTSS_COVERAGE
  `include "InterruptsS_coverage.svh"
`endif
`ifdef INTERRUPTSU_COVERAGE
  `include "InterruptsU_coverage.svh"
`endif
`ifdef INTERRUPTSSSTC_COVERAGE
  `include "InterruptsSstc_coverage.svh"
`endif
`ifdef EXCEPTIONSVM_COVERAGE
  `include "ExceptionsVM_coverage.svh"
`endif
`ifdef EXCEPTIONSVMZAAMO_COVERAGE
  `include "ExceptionsVMZaamo_coverage.svh"
`endif
`ifdef EXCEPTIONSVMZALRSC_COVERAGE
  `include "ExceptionsVMZalrsc_coverage.svh"
`endif
`ifdef SSSTRICTS_COVERAGE
  `include "SsstrictS_coverage.svh"
`endif
`ifdef SSSTRICTM_COVERAGE
  `include "SsstrictM_coverage.svh"
`endif
`ifdef SSSTRICTV_COVERAGE
  `include "SsstrictV_coverage.svh"
`endif
`ifdef EXCEPTIONSZAAMO_COVERAGE
  `include "ExceptionsZaamo_coverage.svh"
`endif
`ifdef EXCEPTIONSZALRSC_COVERAGE
  `include "ExceptionsZalrsc_coverage.svh"
`endif
`ifdef EXCEPTIONSZICBOU_COVERAGE
  `include "ExceptionsZicboU_coverage.svh"
`endif
`ifdef EXCEPTIONSZICBOS_COVERAGE
  `include "ExceptionsZicboS_coverage.svh"
`endif
