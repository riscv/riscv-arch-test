///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:
//
// Copyright (C)`
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_Ssnpm
covergroup Ssnpm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    read_instr: coverpoint ins.current.insn {
        wildcard bins lb = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins lh = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw = {LW};
        `ifdef XLEN64
          wildcard bins lwu = {LWU};
          wildcard bins ld = {LD};
        `endif
    }

    write_instr: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef XLEN64
          wildcard bins sd = {SD};
        `endif
    }

    misalign_instr_half: coverpoint ins.current.insn {
    wildcard bins lh  = {LH};
    wildcard bins lhu = {LHU};
    wildcard bins sh = {SH};
    }

    misalign_instr_word: coverpoint ins.current.insn {
    wildcard bins lw = {LW};
    wildcard bins sw = {SW};
    `ifdef XLEN64
    wildcard bins lwu = {LWU};
    `endif
    }

    `ifdef XLEN64
    misalign_instr_double: coverpoint ins.current.insn {
    wildcard bins ld = {LD};
    wildcard bins sd = {SD};
    }
    `endif


    misaligned_half: coverpoint (ins.current.rs1_val + ins.current.imm)[0]
    iff (ins.current.insn inside {LH, LHU, SH}) {
        bins aligned    = {1'b0};
        bins misaligned = {1'b1};
    }

    misaligned_word: coverpoint (ins.current.rs1_val + ins.current.imm)[1:0]
    iff (ins.current.insn inside {LW,
    `ifdef XLEN64
            LWU,
    `endif
            SW}) {
        bins aligned    = {2'b00};
        bins misaligned = {[2'b01:2'b11]};
    }

    `ifdef XLEN64
    misaligned_double: coverpoint (ins.current.rs1_val + ins.current.imm)[2:0]
    iff (ins.current.insn inside {LD, SD}) {
        bins aligned    = {3'b000};
        bins misaligned = {[3'b001:3'b111]};
    }
    `endif

    senvcfg_pmm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "senvcfg", "pmm") {
        bins enabled_10  = {2'b10};
        bins enabled_11  = {2'b11};
    }

    mode_satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
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



    //cp_address_variant: coverpoint ins.current.address_variant {  // Custom field: 0 for base A, 1 for A_masked (differs only in upper PMLEN bits); testbench must set
    //    bins base = {0};
    //    bins masked = {1};
   // }  // Bins: 2 address variants // IMP NOTE : Do I need this bin? if so how ?

    amo_op: coverpoint ins.current.insn
    iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "A") == 1'b1) {
        wildcard bins amoadd  = {AMOADD_W};
        wildcard bins amoswap = {AMOSWAP_W};
        wildcard bins amoxor  = {AMOXOR_W};
       `ifdef XLEN64
        wildcard bins amoadd_d  = {AMOADD_D};
        wildcard bins amoswap_d = {AMOSWAP_D};
        wildcard bins amoxor_d  = {AMOXOR_D};
        `endif
    }

    exec_op: coverpoint ins.current.insn {
        wildcard bins jal = {JAL};
        wildcard bins jalr = {JALR};
    }

    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        bins enabled  = {1'b1};
    }

   csrops: coverpoint ins.current.insn {
        wildcard bins csrrs  = {CSRRS};
        wildcard bins csrrc  = {CSRRC};
        wildcard bins csrrsi = {CSRRSI};
        wildcard bins csrrci = {CSRRCI};
    }

   uxlen: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "uxl")
   iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "mxl") == 2'b10)
    {
        bins xlen_32 = {2'b01};
        bins xlen_64 = {2'b10};
    }

    cp_pmlen_masking: cross priv_mode_u, senvcfg_pmm, mode_satp_bare, mode_satp_va, read_instr, write_instr;
    cp_effective_address_explicit: cross priv_mode_u, senvcfg_pmm,mode_satp_bare, mode_satp_va, read_instr, write_instr, amo_op ;
    cp_effective_address_fetch: cross priv_mode_u, senvcfg_pmm,mode_satp_bare, exec_op ;
    cp_virtual_address_sign_extension: cross priv_mode_u, senvcfg_pmm, mode_satp_va, read_instr, write_instr ;
    cp_physical_address_zero_extension: cross priv_mode_u, senvcfg_pmm, mode_satp_bare , read_instr, write_instr;
    cp_supported_pmlen_values_cross: cross priv_mode_u, senvcfg_pmm,mode_satp_bare, mode_satp_va, read_instr, write_instr ;
    cp_mask_priv_mode_only_cross: cross priv_mode_u, senvcfg_pmm, mode_satp_bare, mode_satp_va, read_instr, write_instr;
    cp_pm_mxr_disable_cross: cross priv_mode_u, senvcfg_pmm, mxr_bit, mode_satp_va, read_instr, write_instr ;
    cp_pm_misaligned_half_cross: cross priv_mode_u, senvcfg_pmm, mode_satp_bare, mode_satp_va,  misalign_instr_half, misaligned_half ;
    cp_pm_misaligned_word_cross: cross priv_mode_u, senvcfg_pmm,mode_satp_bare, mode_satp_va, misalign_instr_word, misaligned_word ;
    cp_pm_misaligned_double_cross: cross priv_mode_u, senvcfg_pmm, mode_satp_bare, mode_satp_va, misalign_instr_double, misaligned_double ;
    cp_pm_rv64_only_cross: cross priv_mode_u, senvcfg_pmm, mode_satp_bare, mode_satp_va, read_instr, write_instr;
    cp_pm_effective_xlen_constraint_cross: cross priv_mode_u, senvcfg_pmm,  mode_satp_bare, mode_satp_va, uxlen, read_instr, write_instr;



    endgroup

    function void Ssnpm_sample(int hart, int issue, ins_t ins);
    Ssnpm_cg.sample(ins);
endfunction
