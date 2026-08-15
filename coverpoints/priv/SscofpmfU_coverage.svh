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
    `include "RISCV_coverage_sscofpmf.svh"
    sstatus_sie_clear: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins zero = {0};
    }
    mhpmevent_uinh: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][60] {
            bins zero = {0};
            bins one  = {1};
    }

    cp_uinh_inhibits_umode:    cross priv_mode_u, mhpmevent_uinh, hpmcounter_nonzero, mhpmevent_of_zero ;
    cp_of_set_on_overflow:     cross priv_mode_u, mip_clear, mie_clear, mhpmevent_of, mhpmevent_inhibits_all_set;
    `ifdef UDB_MXLEN_64
        cp_overflow_hw_only:   cross priv_mode_u, mip_clear, mie_clear, mhpmcounter_write_extremes, mhpmevent_all_zero;
    `else
        cp_overflow_hw_only:   cross priv_mode_u, mip_clear, mie_clear, mhpmcounter_write_extremes, mhpmevent_all_zero, mhpmevent_base_zero;
    `endif
    cp_lcofi:                  cross priv_mode_u, lcofi_ip, lcofi_ie, lcofi_mideleg, mstatus_mie_clear, mstatus_sie_set;
    cp_lcofi_sip_u:            cross priv_mode_u, sstatus_sie_clear, lcofi_ie, lcofi_ip, lcofi_mideleg_one ;
    cp_lcofip_priority:        cross priv_mode_u, mstatus_mie_set, sstatus_sie_set, mie_clear, lcofi_ip_one, mip_other_pending;

endgroup

function void sscofpmfu_sample(int hart, int issue, ins_t ins);
    SscofpmfU_cg.sample(ins);
endfunction
