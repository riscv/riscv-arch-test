///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Ellen Yu ellyu@hmc.edu July 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZAWRS
`ifndef EXCLUDE_SM
covergroup Zawrs_Sm_cg with function sample(ins_t ins);
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

    mie_zeros: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")) {
        bins zeros = {0}; // zero in all 6 interrupt enable bits
    }
    mie_mtie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mtie")) {
        bins one = {1};
    }

    mip_any_ones: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mtip")[0] ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "meip")[0] ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "msip")[0] ){
        bins any_ones = {1};
    }



    // main coverpoints
    cp_wrs_sto_timeout:     cross priv_mode_m, wrs_sto, mstatus_tw, mstatus_mie_zero, mie_zeros, lr_w;
    cp_wrs_no_res:          cross priv_mode_m, mstatus_tw, mstatus_mie_zero, mie_zeros, sc_w, wrs_ops;
    `ifdef UDB_MTI_INTR_IMPL
        cp_wrs_resume:      cross priv_mode_m, mstatus_tw, mie_mtie_one, mstatus_mie, wrs_ops, lr_w;
    `endif
    // mip_any_ones needs a machine interrupt that can be made pending
    `ifdef UDB_MEI_INTR_IMPL
        cp_wrs_no_mie:      cross priv_mode_m, mstatus_tw_zero, mstatus_mie_one, mie_zeros, mip_any_ones, wrs_sto, lr_w;
    `elsif UDB_MSI_INTR_IMPL
        cp_wrs_no_mie:      cross priv_mode_m, mstatus_tw_zero, mstatus_mie_one, mie_zeros, mip_any_ones, wrs_sto, lr_w;
    `elsif UDB_MTI_INTR_IMPL
        cp_wrs_no_mie:      cross priv_mode_m, mstatus_tw_zero, mstatus_mie_one, mie_zeros, mip_any_ones, wrs_sto, lr_w;
    `endif

endgroup
`endif

covergroup Zawrs_S_cg with function sample(ins_t ins);
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

    mip_any_ones: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mtip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "meip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "msip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "stip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "seip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "ssip")[0]
                            ){
        bins any_ones = {1};
    }


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
    mie_zeros: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")) {
        bins zeros = {0}; // zero in all 6 interrupt enable bits
    }
    `ifdef SSTC_SUPPORTED
        sie_stie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sie", "stie")) {
            bins one = {1};
        }
    `else
        mie_mtie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mtie")) {
            bins one = {1};
        }
    `endif

    `ifdef SSTC_SUPPORTED
        `ifdef UDB_MXLEN_64
            menvcfg_STCE_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")) {
                bins one  = {1};
            }
        `else
            menvcfg_STCE_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")) {
                bins one  = {1};
            }
        `endif
    `endif



    // main coverpoints
    cp_wrs_sto_timeout:     cross wrs_sto, mstatus_tw, mstatus_mie_zero, mstatus_sie_zero, priv_mode_s, mie_zeros, lr_w;

    cp_wrs_no_res:          cross mstatus_tw_zero, mstatus_mie_zero, mstatus_sie_zero, priv_mode_s, mie_zeros, sc_w, wrs_ops;

    `ifdef SSTC_SUPPORTED
        cp_wrs_resume:      cross mstatus_tw_zero, sie_stie_one, menvcfg_STCE_one,
            mstatus_mie, mstatus_sie, priv_mode_s, wrs_ops, lr_w;
    `elsif UDB_MTI_INTR_IMPL
        cp_wrs_resume:      cross mstatus_tw_zero, mie_mtie_one,
            mstatus_mie, mstatus_sie, priv_mode_s, wrs_ops, lr_w;
    `endif

    cp_wrs_nto_timeout:     cross mstatus_tw_one, mstatus_mie_zero, mstatus_sie_zero, priv_mode_s, mie_zeros, wrs_nto, lr_w;

    cp_wrs_no_mie:     cross mstatus_tw_one, mstatus_mie_one, mip_any_ones, mstatus_sie_one, priv_mode_s, mie_zeros, wrs_ops, lr_w;

endgroup

covergroup Zawrs_U_cg with function sample(ins_t ins);
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

    mip_any_ones: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mtip")[0] ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "meip")[0] ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "msip")[0]
                           `ifdef S_SUPPORTED
                        || get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "stip")[0] ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "seip")[0] ||
                           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "ssip")[0]
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
    `ifdef SSTC_SUPPORTED
        cp_wrs_resume:      cross mstatus_tw_zero, sie_stie_one, menvcfg_STCE_one,
            `ifdef S_SUPPORTED
                mstatus_sie,
            `endif
            mstatus_mie, priv_mode_u, wrs_ops, lr_w;
    `elsif UDB_MTI_INTR_IMPL
        cp_wrs_resume:      cross mstatus_tw_zero, mie_mtie_one,
            `ifdef S_SUPPORTED
                mstatus_sie,
            `endif
            mstatus_mie, priv_mode_u, wrs_ops, lr_w;
    `endif

    cp_wrs_nto_timeout:     cross mstatus_tw_one, mstatus_mie_zero, priv_mode_u, mie_zeros, wrs_nto,
        `ifdef S_SUPPORTED
            mstatus_sie_zero,
        `endif
        lr_w;

    // mip_any_ones needs an interrupt that can be made pending, S-mode interrupts can be set through mip
    `ifdef S_SUPPORTED
        cp_wrs_no_mie:      cross mstatus_tw_one, mstatus_mie_one, mip_any_ones, priv_mode_u, mie_zeros, wrs_ops,
            mstatus_sie_one, lr_w;
    `elsif UDB_MEI_INTR_IMPL
        cp_wrs_no_mie:      cross mstatus_tw_one, mstatus_mie_one, mip_any_ones, priv_mode_u, mie_zeros, wrs_ops, lr_w;
    `elsif UDB_MSI_INTR_IMPL
        cp_wrs_no_mie:      cross mstatus_tw_one, mstatus_mie_one, mip_any_ones, priv_mode_u, mie_zeros, wrs_ops, lr_w;
    `elsif UDB_MTI_INTR_IMPL
        cp_wrs_no_mie:      cross mstatus_tw_one, mstatus_mie_one, mip_any_ones, priv_mode_u, mie_zeros, wrs_ops, lr_w;
    `endif


