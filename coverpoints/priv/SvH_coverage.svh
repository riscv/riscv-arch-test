///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written By: Muhammad Abdullah abdullah.gohar@10xengineers.ai January 07, 2026
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVH
covergroup SvH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    read_write_acc: coverpoint {ins.current.write_access, ins.current.read_access} {
        bins read_acc = {2'b01};
        bins write_acc = {2'b10};
    }

    exec_acc: coverpoint ins.current.execute_access {
        bins exec_acc  = {1'b1};
    }

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }

    `ifdef XLEN64
        mode_field_values: coverpoint ins.current.rs1_val[63:60] {
            bins values_to_write[] = {[0:15]};
        }

        vsatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vsatp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }

        vsatp: coverpoint ins.current.insn[31:20] {
            bins vsatp = {CSR_VSATP};
        }

        hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hgatp", "mode") {
            bins bare = {0};
            bins sv39x4 = {8};
        }

        hgatp: coverpoint ins.current.insn[31:20] {
            bins hgatp = {CSR_HGATP};
        }

        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "satp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }

        satp: coverpoint ins.current.insn[31:20] {
            bins satp = {CSR_SATP};
        }
    `endif

    vsatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vsatp", "mode") {
        `ifdef XLEN64
            bins sv39 = {4'b1000};
        `else
            bins sv32 = {1'b1};
        `endif
    }

    ppn_field_values: coverpoint ins.current.rs1_val {
        bins all_zeros = {0};
        `ifdef XLEN32
            bins all_ones        = {22'b1111111111111111111111};
            bins walking_ones_0  = {22'b0000000000000000000001};
            bins walking_ones_1  = {22'b0000000000000000000010};
            bins walking_ones_2  = {22'b0000000000000000000100};
            bins walking_ones_3  = {22'b0000000000000000001000};
            bins walking_ones_4  = {22'b0000000000000000010000};
            bins walking_ones_5  = {22'b0000000000000000100000};
            bins walking_ones_6  = {22'b0000000000000001000000};
            bins walking_ones_7  = {22'b0000000000000010000000};
            bins walking_ones_8  = {22'b0000000000000100000000};
            bins walking_ones_9  = {22'b0000000000001000000000};
            bins walking_ones_10 = {22'b0000000000010000000000};
            bins walking_ones_11 = {22'b0000000000100000000000};
            bins walking_ones_12 = {22'b0000000001000000000000};
            bins walking_ones_13 = {22'b0000000010000000000000};
            bins walking_ones_14 = {22'b0000000100000000000000};
            bins walking_ones_15 = {22'b0000001000000000000000};
            bins walking_ones_16 = {22'b0000010000000000000000};
            bins walking_ones_17 = {22'b0000100000000000000000};
            bins walking_ones_18 = {22'b0001000000000000000000};
            bins walking_ones_19 = {22'b0010000000000000000000};
            bins walking_ones_20 = {22'b0100000000000000000000};
            bins walking_ones_21 = {22'b1000000000000000000000};
        `else
            bins all_ones        = {44'b11111111111111111111111111111111111111111111};
            bins walking_ones_0  = {44'b00000000000000000000000000000000000000000001};
            bins walking_ones_1  = {44'b00000000000000000000000000000000000000000010};
            bins walking_ones_2  = {44'b00000000000000000000000000000000000000000100};
            bins walking_ones_3  = {44'b00000000000000000000000000000000000000001000};
            bins walking_ones_4  = {44'b00000000000000000000000000000000000000010000};
            bins walking_ones_5  = {44'b00000000000000000000000000000000000000100000};
            bins walking_ones_6  = {44'b00000000000000000000000000000000000001000000};
            bins walking_ones_7  = {44'b00000000000000000000000000000000000010000000};
            bins walking_ones_8  = {44'b00000000000000000000000000000000000100000000};
            bins walking_ones_9  = {44'b00000000000000000000000000000000001000000000};
            bins walking_ones_10 = {44'b00000000000000000000000000000000010000000000};
            bins walking_ones_11 = {44'b00000000000000000000000000000000100000000000};
            bins walking_ones_12 = {44'b00000000000000000000000000000001000000000000};
            bins walking_ones_13 = {44'b00000000000000000000000000000010000000000000};
            bins walking_ones_14 = {44'b00000000000000000000000000000100000000000000};
            bins walking_ones_15 = {44'b00000000000000000000000000001000000000000000};
            bins walking_ones_16 = {44'b00000000000000000000000000010000000000000000};
            bins walking_ones_17 = {44'b00000000000000000000000000100000000000000000};
            bins walking_ones_18 = {44'b00000000000000000000000001000000000000000000};
            bins walking_ones_19 = {44'b00000000000000000000000010000000000000000000};
            bins walking_ones_20 = {44'b00000000000000000000000100000000000000000000};
            bins walking_ones_21 = {44'b00000000000000000000001000000000000000000000};
            bins walking_ones_22 = {44'b00000000000000000000010000000000000000000000};
            bins walking_ones_23 = {44'b00000000000000000000100000000000000000000000};
            bins walking_ones_24 = {44'b00000000000000000001000000000000000000000000};
            bins walking_ones_25 = {44'b00000000000000000010000000000000000000000000};
            bins walking_ones_26 = {44'b00000000000000000100000000000000000000000000};
            bins walking_ones_27 = {44'b00000000000000001000000000000000000000000000};
            bins walking_ones_28 = {44'b00000000000000010000000000000000000000000000};
            bins walking_ones_29 = {44'b00000000000000100000000000000000000000000000};
            bins walking_ones_30 = {44'b00000000000001000000000000000000000000000000};
            bins walking_ones_31 = {44'b00000000000010000000000000000000000000000000};
            bins walking_ones_32 = {44'b00000000000100000000000000000000000000000000};
            bins walking_ones_33 = {44'b00000000001000000000000000000000000000000000};
            bins walking_ones_34 = {44'b00000000010000000000000000000000000000000000};
            bins walking_ones_35 = {44'b00000000100000000000000000000000000000000000};
            bins walking_ones_36 = {44'b00000001000000000000000000000000000000000000};
            bins walking_ones_37 = {44'b00000010000000000000000000000000000000000000};
            bins walking_ones_38 = {44'b00000100000000000000000000000000000000000000};
            bins walking_ones_39 = {44'b00001000000000000000000000000000000000000000};
            bins walking_ones_40 = {44'b00010000000000000000000000000000000000000000};
            bins walking_ones_41 = {44'b00100000000000000000000000000000000000000000};
            bins walking_ones_42 = {44'b01000000000000000000000000000000000000000000};
            bins walking_ones_43 = {44'b10000000000000000000000000000000000000000000};
        `endif
    }

    asid_field_value: coverpoint ins.current.rs1_val {
        `ifdef XLEN32
            wildcard bins all_ones = {32'b?_111111111_??????????????????????};
        `else
            wildcard bins all_ones = {64'b????_1111111111111111_????????????????????????????????????????????};
        `endif
    }

    sum_vsstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vsstatus", "sum") {
        bins unset = {0};
        bins set = {1};
    }

    mxr_vsstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vsstatus", "mxr") {
        bins unset = {0};
        bins set = {1};
    }

    vsbe_hstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hstatus", "vsbe") {
        bins unset = {0};
        bins set = {1};
    }

    tvm_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "tvm") {
        bins tvm_set = {1};
        bins tvm_unset = {0};
    }

    mprv_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mprv") {
        bins mprv_set = {1};
    }

    hgatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hgatp", "mode") {
        bins hgatp_bare = {0};
    }
    satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "satp", "mode") {
        bins satp_bare = {0};
    }
    mpv_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mpv") {
        bins mpv_set = {1};
    }

    mpp_mstatus_u: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") {
        bins s_mode = {2'b00};
    }
    mpp_mstatus_s: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") {
        bins m_mode = {2'b01};
    }

    g_pte_xwr100_s_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins pte_s = {8'b11?01001};
    }
    g_pte_xwr100_u_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins pte_u = {8'b11?11001};
    }

    g_pte_xwr111_u_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins leaf_pte = {8'b11?11111};
    }
    g_pte_xwr111_u_i: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins leaf_pte = {8'b11?11111};
    }

    g_pte_i_inv: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins invalid_pte = {8'b11??1??0};
    }
    g_pte_d_inv: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins invalid_pte = {8'b11???110};
    }

    pte_nonleaf_lvl0_i: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins lvl0_xwr000 = {8'b????0001};
    }
    pte_nonleaf_lvl0_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins lvl0_xwr000 = {8'b????0001};
    }

    pte_xwr_comb_i: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins rwx001_u = {8'b???11001};
        wildcard bins rwx001_s = {8'b???01001};
        wildcard bins rwx111_u = {8'b???11111};
        wildcard bins rwx111_s = {8'b???01111};
    }
    pte_xwr_comb_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins rwx001_u = {8'b???11001};
        wildcard bins rwx001_s = {8'b???01001};
        wildcard bins rwx111_u = {8'b???11111};
        wildcard bins rwx111_s = {8'b???01111};
    }

    `ifdef XLEN64
        vsatp_mode_field: cross priv_mode_hs, vsatp_mode, csrrw, vsatp, mode_field_values;
        satp_mode_field:  cross priv_mode_vs, satp_mode, csrrw, satp, mode_field_values;
        hgatp_mode_field: cross priv_mode_hs, hgatp_mode, csrrw, hgatp, mode_field_values;
    `endif

    vsatp_ppn_field:      cross priv_mode_hs, vsatp_mode, csrrw, vsatp, ppn_field_values;
    vsatp_asidlen_detect: cross priv_mode_hs, vsatp_mode, csrrw, vsatp, asid_field_value;

    vsatp_mprv_effects_s: cross priv_mode_m, mprv_mstatus, mpp_mstatus_s, vsatp_mode, hgatp_bare, satp_bare, g_pte_xwr100_s_d, read_write_acc;
    vsatp_mprv_effects_u: cross priv_mode_m, mprv_mstatus, mpp_mstatus_u, vsatp_mode, hgatp_bare, satp_bare, g_pte_xwr100_u_d, read_write_acc;

    vsatp_endianess:   cross priv_mode_vs, vsatp_mode, vsbe_hstatus, read_write_acc;
    hgatp_tvm_effects: cross priv_mode_hs, tvm_mstatus, csrrw, hgatp;

    vsatp_invalid_pte_rw: cross priv_mode_vs, vsatp_mode, g_pte_d_inv, read_write_acc;
    vsatp_invalid_pte_x:  cross priv_mode_vs, vsatp_mode, g_pte_i_inv, exec_acc;

    vsatp_sum_effects_rw: cross priv_mode_vs, sum_vsstatus, g_pte_xwr111_u_d, read_write_acc;
    vsatp_sum_effects_x : cross priv_mode_vs, sum_vsstatus, g_pte_xwr111_u_i, exec_acc;

    vsatp_nonleaf_lvl0_rw: cross priv_mode_vs, vsatp_mode, pte_nonleaf_lvl0_d, read_write_acc;
    vsatp_nonleaf_lvl0_x:  cross priv_mode_vs, vsatp_mode, pte_nonleaf_lvl0_i, exec_acc;

    vsstatus_vs_mxr_sum_rw: cross priv_mode_vs_vu, vsatp_mode, sum_vsstatus, mxr_vsstatus, pte_xwr_comb_d, read_write_acc;
    vsstatus_vs_mxr_sum_x:  cross priv_mode_vs_vu, vsatp_mode, sum_vsstatus, mxr_vsstatus, pte_xwr_comb_i, exec_acc;


endgroup

function void vmh_sample(int hart, int issue, ins_t ins);
    SvH_cg.sample(ins);
endfunction
