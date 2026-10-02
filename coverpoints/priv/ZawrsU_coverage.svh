///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Ellen Yu ellyu@hmc.edu June 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZAWRSU
covergroup ZawrsU_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    wrs_nto: coverpoint ins.current.insn {
        bins wrs_nto = {WRS_NTO};
    }

    wrs_sto: coverpoint ins.current.insn {
        bins wrs_sto = {WRS_STO};
    }

    wrs_ops: coverpoint ins.current.insn {
        bins wrs_nto = {WRS_NTO};
        bins wrs_sto = {WRS_STO};

    }

    sc_w: coverpoint ins.prev.insn {
        wildcard bins sc_w = {SC_W};
    }
    lr_w: coverpoint ins.prev.insn {
        wildcard bins lr_w = {LR_W};
    }

    mstatus_tw:  coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tw")) {
        bins zero = {0};
        bins one  = {1};
    }

    mstatus_tw_one:  coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tw")) {
        bins one = {1};
    }

    mstatus_tw_zero:  coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tw")) {
        bins zero = {0};
    }

    mstatus_mie: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie"))  {
        bins zero = {0};
        bins one  = {1};
    }
    mstatus_mie_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")) {
        bins zero = {0};
    }
    mstatus_mie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")) {
        bins one = {1};
    }

    mip_mtip_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mtip")) {
        bins one = {1};
    }

    mip_any_ones: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mtip") ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "meip") ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "msip")
                           `ifdef S_SUPPORTED
                        || get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "stip") ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "seip") ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "ssip")
                           `endif){
        bins any_ones = {1};
    }

    mie_zeros: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")) {
        bins zeros = {0}; // zero in all 6 interrupt enable bits
    }

    `ifdef S_SUPPORTED
        mstatus_sie: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")) {
            bins zero = {0};
            bins one  = {1};
        }
        mstatus_sie_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")) {
            bins zero = {0};
        }
        mstatus_sie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")) {
            bins one = {1};
        }
    `endif
    `ifdef SSTC_SUPPORTED
        sie_stie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sie", "stie")) {
            bins one = {1};
        }
        `ifdef UDB_MXLEN_64
            menvcfg_STCE_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")) {
                bins one  = {1};
            }

        `else
            menvcfg_STCE_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")) {
                bins one  = {1};
            }
        `endif
    `else
        mie_mtie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mtie")) {
            bins one = {1};
        }
    `endif

    // main coverpoints
    cp_wrs_sto_timeout:     cross wrs_sto, mstatus_tw, mstatus_mie_zero, priv_mode_u, mie_zeros,
        `ifdef S_SUPPORTED
            mstatus_sie_zero,
        `endif
        lr_w;
    cp_wrs_no_res:          cross mstatus_tw_zero, mstatus_mie_zero, priv_mode_u, mie_zeros, sc_w,
        `ifdef S_SUPPORTED
            mstatus_sie_zero,
        `endif
        wrs_ops;
    cp_wrs_resume:          cross mstatus_tw_zero,
        `ifdef SSTC_SUPPORTED
            sie_stie_one, menvcfg_STCE_one,
        `else
            mie_mtie_one,
        `endif
        `ifdef S_SUPPORTED
            mstatus_sie,
        `endif
    mstatus_mie, priv_mode_u, wrs_ops, lr_w;

    cp_wrs_nto_timeout:     cross mstatus_tw_one, mstatus_mie_zero, priv_mode_u, mie_zeros, wrs_nto,
        `ifdef S_SUPPORTED
            mstatus_sie_zero,
        `endif
        lr_w;

    cp_wrs_no_mie:     cross mstatus_tw_one, mstatus_mie_one, mip_any_ones, priv_mode_u, mie_zeros, wrs_ops,
        `ifdef S_SUPPORTED
            mstatus_sie_one,
        `endif
        lr_w;


endgroup

// ---------------------
function void zawrsu_sample(int hart, int issue, ins_t ins);
    ZawrsU_cg.sample(ins);
endfunction