endgroup

`ifdef H_SUPPORTED
// The H group runs WRS in VS-mode and VU-mode, entered from HS-mode. The TW/VTW, hedeleg and VSSIP cases
// come from riscv-arch-test PR 2915 by Wei Shen.
covergroup Zawrs_H_cg with function sample(ins_t ins);
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

    mstatus_tw:  coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tw")[0]) {
    }
    mstatus_tw_one:  coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tw")) {
        bins one = {1};
    }
    mstatus_tw_zero:  coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tw")) {
        bins zero = {0};
    }

    hstatus_vtw: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")[0]) {
    }
    hstatus_vtw_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")) {
        bins one = {1};
    }
    hstatus_vtw_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")) {
        bins zero = {0};
    }

    // hedeleg[2] sends the illegal-instruction exception to HS-mode (0) or VS-mode (1)
    hedeleg_illegal_instr: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[2]) {
    }

    mstatus_mie: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")[0]) {
    }
    mstatus_mie_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")) {
        bins zero = {0};
    }
    mstatus_mie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")) {
        bins one = {1};
    }

    mstatus_sie: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")[0]) {
    }
    mstatus_sie_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")) {
        bins zero = {0};
    }
    mstatus_sie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sie")) {
        bins one = {1};
    }

    vsstatus_sie_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sie")) {
        bins zero = {0};
    }

    mie_zeros: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie")) {
        bins zeros = {0}; // every interrupt enable bit, including the VS-level ones in hie
    }

    mip_any_ones: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mtip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "meip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "msip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "stip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "seip")[0] ||
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "ssip")[0]
                            ){
        bins any_ones = {1};
    }

    hvip_all_ones: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hvip", "vssip")[0] &&
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hvip", "vstip")[0] &&
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hvip", "vseip")[0]
                             ){
        bins all_ones = {1};
    }

    // VSSIP delegated to VS-mode, enabled there (vsie.SSIE is hie.VSSIE) and raised through hvip
    hideleg_vssip_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hideleg", "vssip")) {
        bins one = {1};
    }
    hie_vssie_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hie", "vssie")) {
        bins one = {1};
    }
    hvip_vssip_one: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vssip")) {
        bins one = {1};
    }

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
    cp_wrs_sto_timeout_h:   cross priv_mode_vs_vu, wrs_sto, mstatus_tw, hstatus_vtw, mstatus_mie_zero, mstatus_sie_zero, mie_zeros, lr_w;

    cp_wrs_no_res_h:        cross priv_mode_vs_vu, mstatus_tw_zero, hstatus_vtw_zero, mstatus_mie_zero, mstatus_sie_zero, mie_zeros, sc_w, wrs_ops;

    `ifdef SSTC_SUPPORTED
        cp_wrs_resume_h:    cross priv_mode_vs_vu, mstatus_tw_zero, hstatus_vtw_zero, sie_stie_one, menvcfg_STCE_one,
            mstatus_mie, mstatus_sie, wrs_ops, lr_w;
    `elsif UDB_MTI_INTR_IMPL
        cp_wrs_resume_h:    cross priv_mode_vs_vu, mstatus_tw_zero, hstatus_vtw_zero, mie_mtie_one,
            mstatus_mie, mstatus_sie, wrs_ops, lr_w;
    `endif

    cp_wrs_interrupt_h:     cross priv_mode_vs, mstatus_tw_zero, hstatus_vtw_zero, vsstatus_sie_zero,
        hideleg_vssip_one, hie_vssie_one, hvip_vssip_one, wrs_ops, lr_w;

    cp_wrs_nto_tw_h:        cross priv_mode_vs_vu, mstatus_tw_one, hstatus_vtw, hedeleg_illegal_instr,
        mstatus_mie_zero, mstatus_sie_zero, mie_zeros, wrs_nto, lr_w;

    cp_wrs_nto_vtw_h:       cross priv_mode_vs_vu, mstatus_tw_zero, hstatus_vtw_one,
        mstatus_mie_zero, mstatus_sie_zero, mie_zeros, wrs_nto, lr_w;

    cp_wrs_no_mie_h:        cross priv_mode_vs_vu, mstatus_tw_one, hstatus_vtw_zero, mstatus_mie_one, mstatus_sie_one,
        mip_any_ones, hvip_all_ones, mie_zeros, wrs_ops, lr_w;

endgroup
`endif

function void zawrs_sample(int hart, int issue, ins_t ins);
    `ifndef EXCLUDE_SM
        Zawrs_Sm_cg.sample(ins);
    `endif
    Zawrs_S_cg.sample(ins);
    Zawrs_U_cg.sample(ins);
    `ifdef H_SUPPORTED
        Zawrs_H_cg.sample(ins);
    `endif
endfunction
