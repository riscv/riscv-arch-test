///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVBARE

covergroup Svbare_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    mprv_mstatus: coverpoint ins.current.csr[12'h300][17] {
        bins set = {1};
    }
    mpp_mstatus: coverpoint ins.prev.csr[12'h300][12:11] {
        bins U_mode = {2'b00};
        bins S_mode = {2'b01};
    }
    read_acc: coverpoint ins.current.read_access {
        bins set = {1};
    }
    write_acc: coverpoint ins.current.write_access {
        bins set = {1};
    }
    exec_acc: coverpoint ins.current.execute_access {
        bins set = {1};
    }

    `ifdef XLEN64
        satp_bare: coverpoint ins.current.csr[12'h180][63:60] {
            bins bare = {4'b0000};
        }
    `else
        satp_bare: coverpoint ins.current.csr[12'h180][31] {
            bins bare = {1'b0};
        }
    `endif


    cp_satp_bare_mprv_load:  cross satp_bare, mprv_mstatus, mpp_mstatus, read_acc, priv_mode_m;
    cp_satp_bare_mprv_store: cross satp_bare, mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m;
    cp_satp_bare_mprv_exec:  cross satp_bare, mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m;
    cp_satp_bare_load:       cross satp_bare, read_acc, priv_mode_s_u;
    cp_satp_bare_store:      cross satp_bare, write_acc, priv_mode_s_u;
    cp_satp_bare_exec:       cross satp_bare, exec_acc, priv_mode_s_u;

endgroup


function void svbare_sample(int hart, int issue, ins_t ins);
    Svbare_cg.sample(ins);
endfunction
