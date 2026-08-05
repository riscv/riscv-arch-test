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

    acc_instr: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
        wildcard bins hlv_w = {HLV_W};
        wildcard bins hsv_w = {HSV_W};
    }

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }

    // CSRRW then CSRR (csrrs rd,csr,x0) — VMID readback after write
    raw_csrrw_csrr: coverpoint {ins.prev.insn[14:12], ins.current.insn[14:12]} {
        bins raw = {6'b001_010};
    }

    vs_pte_rsw: coverpoint ins.current.vs_pte_d[9:8];
    g_pte_rsw: coverpoint ins.current.g_pte_d[9:8];

    // CSR address bins (needed on RV32 and RV64; crosses reference these)
    vsatp: coverpoint ins.current.insn[31:20] {
        bins vsatp = {CSR_VSATP};
    }
    hgatp: coverpoint ins.current.insn[31:20] {
        bins hgatp = {CSR_HGATP};
    }
    satp: coverpoint ins.current.insn[31:20] {
        bins satp = {CSR_SATP};
    }

    `ifdef UDB_MXLEN_64
        mode_field_values: coverpoint ins.current.rs1_val[63:60] {
            bins values_to_write[] = {[0:15]};
        }

        mode_vsatp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vsatp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }

        mode_hgatp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hgatp", "mode") {
            bins bare = {0};
            bins sv39x4 = {8};
        }

        mode_satp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "satp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }

        pbmte_menvcfg: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "menvcfg", "pbmte") {
            bins no_support = {1'b0};
        }

        vs_pte_i_svpbmt: coverpoint ins.current.vs_pte_i[62:61];
        vs_pte_d_svpbmt: coverpoint ins.current.vs_pte_d[62:61];

        g_pte_i_svpbmt: coverpoint ins.current.g_pte_i[62:61];
        g_pte_d_svpbmt: coverpoint ins.current.g_pte_d[62:61];

        vs_pte_i_reserved: coverpoint ins.current.vs_pte_i[60:54] {
            bins all_zeros      = {7'b0000000};
            bins walking_one_54 = {7'b0000001};
            bins walking_one_55 = {7'b0000010};
            bins walking_one_56 = {7'b0000100};
            bins walking_one_57 = {7'b0001000};
            bins walking_one_58 = {7'b0010000};
            bins walking_one_59 = {7'b0100000};
            bins walking_one_60 = {7'b1000000};
            bins all_ones       = {7'b1111111};
        }
        vs_pte_d_reserved: coverpoint ins.current.vs_pte_d[60:54] {
            bins all_zeros      = {7'b0000000};
            bins walking_one_54 = {7'b0000001};
            bins walking_one_55 = {7'b0000010};
            bins walking_one_56 = {7'b0000100};
            bins walking_one_57 = {7'b0001000};
            bins walking_one_58 = {7'b0010000};
            bins walking_one_59 = {7'b0100000};
            bins walking_one_60 = {7'b1000000};
            bins all_ones       = {7'b1111111};
        }

        g_pte_i_reserved: coverpoint ins.current.g_pte_i[60:54] {
            bins all_zeros      = {7'b0000000};
            bins walking_one_54 = {7'b0000001};
            bins walking_one_55 = {7'b0000010};
            bins walking_one_56 = {7'b0000100};
            bins walking_one_57 = {7'b0001000};
            bins walking_one_58 = {7'b0010000};
            bins walking_one_59 = {7'b0100000};
            bins walking_one_60 = {7'b1000000};
            bins all_ones       = {7'b1111111};
        }
        g_pte_d_reserved: coverpoint ins.current.g_pte_d[60:54] {
            bins all_zeros      = {7'b0000000};
            bins walking_one_54 = {7'b0000001};
            bins walking_one_55 = {7'b0000010};
            bins walking_one_56 = {7'b0000100};
            bins walking_one_57 = {7'b0001000};
            bins walking_one_58 = {7'b0010000};
            bins walking_one_59 = {7'b0100000};
            bins walking_one_60 = {7'b1000000};
            bins all_ones       = {7'b1111111};
        }
    `endif

    vsatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vsatp", "mode") {
        `ifdef UDB_MXLEN_64
            bins sv39 = {4'b1000};
        `else
            bins sv32 = {1'b1};
        `endif
    }
    hgatp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hgatp", "mode") {
        `ifdef UDB_MXLEN_64
            bins sv39x4 = {4'b1000};
        `else
            bins sv32x4 = {1'b1};
        `endif
    }

    // PPN field alone (not full rs1) — MODE/ASID/VMID must not poison bins
`ifdef UDB_MXLEN_32
    ppn_field_values: coverpoint ins.current.rs1_val[21:0] {
        bins all_zeros = {0};
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
        bins walking_ones_10  = {22'b0000000000010000000000};
        bins walking_ones_11  = {22'b0000000000100000000000};
        bins walking_ones_12  = {22'b0000000001000000000000};
        bins walking_ones_13  = {22'b0000000010000000000000};
        bins walking_ones_14  = {22'b0000000100000000000000};
        bins walking_ones_15  = {22'b0000001000000000000000};
        bins walking_ones_16  = {22'b0000010000000000000000};
        bins walking_ones_17  = {22'b0000100000000000000000};
        bins walking_ones_18  = {22'b0001000000000000000000};
        bins walking_ones_19  = {22'b0010000000000000000000};
        bins walking_ones_20  = {22'b0100000000000000000000};
        bins walking_ones_21  = {22'b1000000000000000000000};
    }
`else
    ppn_field_values: coverpoint ins.current.rs1_val[43:0] {
        bins all_zeros = {0};
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
        bins walking_ones_10  = {44'b00000000000000000000000000000000010000000000};
        bins walking_ones_11  = {44'b00000000000000000000000000000000100000000000};
        bins walking_ones_12  = {44'b00000000000000000000000000000001000000000000};
        bins walking_ones_13  = {44'b00000000000000000000000000000010000000000000};
        bins walking_ones_14  = {44'b00000000000000000000000000000100000000000000};
        bins walking_ones_15  = {44'b00000000000000000000000000001000000000000000};
        bins walking_ones_16  = {44'b00000000000000000000000000010000000000000000};
        bins walking_ones_17  = {44'b00000000000000000000000000100000000000000000};
        bins walking_ones_18  = {44'b00000000000000000000000001000000000000000000};
        bins walking_ones_19  = {44'b00000000000000000000000010000000000000000000};
        bins walking_ones_20  = {44'b00000000000000000000000100000000000000000000};
        bins walking_ones_21  = {44'b00000000000000000000001000000000000000000000};
        bins walking_ones_22  = {44'b00000000000000000000010000000000000000000000};
        bins walking_ones_23  = {44'b00000000000000000000100000000000000000000000};
        bins walking_ones_24  = {44'b00000000000000000001000000000000000000000000};
        bins walking_ones_25  = {44'b00000000000000000010000000000000000000000000};
        bins walking_ones_26  = {44'b00000000000000000100000000000000000000000000};
        bins walking_ones_27  = {44'b00000000000000001000000000000000000000000000};
        bins walking_ones_28  = {44'b00000000000000010000000000000000000000000000};
        bins walking_ones_29  = {44'b00000000000000100000000000000000000000000000};
        bins walking_ones_30  = {44'b00000000000001000000000000000000000000000000};
        bins walking_ones_31  = {44'b00000000000010000000000000000000000000000000};
        bins walking_ones_32  = {44'b00000000000100000000000000000000000000000000};
        bins walking_ones_33  = {44'b00000000001000000000000000000000000000000000};
        bins walking_ones_34  = {44'b00000000010000000000000000000000000000000000};
        bins walking_ones_35  = {44'b00000000100000000000000000000000000000000000};
        bins walking_ones_36  = {44'b00000001000000000000000000000000000000000000};
        bins walking_ones_37  = {44'b00000010000000000000000000000000000000000000};
        bins walking_ones_38  = {44'b00000100000000000000000000000000000000000000};
        bins walking_ones_39  = {44'b00001000000000000000000000000000000000000000};
        bins walking_ones_40  = {44'b00010000000000000000000000000000000000000000};
        bins walking_ones_41  = {44'b00100000000000000000000000000000000000000000};
        bins walking_ones_42  = {44'b01000000000000000000000000000000000000000000};
        bins walking_ones_43  = {44'b10000000000000000000000000000000000000000000};
    }
`endif

    asid_field_value: coverpoint ins.current.rs1_val {
        `ifdef UDB_MXLEN_32
            wildcard bins all_ones = {32'b?_111111111_??????????????????????};
        `else
            wildcard bins all_ones = {64'b????_1111111111111111_????????????????????????????????????????????};
        `endif
    }
    vmid_field_value: coverpoint ins.current.rs1_val {
        `ifdef UDB_MXLEN_32
            wildcard bins all_ones = {32'b???_1111111_??????????????????????};
        `else
            wildcard bins all_ones = {64'b??????_11111111111111_????????????????????????????????????????????};
        `endif
    }
    // For read-after-write scoping: VMID is in prev CSRRW's rs1
    vmid_field_prev: coverpoint ins.prev.rs1_val {
        `ifdef UDB_MXLEN_32
            wildcard bins all_ones = {32'b???_1111111_??????????????????????};
        `else
            wildcard bins all_ones = {64'b??????_11111111111111_????????????????????????????????????????????};
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

    mstatus_mprv_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mprv") {
        bins mprv_set = {1};
    }
    mstatus_mprv_unset: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mprv") {
        bins mprv_unset = {0};
    }
    mprv_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstatus", "mprv") {
        bins mprv_unset = {0};
        bins mprv_set = {1};
    }

    hgatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "hgatp", "mode") {
        bins hgatp_bare = {0};
    }
    vsatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "vsatp", "mode") {
        bins satp_bare = {0};
    }
    satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "satp", "mode") {
        bins satp_bare = {0};
    }

    `ifdef UDB_MXLEN_32
    // RV32: MPV lives in mstatush[7]. Sample PREV so trap CSR updates on the
    // faulting insn do not clear MPV before the coverpoint sees it.
    mstatus_mpv_set: coverpoint ins.prev.csr[CSR_MSTATUSH][7] {
        bins mpv_set = {1};
    }
    mstatus_mpv_unset: coverpoint ins.prev.csr[CSR_MSTATUSH][7] {
        bins mpv_unset = {0};
    }
    `else
    mstatus_mpv_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpv") {
        bins mpv_set = {1};
    }
    mstatus_mpv_unset: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpv") {
        bins mpv_unset = {0};
    }
    `endif

    mpp_mstatus_m: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") {
        bins m_mode = {2'b11};
    }
    mpp_mstatus_s: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") {
        bins s_mode = {2'b01};
    }
    mpp_mstatus_u: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "mpp") {
        bins s_mode = {2'b00};
    }

    vs_pte_xwr111_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins vs_pte_d = {8'b11??1111};
    }
    vs_pte_xwr100_s_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins vs_pte_s = {8'b11?01001};
    }
    vs_pte_xwr100_u_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins vs_pte_u = {8'b11?11001};
    }

    vs_pte_xwr111_u_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins leaf_pte = {8'b11?11111};
    }
    vs_pte_xwr111_u_i: coverpoint ins.current.vs_pte_i[7:0] {
        wildcard bins leaf_pte = {8'b11?11111};
    }

    vs_pte_i_inv: coverpoint ins.current.vs_pte_i[7:0] {
        wildcard bins invalid_pte = {8'b11??1??0};
    }
    vs_pte_d_inv: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins invalid_pte = {8'b11???110};
    }

    vs_pte_legal_xwr_i: coverpoint ins.current.vs_pte_i[7:0] {
        wildcard bins rwx100 = {8'b???00011};
        wildcard bins rwx110 = {8'b???00111};
        wildcard bins rwx001 = {8'b???01001};
        wildcard bins rwx101 = {8'b???01011};
        wildcard bins rwx111 = {8'b???01111};
    }
    vs_pte_legal_xwr_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins rwx100 = {8'b???00011};
        wildcard bins rwx110 = {8'b???00111};
        wildcard bins rwx001 = {8'b???01001};
        wildcard bins rwx101 = {8'b???01011};
        wildcard bins rwx111 = {8'b???01111};
    }

    vs_pte_nonleaf_lvl0_i: coverpoint ins.current.vs_pte_i[7:0] {
        wildcard bins lvl0_xwr000 = {8'b????0001};
    }
    vs_pte_nonleaf_lvl0_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins lvl0_xwr000 = {8'b????0001};
    }

    vs_pte_xwr_comb_i: coverpoint ins.current.vs_pte_i[7:0] {
        wildcard bins rwx001_u = {8'b???11001};
        wildcard bins rwx001_s = {8'b???01001};
        wildcard bins rwx111_u = {8'b???11111};
        wildcard bins rwx111_s = {8'b???01111};
    }
    vs_pte_xwr_comb_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins rwx001_u = {8'b???11001};
        wildcard bins rwx001_s = {8'b???01001};
        wildcard bins rwx111_u = {8'b???11111};
        wildcard bins rwx111_s = {8'b???01111};
    }

    vs_pte_uxwr_perm_i: coverpoint ins.current.vs_pte_i[7:0] {
        wildcard bins urwx0000 = {8'b???00001};
        wildcard bins urwx1000 = {8'b???10001};
        wildcard bins urwx0111 = {8'b???01111};
        wildcard bins urwx1111 = {8'b???11111};
    }
    vs_pte_uxwr_perm_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins urwx0000 = {8'b???00001};
        wildcard bins urwx1000 = {8'b???10001};
        wildcard bins urwx0111 = {8'b???01111};
        wildcard bins urwx1111 = {8'b???11111};
    }

    vs_pte_ad: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins vs_pte_ad_set = {8'b11??1111};
        wildcard bins vs_pte_ad_unset = {8'b00??1111};
    }

    g_pte_xwr100_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins g_pte_xwr100 = {8'b????1001};
    }

    g_pte_ad_unset: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins g_pte_ad = {8'b00??1111};
    }

    g_pte_i_u: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins g_pte_u_unset = {8'b???01111};
        wildcard bins g_pte_u_set = {8'b???11111};
    }
    g_pte_d_u: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins g_pte_u_unset = {8'b???01111};
        wildcard bins g_pte_u_set = {8'b???11111};
    }

    g_pte_nonleaf_lvl0_i: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins lvl0_xwr000 = {8'b????0001};
    }
    g_pte_nonleaf_lvl0_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins lvl0_xwr000 = {8'b????0001};
    }

    g_pte_i_inv: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins invalid_pte = {8'b11??1??0};
    }
    g_pte_d_inv: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins invalid_pte = {8'b11???110};
    }

    g_pte_uxwr_perm_i: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins urwx0000 = {8'b???00001};
        wildcard bins urwx1000 = {8'b???10001};
        wildcard bins urwx0111 = {8'b???01111};
        wildcard bins urwx1111 = {8'b???11111};
    }
    g_pte_uxwr_perm_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins urwx0000 = {8'b???00001};
        wildcard bins urwx1000 = {8'b???10001};
        wildcard bins urwx0111 = {8'b???01111};
        wildcard bins urwx1111 = {8'b???11111};
    }

    g_pte_d_g_set: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins g_bit_set = {8'b1???1111};
    }
    g_pte_i_g_set: coverpoint ins.current.g_pte_i[7:0] {
        wildcard bins g_bit_set = {8'b1???1111};
    }

    // Execute-only leaf (X=1,R=0,W=0,V=1); U/A/D/G wildcard
    vs_pte_xonly_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins xonly = {8'b????1001};
    }
    g_pte_xonly_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins xonly = {8'b????1001};
    }

    // HS sstatus.MXR (two-stage MXR samples HS sstatus)
    mxr_sstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "sstatus", "mxr") {
        bins unset = {0};
        bins set = {1};
    }

    // Acc opcodes split for MPRV×hgatp (HLV/HSV unaffected by MPRV)
    acc_lw_sw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
    }
    acc_hlv_hsv: coverpoint ins.current.insn {
        wildcard bins hlv_w = {HLV_W};
        wildcard bins hsv_w = {HSV_W};
    }

    `ifdef UDB_MXLEN_64
        // Coverpoint: cp_vsatp_mode_field
        cp_vsatp_mode_field: cross priv_mode_hs, csrrw, vsatp, mode_field_values;
        // Coverpoint: cp_satp_mode_field
        cp_satp_mode_field:  cross priv_mode_vs, csrrw, satp, mode_field_values;
        // Coverpoint: cp_hgatp_mode_field
        cp_hgatp_mode_field: cross priv_mode_hs, csrrw, hgatp, mode_field_values;

        // Coverpoint: cp_vsatp_svpbmt
        cp_vsatp_svpbmt_rw: cross priv_mode_hs, vsatp_mode, pbmte_menvcfg, vs_pte_d_svpbmt, read_write_acc;
        cp_vsatp_svpbmt_x:  cross priv_mode_hs, vsatp_mode, pbmte_menvcfg, vs_pte_i_svpbmt, exec_acc;

        // Coverpoint: cp_hgatp_svpbmt
        cp_hgatp_svpbmt_rw: cross priv_mode_hs, hgatp_mode, pbmte_menvcfg, g_pte_d_svpbmt, read_write_acc;
        cp_hgatp_svpbmt_x:  cross priv_mode_hs, hgatp_mode, pbmte_menvcfg, g_pte_i_svpbmt, exec_acc;

        // Coverpoint: cp_vsatp_reserved_fields
        cp_vsatp_reserved_fields_rw: cross priv_mode_hs, vsatp_mode, vs_pte_d_reserved, read_write_acc;
        cp_vsatp_reserved_fields_x : cross priv_mode_hs, vsatp_mode, vs_pte_i_reserved, exec_acc;

        // Coverpoint: cp_hgatp_reserved_fields
        cp_hgatp_reserved_fields_rw : cross priv_mode_hs, hgatp_mode, g_pte_d_reserved, read_write_acc;
        cp_hgatp_reserved_fields_x  : cross priv_mode_hs, hgatp_mode, g_pte_i_reserved, exec_acc;
    `endif

    // Coverpoint: cp_vsatp_ppn_field
    cp_vsatp_ppn_field:      cross priv_mode_hs, vsatp_mode, csrrw, vsatp, ppn_field_values;
    // Coverpoint: cp_vsatp_asidlen_detect
    cp_vsatp_asidlen_detect: cross priv_mode_hs, vsatp_mode, csrrw, vsatp, asid_field_value;

    // Coverpoint: cp_hgatp_ppn_field
    // Sv*x4 WARL forces PPN[1:0]=0 — ignore those walking bins
    cp_hgatp_ppn_field:      cross priv_mode_hs, hgatp_mode, csrrw, hgatp, ppn_field_values {
        // Sv*x4 WARL: PPN[1:0]=0; all-ones PPN not implementable with MODE set
        ignore_bins align0 = binsof(ppn_field_values.walking_ones_0);
        ignore_bins align1 = binsof(ppn_field_values.walking_ones_1);
        ignore_bins all1   = binsof(ppn_field_values.all_ones);
    }
    // Coverpoint: cp_hgatp_vmidlen_detect
    cp_hgatp_vmidlen_detect: cross priv_mode_hs, hgatp_mode, csrrw, hgatp, vmid_field_value;

    // R/W S/U leaves for MPRV×vsatp (translated loads — not X-only)
    vs_pte_rw_s_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins rw_s = {8'b11?00111};
    }
    vs_pte_rw_u_d: coverpoint ins.current.vs_pte_d[7:0] {
        wildcard bins rw_u = {8'b11?10111};
    }
    g_pte_rw_d: coverpoint ins.current.g_pte_d[7:0] {
        wildcard bins rw = {8'b????0111};
    }

    // Coverpoint: cp_vsatp_mprv_effects (Test only does lw. Don’t require sw thus added ignore_bins writes)
    // MPRV=1: data uses vsatp; MPRV=0: negative (no VS translate)
    //Data access as VS → vsatp translates
    cp_vsatp_mprv_effects_s: cross priv_mode_m, mstatus_mprv_set, mpp_mstatus_s, vsatp_mode, hgatp_bare, satp_bare, vs_pte_rw_s_d, read_write_acc {
        ignore_bins writes = binsof(read_write_acc.write_acc);
    }
    //Data access as VU → vsatp translates
    cp_vsatp_mprv_effects_u: cross priv_mode_m, mstatus_mprv_set, mpp_mstatus_u, vsatp_mode, hgatp_bare, satp_bare, vs_pte_rw_u_d, read_write_acc {
        ignore_bins writes = binsof(read_write_acc.write_acc);
    }
    //Data access does not take the MPRV→VS/VU path → vsatp not used
    cp_vsatp_mprv_effects_off: cross priv_mode_m, mstatus_mprv_unset, vsatp_mode, hgatp_bare, satp_bare, read_write_acc {
        ignore_bins writes = binsof(read_write_acc.write_acc);
    }

    // Coverpoint: cp_hgatp_mprv_effects
    // MPRV=1 × {M,HS,VS,U,VU} × lw; HLV/HSV ignore MPRV (separate cross).
    // VS/VU (MPV=1): G walked → X-only leaf deny. M/HS/U (MPV=0 or MPP=M): no G walk.
    cp_hgatp_mprv_effects_m: cross priv_mode_m, mstatus_mprv_set, mpp_mstatus_m, hgatp_mode, acc_lw_sw {
        ignore_bins stores = binsof(acc_lw_sw.sw);
    }
    cp_hgatp_mprv_effects_hs: cross priv_mode_m, mstatus_mprv_set, mpp_mstatus_s, mstatus_mpv_unset, hgatp_mode, acc_lw_sw {
        ignore_bins stores = binsof(acc_lw_sw.sw);
    }
    cp_hgatp_mprv_effects_vs: cross priv_mode_m, mstatus_mprv_set, mpp_mstatus_s, mstatus_mpv_set, hgatp_mode, g_pte_xwr100_d, acc_lw_sw {
        ignore_bins stores = binsof(acc_lw_sw.sw);
    }
    cp_hgatp_mprv_effects_u: cross priv_mode_m, mstatus_mprv_set, mpp_mstatus_u, mstatus_mpv_unset, hgatp_mode, acc_lw_sw {
        ignore_bins stores = binsof(acc_lw_sw.sw);
    }
    cp_hgatp_mprv_effects_vu: cross priv_mode_m, mstatus_mprv_set, mpp_mstatus_u, mstatus_mpv_set, hgatp_mode, g_pte_xwr100_d, acc_lw_sw {
        ignore_bins stores = binsof(acc_lw_sw.sw);
    }
    // HLV ignores MPRV; R/W G leaf allow (not the X-only deny story)
    cp_hgatp_mprv_effects_hlv: cross priv_mode_m, mstatus_mprv_set, hgatp_mode, g_pte_rw_d, acc_hlv_hsv {
        ignore_bins hsv = binsof(acc_hlv_hsv.hsv_w);
    }


    // Coverpoint: cp_vsatp_endianess
    cp_vsatp_endianess:   cross priv_mode_vs, vsatp_mode, vsbe_hstatus, vs_pte_xwr111_d, read_write_acc;
    // Coverpoint: cp_hgatp_tvm_effects
    cp_hgatp_tvm_effects: cross priv_mode_hs, tvm_mstatus, csrrw, hgatp;

    // Coverpoint: cp_vsatp_pte_rsw
    cp_vsatp_pte_rsw: cross priv_mode_vs, vsatp_mode, vs_pte_rsw, read_write_acc;
    // Coverpoint: cp_hgatp_pte_rsw
    cp_hgatp_pte_rsw: cross priv_mode_hs, hgatp_mode, g_pte_rsw, read_write_acc;

    // Coverpoint: cp_vsatp_invalid_pte
    cp_vsatp_invalid_pte_rw: cross priv_mode_hs, vsatp_mode, vs_pte_d_inv, read_write_acc;
    cp_vsatp_invalid_pte_x:  cross priv_mode_hs, vsatp_mode, vs_pte_i_inv, exec_acc;

    // Coverpoint: cp_hgatp_invalid_pte
    cp_hgatp_invalid_pte_rw: cross priv_mode_hs, hgatp_mode, g_pte_d_inv, read_write_acc;
    cp_hgatp_invalid_pte_x:  cross priv_mode_hs, hgatp_mode, g_pte_i_inv, exec_acc;

    // Coverpoint: cp_vsatp_sum_effects
    cp_vsatp_sum_effects_rw: cross priv_mode_vs, sum_vsstatus, vs_pte_xwr111_u_d, read_write_acc;
    cp_vsatp_sum_effects_x : cross priv_mode_vs, sum_vsstatus, vs_pte_xwr111_u_i, exec_acc;

    // Coverpoint: cp_vsatp_nonleaf_lvl0
    cp_vsatp_nonleaf_lvl0_rw: cross priv_mode_vs, vsatp_mode, vs_pte_nonleaf_lvl0_d, read_write_acc;
    cp_vsatp_nonleaf_lvl0_x:  cross priv_mode_vs, vsatp_mode, vs_pte_nonleaf_lvl0_i, exec_acc;

    // Coverpoint: cp_hgatp_nonleaf_lvl0
    cp_hgatp_nonleaf_lvl0_rw: cross priv_mode_hs, hgatp_mode, g_pte_nonleaf_lvl0_d, read_write_acc;
    cp_hgatp_nonleaf_lvl0_x:  cross priv_mode_hs, hgatp_mode, g_pte_nonleaf_lvl0_i, exec_acc;

    // Coverpoint: cp_vsstatus_mxr_sum
    cp_vsstatus_mxr_sum_rw: cross priv_mode_vs_vu, vsatp_mode, sum_vsstatus, mxr_vsstatus, vs_pte_xwr_comb_d, read_write_acc;
    cp_vsstatus_mxr_sum_x:  cross priv_mode_vs_vu, vsatp_mode, sum_vsstatus, mxr_vsstatus, vs_pte_xwr_comb_i, exec_acc;

    // Coverpoint: cp_vsatp_spages_sum_rwx
    cp_vsatp_spages_sum_rw: cross priv_mode_vs, vsatp_mode, sum_vsstatus, vs_pte_legal_xwr_d, read_write_acc;
    cp_vsatp_spages_sum_x:  cross priv_mode_vs, vsatp_mode, sum_vsstatus, vs_pte_legal_xwr_i, exec_acc;

    // Coverpoint: cp_vsatp_perm_checks
    cp_vsatp_perm_checks_rw: cross priv_mode_vs_vu, vsatp_mode, vs_pte_uxwr_perm_d, read_write_acc;
    cp_vsatp_perm_checks_x:  cross priv_mode_vs_vu, vsatp_mode, vs_pte_uxwr_perm_i, exec_acc;

    // Coverpoint: cp_hgatp_perm_checks
    cp_hgatp_perm_checks_rw: cross priv_mode_vs_vu, hgatp_mode, g_pte_uxwr_perm_d, read_write_acc;
    cp_hgatp_perm_checks_x:  cross priv_mode_vs_vu, hgatp_mode, g_pte_uxwr_perm_i, exec_acc;

    // Coverpoint: cp_hgatp_adbit_behavior
    cp_hgatp_adbit_behavior: cross priv_mode_hs, g_pte_ad_unset, vs_pte_ad, read_write_acc;
    // Coverpoint: cp_hgatp_vmid_scoping
    cp_hgatp_vmid_scoping:   cross priv_mode_hs, hgatp_mode, raw_csrrw_csrr, hgatp, vmid_field_prev;

    // Coverpoint: cp_hgatp_u_mode_access
    cp_hgatp_u_mode_access_rw: cross priv_mode_hs, hgatp_mode, vsatp_bare, g_pte_d_u, read_write_acc;
    cp_hgatp_u_mode_access_x:  cross priv_mode_hs, hgatp_mode, vsatp_bare, g_pte_i_u, exec_acc;

    // Coverpoint: hgatp_pte_g_bit
    cp_hgatp_pte_g_bit_rw: cross priv_mode_hs, hgatp_mode, g_pte_d_g_set, read_write_acc;
    cp_hgatp_pte_g_bit_x:  cross priv_mode_hs, hgatp_mode, g_pte_i_g_set, exec_acc;


    //--------------------------------------------------------------------------
    // Two-stage success / Bare / G-walk of VS PT
    //--------------------------------------------------------------------------
    // Coverpoint: two_stage_read
    two_stage_read:  cross priv_mode_vs, vsatp_mode, hgatp_mode, read_write_acc {
        ignore_bins writes = binsof(read_write_acc.write_acc);
    }
    // Coverpoint: two_stage_write
    two_stage_write: cross priv_mode_vs, vsatp_mode, hgatp_mode, read_write_acc {
        ignore_bins reads = binsof(read_write_acc.read_acc);
    }
    // Coverpoint: two_stage_ifetch
    two_stage_ifetch: cross priv_mode_vs, vsatp_mode, hgatp_mode, exec_acc;
    // Coverpoint: stage_both_bare
    stage_both_bare: cross priv_mode_vs, vsatp_bare, hgatp_bare, read_write_acc;
    // Coverpoint: cp_hgatp_bare_trans
    cp_hgatp_bare_trans: cross priv_mode_vs, vsatp_mode, hgatp_bare, read_write_acc;
    // Coverpoint: cp_h_vm_gstagetrans
    cp_h_vm_gstagetrans: cross priv_mode_vs, vsatp_mode, hgatp_mode, read_write_acc;

    //--------------------------------------------------------------------------
    // Two-stage MXR (distinct from cp_vsstatus_mxr_sum)
    //--------------------------------------------------------------------------
    // Coverpoint: cp_two_stage_mxr (MXR only affects loads of X-only pages)
    // Stimulus: VS+G X-only; MXR=0 faults, MXR=1 loads. sstatus↔vsstatus track together.
    cp_two_stage_mxr: cross priv_mode_vs, vsatp_mode, hgatp_mode, mxr_vsstatus, vs_pte_xonly_d, read_write_acc {
        ignore_bins writes = binsof(read_write_acc.write_acc);
    }

    //--------------------------------------------------------------------------
    // TODO — not yet implemented
    //--------------------------------------------------------------------------
    // TODO Coverpoint: cp_vsatp_speculative_a_bit (OBS — squash)
    // TODO Coverpoint: cp_hgatp_gpa_width_checks (RV64)
    // TODO Coverpoint: hgatp_misaligned_superpage
    // TODO Coverpoint: hgatp_root_table_alignment_and_size
    // TODO Coverpoint: hgatp_exception_reporting (needs cause/TRAP bins)
    // TODO Coverpoint: mprv_sum_effect_hs_two_stage
    // TODO Coverpoint: VM_permission_invalid
    // TODO Coverpoint: RWX access on Umode pages in Umode
    // TODO Coverpoint: PTE X=1 MXR=0 HS/VS/VU/G (broader X-only cases; ≠ cp_two_stage_mxr)
    // TODO Coverpoint: cp_hfence_functionality / cp_hfence_vvma_operand
    // TODO Coverpoint: cp_hgatp_mode_change_hfence / cp_hfence_gvma_operand
    //--------------------------------------------------------------------------

endgroup

function void svh_sample(int hart, int issue, ins_t ins);
    SvH_cg.sample(ins);
endfunction
