///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////


`define COVER_SMMPM
covergroup Smmpm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    read_instr: coverpoint ins.current.insn {
        wildcard bins lb = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins lh = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw = {LW};
        wildcard bins lwu = {LWU};
        wildcard bins ld = {LD};
    }

    write_instr: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        wildcard bins sd = {SD};
    }

    misalign_read_instr_half: coverpoint ins.current.insn {
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
    }

    misalign_write_instr_half : coverpoint ins.current.insn {
        wildcard bins sh = {SH};
    }

    misalign_read_instr_word: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
        wildcard bins lwu = {LWU};
    }

    misalign_write_instr_word: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }

    misalign_read_instr_double: coverpoint ins.current.insn {
        wildcard bins ld = {LD};
    }

    misalign_write_instr_double: coverpoint ins.current.insn {
        wildcard bins sd = {SD};
    }


    misaligned_half: coverpoint (ins.current.rs1_val + ins.current.imm)[0]
    iff (ins.current.insn inside {LH, LHU, SH}) {
        bins aligned    = {1'b0};
        bins misaligned = {1'b1};
    }

    misaligned_word: coverpoint (ins.current.rs1_val + ins.current.imm)[1:0]
    iff (ins.current.insn inside {LW, LWU, SW}) {
        bins aligned    = {2'b00};
        bins misaligned = {[2'b01:2'b11]};
    }

    misaligned_double: coverpoint (ins.current.rs1_val + ins.current.imm)[2:0]
    iff (ins.current.insn inside {LD, SD}) {
        bins aligned    = {3'b000};
        bins misaligned = {[3'b001:3'b111]};
    }

    mseccfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mseccfg", "pmm") {
        bins enabled_10  = {2'b10};
        bins enabled_11  = {2'b11};
    }

    `ifdef ZAAMO_SUPPORTED
    amo_op: coverpoint ins.current.insn
    iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "A") == 1'b1) {
        wildcard bins amoadd  = {AMOADD_W};
        wildcard bins amoswap = {AMOSWAP_W};
        wildcard bins amoxor  = {AMOXOR_W};
        wildcard bins amoadd_d  = {AMOADD_D};
        wildcard bins amoswap_d = {AMOSWAP_D};
        wildcard bins amoxor_d  = {AMOXOR_D};
    }
     `endif

    exec_op: coverpoint ins.current.insn {
        wildcard bins jal = {JAL};
        wildcard bins jalr = {JALR};
    }

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        bins enabled  = {1'b1};
    }

    csr_write_op: coverpoint ins.current.insn
    iff (ins.current.rs1 != 5'b00000) {
        wildcard bins csrrw = {CSRRW};
    }

    csr_read_op: coverpoint ins.current.insn
    iff (ins.current.rd != 5'b00000) {
        wildcard bins csrrw = {CSRRW};
    }

    csr_software_target : coverpoint ins.current.csr[11:0] {
    bins mepc     = {`CSR_MEPC};
    bins mtvec    = {`CSR_MTVEC};
    bins mscratch = {`CSR_MSCRATCH};
    }

    mtval_written: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval", "value") {
    bins nonzero = {[1:$]};
    }

    mprv_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
    bins enabled = {1'b1};
    }

    mpp_field: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp") {
    bins u_mode = {2'b00};
    bins s_mode = {2'b01};
    }

    mode_satp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
        bins bare = {4'b0000};
        `ifdef SV39
        bins sv39 = {4'b1000};
        `endif
        `ifdef SV48
        bins sv48 = {4'b1001};
        `endif
        `ifdef SV57
        bins sv57 = {4'b1010};
        `endif
    }

    cp_pmlen_masking_write: cross priv_mode_m, mseccfg_pmm,  write_instr;
    cp_pmlen_masking_read: cross priv_mode_m,  mseccfg_pmm, read_instr;
    `ifdef ZAAMO_SUPPORTED
    cp_effective_address_explicit_write: cross priv_mode_m, mseccfg_pmm, write_instr, amo_op ;
    cp_effective_address_explicit_read: cross priv_mode_m, mseccfg_pmm, read_instr, amo_op ;
    `endif
    cp_effective_address_fetch: cross priv_mode_m, mseccfg_pmm , exec_op ;
    cp_mask_priv_mode_only_write: cross priv_mode_m,  mseccfg_pmm,    write_instr; //still working on this one.
    cp_mask_priv_mode_only_read: cross priv_mode_m,  mseccfg_pmm,   read_instr ;
    cp_pm_misaligned_half_write: cross priv_mode_m, mseccfg_pmm, misalign_write_instr_half, misaligned_half ;
    cp_pm_misaligned_half_read: cross priv_mode_m, mseccfg_pmm, misalign_read_instr_half, misaligned_half ;
    cp_pm_misaligned_word_write: cross priv_mode_m, mseccfg_pmm, misalign_write_instr_word,  misaligned_word ;
    cp_pm_misaligned_word_read: cross priv_mode_m, mseccfg_pmm, misalign_read_instr_word,  misaligned_word ;
    cp_pm_misaligned_double_write: cross priv_mode_m, mseccfg_pmm, misalign_write_instr_double, misaligned_double ;
    cp_pm_misaligned_double_read: cross priv_mode_m, mseccfg_pmm, misalign_read_instr_double, misaligned_double ;
    cp_pm_csr_software_access_write: cross priv_mode_m, mseccfg_pmm, csr_write_op, csr_software_target;
    cp_pm_csr_software_access_read: cross priv_mode_m, mseccfg_pmm,  csr_read_op, csr_software_target;
    cp_hardware_csr_writes_read:  cross priv_mode_m, mseccfg_pmm, read_instr,  mtval_written;
    cp_hardware_csr_writes_write: cross priv_mode_m, mseccfg_pmm, write_instr, mtval_written;
    cp_pm_mprv_read:  cross priv_mode_m, mseccfg_pmm, mprv_bit, mpp_field, read_instr,  satp_mode;
    cp_pm_mprv_write: cross priv_mode_m, mseccfg_pmm, mprv_bit, mpp_field, write_instr, satp_mode;

endgroup

function void smmpm_sample(int hart, int issue, ins_t ins);
Smmpm_cg.sample(ins);
endfunction
