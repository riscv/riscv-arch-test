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

`define COVER_EXCEPTIONSZALRSC
covergroup ExceptionsZalrsc_exceptions_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    lr: coverpoint ins.current.insn {
        wildcard bins lr_w = {32'b00010_??_00000_?????_010_?????_0101111};
        `ifdef XLEN64
            wildcard bins lr_d = {32'b00010_??_00000_?????_011_?????_0101111};
        `endif
    }
    sc: coverpoint ins.current.insn {
        wildcard bins sc_w = {32'b00011_??_?????_?????_010_?????_0101111};
        `ifdef XLEN64
            wildcard bins sc_d = {32'b00011_??_?????_?????_011_?????_0101111};
        `endif
    }
    lr_w: coverpoint ins.current.insn {
    wildcard bins lr_w = {32'b00010_??_00000_?????_010_?????_0101111};
    }
    sc_w: coverpoint ins.current.insn {
        wildcard bins sc_w = {32'b00011_??_?????_?????_010_?????_0101111};
    }
    `ifdef XLEN64
        lr_d: coverpoint ins.current.insn {
            wildcard bins lr_d = {32'b00010_??_00000_?????_011_?????_0101111};
        }
        sc_d: coverpoint ins.current.insn {
                wildcard bins sc_d = {32'b00011_??_?????_?????_011_?????_0101111};
        }
        adr_LSBs_illegal_d: coverpoint ins.current.rs1_val[2:0]  {
        ignore_bins zero = {0};
        }
        adr_LSBs_legal_d: coverpoint ins.current.rs1_val[2:0]  {
            bins zero = {0};
        }
    `endif

    illegal_address: coverpoint ins.current.rs1_val {
        bins illegal = {`ACCESS_FAULT_ADDRESS};
    }
    illegal_address_misaligned: coverpoint ins.current.rs1_val {
        bins illegal = {`ACCESS_FAULT_ADDRESS + 1};
    }
    adr_LSBs: coverpoint ins.current.rs1_val[2:0]  {
        // auto fills 000 through 111
    }
    adr_LSBs_illegal_w: coverpoint ins.current.rs1_val[2:0]  {
        ignore_bins zero = {0};
        ignore_bins four = {3'b100};
    }
    adr_LSBs_legal_w: coverpoint ins.current.rs1_val[2:0]  {
        bins zero = {0};
        bins four = {3'b100};
    }
    rd_gt_one_prev: coverpoint ins.prev.rd_val {
        bins nonzero = {[2:$]};
    }
    rd_gt_one_cur: coverpoint ins.current.rd_val {
        bins nonzero = {[2:$]};
    }
    rd_zero_cur: coverpoint ins.current.rd_val {
        bins zero = {0};
    }

    // Ideally this coverpoint would check the rs1 of the paired lr.x and sc.x
    // to match the test plan. With our current toolflow
    // Testing that the rs1 value of the previous lr.x matches the rs1 of the sc.x
    // is not possible.
    // As a proxy we can check that the rd value changes as expected for rd when an
    // sc.x instruction is executed. Load rd with a value > 1.
    // Faulting instructions should not modify the rd value while
    // Successful instructions should write 0 to rd.
    // sc.w and sc.d have a different set of legal LSB offset
    // (4 byte aligned vs ) so they are handled differently in the coverpoints.

    // main coverpoints
    cp_load_address_misaligned:                cross lr, adr_LSBs;
    cp_load_access_fault:                      cross lr, illegal_address;
    cp_load_misaligned_priority:               cross lr, illegal_address_misaligned;
    cp_store_address_misaligned_legal_w:       cross sc_w, adr_LSBs_legal_w,rd_gt_one_prev, rd_zero_cur;
    cp_store_address_misaligned_illegal_w:     cross sc_w, adr_LSBs_illegal_w, rd_gt_one_prev, rd_gt_one_cur;
    `ifdef XLEN64
        cp_store_address_misaligned_legal_d:     cross sc_d, adr_LSBs_legal_d,rd_gt_one_prev, rd_zero_cur;
        cp_store_address_misaligned_illegal_d:   cross sc_d, adr_LSBs_illegal_d, rd_gt_one_prev, rd_gt_one_cur;
    `endif
    cp_store_access_fault:         cross sc, illegal_address, rd_gt_one_prev, rd_gt_one_cur;
    cp_store_misaligned_priority:  cross sc, illegal_address_misaligned, rd_gt_one_prev, rd_gt_one_cur;


endgroup

function void exceptionszalrsc_sample(int hart, int issue, ins_t ins);
    ExceptionsZalrsc_exceptions_cg.sample(ins);
    //  $display("adr_LSBs: %b, op[6:0]: %b, rd_boolean: %b",
    //   ins.current.rs1_val[2:0],
    //   ins.current.insn[6:0],
    //   ins.current.rd_val);
endfunction
