///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Aman Murad aman.murad@10xengineers.ai 24 August 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSZICBOSM
covergroup ExceptionsZicboSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    `ifdef ZICBOM_SUPPORTED
        cbo_inval: coverpoint ins.current.insn {
            wildcard bins cbo_inval = {CBO_INVAL};
        }
        cbo_flushclean: coverpoint ins.current.insn {
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_clean = {CBO_CLEAN};
        }

        // menvcfg does not exist before Sm1.12.0
        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            `ifdef U_SUPPORTED
                menvcfg_cbie: coverpoint ins.current.csr[CSR_MENVCFG][5:4] {
                    ignore_bins reserved = {2'b10};
                }
                menvcfg_cbcfe: coverpoint ins.current.csr[CSR_MENVCFG][6] {
                }
            `endif
        `endif
    `endif

    `ifdef ZICBOZ_SUPPORTED
        cbo_zero: coverpoint ins.current.insn {
            wildcard bins cbo_zero = {CBO_ZERO};
        }

        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            `ifdef U_SUPPORTED
                menvcfg_cbze: coverpoint ins.current.csr[CSR_MENVCFG][7] {
                }
            `endif
        `endif
    `endif

    adr_misaligned: coverpoint ins.current.rs1_val[0]  {
    }

    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        `ifdef U_SUPPORTED
            menvcfg_all_enable: coverpoint ins.current.csr[CSR_MENVCFG][7:4] {
                bins ones = {4'b1111};
            }
        `endif
    `endif
`
    cbo_instrs: coverpoint ins.current.insn {
        `ifdef ZICBOM_SUPPORTED
            wildcard bins inval  = {CBO_INVAL};
            wildcard bins clean  = {CBO_CLEAN};
            wildcard bins flush  = {CBO_FLUSH};
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins zero   = {CBO_ZERO};
        `endif
        wildcard bins prefetch_i = {PREFETCH_I};
        wildcard bins prefetch_w = {PREFETCH_W};
        wildcard bins prefetch_r = {PREFETCH_R};
    }

    // main coverpoints
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        `ifdef U_SUPPORTED
            `ifdef ZICBOM_SUPPORTED
                cp_cbie: cross cbo_inval, menvcfg_cbie, priv_mode_m;
                cp_cbcfe: cross cbo_flushclean, menvcfg_cbcfe, priv_mode_m;
            `endif
            `ifdef ZICBOZ_SUPPORTED
                cp_cbze: cross cbo_zero, menvcfg_cbze, priv_mode_m;
            `endif
            cp_cbo_address_misaligned: cross cbo_instrs, adr_misaligned, priv_mode_m, menvcfg_all_enable;
        `else
            cp_cbo_address_misaligned: cross cbo_instrs, adr_misaligned, priv_mode_m;
        `endif
    `else
        cp_cbo_address_misaligned:  cross cbo_instrs, adr_misaligned, priv_mode_m;
    `endif

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        illegal_address: coverpoint {ins.current.rs1_val[XLEN-1:1], 1'b0} {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }

        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            `ifdef U_SUPPORTED
                cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_m, menvcfg_all_enable;
            `else
                cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_m;
`            `endif
        `else
            cp_cbo_access_fault: cross cbo_instrs, illegal_address, adr_misaligned, priv_mode_m;
        `endif
    `endif
endgroup

function void exceptionszicbosm_sample(int hart, int issue, ins_t ins);
    ExceptionsZicboSm_cg.sample(ins);
endfunction
