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

    read_acc: coverpoint ins.current.read_access {
        bins set = {1};
    }
    write_acc: coverpoint ins.current.write_access {
        bins set = {1};
    }
    exec_acc: coverpoint ins.current.execute_access {
        bins set = {1};
    }

    `ifdef UDB_MXLEN_64
        satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
            bins bare = {4'b0000};
        }
    `else
        satp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins bare = {1'b0};
        }
    `endif


    cp_satp_bare_load:       cross satp_bare, read_acc, priv_mode_s_u;
    cp_satp_bare_store:      cross satp_bare, write_acc, priv_mode_s_u;
    cp_satp_bare_exec:       cross satp_bare, exec_acc, priv_mode_s_u;

endgroup

`ifndef EXCLUDE_SM
covergroup Svbare_Sm_cg with function sample(ins_t ins);
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
`endif


function void svbare_sample(int hart, int issue, ins_t ins);
    `ifndef EXCLUDE_SM
        Svbare_Sm_cg.sample(ins);
    `endif
    Svbare_cg.sample(ins);
endfunction
