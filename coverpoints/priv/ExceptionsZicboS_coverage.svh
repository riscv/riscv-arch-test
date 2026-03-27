///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 29 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSZICBOS
covergroup ExceptionsZicboS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    `ifdef ZICBOM_SUPPORTED
        cbo_inval: coverpoint ins.current.insn {
            wildcard bins cbo_inval = {32'b000000000000_?????_010_00000_0001111};
        }
        cbo_flushclean: coverpoint ins.current.insn {
            wildcard bins cbo_flush = {32'b000000000010_?????_010_00000_0001111};
            wildcard bins cbo_clean = {32'b000000000001_?????_010_00000_0001111};
        }
        menvcfg_cbie: coverpoint ins.current.csr[12'h30A][5:4] {
            ignore_bins reserved = {2'b10};
        }
        menvcfg_cbcfe: coverpoint ins.current.csr[12'h30A][6] {
        }
        senvcfg_cbie: coverpoint ins.current.csr[12'h10A][5:4] {
            ignore_bins reserved = {2'b10};
        }
        senvcfg_cbcfe: coverpoint ins.current.csr[12'h10A][6] {
        }
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cbo_zero: coverpoint ins.current.insn {
            wildcard bins cbo_zero = {32'b000000000100_?????_010_00000_0001111};
        }
        menvcfg_cbze: coverpoint ins.current.csr[12'h30A][7] {
        }
        senvcfg_cbze: coverpoint ins.current.csr[12'h10A][7] {
        }
    `endif

    illegal_address: coverpoint ins.current.rs1_val {
        bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }
    adr_misaligned: coverpoint ins.current.rs1_val[0]  {
        bins misaligned = {1};
    }
    menvcfg_all_enable: coverpoint ins.current.csr[12'h30A][7:4] {
        bins ones = {4'b1111};
    }
    senvcfg_all_enable: coverpoint ins.current.csr[12'h10A][7:4] {
        bins ones = {4'b1111};
    }
    cbo_instrs: coverpoint ins.current.insn {
        `ifdef ZICBOM_SUPPORTED
            wildcard bins inval = {32'b000000000000_?????_010_00000_0001111};
            wildcard bins clean  = {32'b000000000001_?????_010_00000_0001111};
            wildcard bins flush  = {32'b000000000010_?????_010_00000_0001111};
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins zero   = {32'b000000000100_?????_010_00000_0001111};
        `endif
        wildcard bins prefetch_i  = {32'b???????_00000_?????_110_00000_0010011};
        wildcard bins prefetch_w  = {32'b???????_00001_?????_110_00000_0010011};
        wildcard bins prefetch_r  = {32'b???????_00011_?????_110_00000_0010011};
    }

    // main coverpoints
    `ifdef ZICBOM_SUPPORTED
        cp_cbie:                    cross cbo_inval,      menvcfg_cbie,  senvcfg_cbie,  priv_mode_m_s_u;
        cp_cbcfe:                   cross cbo_flushclean, menvcfg_cbcfe, senvcfg_cbcfe, priv_mode_m_s_u;
    `endif
    `ifdef ZICBOZ_SUPPORTED
        cp_cbze:                    cross cbo_zero,       menvcfg_cbze,  senvcfg_cbze,  priv_mode_m_s_u;
    `endif
    cp_cbo_access_fault:        cross cbo_instrs,     illegal_address, priv_mode_m_s_u, menvcfg_all_enable, senvcfg_all_enable;
    cp_cbo_address_misaligned:  cross cbo_instrs,     adr_misaligned, priv_mode_m_s_u, menvcfg_all_enable, senvcfg_all_enable;

endgroup

function void exceptionszicbos_sample(int hart, int issue, ins_t ins);
    ExceptionsZicboS_cg.sample(ins);
endfunction
