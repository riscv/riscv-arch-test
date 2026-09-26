///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 20 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ENDIANS
covergroup EndianS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    // "Endianness tests in machine mode"

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
    `ifdef UDB_MXLEN_64
        mstatus_mbe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mbe")[0] {
        }
    `else
        mstatus_mbe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "mbe")[0] {
        }
    `endif
    `ifdef UDB_MXLEN_64
        mstatus_sbe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "sbe")[0] {
        }
    `else
        mstatus_sbe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "sbe")[0] {
        }
    `endif
    sstatus_ube: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstatus", "ube")[0] {
    }
    mstatus_mprv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mprv")[0] {
    }
    mstatus_mpp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mpp")[1:0] {
        bins S_Mode = {2'b01};
        bins M_Mode = {2'b11};
    }
    // main coverpoints
    cp_mstatus_sbe_endianness_sw:  cross priv_mode_s, mstatus_sbe, cp_sw,  cp_wordoffset;
    cp_mstatus_sbe_endianness_sh:  cross priv_mode_s, mstatus_sbe, cp_sh,  cp_halfoffset;
    cp_mstatus_sbe_endianness_sb:  cross priv_mode_s, mstatus_sbe, cp_sb,  cp_byteoffset;
    cp_mstatus_sbe_endianness_lw:  cross priv_mode_s, mstatus_sbe, cp_lw,  cp_wordoffset;
    cp_mstatus_sbe_endianness_lh:  cross priv_mode_s, mstatus_sbe, cp_lh,  cp_halfoffset;
    cp_mstatus_sbe_endianness_lb:  cross priv_mode_s, mstatus_sbe, cp_lb,  cp_byteoffset;
    cp_mstatus_sbe_endianness_lhu: cross priv_mode_s, mstatus_sbe, cp_lhu, cp_halfoffset;
    cp_mstatus_sbe_endianness_lbu: cross priv_mode_s, mstatus_sbe, cp_lbu, cp_byteoffset;
    cp_mstatus_mprv_sbe_endianness_sw:  cross priv_mode_m, mstatus_sbe, cp_sw,  cp_wordoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_mstatus_mprv_sbe_endianness_sh:  cross priv_mode_m, mstatus_sbe, cp_sh,  cp_halfoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_mstatus_mprv_sbe_endianness_sb:  cross priv_mode_m, mstatus_sbe, cp_sb,  cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_mstatus_mprv_sbe_endianness_lw:  cross priv_mode_m, mstatus_sbe, cp_lw,  cp_wordoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_mstatus_mprv_sbe_endianness_lh:  cross priv_mode_m, mstatus_sbe, cp_lh,  cp_halfoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_mstatus_mprv_sbe_endianness_lb:  cross priv_mode_m, mstatus_sbe, cp_lb,  cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_mstatus_mprv_sbe_endianness_lhu: cross priv_mode_m, mstatus_sbe, cp_lhu, cp_halfoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_mstatus_mprv_sbe_endianness_lbu: cross priv_mode_m, mstatus_sbe, cp_lbu, cp_byteoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
    cp_sstatus_ube_endianness_sw:  cross priv_mode_u, sstatus_ube, cp_sw,  cp_wordoffset;
    cp_sstatus_ube_endianness_sh:  cross priv_mode_u, sstatus_ube, cp_sh,  cp_halfoffset;
    cp_sstatus_ube_endianness_sb:  cross priv_mode_u, sstatus_ube, cp_sb,  cp_byteoffset;
    cp_sstatus_ube_endianness_lw:  cross priv_mode_u, sstatus_ube, cp_lw,  cp_wordoffset;
    cp_sstatus_ube_endianness_lh:  cross priv_mode_u, sstatus_ube, cp_lh,  cp_halfoffset;
    cp_sstatus_ube_endianness_lb:  cross priv_mode_u, sstatus_ube, cp_lb,  cp_byteoffset;
    cp_sstatus_ube_endianness_lhu: cross priv_mode_u, sstatus_ube, cp_lhu, cp_halfoffset;
    cp_sstatus_ube_endianness_lbu: cross priv_mode_u, sstatus_ube, cp_lbu, cp_byteoffset;
    `ifdef UDB_MXLEN_64
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
        cp_mstatus_sbe_endianness_sd:  cross priv_mode_s, mstatus_sbe, cp_sd,  cp_doubleoffset;
        cp_mstatus_sbe_endianness_ld:  cross priv_mode_s, mstatus_sbe, cp_ld,  cp_doubleoffset;
        cp_mstatus_sbe_endianness_lwu: cross priv_mode_s, mstatus_sbe, cp_lwu, cp_wordoffset;
        cp_mstatus_mprv_sbe_endianness_sd:  cross priv_mode_m, mstatus_sbe, cp_sd, cp_doubleoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
        cp_mstatus_mprv_sbe_endianness_ld:  cross priv_mode_m, mstatus_sbe, cp_ld, cp_doubleoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
        cp_mstatus_mprv_sbe_endianness_lwu: cross priv_mode_m, mstatus_sbe, cp_lwu,  cp_wordoffset, mstatus_mprv, mstatus_mbe, mstatus_mpp;
        cp_sstatus_ube_endianness_sd:  cross priv_mode_u, sstatus_ube, cp_sd,  cp_doubleoffset;
        cp_sstatus_ube_endianness_ld:  cross priv_mode_u, sstatus_ube, cp_ld,  cp_doubleoffset;
        cp_sstatus_ube_endianness_lwu: cross priv_mode_u, sstatus_ube, cp_lwu, cp_wordoffset;
    `endif

endgroup

function void endians_sample(int hart, int issue, ins_t ins);
    EndianS_cg.sample(ins);
endfunction
