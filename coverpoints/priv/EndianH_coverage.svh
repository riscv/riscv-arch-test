///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Julia Gong jgong@g.hmc.edu November 10, 2025
//
// Copyright (C) 2025 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ENDIANH
covergroup EndianH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // "Endianness tests in hypervisor mode"

    // building blocks for the main coverpoints
    // ENDIANNESS COVERPOINTS: check writes and reads with various endianness
    cp_sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    cp_sh: coverpoint ins.current.insn {
        wildcard bins sh = {SH};
    }
    cp_sb: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
    }
    cp_lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    cp_lh: coverpoint ins.current.insn {
        wildcard bins lh = {LH};
    }
    cp_lhu: coverpoint ins.current.insn {
        wildcard bins lhu = {LHU};
    }
    cp_lb: coverpoint ins.current.insn {
        wildcard bins lb = {LB};
    }
    cp_lbu: coverpoint ins.current.insn {
        wildcard bins lbu = {LBU};
    }

    `ifdef XLEN64
    cp_sd: coverpoint ins.current.insn {
        wildcard bins sd = {SD};
    }
    cp_ld: coverpoint ins.current.insn {
        wildcard bins ld = {LD};
    }
    cp_lwu: coverpoint ins.current.insn {
        wildcard bins lwu = {LWU};
    }
    cp_doubleoffset: coverpoint ins.current.imm[2:0] iff (ins.current.rs1_val[2:0] == 3'b000)  {
        bins zero = {3'b000};
    }
    `endif

    cp_byteoffset: coverpoint {ins.current.imm + ins.current.rs1_val}[2:0] {
        // all byte offsets
    }
    cp_halfoffset: coverpoint {ins.current.imm + ins.current.rs1_val}[2:0] {
        wildcard ignore_bins lsb = {3'b??1};
        // all halfword offsets
    }
    cp_wordoffset: coverpoint {ins.current.imm + ins.current.rs1_val}[2:0] {
        wildcard ignore_bins b0 = {3'b??1};
        wildcard ignore_bins b2 = {3'b?1?};
        // all word offsets
    }


    hstatus_vsbe: coverpoint ins.current.csr[CSR_HSTATUS][5] { // vsbe is hstatus[5]
    }


    mstatus_mprv: coverpoint ins.current.csr[CSR_MSTATUS][17] { // mprv is mstatus[17]
    }

    mstatus_mpp: coverpoint ins.current.csr[CSR_MSTATUS][12:11] { // mpp is mstatus[12:11]
        bins S_Mode = {2'b01};
        bins M_Mode = {2'b11};
    }

    `ifdef XLEN64
        mstatus_mpv: coverpoint ins.current.csr[300][37] {// mpv is mstatus[39] in RV64
        }
    `else
        mstatus_mpv: coverpoint ins.current.csr[310][7] { // mpv is mstatush[7] in RV32
        }
    `endif

    `ifdef XLEN64
        mstatus_mbe: coverpoint ins.current.csr[CSR_MSTATUS][37] { // mbe is mstatus[37] in RV64
        }
    `else
        mstatus_mbe: coverpoint ins.current.csr[CSR_MSTATUSH][5] { // mbe is mstatush[5] in RV32
        }
    `endif

    vsstatus_ube: coverpoint ins.current.csr[CSR_VSSTATUS][6] { // ube is vsstatus[6]
    }



    // main coverpoints
    cp_hstatus_vbe_endianness_sw:  cross priv_mode_vs, hstatus_vsbe, cp_sw,  cp_wordoffset;
    cp_hstatus_vbe_endianness_sh:  cross priv_mode_vs, hstatus_vsbe, cp_sh,  cp_halfoffset;
    cp_hstatus_vbe_endianness_sb:  cross priv_mode_vs, hstatus_vsbe, cp_sb,  cp_byteoffset;
    cp_hstatus_vbe_endianness_lw:  cross priv_mode_vs, hstatus_vsbe, cp_lw,  cp_wordoffset;
    cp_hstatus_vbe_endianness_lh:  cross priv_mode_vs, hstatus_vsbe, cp_lh,  cp_halfoffset;
    cp_hstatus_vbe_endianness_lb:  cross priv_mode_vs, hstatus_vsbe, cp_lb,  cp_byteoffset;
    cp_hstatus_vbe_endianness_lhu: cross priv_mode_vs, hstatus_vsbe, cp_lhu, cp_halfoffset;
    cp_hstatus_vbe_endianness_lbu: cross priv_mode_vs, hstatus_vsbe, cp_lbu, cp_byteoffset;
    cp_mstatus_mprv_vsbe_endianness_sw:  cross priv_mode_m, hstatus_vsbe, cp_sw,  cp_wordoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_mstatus_mprv_vsbe_endianness_sh:  cross priv_mode_m, hstatus_vsbe, cp_sh,  cp_halfoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_mstatus_mprv_vsbe_endianness_sb:  cross priv_mode_m, hstatus_vsbe, cp_sb,  cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_mstatus_mprv_vsbe_endianness_lw:  cross priv_mode_m, hstatus_vsbe, cp_lw,  cp_wordoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_mstatus_mprv_vsbe_endianness_lh:  cross priv_mode_m, hstatus_vsbe, cp_lh,  cp_halfoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_mstatus_mprv_vsbe_endianness_lb:  cross priv_mode_m, hstatus_vsbe, cp_lb,  cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_mstatus_mprv_vsbe_endianness_lhu: cross priv_mode_m, hstatus_vsbe, cp_lhu, cp_halfoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_mstatus_mprv_vsbe_endianness_lbu: cross priv_mode_m, hstatus_vsbe, cp_lbu, cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
    cp_vsstatus_ube_endianness_sw:  cross priv_mode_vu, vsstatus_ube, cp_sw,  cp_wordoffset;
    cp_vsstatus_ube_endianness_sh:  cross priv_mode_vu, vsstatus_ube, cp_sh,  cp_halfoffset;
    cp_vsstatus_ube_endianness_sb:  cross priv_mode_vu, vsstatus_ube, cp_sb,  cp_byteoffset;
    cp_vsstatus_ube_endianness_lw:  cross priv_mode_vu, vsstatus_ube, cp_lw,  cp_wordoffset;
    cp_vsstatus_ube_endianness_lh:  cross priv_mode_vu, vsstatus_ube, cp_lh,  cp_halfoffset;
    cp_vsstatus_ube_endianness_lb:  cross priv_mode_vu, vsstatus_ube, cp_lb,  cp_byteoffset;
    cp_vsstatus_ube_endianness_lhu: cross priv_mode_vu, vsstatus_ube, cp_lhu, cp_halfoffset;
    cp_vsstatus_ube_endianness_lbu: cross priv_mode_vu, vsstatus_ube, cp_lbu, cp_byteoffset;
    `ifdef XLEN64
        cp_hstatus_vbe_endianness_sd:  cross priv_mode_vs, hstatus_vsbe, cp_sd,  cp_doubleoffset;
        cp_hstatus_vbe_endianness_ld:  cross priv_mode_vs, hstatus_vsbe, cp_ld,  cp_doubleoffset;
        cp_hstatus_vbe_endianness_lwu: cross priv_mode_vs, hstatus_vsbe, cp_lwu, cp_wordoffset;
        cp_mstatus_mprv_vsbe_endianness_sd:  cross priv_mode_m, hstatus_vsbe, cp_lbu, cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
        cp_mstatus_mprv_vsbe_endianness_ld:  cross priv_mode_m, hstatus_vsbe, cp_lbu, cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
        cp_mstatus_mprv_vsbe_endianness_lwu: cross priv_mode_m, hstatus_vsbe, cp_lbu, cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp, mstatus_mpv;
        cp_vsstatus_ube_endianness_sd:  cross priv_mode_vu, vsstatus_ube, cp_sd,  cp_doubleoffset;
        cp_vsstatus_ube_endianness_ld:  cross priv_mode_vu, vsstatus_ube, cp_ld,  cp_doubleoffset;
        cp_vsstatus_ube_endianness_lwu: cross priv_mode_vu, vsstatus_ube, cp_lwu, cp_wordoffset;
    `endif

endgroup

function void endianh_sample(int hart, int issue, ins_t ins);
    EndianH_cg.sample(ins);
endfunction
