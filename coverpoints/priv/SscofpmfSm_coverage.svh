///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written by Ayesha Anwar ayesha.anwaar2005@gmail.com
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSCOFPMFSM
covergroup SscofpmfSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RVTEST_coverage_sscofpmf.svh"
    cp_mhpmevent_inhibit_bits: cross mhpmevent_minh, mhpmevent_sinh, mhpmevent_uinh;
    cp_minh_inhibits_mmode:    cross priv_mode_m, mhpmevent_minh, hpmcounter_nonzero, mhpmevent_of_zero ;
    cp_of_set_on_overflow:     cross priv_mode_m, mip_clear, mie_clear, mhpmevent_of;
    cp_overflow_hw_only:       cross priv_mode_m, mip_clear, mie_clear, mhpmcounter_extremes, mhpmevent_all_zero;
    cp_scountovf_mcounteren:   cross priv_mode_m, of_write_pattern, mcounteren_write_pattern ;
    cp_sscofpmf_access:        cross priv_mode_m, csr_access_pattern, hpm_csr_target ;
    cp_lcofi:                  cross priv_mode_m, lcofi_ip, lcofi_ie, lcofi_mideleg, mstatus_mie_clear, mstatus_sie_set;
    cp_lcofip_priority:        cross priv_mode_m, mstatus_mie_set, sstatus_sie_set, csrops,  lcofi_ip_one, mip_other_pending {ignore_bins not_csrw    = binsof(csrops.csrs) || binsof(csrops.csrc);}
endgroup

function void sscofpmfSm_sample(int hart, int issue, ins_t ins);
    Sscofpmfsm_cg.sample(ins);
endfunction
