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

`define COVER_SSCOFPMFS
covergroup SscofpmfS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "RVTEST_coverage_sscofpmf.svh"
    of_walking_one: coverpoint $clog2(`OF_VEC) iff ($onehot(`OF_VEC)) {
            bins b_of[] = {[0:28]};  // one bin per OF bit position (mhpmevent3..mhpmevent31 = 29 bits)
    }
    of_pattern_class: coverpoint $countones(`OF_VEC) {
            bins all_zeros   = {0};
            bins all_ones    = {29};
    }

    scountovf_of_match: coverpoint ((ins.current.csr[CSR_SCOUNTOVF][31:3] & ins.current.csr[CSR_MCOUNTEREN][31:3]) == (`OF_VEC & ins.current.csr[CSR_MCOUNTEREN][31:3])) {
            bins match = {1};
    }
    sstatus_sie_set: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins one = {1};
    }

    cp_sinh_inhibits_smode:    cross priv_mode_s, mhpmevent_sinh, hpmcounter_nonzero, mhpmevent_of_zero ;
    cp_of_set_on_overflow:     cross priv_mode_s, mip_clear, mie_clear, mhpmevent_of;
    cp_overflow_hw_only:       cross priv_mode_s, mip_clear, mie_clear, mhpmcounter_extremes, mhpmevent_all_zero;
    cp_lcofip_hw_only:         cross priv_mode_s, mhpmevent_of_set_then_cleared;
    cp_scountovf_shadow:       cross priv_mode_s, mcounteren_write_all_ones, of_pattern_class, of_walking_one, scountovf_of_match;
    cp_scountovf_mcounteren:   cross priv_mode_s, of_write_pattern, mcounteren_write_pattern ;
    cp_sscofpmf_access:        cross priv_mode_s, csr_access_pattern, hpm_csr_target ;
    cp_lcofi_sip_s:            cross priv_mode_s, sstatus_sie_set, lcofi_ie, lcofi_ip, lcofi_mideleg_one ;
    cp_lcofip_priority:        cross priv_mode_s, mstatus_mie_set, sstatus_sie_set, csrops,  lcofi_ip_one, mip_other_pending {ignore_bins not_csrw    = binsof(csrops.csrs) || binsof(csrops.csrc);}
endgroup

function void sscofpmfs_sample(int hart, int issue, ins_t ins);
    SscofpmfS_cg.sample(ins);
endfunction
