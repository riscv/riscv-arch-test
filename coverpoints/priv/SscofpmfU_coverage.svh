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

`define COVER_SSCOFPMFU

covergroup SscofpmfU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RVTEST_coverage_sscofpmf.svh"
    sstatus_sie_clear: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins zero = {0};
    }
    cp_mhpmevent_inhibit_bits: cross mhpmevent_minh, mhpmevent_sinh, mhpmevent_uinh;
    cp_uinh_inhibits_umode:    cross priv_mode_u, mhpmevent_uinh, hpmcounter_nonzero, mhpmevent_of_zero ;
    cp_of_set_on_overflow:     cross priv_mode_u, mip_clear, mie_clear, mhpmevent_of;
    cp_overflow_hw_only:       cross priv_mode_u, mip_clear, mie_clear, mhpmcounter_extremes, mhpmevent_all_zero;
    cp_scountovf_mcounteren:   cross priv_mode_u, of_write_pattern, mcounteren_write_pattern ;
    cp_sscofpmf_access:        cross priv_mode_u, csr_access_pattern, hpm_csr_target ;
    cp_lcofi_sip_u:            cross priv_mode_u, sstatus_sie_clear, lcofi_ie, lcofi_ip, lcofi_mideleg_one ;
    cp_lcofip_priority:        cross priv_mode_u, mstatus_mie_set, sstatus_sie_set, csrops,  lcofi_ip_one, mip_other_pending {ignore_bins not_csrw    = binsof(csrops.csrs) || binsof(csrops.csrc);}
endgroup

function void sscofpmfu_sample(int hart, int issue, ins_t ins);
    SscofpmfU_cg.sample(ins);
endfunction
