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

`define COVER_SVSM

covergroup SvSm_satp_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    tvm_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tvm")[0]{
        bins zero = {0};
        bins set  = {1};
    }

    // satp is always accessible from M-mode, so an access here never raises an exception.
    Mcause: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins no_exception = {0};
    }

    cp_ins: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrw = {CSRRW};
        wildcard bins csrrc = {CSRRC};
    }
    satp_csr: coverpoint ins.current.insn[31:20] {
        bins satp = {CSR_SATP};
    }

    cp_access_m: cross priv_mode_m, cp_ins, satp_csr, Mcause, tvm_mstatus; //sat.1
endgroup

covergroup SvSm_mstatus_mprv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    tvm_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tvm")[0] {
        bins set = {1};
    }
    Mcause: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins illegal_ins = {2};
    }
    cp_ins: coverpoint ins.current.insn {
        wildcard bins csrrs  = {CSRRS} iff (ins.current.insn[31:20] == CSR_SATP);
        wildcard bins csrrw  = {CSRRW} iff (ins.current.insn[31:20] == CSR_SATP);
        wildcard bins csrrc  = {CSRRC} iff (ins.current.insn[31:20] == CSR_SATP);
        wildcard bins sfence = {SFENCE_VMA};
    }

    cp_tvm_exception_s: cross tvm_mstatus, priv_mode_s, Mcause, cp_ins; //ms.1

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

    `ifdef UDB_MXLEN_64
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
            `ifdef SV57_SUPPORTED
                bins sv57 = {4'b1010};
            `endif
            `ifdef SV48_SUPPORTED
                bins sv48 = {4'b1001};
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39 = {4'b1000};
            `endif
        }
    `else
        satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins sv32 = {1'b1};
        }
    `endif

    cp_mprv_load:  cross mprv_mstatus, mpp_mstatus, read_acc,  priv_mode_m, satp_mode; //ms.2
    cp_mprv_store: cross mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m, satp_mode; //ms.2
    cp_mprv_ins:   cross mprv_mstatus, mpp_mstatus, exec_acc,  priv_mode_m, satp_mode; //ms.2

    PTE_upage_i: coverpoint ins.current.pte_i[7:0] { //ms.3 & 4
        wildcard bins leaflvl_u = {8'b11?11111};
    }
    PTE_upage_d: coverpoint ins.current.pte_d[7:0] { //ms.3 & 4
        wildcard bins leaflvl_u = {8'b11?11111};
    }

    `ifdef UDB_MXLEN_64
        PageType_i: coverpoint ins.current.page_type_i {
            `ifdef SV48_SUPPORTED
                bins sv48_tera = {2'b11} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
            `endif
        }
        PageType_d: coverpoint ins.current.page_type_d {
            `ifdef SV48_SUPPORTED
                bins sv48_tera = {2'b11} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
            `endif
        }
    `else
        PageType_i: coverpoint ins.current.page_type_i {
            bins sv32_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
            bins sv32_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
        }
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
            bins sv32_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
        }
    `endif

    load_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins load_page_fault = {13};
    }
    store_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins store_amo_page_fault = {15};
    }
    sum_sstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "sum")[0] {
        bins notset = {0};
        bins set = {1};
    }

    cp_mprv_upage_smode_sumunset_noread: cross mprv_mstatus, mpp_mstatus, read_acc, priv_mode_m, PTE_upage_d, PageType_d, load_page_fault, sum_sstatus { //ms.3
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig5 = binsof(sum_sstatus.set);
    }
    cp_mprv_upage_smode_sumunset_nowrite: cross mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m, PTE_upage_d, PageType_d, store_page_fault, sum_sstatus { //ms.3
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig5 = binsof(sum_sstatus.set);
    }
    cp_mprv_upage_smode_sumunset_noexec: cross mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m, PageType_i, sum_sstatus { //ms.3
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.set);
    }
    cp_mprv_upage_smode_sumset_exec: cross mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m, PageType_i, sum_sstatus  { //ms.4
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.notset);
    }
    cp_mprv_upage_smode_sumset_read: cross mprv_mstatus, mpp_mstatus, read_acc, priv_mode_m, PTE_upage_d, PageType_d, sum_sstatus { //ms.4
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.notset);
    }
    cp_mprv_upage_smode_sumset_write: cross mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m, PTE_upage_d, PageType_d, sum_sstatus { //ms.4
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.notset);
    }

    PTE_sbe_d: coverpoint ins.current.pte_d[7:0] { //ms.5
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    `ifdef UDB_MXLEN_64
        sbe_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "sbe")[0] { //ms.5
            bins set = {1};
            bins not_set = {0};
        }
    `else
        sbe_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "sbe")[0] { //ms.5
            bins set = {1};
            bins not_set = {0};
        }
    `endif

    cp_mstatus_sbe_read: cross read_acc, PTE_sbe_d, PageType_d, sbe_mstatus; //ms.5
    cp_mstatus_sbe_write: cross write_acc, PTE_sbe_d, PageType_d, sbe_mstatus; //ms.5

endgroup

function void svsm_sample(int hart, int issue, ins_t ins);
    SvSm_satp_cg.sample(ins);
    SvSm_mstatus_mprv_cg.sample(ins);
endfunction
