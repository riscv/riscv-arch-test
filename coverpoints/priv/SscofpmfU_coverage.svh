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

    `ifdef S_SUPPORTED

        sie_lcofi: coverpoint ins.current.csr[CSR_SIE][13] {}
        sip_lcofi: coverpoint ins.current.csr[CSR_SIP][13] {}
        sip_lcofi_one: coverpoint ins.current.csr[CSR_SIP][13] {
                bins one = {1};
        }
        sip_lcofi_zero: coverpoint ins.current.csr[CSR_SIP][13] {
            bins zero = {0};
        }

        sret_insn: coverpoint ins.current.insn {
                type_option.weight = 0;
                bins sret = {SRET};
        }
        old_sstatus_spp_u: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "spp")[0] {
                type_option.weight = 0;
                bins to_u = {0};
        }
    `else
        lcofi_ip_one: coverpoint ins.current.csr[CSR_MIP][13] {
                bins one  = {1};
        }
        lcofi_ip_zero: coverpoint ins.current.csr[CSR_MIP][13] {
                bins zero  = {0};
        }

        lcofi_ip: coverpoint ins.current.csr[CSR_MIP][13] {}
        lcofi_ie: coverpoint ins.current.csr[CSR_MIE][13] {}
    `endif

    cp_uinh_inhibits_umode:    cross priv_mode_u, mhpmevent_xinh_combos, mhpmevent_of_zero;
    `ifdef S_SUPPORTED

        cp_of_set_on_overflow: cross priv_mode_u, sip_lcofi_one, mie_clear, mhpmevent_of_one, mhpmevent_inhibits_pattern_state;
    `else
        cp_of_set_on_overflow: cross priv_mode_u, lcofi_ip_one, mie_clear, mhpmevent_of_one, mhpmevent_inhibits_pattern_state;
    `endif
    cp_overflow_hw_only:       cross priv_mode_u, mip_clear, mie_clear, mhpmcounter_extreme_state, mhpmevent_all_zero;
    `ifdef S_SUPPORTED

        cp_lcofip_hw_only:     cross priv_mode_u, mhpmevent_of, sip_lcofi_zero ;

    `else
        cp_lcofip_hw_only:     cross priv_mode_u, mhpmevent_of, lcofi_ip_zero;
    `endif
    `ifdef S_SUPPORTED

        cp_lcofi_sip_u: cross sret_insn, old_sstatus_spp_u, sie_lcofi, sip_lcofi;
    `else

        cp_lcofi_sip_u: cross priv_mode_u, lcofi_ie, lcofi_ip;
    `endif

endgroup

function void sscofpmfu_sample(int hart, int issue, ins_t ins);
    SscofpmfU_cg.sample(ins);
endfunction
