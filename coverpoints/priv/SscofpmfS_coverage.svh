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
    `include "RISCV_coverage_sscofpmf.svh"
    sstatus_sie_set: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins one = {1};
    }
    `ifdef UDB_MXLEN_64
        mhpmevent_sinh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][61] {
                bins zero = {0};
                bins one  = {1};
        }
        mhpmevent_xinh_combos: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][62:58] {
                bins combo[] = {[0:31]};
        }
        `else
        mhpmevent_sinh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT + 12'h400][29] {
                bins zero = {0};
                bins one  = {1};
        }
        mhpmevent_xinh_combos: coverpoint ins.current.csr[RVMODEL_MHPMEVENT + 12'h400][30:26] {
                bins combo[] = {[0:31]};
        }
        `endif

    cp_sinh_inhibits_smode:    cross priv_mode_s, mhpmevent_sinh, mhpmevent_xinh_combos, hpmcounter_nonzero, mhpmevent_of_zero;
    cp_of_set_on_overflow:     cross priv_mode_s, mip_clear, mie_clear, mhpmevent_of, mhpmevent_inhibits_all_set;
    `ifdef UDB_MXLEN_64
        cp_overflow_hw_only: cross priv_mode_s, mip_clear, mie_clear, mhpmcounter_write_extremes, mhpmevent_all_zero;
    `else
        cp_overflow_hw_only: cross priv_mode_s, mip_clear, mie_clear, mhpmcounter_write_extremes, mhpmevent_all_zero, mhpmevent_base_zero;
    `endif
    cp_lcofip_hw_only:         cross priv_mode_s, mhpmevent_of;
    cp_scountovf_shadow:       cross priv_mode_s, mcounteren_write_all_ones, of_pattern_class, of_walking_one;
    cp_scountovf_mcounteren:   cross priv_mode_s, of_write_pattern, mcounteren_write_pattern, mcounteren_walking_one;
    cp_sscofpmf_access:        cross priv_mode_s, csr_access_pattern, hpm_csr_target ;
    cp_lcofi_sip_s:            cross priv_mode_s, sstatus_sie_set, sie_lcofi, sip_lcofi, lcofi_mideleg_one;
    cp_lcofip_priority_s:      cross priv_mode_s, mstatus_mie_set, sstatus_sie_set, mie_clear, lcofi_ip_one, mip_other_pending;
endgroup

function void sscofpmfs_sample(int hart, int issue, ins_t ins);
    SscofpmfS_cg.sample(ins);
endfunction
