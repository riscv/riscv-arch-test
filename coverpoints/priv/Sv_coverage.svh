///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SV

`ifdef ZICBOM_SUPPORTED
    `define SV_ZICBO_ANY
`elsif ZICBOZ_SUPPORTED
    `define SV_ZICBO_ANY
`elsif ZICBOP_SUPPORTED
    `define SV_ZICBO_ANY
`endif

covergroup Sv_satp_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    `ifdef UDB_MXLEN_64
        satp_asid_PPN: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "satp")[59:0] {
            bins all_zero = {60'd0};
            bins not_zero = {[1:$]};
        }
    `else
        satp_asid_PPN: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "satp")[30:0] {
            bins all_zero = {31'd0};
            bins not_zero = {[1:$]};
        }
    `endif

    `ifdef UDB_MXLEN_64
        asid_length: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "asid")[15:0] { //sat.5
            bins values = {16'h0001, 16'h0002, 16'h0004, 16'h0008, 16'h0010, 16'h0020, 16'h0040, 16'h0080, 16'h0100, 16'h0200, 16'h0400, 16'h0800, 16'h1000, 16'h2000, 16'h0400, 16'h8000};
        }
    `else
        asid_length: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "asid")[8:0] {
            bins values = {9'h001, 9'h002, 9'h004, 9'h008, 9'h010, 9'h020, 9'h040, 9'h080, 9'h100};
        }
    `endif

    tvm_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tvm")[0]{
        bins zero = {0};
    }

    Scause: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins illegal_ins  = {ILLEGAL_INSTRUCTION};
        bins no_exception = {0};
    }

    cp_ins: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS} iff (ins.current.insn[31:20] == CSR_SATP);
        wildcard bins csrrw = {CSRRW} iff (ins.current.insn[31:20] == CSR_SATP);
        wildcard bins csrrc = {CSRRC} iff (ins.current.insn[31:20] == CSR_SATP);
    }

    cp_access_u: cross priv_mode_u, Scause, tvm_mstatus { //sat.1
        ignore_bins ig1 = binsof(Scause.no_exception);
    }
    cp_access_s: cross priv_mode_s, cp_ins, Scause, tvm_mstatus { //sat.1
        ignore_bins ig1 = binsof(Scause.illegal_ins);
    }
endgroup

covergroup Sv_VA_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `ifdef UDB_MXLEN_64
        VA_i: coverpoint ins.current.virt_adr_i {
            bins all_zeros = {64'd0};
            bins all_ones  = {64'hFFFFFFFF_FFFFFFFC};
        }
        VA_d: coverpoint ins.current.virt_adr_d {
            bins all_zeros = {64'd0};
            bins all_ones  = {64'hFFFFFFFF_FFFFFFFF};
        }
    `else
        VA_i: coverpoint ins.current.virt_adr_i {
            bins all_zeros = {32'd0};
            bins all_ones  = {32'hFFFFFFFC};
        }
        VA_d: coverpoint ins.current.virt_adr_d {
            bins all_zeros = {32'd0};
            bins all_ones  = {32'hFFFFFFFF};
        }
    `endif

    `ifdef UDB_MXLEN_64
        mode_supported: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
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
        mode_supported: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins sv32 = {1'b1};
        }
    `endif

    cp_VA_i_mode: cross mode_supported, VA_i;
    cp_VA_d_mode: cross mode_supported, VA_d;

endgroup

covergroup Sv_sfence_cg with function sample(ins_t ins); //sf.1
    option.per_instance = 0;
    cp_ins: coverpoint ins.current.insn {
        wildcard bins sfence = {SFENCE_VMA};
    }
endgroup

covergroup Sv_vm_permissions_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    //pte permission for leaf PTEs
    PTE_i_inv: coverpoint ins.current.pte_i[7:0] { //pte.2
        wildcard bins leaflvl_u = {8'b11?11??0};
        wildcard bins leaflvl_s = {8'b11?01??0};
    }
    PTE_d_inv: coverpoint ins.current.pte_d[7:0] { //pte.2
        wildcard bins leaflvl_u_r = {8'b11?1??10};
        wildcard bins leaflvl_u_w = {8'b11?1?110};
        wildcard bins leaflvl_s_r = {8'b11?0??10};
        wildcard bins leaflvl_s_w = {8'b11?0?110};
    }

    PTE_i_res_rwx: coverpoint ins.current.pte_i[7:0] { //pte.3
        wildcard bins leaflvl_exec_u   = {8'b11?11101};
        wildcard bins leaflvl_noexec_u = {8'b11?10101};
        wildcard bins leaflvl_exec_s   = {8'b11?01101};
        wildcard bins leaflvl_noexec_s = {8'b11?00101};
    }
    PTE_d_res_rwx: coverpoint ins.current.pte_d[7:0] { //pte.3
        wildcard bins leaflvl_exec_u   = {8'b11?11101};
        wildcard bins leaflvl_noexec_u = {8'b11?10101};
        wildcard bins leaflvl_exec_s   = {8'b11?01101};
        wildcard bins leaflvl_noexec_s = {8'b11?00101};
    }

    PTE_nonleaf_lvl0_i: coverpoint ins.current.pte_i[7:0] { //pte.4
        wildcard bins lvl0_s = {8'b???00001};
        wildcard bins lvl0_u = {8'b???10001};
    }
    PTE_nonleaf_lvl0_d: coverpoint ins.current.pte_d[7:0] { //pte.4
        wildcard bins lvl0_s = {8'b???00001};
        wildcard bins lvl0_u = {8'b???10001};
    }

    PTE_x_spage_i: coverpoint ins.current.pte_i[7:0] { //pte.5 & 6
        wildcard bins leaflvl_x_0 = {8'b11?00??1};
        wildcard bins leaflvl_x_1 = {8'b11?01??1};
    }
    PTE_rw_spage_d: coverpoint ins.current.pte_d[7:0] { //pte.5 & 6
        wildcard bins leaflvl_w_0 = {8'b11?0?0?1};
        wildcard bins leaflvl_w_1 = {8'b11?0?111};
        wildcard bins leaflvl_r_0 = {8'b11?0??01};
        wildcard bins leaflvl_r_1 = {8'b11?0??11};
    }

    PTE_spage_i: coverpoint ins.current.pte_i[7:0] { //pte.7
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_spage_d: coverpoint ins.current.pte_d[7:0] { //pte.7
        wildcard bins leaflvl_s = {8'b11?01111};
    }

    PTE_upage_i: coverpoint ins.current.pte_i[7:0] { //pte.8 & 9
        wildcard bins leaflvl_u = {8'b11?11111};
    }
    PTE_upage_d: coverpoint ins.current.pte_d[7:0] { //pte.8 & 9
        wildcard bins leaflvl_u = {8'b11?11111};
    }

    PTE_x_upage_i: coverpoint ins.current.pte_i[7:0] { //pte.10
        wildcard bins leaflvl_x_0 = {8'b11?10??1};
        wildcard bins leaflvl_x_1 = {8'b11?11??1};
    }
    PTE_rw_upage_d: coverpoint ins.current.pte_d[7:0] { //pte.10
        wildcard bins leaflvl_w_0 = {8'b11?1?0?1};
        wildcard bins leaflvl_w_1 = {8'b11?1?111};
        wildcard bins leaflvl_r_0 = {8'b11?1??01};
        wildcard bins leaflvl_r_1 = {8'b11?1??11};
    }

    PTE_XnoRW_d: coverpoint ins.current.pte_d[7:0] { //pte.11 & 12
        wildcard bins leaflvl_u = {8'b11?11001};
        wildcard bins leaflvl_s = {8'b11?01001};
    }

    PTE_RWX_i: coverpoint ins.current.pte_i[7:0] { //pte.16
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_RWX_d: coverpoint ins.current.pte_d[7:0] { //pte.16
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }

    PTE_canonical_i: coverpoint ins.current.pte_i[7:0] { //va.1
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_canonical_d: coverpoint ins.current.pte_d[7:0] { //va.1
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }

    PTE_DAU_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins nonleaf_D_bit = {8'b10?00001};
        wildcard bins nonleaf_A_bit = {8'b01?00001};
        wildcard bins nonleaf_U_bit = {8'b00?10001};
    }
    PTE_DAU_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins nonleaf_D_bit = {8'b10?00001};
        wildcard bins nonleaf_A_bit = {8'b01?00001};
        wildcard bins nonleaf_U_bit = {8'b00?10001};
    }

    `ifdef UDB_MXLEN_64
        // Non-leaf PTEs with one of the reserved bits 63:54 set
        PTE_nonleaf_i: coverpoint ins.current.pte_i[7:0] {
            wildcard bins nonleaf = {8'b00?00001};
        }
        PTE_nonleaf_rsv_i: coverpoint ins.current.pte_i[63:54] {
            bins bit_54 = {10'h001};
            bins bit_55 = {10'h002};
            bins bit_56 = {10'h004};
            bins bit_57 = {10'h008};
            bins bit_58 = {10'h010};
            // With Svrsw60t59b, bits 60:59 are ignored and the access does not fault
            `ifndef SVRSW60T59B_SUPPORTED
                bins bit_59 = {10'h020};
                bins bit_60 = {10'h040};
            `endif
            bins bit_61 = {10'h080};
            bins bit_62 = {10'h100};
            bins bit_63 = {10'h200};
        }
        // A non-leaf PTE is never at level 0
        PTE_nonleaf_level_i: coverpoint ins.current.page_type_i {
            `ifdef SV48_SUPPORTED
                bins sv48_tera = {2'b11} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
            `endif
        }
        PTE_nonleaf_d: coverpoint ins.current.pte_d[7:0] {
            wildcard bins nonleaf = {8'b00?00001};
        }
        PTE_nonleaf_rsv_d: coverpoint ins.current.pte_d[63:54] {
            bins bit_54 = {10'h001};
            bins bit_55 = {10'h002};
            bins bit_56 = {10'h004};
            bins bit_57 = {10'h008};
            bins bit_58 = {10'h010};
            // With Svrsw60t59b, bits 60:59 are ignored and the access does not fault
            `ifndef SVRSW60T59B_SUPPORTED
                bins bit_59 = {10'h020};
                bins bit_60 = {10'h040};
            `endif
            bins bit_61 = {10'h080};
            bins bit_62 = {10'h100};
            bins bit_63 = {10'h200};
        }
        // A non-leaf PTE is never at level 0
        PTE_nonleaf_level_d: coverpoint ins.current.page_type_d {
            `ifdef SV48_SUPPORTED
                bins sv48_tera = {2'b11} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
                bins sv48_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001);
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga = {2'b10} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
                bins sv39_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000);
            `endif
        }
    `endif

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

    `ifdef UDB_MXLEN_64
        misaligned_PPN_i: coverpoint ins.current.page_type_i {
            `ifdef SV48_SUPPORTED
                bins sv48_tera_misaligned = {2'b11} iff ((ins.current.ppn_i[26:0] != 27'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
                bins sv48_giga_misaligned = {2'b10} iff ((ins.current.ppn_i[17:0] != 18'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
                bins sv48_mega_misaligned = {2'b01} iff ((ins.current.ppn_i[8:0]  !=  9'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga_misaligned = {2'b10} iff ((ins.current.ppn_i[17:0] != 18'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000));
                bins sv39_mega_misaligned = {2'b01} iff ((ins.current.ppn_i[8:0]  !=  9'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000));
            `endif
        }
        misaligned_PPN_d: coverpoint ins.current.page_type_d {
            `ifdef SV48_SUPPORTED
                bins sv48_tera_misaligned = {2'b11} iff ((ins.current.ppn_d[26:0] != 27'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
                bins sv48_giga_misaligned = {2'b10} iff ((ins.current.ppn_d[17:0] != 18'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
                bins sv48_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[8:0]  !=  9'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga_misaligned = {2'b10} iff ((ins.current.ppn_d[17:0] != 18'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000));
                bins sv39_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[8:0]  !=  9'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000));
            `endif
        }
    `else
        misaligned_PPN_i: coverpoint ins.current.page_type_i {
            bins sv32_mega_misaligned = {2'b01} iff ((ins.current.ppn_i[9:0] != 10'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1));
        }
        misaligned_PPN_d: coverpoint ins.current.page_type_d {
            bins sv32_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[9:0] != 10'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1));
        }
    `endif

    // satp.mode for coverage of SV32, SV39, SV48 & SV57
    `ifdef UDB_MXLEN_64
        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
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
        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins sv32 = {1'b1};
        }
    `endif

    //For crosses with Read, write and execute accesses and their corresponding faults
    exec_acc: coverpoint ins.current.execute_access {
        bins set = {1};
    }
    read_acc: coverpoint ins.current.read_access {
        bins set = {1};
    }
    write_acc: coverpoint ins.current.write_access{
        bins set = {1};
    }
    load_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins load_page_fault = {LOAD_PAGE_FAULT};
    }
    ins_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins ins_page_fault = {INSTRUCTION_PAGE_FAULT};
    }
    store_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
        bins store_amo_page_fault = {STORE_AMO_PAGE_FAULT};
    }
    Nopagefault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "stval", "stval"){
        bins no_fault  = {64'd0};
    }
    kilo_page_i: coverpoint ins.current.page_type_i {
        bins kilo_page = {2'b00};
    }
    kilo_page_d: coverpoint ins.current.page_type_d {
        bins kilo_page = {2'b00};
    }
    sum_sstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstatus", "sum")[0]{
        bins notset = {0};
        bins set = {1};
    }
    mxr_sstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstatus", "mxr")[0] {
        bins notset = {0};
        bins set = {1};
    }

    cp_PTE_inv_exec_s_i: cross PTE_i_inv, PageType_i, ins_page_fault, priv_mode_s, exec_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_i_inv.leaflvl_u);
    }
    cp_PTE_inv_exec_u_i: cross PTE_i_inv, PageType_i, ins_page_fault, priv_mode_u, exec_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_i_inv.leaflvl_s);
    }

    cp_PTE_inv_read_s_d: cross PTE_d_inv, PageType_d, load_page_fault, priv_mode_s, read_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_u_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_u_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_s_w);
    }
    cp_PTE_inv_read_u_d: cross PTE_d_inv, PageType_d, load_page_fault, priv_mode_u, read_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_s_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_s_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_u_w);
    }

    cp_PTE_inv_write_s_d: cross PTE_d_inv, PageType_d, store_page_fault, priv_mode_s, write_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_u_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_u_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_s_r);
    }
    cp_PTE_inv_write_u_d: cross PTE_d_inv, PageType_d, store_page_fault, priv_mode_u, write_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_s_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_s_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_u_r);
    }

    cp_PTE_res_rwx_s_i_exec: cross PTE_i_res_rwx, PageType_i, ins_page_fault, priv_mode_s, exec_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_i_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_i_res_rwx.leaflvl_noexec_u);
    }
    cp_PTE_res_rwx_u_i_exec: cross PTE_i_res_rwx, PageType_i, ins_page_fault, priv_mode_u, exec_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_i_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_i_res_rwx.leaflvl_noexec_s);
    }

    cp_PTE_res_rwx_s_d_read: cross PTE_d_res_rwx, PageType_d, load_page_fault, priv_mode_s, read_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_u);
    }
    cp_PTE_res_rwx_u_d_read: cross PTE_d_res_rwx, PageType_d, load_page_fault, priv_mode_u, read_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_s);
    }

    cp_PTE_res_rwx_s_d_write: cross PTE_d_res_rwx, PageType_d, store_page_fault, priv_mode_s, write_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_u);
    }
    cp_PTE_res_rwx_u_d_write: cross PTE_d_res_rwx, PageType_d, store_page_fault, priv_mode_u, write_acc  { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_s);
    }

    cp_PTE_nonleaf_lvl0_s_i_exec: cross PTE_nonleaf_lvl0_i, kilo_page_i, mode, ins_page_fault, priv_mode_s, exec_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_i.lvl0_u);
    }
    cp_PTE_nonleaf_lvl0_u_i_exec: cross PTE_nonleaf_lvl0_i, kilo_page_i, mode, ins_page_fault, priv_mode_u, exec_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_i.lvl0_s);
    }
    cp_PTE_nonleaf_lvl0_s_d_read: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, load_page_fault, priv_mode_s, read_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_u);
    }
    cp_PTE_nonleaf_lvl0_u_d_read: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, load_page_fault, priv_mode_u, read_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_s);
    }
    cp_PTE_nonleaf_lvl0_s_d_write: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, store_page_fault, priv_mode_s, write_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_u);
    }
    cp_PTE_nonleaf_lvl0_u_d_write: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, store_page_fault, priv_mode_u, write_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_s);
    }

    cp_spage_exec_s_i: cross PTE_x_spage_i, PageType_i, exec_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_x_spage_i.leaflvl_x_0);
    }
    cp_spage_noexec_s_i: cross PTE_x_spage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_x_spage_i.leaflvl_x_1);
    }

    cp_spage_read_s_d: cross PTE_rw_spage_d, PageType_d, read_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_w_1);
    }
    cp_spage_noread_s_d: cross PTE_rw_spage_d, PageType_d, load_page_fault, read_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_1);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_w_1);
    }

    cp_spage_write_s_d: cross PTE_rw_spage_d, PageType_d, write_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_r_1);
    }
    cp_spage_nowrite_s_d: cross PTE_rw_spage_d, PageType_d, store_page_fault, write_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_r_1);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_w_1);
    }

    cp_spage_rwx_s_i_noexec:  cross PTE_spage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_u; //pte.7
    cp_spage_rwx_s_d_noread:  cross PTE_spage_d, PageType_d, load_page_fault, read_acc, priv_mode_u; //pte.7
    cp_spage_rwx_s_d_nowrite: cross PTE_spage_d, PageType_d, store_page_fault, write_acc, priv_mode_u; //pte.7

    cp_upage_smode_sumunset_noexec_s: cross PTE_upage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_s, sum_sstatus { //pte.8
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }
    cp_upage_smode_sumunset_noread_s: cross PTE_upage_d, PageType_d, load_page_fault, read_acc, priv_mode_s, sum_sstatus { //pte.8
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }
    cp_upage_smode_sumunset_nowrite_s: cross PTE_upage_d, PageType_d, store_page_fault, write_acc, priv_mode_s, sum_sstatus { //pte.8
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }

    cp_upage_smode_sumset_noexec_s: cross PTE_upage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_s, sum_sstatus  { //pte.9
        ignore_bins ig1 = binsof(sum_sstatus.notset);
    }
    cp_upage_smode_sumset_read_s: cross PTE_upage_d, PageType_d, read_acc, priv_mode_s, sum_sstatus  { //pte.9
        ignore_bins ig1 = binsof(sum_sstatus.notset);
    }
    cp_upage_smode_sumset_write_s: cross PTE_upage_d, PageType_d, write_acc, priv_mode_s, sum_sstatus  { //pte.9
        ignore_bins ig1 = binsof(sum_sstatus.notset);
    }

    cp_upage_umode_exec_u: cross PTE_x_upage_i, PageType_i, exec_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_x_upage_i.leaflvl_x_0);
    }
    cp_upage_umode_noexec_u: cross PTE_x_upage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_x_upage_i.leaflvl_x_1);
    }

    cp_upage_umode_read_u: cross PTE_rw_upage_d, PageType_d, read_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_w_1);
    }
    cp_upage_umode_noread_u: cross PTE_rw_upage_d, PageType_d, load_page_fault, read_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_1);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_w_1);
    }

    cp_upage_umode_write_u: cross PTE_rw_upage_d, PageType_d, write_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_r_1);
    }
    cp_upage_umode_nowrite_u: cross PTE_rw_upage_d, PageType_d, store_page_fault, write_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_r_1);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_w_1);
    }

    cp_xpage_mxrunset_read_s: cross PTE_XnoRW_d, PageType_d, load_page_fault, read_acc, mxr_sstatus, priv_mode_s { //pte.11
        ignore_bins ig1 = binsof(mxr_sstatus.set);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_u);
    }
    cp_xpage_mxrunset_read_u: cross PTE_XnoRW_d, PageType_d, load_page_fault, read_acc, mxr_sstatus, priv_mode_u { //pte.11
        ignore_bins ig1 = binsof(mxr_sstatus.set);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_s);
    }

    cp_xpage_mxrset_read_s: cross PTE_XnoRW_d, PageType_d, mxr_sstatus, read_acc, priv_mode_s { //pte.12
        ignore_bins ig1 = binsof(mxr_sstatus.notset);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_u);
    }
    cp_xpage_mxrset_read_u: cross PTE_XnoRW_d, PageType_d, mxr_sstatus, read_acc, priv_mode_u { //pte.12
        ignore_bins ig1 = binsof(mxr_sstatus.notset);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_s);
    }

    cp_PTE_DAU_nleaf_read_s: cross PTE_DAU_d, PageType_d, load_page_fault, priv_mode_s {
        `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }
    cp_PTE_DAU_nleaf_read_u: cross PTE_DAU_d, PageType_d, load_page_fault, priv_mode_u {
        `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }

    cp_PTE_DAU_nleaf_write_s: cross PTE_DAU_d, PageType_d, store_page_fault, priv_mode_s {
        `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }
    cp_PTE_DAU_nleaf_write_u: cross PTE_DAU_d, PageType_d, store_page_fault, priv_mode_u {
        `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }

    cp_PTE_DAU_nleaf_exec_s: cross PTE_DAU_i, PageType_i, ins_page_fault, priv_mode_s {
        `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_i.sv48_kilo); `endif
        `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_i.sv32_kilo); `endif
    }
    cp_PTE_DAU_nleaf_exec_u: cross PTE_DAU_i, PageType_i, ins_page_fault, priv_mode_u {
        `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_i.sv48_kilo); `endif
        `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_i.sv32_kilo); `endif
    }

    `ifdef UDB_MXLEN_64
        cp_PTE_rsv_nleaf_read_s: cross PTE_nonleaf_d, PTE_nonleaf_rsv_d, PTE_nonleaf_level_d, load_page_fault, priv_mode_s;
        cp_PTE_rsv_nleaf_write_s: cross PTE_nonleaf_d, PTE_nonleaf_rsv_d, PTE_nonleaf_level_d, store_page_fault, priv_mode_s;
        cp_PTE_rsv_nleaf_exec_s: cross PTE_nonleaf_i, PTE_nonleaf_rsv_i, PTE_nonleaf_level_i, ins_page_fault, priv_mode_s;
    `endif

    cp_misaligned_exec_s: cross PTE_RWX_i, misaligned_PPN_i, ins_page_fault, exec_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_i.leaflvl_u);
    }
    cp_misaligned_exec_u: cross PTE_RWX_i, misaligned_PPN_i, ins_page_fault, exec_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_i.leaflvl_s);
    }

    cp_misaligned_read_s: cross PTE_RWX_d, misaligned_PPN_d, load_page_fault, read_acc { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
    }
    cp_misaligned_read_u: cross PTE_RWX_d, misaligned_PPN_d, load_page_fault, read_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
    }

    cp_misaligned_write_s: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, write_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
    }
    cp_misaligned_write_u: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, write_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
    }

    `ifdef UDB_MXLEN_64
        canonical_page_d: coverpoint ins.current.page_type_d {
            `ifdef SV48_SUPPORTED
                bins sv48_tera_canonical = {2'b11} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
                bins sv48_giga_canonical = {2'b10} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
                bins sv48_mega_canonical = {2'b01} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
                bins sv48_kilo_canonical = {2'b00} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga_canonical = {2'b10} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000) && (ins.current.virt_adr_d[63:39] != 0) && (ins.current.virt_adr_d[63:39] != '1));
                bins sv39_mega_canonical = {2'b01} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000) && (ins.current.virt_adr_d[63:39] != 0) && (ins.current.virt_adr_d[63:39] != '1));
                bins sv39_kilo_canonical = {2'b00} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000) && (ins.current.virt_adr_d[63:39] != 0) && (ins.current.virt_adr_d[63:39] != '1));
            `endif
        }
        canonical_page_i: coverpoint ins.current.page_type_i {
            `ifdef SV48_SUPPORTED
                bins sv48_tera_canonical = {2'b11} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
                bins sv48_giga_canonical = {2'b10} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
                bins sv48_mega_canonical = {2'b01} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
                bins sv48_kilo_canonical = {2'b00} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga_canonical = {2'b10} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000) && (ins.current.virt_adr_i[63:39] != 0) && (ins.current.virt_adr_i[63:39] != '1));
                bins sv39_mega_canonical = {2'b01} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000) && (ins.current.virt_adr_i[63:39] != 0) && (ins.current.virt_adr_i[63:39] != '1));
                bins sv39_kilo_canonical = {2'b00} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000) && (ins.current.virt_adr_i[63:39] != 0) && (ins.current.virt_adr_i[63:39] != '1));
            `endif
        }

        cp_canonical_read_s: cross PTE_canonical_d, canonical_page_d, load_page_fault, read_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_u);
        }
        cp_canonical_read_u: cross PTE_canonical_d, canonical_page_d, load_page_fault, read_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_s);
        }

        cp_canonical_write_s: cross PTE_canonical_d, canonical_page_d, store_page_fault, write_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_u);
        }
        cp_canonical_write_u: cross PTE_canonical_d, canonical_page_d, store_page_fault, write_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_s);
        }

        cp_canonical_exec_s: cross PTE_canonical_i, canonical_page_i, ins_page_fault, exec_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_i.leaflvl_u);
        }
        cp_canonical_exec_u: cross PTE_canonical_i, canonical_page_i, ins_page_fault, exec_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_i.leaflvl_s);
        }
    `endif
endgroup

covergroup Sv_res_global_pte_cg with function sample(ins_t ins);
    option.per_instance = 0;
    //pte.1
    RSW: coverpoint ins.current.pte_i[9:8] {
        bins all_comb[] = {[2'd0:2'd3]};
    }

    `ifdef UDB_MXLEN_64
        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
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
        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins sv32 = {1'b1};
        }
    `endif

    cp_rsw_pte: cross RSW, mode;

    //pte.13
    global_PTE_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins leaflvl_u = {8'b??111111};
        wildcard bins leaflvl_s = {8'b??101111};
    }
    global_PTE_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b??111111};
        wildcard bins leaflvl_s = {8'b??101111};
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

    exec_acc: coverpoint ins.current.execute_access {
        bins set = {1};
    }
    read_acc : coverpoint ins.current.read_access {
        bins set = {1};
    }
    write_acc: coverpoint ins.current.write_access {
        bins set = {1};
    }

    cp_global_read_s: cross global_PTE_d, PageType_d, read_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_u);
    }
    cp_global_read_u: cross global_PTE_d, PageType_d, read_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_s);
    }
    cp_global_write_s: cross global_PTE_d, PageType_d, write_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_u);
    }
    cp_global_write_u: cross global_PTE_d, PageType_d, write_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_s);
    }
    cp_global_exec_s: cross global_PTE_i, PageType_i, exec_acc {
        ignore_bins ig1 = binsof(global_PTE_i.leaflvl_u);
    }
    cp_global_exec_u: cross global_PTE_i, PageType_i, exec_acc {
        ignore_bins ig1 = binsof(global_PTE_i.leaflvl_s);
    }
endgroup

covergroup Sv_add_feature_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `ifdef UDB_MXLEN_64
        zeros_PTE_i: coverpoint ins.current.pte_i[63:54] {
            bins all_zeros = {10'd0};
        }
        zeros_PTE_d: coverpoint ins.current.pte_d[63:54] {
            bins all_zeros = {10'd0};
        }

        svpbmt_PTE_i: coverpoint ins.current.pte_i[62:61] {
            bins svpbmt_1    = {2'b01};
            bins svpbmt_2    = {2'b10};
            bins svpbmt_3    = {2'b11};
        }
        svpbmt_PTE_d: coverpoint ins.current.pte_d[62:61] {
            bins svpbmt_1    = {2'b01};
            bins svpbmt_2    = {2'b10};
            bins svpbmt_3    = {2'b11};
        }

        reserved_PTE_i: coverpoint ins.current.pte_i[60:54] {
            bins reserved_bit_54 = {7'b0000001};
            bins reserved_bit_55 = {7'b0000010};
            bins reserved_bit_56 = {7'b0000100};
            bins reserved_bit_57 = {7'b0001000};
            bins reserved_bit_58 = {7'b0010000};
            bins reserved_bit_59 = {7'b0100000};
            bins reserved_bit_60 = {7'b1000000};
        }
        reserved_PTE_d: coverpoint ins.current.pte_d[60:54] {
            bins reserved_bit_54 = {7'b0000001};
            bins reserved_bit_55 = {7'b0000010};
            bins reserved_bit_56 = {7'b0000100};
            bins reserved_bit_57 = {7'b0001000};
            bins reserved_bit_58 = {7'b0010000};
            bins reserved_bit_59 = {7'b0100000};
            bins reserved_bit_60 = {7'b1000000};
        }

        PBMTE_unset: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "pbmte")[0] {
            bins not_set = {1'b0};
        }
        ADUE_unset: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "adue")[0] {
            bins not_set = {1'b0};
        }

        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
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

        exec_acc: coverpoint ins.current.execute_access {
            bins set = {1};
        }
        read_acc : coverpoint ins.current.read_access {
            bins set = {1};
        }
        write_acc: coverpoint ins.current.write_access {
            bins set = {1};
        }
        load_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
            bins load_page_fault = {LOAD_PAGE_FAULT};
        }
        ins_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
            bins ins_page_fault = {INSTRUCTION_PAGE_FAULT};
        }
        store_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") {
            bins store_amo_page_fault = {STORE_AMO_PAGE_FAULT};
        }

        //pte.17
        `ifndef SVNAPOT_SUPPORTED
            svnapot_PTE_i: coverpoint ins.current.pte_i[63] {
                bins svnapot   = {1'b1};
            }
            svnapot_PTE_d: coverpoint ins.current.pte_d[63] {
                bins svnapot   = {1'b1};
            }
            cp_svnapot_read_fault:  cross svnapot_PTE_d, load_page_fault, read_acc, mode;
            cp_svnapot_write_fault: cross svnapot_PTE_d, store_page_fault, write_acc, mode;
            cp_svnapot_exec_fault:  cross svnapot_PTE_i, ins_page_fault, exec_acc, mode;
        `endif

        //pte.19
        cp_svpbmt_read_fault:  cross svpbmt_PTE_d, load_page_fault, read_acc, mode, PBMTE_unset;
        cp_svpbmt_write_fault: cross svpbmt_PTE_d, store_page_fault, write_acc, mode, PBMTE_unset;
        cp_svpbmt_exec_fault:  cross svpbmt_PTE_i, ins_page_fault, exec_acc, mode, PBMTE_unset;

        //pte.20
        cp_reserved_read_fault:  cross reserved_PTE_d, load_page_fault, read_acc, mode;
        cp_reserved_write_fault: cross reserved_PTE_d, store_page_fault, write_acc, mode;
        cp_reserved_exec_fault:  cross reserved_PTE_i, ins_page_fault, exec_acc, mode;

        //pte.17&19&20
        cp_read_nofault:  cross zeros_PTE_d, read_acc, mode;
        cp_write_nofault: cross zeros_PTE_d, write_acc, mode;
        cp_exec_nofault:  cross zeros_PTE_i, exec_acc, mode;

        //pte.18
        cp_svadu_disabled: cross ADUE_unset, mode;
    `else

        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins sv32 = {1'b1};
        }
        ADUE_unset: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfgh", "adue")[0] {
            bins not_set = {1'b0};
        }
        cp_svadu_disabled: cross ADUE_unset, mode;

    `endif
endgroup

`ifndef EXCLUDE_SM
covergroup Sv_Sm_satp_cg with function sample(ins_t ins);
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

covergroup Sv_Sm_mstatus_mprv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    tvm_mstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "tvm")[0] {
        bins set = {1};
    }
    Mcause: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins illegal_ins = {ILLEGAL_INSTRUCTION};
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

    PTE_upage_d: coverpoint ins.current.pte_d[7:0] { //ms.3 & 4
        wildcard bins leaflvl_u = {8'b11?11111};
    }

    `ifdef UDB_MXLEN_64
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
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
            bins sv32_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
        }
    `endif

    load_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins load_page_fault = {LOAD_PAGE_FAULT};
    }
    store_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") {
        bins store_amo_page_fault = {STORE_AMO_PAGE_FAULT};
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
    // MPRV does not translate instruction fetch, so the fetch has no page type to cross with
    cp_mprv_upage_smode_sumunset_noexec: cross mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m, satp_mode, sum_sstatus { //ms.3
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.set);
    }
    cp_mprv_upage_smode_sumset_exec: cross mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m, satp_mode, sum_sstatus { //ms.4
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
`endif // EXCLUDE_SM

`ifdef SV_ZICBO_ANY
covergroup Sv_Zicbo_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"
    //pte permission for leaf PTEs
    PTE_d_inv: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u_w = {8'b11?1?110};
        wildcard bins leaflvl_s_w = {8'b11?0?110};
    }

    PTE_d_res_rwx: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_exec_u = {8'b11?11101};
        wildcard bins leaflvl_noexec_u = {8'b11?10101};
        wildcard bins leaflvl_exec_s = {8'b11?01101};
        wildcard bins leaflvl_noexec_s = {8'b11?00101};
    }

    PTE_nonleaf_lvl0_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins lvl0_s = {8'b???00001};
        wildcard bins lvl0_u = {8'b???10001};
    }

    PTE_r_set_w_unset_spage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_r_s = {8'b11?0?011};
    }

    PTE_w_unset_spage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_w_0 = {8'b11?0?0?1};
    }

    PTE_spage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_s = {8'b11?01111};
    }

    PTE_upage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
    }

    PTE_r_set_w_unset_upage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_r_u = {8'b11?1?011};
    }

    PTE_w_unset_upage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_w_0 = {8'b11?1?0?1};
    }

    PTE_Abit_unset_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b?0?11111};
        wildcard bins leaflvl_s = {8'b?0?01111};
    }

    PTE_Dbit_unset_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b01?1?111};
        wildcard bins leaflvl_s = {8'b01?0?111};
    }

    PTE_RWX_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }

    pointer_PTE_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins pointer = {8'b00?00001};
    }

    PTE_DAU_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins nonleaf_D_bit = {8'b10?00001};
        wildcard bins nonleaf_A_bit = {8'b01?00001};
        wildcard bins nonleaf_U_bit = {8'b00?10001};
    }

    // satp.mode for coverage of SV32, SV39, SV48 & SV57
    `ifdef UDB_MXLEN_64
        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] {
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
        mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] {
            bins sv32 = {1'b1};
        }
    `endif

    `ifdef UDB_MXLEN_64
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
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
            bins sv32_kilo = {2'b00} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1);
        }
    `endif

    kilo_page: coverpoint ins.current.page_type_d {
        bins kilo_page = {2'b00};
    }

    `ifdef UDB_MXLEN_64
        misaligned_PPN_d: coverpoint ins.current.page_type_d {
            `ifdef SV48_SUPPORTED
                bins sv48_tera_misaligned = {2'b11} iff ((ins.current.ppn_d[26:0] != 27'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
                bins sv48_giga_misaligned = {2'b10} iff ((ins.current.ppn_d[17:0] != 18'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
                bins sv48_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[8:0]  !=  9'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1001));
            `endif
            `ifdef SV39_SUPPORTED
                bins sv39_giga_misaligned = {2'b10} iff ((ins.current.ppn_d[17:0] != 18'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000));
                bins sv39_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[8:0]  !=  9'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[3:0] == 4'b1000));
            `endif
        }
    `else
        misaligned_PPN_d: coverpoint ins.current.page_type_d {
            bins sv32_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[9:0] != 10'b0) && (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "satp", "mode")[0] == 1'b1));
        }
    `endif

    store_page_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause") iff (ins.trap == 1) {
        bins store_amo_page_fault = {STORE_AMO_PAGE_FAULT};
    }
    // Only reachable when the DUT has an address that faults: its sole bin is the
    // store/AMO access fault cause, and its only consumers are the guarded
    // cp_*_to_nonexistent_pa_cbo_* crosses below.
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        store_acc_fault: coverpoint  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause") iff (ins.trap == 1) {
            bins store_amo_access_fault = {STORE_AMO_ACCESS_FAULT};
        }
    `endif
    sum_sstatus: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstatus", "sum")[0]{
        bins notset = {0};
        bins set = {1};
    }

    cbo_ins: coverpoint ins.current.insn {
        `ifdef ZICBOM_SUPPORTED
            wildcard bins any_zicbom_ins = {CBO_INVAL, CBO_CLEAN, CBO_FLUSH};
        `endif
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins zicboz_ins = {CBO_ZERO};
        `endif
    }

    zicbop_ins: coverpoint ins.current.insn {
        wildcard bins any_prefetch_ins = {PREFETCH_I, PREFETCH_R, PREFETCH_W};
    }

    // A prefetch is a hint that need not translate, so it has no PTE or page type to cross with
    cp_zicbop_no_fault_s: cross zicbop_ins, mode, priv_mode_s iff (ins.trap == 0);
    cp_zicbop_no_fault_u: cross zicbop_ins, mode, priv_mode_u iff (ins.trap == 0);

    cp_PTE_inv_cbo_s: cross PTE_d_inv, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_u_w);
    }
    cp_PTE_inv_cbo_u: cross PTE_d_inv, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_s_w);
    }

    cp_PTE_res_rwx_cbo_s: cross PTE_d_res_rwx, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_u);
    }
    cp_PTE_res_rwx_cbo_u: cross PTE_d_res_rwx, PageType_d, store_page_fault, cbo_ins, priv_mode_u  {
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_s);
    }

    cp_PTE_nonleaf_lvl0_cbo_s: cross PTE_nonleaf_lvl0_d, kilo_page, mode, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_u);
    }

    cp_PTE_nonleaf_lvl0_cbo_u: cross PTE_nonleaf_lvl0_d, kilo_page, mode, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_s);
    }

    // A Zicbom instruction is allowed if a load or store instruction is permitted to access the corresponding physical addresses
    cp_PTE_r_set_w_unset_zicbom_s: cross PTE_r_set_w_unset_spage_d, PageType_d, cbo_ins, priv_mode_s, sum_sstatus {
        ignore_bins ig1 = binsof(cbo_ins.zicboz_ins);
    }
    cp_PTE_r_set_w_unset_zicbom_u: cross PTE_r_set_w_unset_upage_d, PageType_d, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(cbo_ins.zicboz_ins);
    }

    // A Zicboz instruction is allowed if a store instruction is permitted to access the corresponding physical addresses
    cp_PTE_w_unset_zicboz_s: cross PTE_w_unset_spage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s, sum_sstatus {
        ignore_bins ig1 = binsof(cbo_ins.any_zicbom_ins);
    }
    cp_PTE_w_unset_zicboz_u: cross PTE_w_unset_upage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(cbo_ins.any_zicbom_ins);
    }

    cp_spage_rwx_cbo_u: cross PTE_spage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u;

    cp_upage_sumunset_cbo_s: cross PTE_upage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s, sum_sstatus {
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }

    cp_Abit_unset_cbo_s: cross PTE_Abit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_Abit_unset_d.leaflvl_u);
    }
    cp_Abit_unset_cbo_u: cross PTE_Abit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_Abit_unset_d.leaflvl_s);
    }

    // A Zicbom instruction does not check the dirty bit and neither raises an exception nor sets the bit
    cp_Dbit_unset_zicbom_s: cross PTE_Dbit_unset_d, PageType_d, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_u);
        ignore_bins ig2 = binsof(cbo_ins.zicboz_ins);
    }
    cp_Dbit_unset_zicbom_u: cross PTE_Dbit_unset_d, PageType_d, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_s);
        ignore_bins ig2 = binsof(cbo_ins.zicboz_ins);
    }
    // A Zicboz instruction checks the dirty bit and may raise an exception and set the bit as required
    cp_Dbit_unset_zicboz_s: cross PTE_Dbit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_u);
        ignore_bins ig2 = binsof(cbo_ins.any_zicbom_ins);
    }
    cp_Dbit_unset_zicboz_u: cross PTE_Dbit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_s);
        ignore_bins ig2 = binsof(cbo_ins.any_zicbom_ins);
    }

    cp_misaligned_page_cbo_s: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, cbo_ins, priv_mode_s  {
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
    }
    cp_misaligned_page_cbo_u: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, cbo_ins, priv_mode_u  {
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
    }

    cp_PTE_nonleaf_DAU_cbo: cross PTE_DAU_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s_u {
        `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        `ifdef UDB_MXLEN_64
            d_phys_address_nonexistent: coverpoint ({8'b0, ins.current.phys_adr_d[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                bins non_existent_pa = {1};
            }
        `else
            d_phys_address_nonexistent: coverpoint ({30'b0, ins.current.phys_adr_d[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                bins non_existent_pa = {1};
            }
        `endif
        // PTE points to a non existent physical address
        cp_leaf_PTE_to_nonexistent_pa_cbo_s: cross PTE_RWX_d, d_phys_address_nonexistent, PageType_d, store_acc_fault, cbo_ins, priv_mode_s {
            ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
        }
        cp_leaf_PTE_to_nonexistent_pa_cbo_u: cross PTE_RWX_d, d_phys_address_nonexistent, PageType_d, store_acc_fault, cbo_ins, priv_mode_u {
            ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
        }

        // Non leaf PTE points to a non existatant phys addr instead of next page table. Store access fault required during walk
        // Example: Setup a giga page in sv48, lvl 3 pte (tera) should point to lvl2 page table, but it points to non existent PA
        // The walk faults before any data physical address exists, so check where the pointer PTE points instead
        `ifdef UDB_MXLEN_64
            nonleaf_ppn_nonexistent: coverpoint (ins.current.pte_d[53:10] == 44'(`RVMODEL_ACCESS_FAULT_ADDRESS >> 12)) {
                bins non_existent_pa = {1};
            }
        `else
            nonleaf_ppn_nonexistent: coverpoint (ins.current.pte_d[31:10] == 22'(`RVMODEL_ACCESS_FAULT_ADDRESS >> 12)) {
                bins non_existent_pa = {1};
            }
        `endif
        cp_nonleaf_PTE_to_nonexistent_pa_cbo: cross pointer_PTE_d, nonleaf_ppn_nonexistent, PageType_d, store_acc_fault, cbo_ins, priv_mode_s_u {
            `ifdef SV48_SUPPORTED ignore_bins ig1 = binsof(PageType_d.sv48_tera); `endif     // Here PageType_d will be the page being pointed towards
            `ifdef SV39_SUPPORTED ignore_bins ig2 = binsof(PageType_d.sv39_giga); `endif
            `ifdef UDB_MXLEN_32   ignore_bins ig3 = binsof(PageType_d.sv32_mega); `endif
        }
    `endif

endgroup
`endif // SV_ZICBO_ANY

covergroup Sv_Exceptions_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    instr_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") == `UDB_MXLEN'(INSTRUCTION_PAGE_FAULT)) {
        // auto fill 0/1
    }
    load_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") == `UDB_MXLEN'(LOAD_PAGE_FAULT)) {
        // auto fill 0/1
    }
    store_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "code") == `UDB_MXLEN'(STORE_AMO_PAGE_FAULT)) {
        // auto fill 0/1
    }
    // The PC of the target: a fetch that spans two parcels may report either parcel in virt_adr_i
    i_virt_adr_misaligned: coverpoint ins.current.pc_rdata[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    i_page_table_entry_invalid: coverpoint ins.current.pte_i[0] {
        // auto fill valid bit 0/1
    }
    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    memops: coverpoint ins.current.insn {
        wildcard bins sw       = {SW};
        wildcard bins lw       = {LW};
    }
    lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    jalr: coverpoint ins.prev.insn {
        wildcard bins jalr = {JALR};
    }

    d_page_table_entry_bad: coverpoint ins.current.pte_d[7:0] {
        bins invalid = {8'b00000000}; // invalid
    }

    d_phys_address: coverpoint ins.current.phys_adr_d[11:0] {
        // check that fault occurs on the last halfword of the first page and the first halfword of the second page
        bins first  = {12'b111111111110};
        bins second = {12'b000000000000};
    }

    i_page_table_entry_bad: coverpoint ins.current.pte_i[7:0] {
        bins invalid = {8'b00000000}; // invalid
    }

    i_phys_address: coverpoint ins.current.phys_adr_i[11:0] {
        // check that fault occurs on the last halfword of the first page and the first halfword of the second page
        bins first  = {12'b111111111110};
        bins second = {12'b000000000000};
    }


    // Main Coverpoints
    cp_instr_page_fault_s:           cross priv_mode_s, instr_page_fault;
    cp_load_page_fault_s:            cross priv_mode_s, load_page_fault;
    cp_store_page_fault_s:           cross priv_mode_s, store_page_fault;
    cp_misaligned_load_page_fault_s: cross priv_mode_s, d_page_table_entry_bad, d_phys_address, lw;
    cp_misaligned_store_page_fault_s:cross priv_mode_s, d_page_table_entry_bad, d_phys_address, sw;
    cp_misaligned_inst_page_fault_s: cross priv_mode_s, i_page_table_entry_bad, i_phys_address, jalr;
    cp_instr_page_fault_u:           cross priv_mode_u, instr_page_fault;
    cp_load_page_fault_u:            cross priv_mode_u, load_page_fault;
    cp_store_page_fault_u:           cross priv_mode_u, store_page_fault;

    // Access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Accesses land at an offset into the faulting region, which is at least 128 bytes
        i_phys_address_nonexistent: coverpoint ((64'(ins.current.phys_adr_i) - 64'(`RVMODEL_ACCESS_FAULT_ADDRESS)) < 64'd128) {
            // auto fill 1/0 for the physical address being valid
        }
        d_phys_address_nonexistent: coverpoint ((64'(ins.current.phys_adr_d) - 64'(`RVMODEL_ACCESS_FAULT_ADDRESS)) < 64'd128) {
            // auto fill 1/0 for the physical address being valid
        }
        cp_misaligned_priority_s:        cross priv_mode_s, memops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_LDST
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
        cp_misaligned_priority_fetch_s:  cross priv_mode_s, jalr,   i_virt_adr_misaligned, i_page_table_entry_invalid, i_phys_address_nonexistent {
            `ifndef ZCA_SUPPORTED
                // Without Zca, a jalr to a misaligned target raises instruction-address-misaligned on the jalr
                ignore_bins misaligned_target = binsof(i_virt_adr_misaligned.misaligned);
            `endif
        }
        cp_misaligned_priority_u:        cross priv_mode_u, memops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_LDST
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
        cp_misaligned_priority_fetch_u:  cross priv_mode_u, jalr,   i_virt_adr_misaligned, i_page_table_entry_invalid, i_phys_address_nonexistent {
            `ifndef ZCA_SUPPORTED
                // Without Zca, a jalr to a misaligned target raises instruction-address-misaligned on the jalr
                ignore_bins misaligned_target = binsof(i_virt_adr_misaligned.misaligned);
            `endif
        }
    `endif

endgroup

`ifndef EXCLUDE_SM
covergroup Sv_ExceptionsSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    mstatus_mprv_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mprv")[0] {
        bins one = {1};
    }
    mstatus_mpp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0] {
        bins u_mode = {2'b00};
        bins s_mode = {2'b01};
    }
    instr_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") == `UDB_MXLEN'(INSTRUCTION_PAGE_FAULT)) {
        // auto fill 0/1
    }
    load_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") == `UDB_MXLEN'(LOAD_PAGE_FAULT)) {
        // auto fill 0/1
    }
    store_page_fault: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "code") == `UDB_MXLEN'(STORE_AMO_PAGE_FAULT)) {
        // auto fill 0/1
    }
    i_page_table_entry_invalid: coverpoint ins.current.pte_i[0] {
        // auto fill valid bit 0/1
    }
    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    memops: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
        wildcard bins lw = {LW};
    }
    medeleg_walk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "medeleg", "medeleg") {
        bins zeros                    = {16'b0000_0000_0000_0000};
        `ifndef ZCA_SUPPORTED
            bins instrmisaligned_enabled = {16'b0000_0000_0000_0001};
        `endif
        bins illegalinstr_enabled     = {16'b0000_0000_0000_0100};
        bins breakpoint_enabled       = {16'b0000_0000_0000_1000};
        bins loadmisaligned_enabled   = {16'b0000_0000_0001_0000};
        bins storemisaligned_enabled  = {16'b0000_0000_0100_0000};
        bins ecallu_enabled           = {16'b0000_0001_0000_0000};
        // Delegating ecall to S mode makes it impossible to escape S mode
        // bins ecalls_enabled           = {16'b0000_0010_0000_0000};
        // bit 10 reserved
        // bit 11 is read only zero
        bins instrpagefault_enabled   = {16'b0001_0000_0000_0000};
        bins loadpagefault_enabled    = {16'b0010_0000_0000_0000};
        // bit 14 reserved
        bins storepagefault_enabled   = {16'b1000_0000_0000_0000};
        wildcard bins ones            = {16'b1011_0001_?1?1_11??}; // access faults might not be possible to delegate if they don't exist
        `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
            bins instraccessfault_enabled = {16'b0000_0000_0000_0010};
            bins loadaccessfault_enabled  = {16'b0000_0000_0010_0000};
            bins storeaccessfault_enabled = {16'b0000_0000_1000_0000};
        `endif
    }
    jalr: coverpoint ins.prev.insn {
        wildcard bins jalr = {JALR};
    }

    // Main Coverpoints
    // Test M mode fetches using an identity mapped Virtual Address with V=0. No translation for instruction fetches and V=0 won't be checked, therefore it must not fault
    cp_instr_page_fault_m: cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, jalr;
    cp_load_page_fault_m:  cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, load_page_fault;
    cp_store_page_fault_m: cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, store_page_fault;
    cp_medeleg_m:          cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, memops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_fetch_m:    cross priv_mode_m, mstatus_mprv_one, mstatus_mpp, medeleg_walk, jalr;
    cp_medeleg_s:          cross priv_mode_s, memops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_fetch_s:    cross priv_mode_s, jalr,   i_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_u:          cross priv_mode_u, memops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_fetch_u:    cross priv_mode_u, jalr,   i_page_table_entry_invalid, medeleg_walk;

    // Access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Accesses land at an offset into the faulting region, which is at least 128 bytes
        d_phys_address_nonexistent: coverpoint ((64'(ins.current.phys_adr_d) - 64'(`RVMODEL_ACCESS_FAULT_ADDRESS)) < 64'd128) {
            // auto fill 1/0 for the physical address being valid
        }
        cp_misaligned_priority_m:       cross priv_mode_m, memops, d_virt_adr_misaligned, d_phys_address_nonexistent, d_page_table_entry_invalid {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_LDST
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
    `endif
endgroup
`endif // EXCLUDE_SM

`ifdef ZAAMO_SUPPORTED
covergroup Sv_ExceptionsZaamo_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    amoops: coverpoint ins.current.insn {
        wildcard bins amoadd_w = {AMOADD_W};
    }
    // main coverpoints
    // Access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            d_phys_address_nonexistent: coverpoint ({8'b0, ins.current.phys_adr_d[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            d_phys_address_nonexistent: coverpoint ({30'b0, ins.current.phys_adr_d[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_s:        cross priv_mode_s, amoops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_AMO
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
        cp_misaligned_priority_u:        cross priv_mode_u, amoops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_AMO
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
    `endif

endgroup
`endif // ZAAMO_SUPPORTED

`ifdef ZAAMO_SUPPORTED
`ifndef EXCLUDE_SM
covergroup Sv_ExceptionsZaamoSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    amoops: coverpoint ins.current.insn {
        wildcard bins amoadd_w = {AMOADD_W};
    }
    medeleg_walk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "medeleg", "medeleg") {
        bins zeros                    = {16'b0000_0000_0000_0000};
        `ifndef ZCA_SUPPORTED
            bins instrmisaligned_enabled = {16'b0000_0000_0000_0001};
        `endif
        bins instraccessfault_enabled = {16'b0000_0000_0000_0010};
        bins illegalinstr_enabled     = {16'b0000_0000_0000_0100};
        bins breakpoint_enabled       = {16'b0000_0000_0000_1000};
        bins loadmisaligned_enabled   = {16'b0000_0000_0001_0000};
        bins loadaccessfault_enabled  = {16'b0000_0000_0010_0000};
        bins storemisaligned_enabled  = {16'b0000_0000_0100_0000};
        bins storeaccessfault_enabled = {16'b0000_0000_1000_0000};
        bins ecallu_enabled           = {16'b0000_0001_0000_0000};
        // Delegating ecall to S mode makes it impossible to escape S mode
        // bins ecalls_enabled           = {16'b0000_0010_0000_0000};
        // bit 10 reserved
        // bit 11 is read only zero
        bins instrpagefault_enabled   = {16'b0001_0000_0000_0000};
        bins loadpagefault_enabled    = {16'b0010_0000_0000_0000};
        // bit 14 reserved
        bins storepagefault_enabled   = {16'b1000_0000_0000_0000};
        wildcard bins ones            = {16'b1011_0001_1111_111?};
    }

    // main coverpoints
    cp_medeleg_m: cross priv_mode_m, amoops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_s: cross priv_mode_s, amoops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_u: cross priv_mode_u, amoops, d_page_table_entry_invalid, medeleg_walk;

    // Access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            d_phys_address_nonexistent: coverpoint ({8'b0, ins.current.phys_adr_d[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            d_phys_address_nonexistent: coverpoint ({30'b0, ins.current.phys_adr_d[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_m: cross priv_mode_m, amoops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifndef UDB_MISALIGNED_AMO
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
    `endif
endgroup
`endif // EXCLUDE_SM
`endif // ZAAMO_SUPPORTED

`ifdef ZALRSC_SUPPORTED
covergroup Sv_ExceptionsZalrsc_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints

    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    lrscops: coverpoint ins.current.insn {
        wildcard bins lr_w     = {LR_W};
        wildcard bins sc_w     = {SC_W};
    }
    // main coverpoints

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            d_phys_address_nonexistent: coverpoint ({8'b0, ins.current.phys_adr_d[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            d_phys_address_nonexistent: coverpoint ({30'b0, ins.current.phys_adr_d[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_s:        cross priv_mode_s, lrscops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifdef UDB_LRSC_MISALIGNED_BEHAVIOR_ALWAYS_RAISE_MISALIGNED_EXCEPTION
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
        cp_misaligned_priority_u:        cross priv_mode_u, lrscops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifdef UDB_LRSC_MISALIGNED_BEHAVIOR_ALWAYS_RAISE_MISALIGNED_EXCEPTION
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
    `endif
endgroup
`endif // ZALRSC_SUPPORTED

`ifdef ZALRSC_SUPPORTED
`ifndef EXCLUDE_SM
covergroup Sv_ExceptionsZalrscSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    d_virt_adr_misaligned: coverpoint ins.current.virt_adr_d[1:0] {
        bins aligned    = {2'b00};
        bins misaligned = {2'b10};
    }
    d_page_table_entry_invalid: coverpoint ins.current.pte_d[0] {
        // auto fill valid bit 0/1
    }
    lrscops: coverpoint ins.current.insn {
        wildcard bins lr_w = {LR_W};
        wildcard bins sc_w = {SC_W};
    }
    medeleg_walk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "medeleg", "medeleg") {
        bins zeros                    = {16'b0000_0000_0000_0000};
        `ifndef ZCA_SUPPORTED
            bins instrmisaligned_enabled = {16'b0000_0000_0000_0001};
        `endif
        bins instraccessfault_enabled = {16'b0000_0000_0000_0010};
        bins illegalinstr_enabled     = {16'b0000_0000_0000_0100};
        bins breakpoint_enabled       = {16'b0000_0000_0000_1000};
        bins loadmisaligned_enabled   = {16'b0000_0000_0001_0000};
        bins loadaccessfault_enabled  = {16'b0000_0000_0010_0000};
        bins storemisaligned_enabled  = {16'b0000_0000_0100_0000};
        bins storeaccessfault_enabled = {16'b0000_0000_1000_0000};
        bins ecallu_enabled           = {16'b0000_0001_0000_0000};
        // Delegating ecall to S mode makes it impossible to escape S mode
        // bins ecalls_enabled           = {16'b0000_0010_0000_0000};
        // bit 10 reserved
        // bit 11 is read only zero
        bins instrpagefault_enabled   = {16'b0001_0000_0000_0000};
        bins loadpagefault_enabled    = {16'b0010_0000_0000_0000};
        // bit 14 reserved
        bins storepagefault_enabled   = {16'b1000_0000_0000_0000};
        wildcard bins ones            = {16'b1011_0001_1111_111?};
    }

    // main coverpoints
    cp_medeleg_m: cross priv_mode_m, lrscops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_s: cross priv_mode_s, lrscops, d_page_table_entry_invalid, medeleg_walk;
    cp_medeleg_u: cross priv_mode_u, lrscops, d_page_table_entry_invalid, medeleg_walk;

    // access fault coverpoints
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        `ifdef UDB_MXLEN_64 // Number of physical address bits is different by XLEN, either 34 or 56
            d_phys_address_nonexistent: coverpoint ({8'b0, ins.current.phys_adr_d[55:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `else
            d_phys_address_nonexistent: coverpoint ({30'b0, ins.current.phys_adr_d[33:2], 2'b00} == `RVMODEL_ACCESS_FAULT_ADDRESS) {
                // auto fill 1/0 for the physical address being valid
            }
        `endif
        cp_misaligned_priority_m: cross priv_mode_m, lrscops, d_virt_adr_misaligned, d_page_table_entry_invalid, d_phys_address_nonexistent {
            `ifdef UDB_MISALIGNED_LDST_EXCEPTION_PRIORITY_HIGH
                `ifdef UDB_LRSC_MISALIGNED_BEHAVIOR_ALWAYS_RAISE_MISALIGNED_EXCEPTION
                    // The misaligned exception is raised before translation, so there is no PTE or physical address
                    ignore_bins misaligned_before_translation = binsof(d_virt_adr_misaligned.misaligned);
                `endif
            `endif
        }
    `endif
endgroup
`endif // EXCLUDE_SM
`endif // ZALRSC_SUPPORTED

// H groups: two-stage address translation.  sail_to_rvvi.py records one PTE per walk (PTE_I, PTE_D) and does not
// tell the VS-stage leaf from the G-stage leaf, so the coverpoints record each guest access with its privilege mode,
// the translation modes, the controls that affect it and the trap it takes; the PTE a testcase uses is in the test,
// and its effect is checked by the signature.
// TODO: once sail_to_rvvi.py records the VS-stage and G-stage leaf PTEs of each walk separately, bin the leaf's V,
// U, R, W, X, A, D, N, PBMT, RSW and reserved bits in cp_vsatp_perm, cp_hgatp_perm and cp_twostage_perm.
`ifdef H_SUPPORTED

`ifdef ZICBOM_SUPPORTED
    `define SV_HZICBO_ANY
`elsif ZICBOZ_SUPPORTED
    `define SV_HZICBO_ANY
`elsif ZICBOP_SUPPORTED
    `define SV_HZICBO_ANY
`endif

covergroup Sv_H_vsstage_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    // Each supported VS-stage mode
    vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            bins sv39 = {8};
        `endif
        `ifdef UDB_SV48_VSMODE_TRANSLATION
            bins sv48 = {9};
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            bins sv57 = {10};
        `endif
        `ifdef UDB_SV32_VSMODE_TRANSLATION
            bins sv32 = {1};
        `endif
    }
    hgatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }
    // The trap into HS-mode that the access takes, if any.  Only a trap writes scause on these instructions.
    trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        wildcard bins none = {6'b0?????};
        bins page_fault    = {6'b101100, 6'b101101, 6'b101111};
    }
    vsstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        henvcfg_pbmte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "pbmte") {
            bins off = {0};
            `ifdef SVPBMT_SUPPORTED
                bins on  = {1};
            `endif
        }
        `ifdef SVNAPOT_SUPPORTED
            // Pages 0, 2 and 15 of the 64 KiB NAPOT region
            napot_page : coverpoint ins.current.rs1_val[15:12] {
                bins page0  = {0};
                bins page2  = {2};
                bins page15 = {15};
            }
        `endif
    `else
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
    `endif

    // VS-stage leaf permissions and formats (hgatp = Bare), with vsstatus.SUM and vsstatus.MXR
    cp_vsatp_perm   : cross priv_mode_vs_vu, access, vsatp_mode, hgatp_bare, trap;
    cp_vsatp_sum    : cross priv_mode_vs_vu, access, vsatp_mode, hgatp_bare, vsstatus_sum;
    cp_vsstatus_mxr : cross priv_mode_vs_vu, lw, vsatp_mode, hgatp_bare, vsstatus_sum, vsstatus_mxr;
    // VS-stage A/D bits: Svade faults with henvcfg.ADUE = 0; Svadu updates them with henvcfg.ADUE = 1
    cp_vsatp_adue   : cross priv_mode_vs, access, vsatp_mode, hgatp_bare, menvcfg_adue, henvcfg_adue {
        // henvcfg.ADUE is read-only zero while menvcfg.ADUE = 0
        `ifdef SVADU_SUPPORTED
            ignore_bins read_only = binsof(menvcfg_adue.off) && binsof(henvcfg_adue.on);
        `endif
    }
    `ifdef UDB_MXLEN_64
        // PBMT in a VS-stage leaf is reserved unless henvcfg.PBMTE = 1, and PBMT = 3 always
        cp_vsatp_pbmt  : cross priv_mode_vs, access, vsatp_mode, hgatp_bare, henvcfg_pbmte, trap;
        `ifdef SVNAPOT_SUPPORTED
            cp_vsatp_napot : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_bare, napot_page;
        `endif
    `endif
endgroup

covergroup Sv_H_gstage_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    vsatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    // Each supported G-stage mode
    hgatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        `ifdef UDB_SV39X4_TRANSLATION
            bins sv39x4 = {8};
        `endif
        `ifdef UDB_SV48X4_TRANSLATION
            bins sv48x4 = {9};
        `endif
        `ifdef UDB_SV57X4_TRANSLATION
            bins sv57x4 = {10};
        `endif
        `ifdef UDB_SV32X4_TRANSLATION
            bins sv32x4 = {1};
        `endif
    }
    trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        wildcard bins none     = {6'b0?????};
        bins guest_page_fault  = {6'b110100, 6'b110101, 6'b110111};
    }
    // HS-level MXR: mret into the guest logs mstatus
    mstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        menvcfg_pbmte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte") {
            bins off = {0};
            `ifdef SVPBMT_SUPPORTED
                bins on  = {1};
            `endif
        }
        `ifdef SVNAPOT_SUPPORTED
            napot_page : coverpoint ins.current.rs1_val[15:12] {
                bins page0  = {0};
                bins page2  = {2};
                bins page15 = {15};
            }
        `endif
        // The one set bit above bit 36 of the guest physical address (vsatp = Bare)
        gpa_bit : coverpoint ($clog2(ins.current.rs1_val + 1) - 1) {
            bins b[] = {[37:63]};
        }
    `else
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
    `endif

    // G-stage leaf permissions and formats (vsatp = Bare); the U bit is checked as for U-mode
    cp_hgatp_perm : cross priv_mode_vs_vu, access, vsatp_bare, hgatp_mode, trap;
    // Only the HS-level MXR makes G-stage execute-only pages readable
    cp_hgatp_mxr  : cross priv_mode_vs_vu, lw, vsatp_bare, hgatp_mode, mstatus_mxr, vsstatus_mxr;
    // G-stage A/D bits: Svade faults with menvcfg.ADUE = 0; Svadu updates them with menvcfg.ADUE = 1
    cp_hgatp_adue : cross priv_mode_vs, access, vsatp_bare, hgatp_mode, menvcfg_adue;
    `ifdef UDB_MXLEN_64
        cp_hgatp_pbmt  : cross priv_mode_vs, access, vsatp_bare, hgatp_mode, menvcfg_pbmte, trap;
        `ifdef SVNAPOT_SUPPORTED
            cp_hgatp_napot : cross priv_mode_vs_vu, access, vsatp_bare, hgatp_paged, napot_page;
        `endif
        // Guest physical address bits above the mode's width raise guest-page faults
        cp_hgatp_gpa_width : cross priv_mode_vs, lw, vsatp_bare, hgatp_mode, gpa_bit;
    `endif
endgroup

covergroup Sv_H_twostage_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    jalr : coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    vsatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }
    // Each pair of VS-stage and G-stage modes with the same number of levels that the hart supports
    stage_modes : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[3:0]} {
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            `ifdef UDB_SV39X4_TRANSLATION
                bins sv39_sv39x4 = {8'h88};
            `endif
        `endif
        `ifdef UDB_SV48_VSMODE_TRANSLATION
            `ifdef UDB_SV48X4_TRANSLATION
                bins sv48_sv48x4 = {8'h99};
            `endif
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            `ifdef UDB_SV57X4_TRANSLATION
                bins sv57_sv57x4 = {8'haa};
            `endif
        `endif
        `ifdef UDB_SV32_VSMODE_TRANSLATION
            `ifdef UDB_SV32X4_TRANSLATION
                bins sv32_sv32x4 = {8'h11};
            `endif
        `endif
    }
    trap : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        wildcard bins none     = {6'b0?????};
        bins page_fault        = {6'b101100, 6'b101101, 6'b101111};
        bins guest_page_fault  = {6'b110100, 6'b110101, 6'b110111};
    }
    guest_page_fault : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        bins guest_page_fault  = {6'b110100, 6'b110101, 6'b110111};
    }
    page_fault : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        bins page_fault = {6'b101100, 6'b101101, 6'b101111};
    }
    access_fault : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        bins access_fault = {6'b100001, 6'b100101, 6'b100111};
    }
    // A page fault delegated to VS-mode
    vs_page_fault : coverpoint {ins.current.csr_wb[CSR_VSCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vscause", "vscause")[4:0]} {
        bins page_fault = {6'b101100, 6'b101101, 6'b101111};
    }
    hedeleg_page_faults : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[15:12] {
        bins delegated = {4'b1011};
    }
    mstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    // The pseudoinstruction that htinst holds after a guest-page fault on an implicit VS-stage access
    htinst_pseudo : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htinst", "htinst") iff (ins.current.csr_wb[CSR_HTINST]) {
        `ifdef UDB_MXLEN_64
            bins read  = {'h3000};
            `ifdef SVADU_SUPPORTED
                bins write = {'h3020};
            `endif
        `else
            bins read  = {'h2000};
            `ifdef SVADU_SUPPORTED
                bins write = {'h2020};
            `endif
        `endif
    }
    htinst_read : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htinst", "htinst") iff (ins.current.csr_wb[CSR_HTINST]) {
        `ifdef UDB_MXLEN_64
            bins read = {'h3000};
        `else
            bins read = {'h2000};
        `endif
    }
    // A fetch at the last halfword of a page
    page_end : coverpoint ins.current.rs1_val[11:0] {
        bins page_end = {12'hffe};
    }
    ldst : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
    }
    // A word two bytes below the end of a page
    ldst_page_end : coverpoint ((ins.current.rs1_val + ins.current.imm) & 'hFFF) {
        bins page_end = {'hFFE};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        `ifdef SVNAPOT_SUPPORTED
            napot_page : coverpoint ins.current.rs1_val[15:12] {
                bins page0  = {0};
                bins page2  = {2};
                bins page15 = {15};
            }
        `endif
        // A guest virtual address whose bits 63 down to the VS-stage mode's top address bit are not all equal
        va_noncanonical : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            `ifdef UDB_SV39_VSMODE_TRANSLATION
                `ifdef UDB_SV39X4_TRANSLATION
                    bins sv39 = {8} iff (ins.current.rs1_val[63:38] != 0 && ins.current.rs1_val[63:38] != '1);
                `endif
            `endif
            `ifdef UDB_SV48_VSMODE_TRANSLATION
                `ifdef UDB_SV48X4_TRANSLATION
                    bins sv48 = {9} iff (ins.current.rs1_val[63:47] != 0 && ins.current.rs1_val[63:47] != '1);
                `endif
            `endif
            `ifdef UDB_SV57_VSMODE_TRANSLATION
                `ifdef UDB_SV57X4_TRANSLATION
                    bins sv57 = {10} iff (ins.current.rs1_val[63:56] != 0 && ins.current.rs1_val[63:56] != '1);
                `endif
            `endif
        }
        `ifdef UDB_REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT
            // A guest-page fault on a guest physical address above the G-stage mode's width: htval holds it shifted
            // right by 2, so bits 63:39 (Sv39x4) or 63:48 (Sv48x4) of htval are not all zero.  A VS-stage PPN reaches
            // guest physical address bit 55 at most, which is within Sv57x4.
            htval_gpa_wide : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")
                             iff (ins.current.csr_wb[CSR_HTVAL]) {
                `ifdef UDB_SV39X4_TRANSLATION
                    bins sv39x4 = {8} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htval", "htval")[63:39] != 0);
                `endif
                `ifdef UDB_SV48X4_TRANSLATION
                    bins sv48x4 = {9} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htval", "htval")[63:48] != 0);
                `endif
            }
        `endif
    `else
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        henvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        `ifdef UDB_REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT
            // Guest physical address bits 33:32, which htval reports as bits 31:30 after a guest-page fault
            htval_gpa_high : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htval", "htval")[31:30] iff (ins.current.csr_wb[CSR_HTVAL]) {
                bins bit32 = {1};
                bins bit33 = {2};
                bins both  = {3};
            }
        `endif
    `endif

    // VS-stage and G-stage permissions combined: a VS-stage denial is a page fault, a G-stage one a guest-page fault
    cp_twostage_perm   : cross priv_mode_vs_vu, access, stage_modes, trap;
    // vsstatus.MXR affects only the VS-stage; the HS-level MXR affects both
    cp_twostage_mxr    : cross priv_mode_vs_vu, lw, stage_modes, vsstatus_mxr, mstatus_mxr;
    cp_twostage_adue   : cross priv_mode_vs, access, stage_modes, menvcfg_adue, henvcfg_adue {
        `ifdef SVADU_SUPPORTED
            ignore_bins read_only = binsof(menvcfg_adue.off) && binsof(henvcfg_adue.on);
        `endif
    }
    // Guest-page faults on implicit VS-stage page-table reads and A/D writes
    cp_implicit_gpf    : cross priv_mode_vs, access, stage_modes, htinst_pseudo;
    // MXR does not make an execute-only G-stage leaf of a VS-stage page table readable to an implicit read
    cp_implicit_mxr    : cross priv_mode_vs, lw, stage_modes, vsstatus_mxr, mstatus_mxr, htinst_read;
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // An access fault on the final address or on a VS-stage or G-stage page-table read reports the original access
        cp_twostage_access_fault : cross priv_mode_vs, access, stage_modes, access_fault;
    `endif
    // Page faults go to VS-mode when hedeleg delegates them; guest-page faults cannot be delegated
    cp_hedeleg_page_fault       : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, hedeleg_page_faults, vs_page_fault;
    cp_hedeleg_guest_page_fault : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, hedeleg_page_faults, guest_page_fault;
    cp_stage_both_bare : cross priv_mode_vs_vu, access, vsatp_bare, hgatp_bare;
    `ifdef ZCA_SUPPORTED
        // A fetch straddling a page boundary faults on the second page
        cp_straddle    : cross priv_mode_vs, jalr, vsatp_paged, hgatp_paged, page_end, trap;
    `endif
    `ifdef UDB_MISALIGNED_LDST
    `ifdef UDB_MISALIGNED_SPLIT_STRATEGY_SEQUENTIAL_BYTES
        // A misaligned store or load straddling a page boundary, performed byte by byte, faults on the second page
        cp_ldst_straddle : cross priv_mode_vs, ldst, vsatp_paged, hgatp_paged, ldst_page_end, trap;
    `endif
    `endif
    `ifdef UDB_MXLEN_64
        `ifdef SVNAPOT_SUPPORTED
            cp_twostage_napot   : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, napot_page;
        `endif
        // A non-canonical guest virtual address raises a page fault, not a guest-page fault
        cp_twostage_canonical : cross priv_mode_vs_vu, access, va_noncanonical, page_fault;
        `ifdef UDB_REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT
            // A guest physical address from a VS-stage leaf or non-leaf PPN that is wider than the G-stage mode allows
            cp_twostage_gpa_width : cross priv_mode_vs, access, vsatp_paged, htval_gpa_wide, guest_page_fault;
        `endif
    `else
        `ifdef UDB_REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT
            // Sv32x4 translates 34-bit guest physical addresses
            cp_hgatp_sv32x4_gpa : cross priv_mode_vs, lw, vsatp_paged, hgatp_paged, htval_gpa_high;
        `endif
    `endif
endgroup

covergroup Sv_H_hlv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    hlv : coverpoint ins.current.insn {
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_wu = {HLVX_WU};
        wildcard bins hsv_w   = {HSV_W};
    }
    hlv_load : coverpoint ins.current.insn {
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_wu = {HLVX_WU};
    }
    hlvx : coverpoint ins.current.insn {
        wildcard bins hlvx_wu = {HLVX_WU};
    }
    // Each pair of VS-stage and G-stage modes with the same number of levels that the hart supports
    stage_modes : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode")[3:0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode")[3:0]} {
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            `ifdef UDB_SV39X4_TRANSLATION
                bins sv39_sv39x4 = {8'h88};
            `endif
        `endif
        `ifdef UDB_SV48_VSMODE_TRANSLATION
            `ifdef UDB_SV48X4_TRANSLATION
                bins sv48_sv48x4 = {8'h99};
            `endif
        `endif
        `ifdef UDB_SV57_VSMODE_TRANSLATION
            `ifdef UDB_SV57X4_TRANSLATION
                bins sv57_sv57x4 = {8'haa};
            `endif
        `endif
        `ifdef UDB_SV32_VSMODE_TRANSLATION
            `ifdef UDB_SV32X4_TRANSLATION
                bins sv32_sv32x4 = {8'h11};
            `endif
        `endif
    }
    // The load page fault (VS-stage) or load guest-page fault (G-stage) that HLVX takes on a non-executable page
    load_fault : coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
        bins page_fault       = {6'b101101};
        bins guest_page_fault = {6'b110101};
    }
    hstatus_spvp : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        bins vu = {0};
        bins vs = {1};
    }
    vsstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    sstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    sstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    // The pseudoinstruction that htinst holds after a guest-page fault on an implicit VS-stage access
    htinst_pseudo : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htinst", "htinst") iff (ins.current.csr_wb[CSR_HTINST]) {
        `ifdef UDB_MXLEN_64
            bins read  = {'h3000};
            `ifdef SVADU_SUPPORTED
                bins write = {'h3020};
            `endif
        `else
            bins read  = {'h2000};
            `ifdef SVADU_SUPPORTED
                bins write = {'h2020};
            `endif
        `endif
    }
    htinst_read : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htinst", "htinst") iff (ins.current.csr_wb[CSR_HTINST]) {
        `ifdef UDB_MXLEN_64
            bins read = {'h3000};
        `else
            bins read = {'h2000};
        `endif
    }
    `ifdef UDB_REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT
        // htval holds the guest physical address of the VS-stage root PTE, shifted right by 2
        htval_root : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htval", "htval") iff (ins.current.csr_wb[CSR_HTVAL]) {
            `ifdef UDB_MXLEN_64
                bins root = {[0:$]} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htval", "htval") >> 10) ==
                                         (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "vsatp") & 64'h00000fffffffffff));
            `else
                bins root = {[0:$]} iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htval", "htval") >> 10) ==
                                         (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "vsatp") & 32'h003fffff));
            `endif
        }
    `endif

    // hstatus.SPVP selects VU-level or VS-level access; vsstatus.SUM applies and sstatus.SUM does not
    cp_hlv_priv  : cross priv_mode_hs, hlv, stage_modes, hstatus_spvp, vsstatus_sum, sstatus_sum;
    // sstatus.MXR affects both stages, vsstatus.MXR only the VS-stage
    cp_hlv_mxr   : cross priv_mode_hs, hlv_load, stage_modes, vsstatus_mxr, sstatus_mxr;
    // HLVX needs execute permission in both stages, which neither MXR grants
    cp_hlvx_perm : cross priv_mode_hs, hlvx, stage_modes, vsstatus_mxr, sstatus_mxr, load_fault;
    // Guest-page faults on the implicit VS-stage page-table reads and A/D writes of HLV, HLVX and HSV
    cp_hlv_implicit : cross priv_mode_hs, hlv, stage_modes, htinst_pseudo;
    `ifdef UDB_REPORT_GPA_IN_HTVAL_ON_GUEST_PAGE_FAULT
        // A guest-page fault on the read of the VS-stage root table
        cp_hlv_root_gpf : cross priv_mode_hs, hlv, stage_modes, htinst_read, htval_root;
    `endif
endgroup

covergroup Sv_H_csr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    csrrs : coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
    }
    henvcfg : coverpoint ins.current.insn[31:20] {
        `ifdef UDB_MXLEN_64
            bins henvcfg = {CSR_HENVCFG};
        `else
            bins henvcfgh = {CSR_HENVCFGH};
        `endif
    }
    `ifdef UDB_MXLEN_64
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
        menvcfg_pbmte : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pbmte") {
            bins off = {0};
            `ifdef SVPBMT_SUPPORTED
                bins on  = {1};
            `endif
        }
        vsatp : coverpoint ins.current.insn[31:20] {
            bins vsatp = {CSR_VSATP};
        }
        hgatp : coverpoint ins.current.insn[31:20] {
            bins hgatp = {CSR_HGATP};
        }
        satp : coverpoint ins.current.insn[31:20] {
            bins satp = {CSR_SATP};
        }
        mode_written : coverpoint ins.current.rs1_val[63:60] {
            bins b[] = {[0:15]};
        }
        vsatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }
        hgatp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
            bins bare   = {0};
            bins sv39x4 = {8};
        }
        // In VS-mode, satp is vsatp
        satp_mode : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
            bins bare = {0};
            bins sv39 = {8};
        }

        // Each MODE written starting from Bare and Sv39 (Sv39x4)
        `ifdef UDB_SV39_VSMODE_TRANSLATION
            cp_vsatp_mode_field : cross priv_mode_hs, csrrw, vsatp, vsatp_mode, mode_written;
            cp_satp_mode_field  : cross priv_mode_vs, csrrw, satp, satp_mode, mode_written;
        `endif
        `ifdef UDB_SV39X4_TRANSLATION
            cp_hgatp_mode_field : cross priv_mode_hs, csrrw, hgatp, hgatp_mode, mode_written;
        `endif
        // Svpbmt is RV64-only, so menvcfgh.PBMTE and henvcfgh.PBMTE are read-only zero on RV32
        cp_henvcfg_menvcfg_pbmte : cross priv_mode_hs, csrrs, henvcfg, menvcfg_pbmte;
    `else
        menvcfg_adue : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "adue") {
            bins off = {0};
            `ifdef SVADU_SUPPORTED
                bins on  = {1};
            `endif
        }
    `endif

    // henvcfg.ADUE and PBMTE are read-only zero while the menvcfg bits are zero
    cp_henvcfg_menvcfg       : cross priv_mode_hs, csrrs, henvcfg, menvcfg_adue;
endgroup

// A fence after a VS-stage or G-stage leaf change, with x0 or a register in rs1 and rs2.  The test checks that the
// next guest access uses the new leaf.
covergroup Sv_H_fence_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    hfence_vvma : coverpoint ins.current.insn {
        wildcard bins hfence_vvma = {HFENCE_VVMA};
    }
    hfence_gvma : coverpoint ins.current.insn {
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }
    sfence_vma : coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
    }
    rs1 : coverpoint ins.current.insn[19:15] {
        bins x0       = {0};
        bins register = {[1:31]};
    }
    rs2 : coverpoint ins.current.insn[24:20] {
        bins x0       = {0};
        bins register = {[1:31]};
    }
    // An ID in rs2: the current vsatp.ASID or hgatp.VMID, or every ASIDMAX or VMIDMAX bit set
    rs2_asid : coverpoint ins.current.rs2_val iff (ins.current.insn[24:20] != 0) {
        bins current  = {[0:$]} iff (ins.current.rs2_val == get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "asid"));
        `ifdef UDB_MXLEN_64
            bins all_bits = {'hffff};
        `else
            bins all_bits = {'h1ff};
        `endif
    }
    rs2_vmid : coverpoint ins.current.rs2_val iff (ins.current.insn[24:20] != 0) {
        bins current  = {[0:$]} iff (ins.current.rs2_val == get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "vmid"));
        `ifdef UDB_MXLEN_64
            bins all_bits = {'h3fff};
        `else
            bins all_bits = {'h7f};
        `endif
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }

    cp_hfence_vvma   : cross priv_mode_hs, hfence_vvma, vsatp_paged, hgatp_paged, rs1, rs2;
    cp_hfence_gvma   : cross priv_mode_hs, hfence_gvma, vsatp_paged, hgatp_paged, rs1, rs2;
    cp_sfence_vma_vs : cross priv_mode_vs, sfence_vma, vsatp_paged, hgatp_paged, rs1, rs2;
    cp_hfence_vvma_asid   : cross priv_mode_hs, hfence_vvma, vsatp_paged, hgatp_paged, rs2_asid;
    cp_hfence_gvma_vmid   : cross priv_mode_hs, hfence_gvma, vsatp_paged, hgatp_paged, rs2_vmid;
    cp_sfence_vma_vs_asid : cross priv_mode_vs, sfence_vma, vsatp_paged, hgatp_paged, rs2_asid;
endgroup

// HSm group: two-stage address translation seen from M-mode through MPRV and MPV, and guest traps taken in M-mode
`ifndef EXCLUDE_SM
covergroup Sv_HSm_mprv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    load_store : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
    }
    lw : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    hlv_access : coverpoint ins.current.insn {
        wildcard bins lw    = {LW};
        wildcard bins sw    = {SW};
        wildcard bins hlv_w = {HLV_W};
        wildcard bins hsv_w = {HSV_W};
    }
    mprv : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins off = {0};
        bins on  = {1};
    }
    mprv_on : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mprv") {
        bins on = {1};
    }
    // {MPV, MPP}: the mode whose translation MPRV = 1 selects
    `ifdef UDB_MXLEN_64
        mpp_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `else
        mpp_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `endif
        bins m      = {3'b011};
        bins m_mpv1 = {3'b111};
        bins hs     = {3'b001};
        bins vs     = {3'b101};
        bins u      = {3'b000};
        bins vu     = {3'b100};
    }
    `ifdef UDB_MXLEN_64
        mpp_mpv_guest : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpv")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `else
        mpp_mpv_guest : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatush", "mpv")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mpp")[1:0]} {
    `endif
        bins vs = {3'b101};
        bins vu = {3'b100};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    vsatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins bare = {0};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_bare : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins bare = {0};
    }
    // The trap into M-mode that the access takes, if any.  Only a trap writes mcause on these instructions.
    trap : coverpoint {ins.current.csr_wb[CSR_MCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "mcause")[4:0]} {
        wildcard bins none = {6'b0?????};
        bins page_fault    = {6'b101101, 6'b101111};
    }
    vsstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    mstatus_sum : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "sum") {
        bins off = {0};
        bins on  = {1};
    }
    vsstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }
    mstatus_mxr : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
        bins off = {0};
        bins on  = {1};
    }

    // MPRV = 1 and MPV = 1 translate M-mode loads and stores through the VS-stage
    cp_vsatp_mprv_effects : cross priv_mode_m, load_store, mprv_on, mpp_mpv_guest, vsatp_paged, hgatp_bare, trap;
    // Loads and stores use the G-stage only with MPRV = 1 and MPV = 1; HLV and HSV always do
    cp_hgatp_mprv_effects : cross priv_mode_m, hlv_access, mprv, mpp_mpv, vsatp_bare, hgatp_paged;
    // With MPV = 1, vsstatus.SUM applies instead of mstatus.SUM
    cp_mprv_sum           : cross priv_mode_m, load_store, mprv_on, mpp_mpv_guest, vsatp_paged, hgatp_paged, vsstatus_sum, mstatus_sum;
    // mstatus.MXR makes execute-only pages readable in both stages, vsstatus.MXR only in the VS-stage
    cp_mprv_mxr           : cross priv_mode_m, lw, mprv_on, mpp_mpv_guest, vsatp_paged, hgatp_paged, vsstatus_mxr, mstatus_mxr;
endgroup

covergroup Sv_HSm_trap_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    access : coverpoint ins.current.insn {
        wildcard bins lw   = {LW};
        wildcard bins sw   = {SW};
        wildcard bins jalr = {JALR};
    }
    vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
        bins paged = {[1:15]};
    }
    hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
        bins paged = {[1:15]};
    }
    trap : coverpoint {ins.current.csr_wb[CSR_MCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "mcause")[4:0]} {
        bins page_fault       = {6'b101100, 6'b101101, 6'b101111};
        bins guest_page_fault = {6'b110100, 6'b110101, 6'b110111};
    }
    // The trap records a guest virtual address and that it came from V = 1
    `ifdef UDB_MXLEN_64
        gva_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "gva")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mpv")[0]} {
    `else
        gva_mpv : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "gva")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatush", "mpv")[0]} {
    `endif
        bins guest = {2'b11};
    }
    // The pseudoinstruction that mtinst holds after a guest-page fault on an implicit VS-stage access
    mtinst_pseudo : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtinst", "mtinst") iff (ins.current.csr_wb[CSR_MTINST]) {
        `ifdef UDB_MXLEN_64
            bins read = {'h3000};
        `else
            bins read = {'h2000};
        `endif
    }

    jalr : coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    ldst : coverpoint ins.current.insn {
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
    }
    // A fetch at the last halfword of a page, or a word two bytes below the end of a page
    page_end : coverpoint ((ins.current.rs1_val + ins.current.imm) & 'hFFF) {
        bins page_end = {'hFFE};
    }
    guest_page_fault : coverpoint {ins.current.csr_wb[CSR_MCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "mcause")[4:0]} {
        bins guest_page_fault = {6'b110100, 6'b110101, 6'b110111};
    }
    // A nonzero mtval2 holding the guest physical address of a page boundary >> 2: the faulting second portion
    mtval2_page_boundary : coverpoint ((get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval2", "mtval2") << 2) & 'hFFF)
                           iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mtval2", "mtval2") != 0) {
        bins page_boundary = {0};
    }

    // Guest page faults and guest-page faults taken in M-mode (mtval2 and mtinst are in the trap signature)
    cp_guest_page_fault_m : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, trap, gva_mpv;
    cp_implicit_gpf_m     : cross priv_mode_vs_vu, access, vsatp_paged, hgatp_paged, mtinst_pseudo;
    // A fetch, or a misaligned store or load performed byte by byte, whose second page has an invalid G-stage leaf
    `ifdef ZCA_SUPPORTED
        cp_straddle_m      : cross priv_mode_vs_vu, jalr, vsatp_paged, hgatp_paged, page_end, guest_page_fault, mtval2_page_boundary;
    `endif
    `ifdef UDB_MISALIGNED_LDST
    `ifdef UDB_MISALIGNED_SPLIT_STRATEGY_SEQUENTIAL_BYTES
        cp_ldst_straddle_m : cross priv_mode_vs_vu, ldst, vsatp_paged, hgatp_paged, page_end, guest_page_fault, mtval2_page_boundary;
    `endif
    `endif
endgroup
`endif // EXCLUDE_SM

`ifdef SV_HZICBO_ANY
// HZicbo group: cache-block operations from VS-mode and VU-mode, the henvcfg enables, and each VS-stage and G-stage
// PTE under two-stage translation
covergroup Sv_HZicbo_cg with function sample(ins_t ins);
  option.per_instance = 0;
  `include "general/RISCV_coverage_standard_coverpoints.svh"

  cbo: coverpoint ins.current.insn {
    `ifdef ZICBOM_SUPPORTED
      wildcard bins clean = {CBO_CLEAN};
      wildcard bins flush = {CBO_FLUSH};
      wildcard bins inval = {CBO_INVAL};
    `endif
    `ifdef ZICBOZ_SUPPORTED
      wildcard bins zero = {CBO_ZERO};
    `endif
  }
  vsatp_paged: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
    bins paged = {[1:15]};
  }
  hgatp_paged: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
    bins paged = {[1:15]};
  }
  // The superpage of the guest virtual address: VS-stage cases use VS_SV39/VS_SV32 data_va, and G-stage cases
  // SV39X4/SV32X4 data_va through a VS-stage identity superpage
  `ifdef UDB_MXLEN_64
    vs_stage: coverpoint ins.current.rs1_val[63:30] {
      bins vs = {5};
    }
    g_stage: coverpoint ins.current.rs1_val[63:30] {
      bins g = {11};
    }
  `else
    vs_stage: coverpoint ins.current.rs1_val[31:22] {
      bins vs = {'h241};
    }
    g_stage: coverpoint ins.current.rs1_val[31:22] {
      bins g = {'h341};
    }
  `endif

  // The trap the CBO takes, from the scause the trace shows it writing
  vs_pte_outcome: coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
    wildcard bins no_fault = {6'b0?????};
    bins store_page_fault  = {6'b101111};
  }
  g_pte_outcome: coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
    wildcard bins no_fault       = {6'b0?????};
    bins store_guest_page_fault  = {6'b110111};
  }
  gpa_outcome: coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
    bins store_guest_page_fault = {6'b110111};
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
      bins store_access_fault   = {6'b100111};
    `endif
  }
  no_fault: coverpoint ins.current.csr_wb[CSR_SCAUSE] {
    bins no_fault = {0};
  }
  store_access_fault: coverpoint {ins.current.csr_wb[CSR_SCAUSE], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "scause", "scause")[4:0]} {
    bins store_access_fault = {6'b100111};
  }
  // htinst holds the pseudoinstruction of a guest-page fault on an implicit VS-stage page-table read
  pseudoinstruction: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "htinst", "htinst") iff (ins.current.csr_wb[CSR_HTINST]) {
    bins read = {'h2000, 'h3000};
  }
  // In VS-mode the trace logs vsstatus as sstatus
  vsstatus_sum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum") {
    bins set = {1};
  }

  cp_vs_pte:          cross priv_mode_vs_vu, cbo, vs_stage, vs_pte_outcome, vsatp_paged, hgatp_paged;
  cp_vs_sum:          cross priv_mode_vs, cbo, vs_stage, vsstatus_sum, no_fault;
  cp_vs_gpa:          cross priv_mode_vs_vu, cbo, vs_stage, gpa_outcome;
  cp_vs_gpa_implicit: cross priv_mode_vs_vu, cbo, vs_stage, pseudoinstruction;
  cp_g_pte:           cross priv_mode_vs_vu, cbo, g_stage, g_pte_outcome, vsatp_paged, hgatp_paged;
  `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
    cp_g_pa:          cross priv_mode_vs_vu, cbo, g_stage, store_access_fault;
  `endif

  // A prefetch is a HINT, so it raises no exception even where a load or store would fault in either stage
  `ifdef ZICBOP_SUPPORTED
    prefetch: coverpoint ins.current.insn {
      wildcard bins prefetch_i = {PREFETCH_I};
      wildcard bins prefetch_r = {PREFETCH_R};
      wildcard bins prefetch_w = {PREFETCH_W};
    }
    cp_vs_prefetch: cross priv_mode_vs_vu, prefetch, vs_stage, vsatp_paged, hgatp_paged, no_fault;
    cp_g_prefetch:  cross priv_mode_vs_vu, prefetch, g_stage, vsatp_paged, hgatp_paged, no_fault;
  `endif

  // CBOs in VS-mode and VU-mode across the menvcfg, henvcfg and senvcfg enables, with translation Bare
  inval: coverpoint ins.current.insn {
    wildcard bins inval = {CBO_INVAL};
  }
  clean_flush: coverpoint ins.current.insn {
    wildcard bins clean = {CBO_CLEAN};
    wildcard bins flush = {CBO_FLUSH};
  }
  zero: coverpoint ins.current.insn {
    wildcard bins zero = {CBO_ZERO};
  }
  menvcfg_cbie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "cbie") {
    bins off   = {2'b00};
    bins flush = {2'b01};
    bins inval = {2'b11};
  }
  henvcfg_cbie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "cbie") {
    bins off   = {2'b00};
    bins flush = {2'b01};
    bins inval = {2'b11};
  }
  senvcfg_cbie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "cbie") {
    bins off   = {2'b00};
    bins flush = {2'b01};
    bins inval = {2'b11};
  }
  menvcfg_cbcfe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "cbcfe") {
    bins off = {0};
    bins on  = {1};
  }
  henvcfg_cbcfe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "cbcfe") {
    bins off = {0};
    bins on  = {1};
  }
  senvcfg_cbcfe: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "cbcfe") {
    bins off = {0};
    bins on  = {1};
  }
  menvcfg_cbze: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "cbze") {
    bins off = {0};
    bins on  = {1};
  }
  henvcfg_cbze: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "cbze") {
    bins off = {0};
    bins on  = {1};
  }
  senvcfg_cbze: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "senvcfg", "cbze") {
    bins off = {0};
    bins on  = {1};
  }
  vsatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
    bins bare = {0};
  }

  `ifdef ZICBOM_SUPPORTED
    cp_cbie_vs:  cross priv_mode_vs, inval, menvcfg_cbie, henvcfg_cbie, vsatp_bare;
    cp_cbie_vu:  cross priv_mode_vu, inval, menvcfg_cbie, henvcfg_cbie, senvcfg_cbie, vsatp_bare;
    cp_cbcfe_vs: cross priv_mode_vs, clean_flush, menvcfg_cbcfe, henvcfg_cbcfe, vsatp_bare;
    cp_cbcfe_vu: cross priv_mode_vu, clean_flush, menvcfg_cbcfe, henvcfg_cbcfe, senvcfg_cbcfe, vsatp_bare;
  `endif
  `ifdef ZICBOZ_SUPPORTED
    cp_cbze_vs:  cross priv_mode_vs, zero, menvcfg_cbze, henvcfg_cbze, vsatp_bare;
    cp_cbze_vu:  cross priv_mode_vu, zero, menvcfg_cbze, henvcfg_cbze, senvcfg_cbze, vsatp_bare;
  `endif
endgroup


`endif // SV_HZICBO_ANY

`endif // H_SUPPORTED

function void sv_sample(int hart, int issue, ins_t ins);
    Sv_satp_cg.sample(ins);
    Sv_VA_cg.sample(ins);
    Sv_sfence_cg.sample(ins);
    Sv_vm_permissions_cg.sample(ins);
    Sv_res_global_pte_cg.sample(ins);
    Sv_add_feature_cg.sample(ins);
`ifndef EXCLUDE_SM
    Sv_Sm_satp_cg.sample(ins);
    Sv_Sm_mstatus_mprv_cg.sample(ins);
`endif // EXCLUDE_SM
`ifdef SV_ZICBO_ANY
    Sv_Zicbo_cg.sample(ins);
`endif // SV_ZICBO_ANY
    Sv_Exceptions_cg.sample(ins);
`ifndef EXCLUDE_SM
    Sv_ExceptionsSm_cg.sample(ins);
`endif // EXCLUDE_SM
`ifdef ZAAMO_SUPPORTED
    Sv_ExceptionsZaamo_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Sv_ExceptionsZaamoSm_cg.sample(ins);
    `endif // EXCLUDE_SM
`endif // ZAAMO_SUPPORTED
`ifdef ZALRSC_SUPPORTED
    Sv_ExceptionsZalrsc_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Sv_ExceptionsZalrscSm_cg.sample(ins);
    `endif // EXCLUDE_SM
`endif // ZALRSC_SUPPORTED
`ifdef H_SUPPORTED
    Sv_H_vsstage_cg.sample(ins);
    Sv_H_gstage_cg.sample(ins);
    Sv_H_twostage_cg.sample(ins);
    Sv_H_hlv_cg.sample(ins);
    Sv_H_csr_cg.sample(ins);
    Sv_H_fence_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Sv_HSm_mprv_cg.sample(ins);
        Sv_HSm_trap_cg.sample(ins);
    `endif // EXCLUDE_SM
    `ifdef SV_HZICBO_ANY
        Sv_HZicbo_cg.sample(ins);
    `endif // SV_HZICBO_ANY
`endif // H_SUPPORTED
endfunction
