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


`define COVER_SSNPM
covergroup Ssnpm_cg with function sample(ins_t ins);
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

    mode_satp_pa: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
        bins bare = {4'b0000};
    }

    mode_satp_va: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
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

    senvcfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "pmm") {
        bins enabled_10  = {2'b10};
        bins enabled_11  = {2'b11};
    }

    `ifdef ZAAMO_SUPPORTED
    amo_op: coverpoint ins.current.insn {
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

    cp_pmlen_masking_write: cross priv_mode_u, senvcfg_pmm, mode_satp,  write_instr;
    cp_pmlen_masking_read: cross priv_mode_u, senvcfg_pmm, mode_satp, read_instr;
    `ifdef ZAAMO_SUPPORTED
    cp_effective_address_explicit_write: cross priv_mode_u, senvcfg_pmm,mode_satp, amo_op ;
    `endif
    cp_effective_address_fetch: cross priv_mode_u, senvcfg_pmm,mode_satp_pa, exec_op ;
    cp_virtual_address_sign_extension_write: cross priv_mode_u, senvcfg_pmm, mode_satp_va, write_instr ;
    cp_virtual_address_sign_extension_read: cross priv_mode_u, senvcfg_pmm, mode_satp_va, read_instr ;
    cp_physical_address_zero_extension_write: cross priv_mode_u, senvcfg_pmm, mode_satp_pa ,  write_instr;
    cp_physical_address_zero_extension_read: cross priv_mode_u, senvcfg_pmm, mode_satp_pa , read_instr;
    cp_mask_priv_mode_only_write: cross priv_mode_u, senvcfg_pmm, mode_satp,   write_instr;
    cp_mask_priv_mode_only_read: cross priv_mode_u, senvcfg_pmm, mode_satp,  read_instr ;
    cp_pm_mxr_disable_write: cross priv_mode_u, senvcfg_pmm, mxr_bit, mode_satp_va,  write_instr ;
    cp_pm_mxr_disable_read: cross priv_mode_u, senvcfg_pmm, mxr_bit, mode_satp_va, read_instr ;
    cp_pm_misaligned_half_write: cross priv_mode_u, senvcfg_pmm, mode_satp, misalign_write_instr_half, misaligned_half ;
    cp_pm_misaligned_half_read: cross priv_mode_u, senvcfg_pmm, mode_satp,  misalign_read_instr_half, misaligned_half ;
    cp_pm_misaligned_word_write: cross priv_mode_u, senvcfg_pmm,mode_satp,  misalign_write_instr_word,  misaligned_word ;
    cp_pm_misaligned_word_read: cross priv_mode_u, senvcfg_pmm,mode_satp, misalign_read_instr_word,  misaligned_word ;
    cp_pm_misaligned_double_write: cross priv_mode_u, senvcfg_pmm, mode_satp, misalign_write_instr_double, misaligned_double ;
    cp_pm_misaligned_double_read: cross priv_mode_u, senvcfg_pmm, mode_satp, misalign_read_instr_double, misaligned_double ;

endgroup

function void ssnpm_sample(int hart, int issue, ins_t ins);
Ssnpm_cg.sample(ins);
endfunction
