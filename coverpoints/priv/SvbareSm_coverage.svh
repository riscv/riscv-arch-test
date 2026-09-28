///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Written: Umer Shahid umer@riscv.org September 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVBARESM

covergroup SvbareSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    mprv_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mprv")[0] {
        bins set = {1};
    }
    mpp_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] {
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

    satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
        bins bare = {'0};
    }


    cp_satp_bare_mprv_load:  cross satp_bare, mprv_mstatus, mpp_mstatus, read_acc, priv_mode_m;
    cp_satp_bare_mprv_store: cross satp_bare, mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m;
    cp_satp_bare_mprv_exec:  cross satp_bare, mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m;

endgroup


function void svbaresm_sample(int hart, int issue, ins_t ins);
    SvbareSm_cg.sample(ins);
endfunction
