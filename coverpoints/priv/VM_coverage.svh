///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_VM
`define SVNAPOT_SUPPORTED
covergroup VM_satp_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    `ifdef XLEN64
        mode_supported: coverpoint ins.current.csr[12'h180][63:60] { //sat.2
            `ifdef SV57
                bins sv57 = {4'b1010};
            `endif
            `ifdef SV48
                bins sv48 = {4'b1001};
            `endif
            `ifdef SV39
                bins sv39 = {4'b1000};
            `endif
        }
        bare_mode: coverpoint ins.current.csr[12'h180][63:60] { //bare.1
            bins bare   = {4'b0000};
        }
    `else
        mode_supported: coverpoint ins.current.csr[12'h180][31] {
            bins sv32 = {1'b1};
        }
        bare_mode: coverpoint ins.current.csr[12'h180][31] {
            bins bare = {1'b0};
        }
    `endif

    `ifdef XLEN64
        satp_PPN: coverpoint ins.current.csr[12'h180][43:0] { //sat.4
            bins all_zeros  = {44'b00000000000000000000000000000000000000000000};
            bins walking_0  = {44'b00000000000000000000000000000000000000000001};
            bins walking_1  = {44'b00000000000000000000000000000000000000000010};
            bins walking_2  = {44'b00000000000000000000000000000000000000000100};
            bins walking_3  = {44'b00000000000000000000000000000000000000001000};
            bins walking_4  = {44'b00000000000000000000000000000000000000010000};
            bins walking_5  = {44'b00000000000000000000000000000000000000100000};
            bins walking_6  = {44'b00000000000000000000000000000000000001000000};
            bins walking_7  = {44'b00000000000000000000000000000000000010000000};
            bins walking_8  = {44'b00000000000000000000000000000000000100000000};
            bins walking_9  = {44'b00000000000000000000000000000000001000000000};
            bins walking_10 = {44'b00000000000000000000000000000000010000000000};
            bins walking_11 = {44'b00000000000000000000000000000000100000000000};
            bins walking_12 = {44'b00000000000000000000000000000001000000000000};
            bins walking_13 = {44'b00000000000000000000000000000010000000000000};
            bins walking_14 = {44'b00000000000000000000000000000100000000000000};
            bins walking_15 = {44'b00000000000000000000000000001000000000000000};
            bins walking_16 = {44'b00000000000000000000000000010000000000000000};
            bins walking_17 = {44'b00000000000000000000000000100000000000000000};
            bins walking_18 = {44'b00000000000000000000000001000000000000000000};
            bins walking_19 = {44'b00000000000000000000000010000000000000000000};
            bins walking_20 = {44'b00000000000000000000000100000000000000000000};
            bins walking_21 = {44'b00000000000000000000001000000000000000000000};
            bins walking_22 = {44'b00000000000000000000010000000000000000000000};
            bins walking_23 = {44'b00000000000000000000100000000000000000000000};
            bins walking_24 = {44'b00000000000000000001000000000000000000000000};
            bins walking_25 = {44'b00000000000000000010000000000000000000000000};
            bins walking_26 = {44'b00000000000000000100000000000000000000000000};
            bins walking_27 = {44'b00000000000000001000000000000000000000000000};
            bins walking_28 = {44'b00000000000000010000000000000000000000000000};
            bins walking_29 = {44'b00000000000000100000000000000000000000000000};
            bins walking_30 = {44'b00000000000001000000000000000000000000000000};
            bins walking_31 = {44'b00000000000010000000000000000000000000000000};
            bins walking_32 = {44'b00000000000100000000000000000000000000000000};
            bins walking_33 = {44'b00000000001000000000000000000000000000000000};
            bins walking_34 = {44'b00000000010000000000000000000000000000000000};
            bins walking_35 = {44'b00000000100000000000000000000000000000000000};
            bins walking_36 = {44'b00000001000000000000000000000000000000000000};
            bins walking_37 = {44'b00000010000000000000000000000000000000000000};
            bins walking_38 = {44'b00000100000000000000000000000000000000000000};
            bins walking_39 = {44'b00001000000000000000000000000000000000000000};
            bins walking_40 = {44'b00010000000000000000000000000000000000000000};
            bins walking_41 = {44'b00100000000000000000000000000000000000000000};
            bins walking_42 = {44'b01000000000000000000000000000000000000000000};
            bins walking_43 = {44'b10000000000000000000000000000000000000000000};
            bins all_ones   = {44'b11111111111111111111111111111111111111111111};
        }
    `else
        satp_PPN: coverpoint ins.current.csr[12'h180][21:0] {
            bins all_zeros  = {22'b0000000000000000000000};
            bins walking_0  = {22'b0000000000000000000001};
            bins walking_1  = {22'b0000000000000000000010};
            bins walking_2  = {22'b0000000000000000000100};
            bins walking_3  = {22'b0000000000000000001000};
            bins walking_4  = {22'b0000000000000000010000};
            bins walking_5  = {22'b0000000000000000100000};
            bins walking_6  = {22'b0000000000000001000000};
            bins walking_7  = {22'b0000000000000010000000};
            bins walking_8  = {22'b0000000000000100000000};
            bins walking_9  = {22'b0000000000001000000000};
            bins walking_10 = {22'b0000000000010000000000};
            bins walking_11 = {22'b0000000000100000000000};
            bins walking_12 = {22'b0000000001000000000000};
            bins walking_13 = {22'b0000000010000000000000};
            bins walking_14 = {22'b0000000100000000000000};
            bins walking_15 = {22'b0000001000000000000000};
            bins walking_16 = {22'b0000010000000000000000};
            bins walking_17 = {22'b0000100000000000000000};
            bins walking_18 = {22'b0001000000000000000000};
            bins walking_19 = {22'b0010000000000000000000};
            bins walking_20 = {22'b0100000000000000000000};
            bins walking_21 = {22'b1000000000000000000000};
            bins all_ones   = {22'b1111111111111111111111};
        }
    `endif

    `ifdef XLEN64
        satp_asid_PPN: coverpoint ins.current.csr[12'h180][59:0] {
            bins all_zero = {60'd0};
            bins not_zero = {[1:$]};
        }
    `else
        satp_asid_PPN: coverpoint ins.current.csr[12'h180][30:0] {
            bins all_zero = {31'd0};
            bins not_zero = {[1:$]};
        }
    `endif

    `ifdef XLEN64
        asid_length: coverpoint ins.current.csr[12'h180][59:44] { //sat.5
            bins values = {16'h0001, 16'h0002, 16'h0004, 16'h0008, 16'h0010, 16'h0020, 16'h0040, 16'h0080, 16'h0100, 16'h0200, 16'h0400, 16'h0800, 16'h1000, 16'h2000, 16'h0400, 16'h8000};
        }
    `else
        asid_length: coverpoint ins.current.csr[12'h180][30:22] {
            bins values = {9'h001, 9'h002, 9'h004, 9'h008, 9'h010, 9'h020, 9'h040, 9'h080, 9'h100};
        }
    `endif

    tvm_mstatus: coverpoint ins.current.csr[12'h300][20]{
        bins zero = {0};
    }

    Mcause: coverpoint ins.current.csr[12'h342][31:0] {
        bins illegal_ins  = {32'd2};
        bins no_exception = {32'd0};
    }

    ins: coverpoint ins.current.insn {
        wildcard bins csrrs = {32'b000110000000_?????_010_?????_1110011};
        wildcard bins csrrw = {32'b000110000000_?????_001_?????_1110011};
        wildcard bins csrrc = {32'b000110000000_?????_011_?????_1110011};
    }

    satp_bare: cross bare_mode, satp_asid_PPN;

    access_u: cross priv_mode_u, Mcause, tvm_mstatus { //sat.1
        ignore_bins ig1 = binsof(Mcause.no_exception);
    }
    access_m_s: cross priv_mode_ms, ins, Mcause, tvm_mstatus { //sat.1
        ignore_bins ig1 = binsof(Mcause.illegal_ins);
    }
endgroup

covergroup VM_PA_VA_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `ifdef XLEN64
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

    `ifdef XLEN64
        mode_supported: coverpoint ins.current.csr[12'h180][63:60] {
            `ifdef SV57
                bins sv57 = {4'b1010};
            `endif
            `ifdef SV48
                bins sv48 = {4'b1001};
            `endif
            `ifdef SV39
                bins sv39 = {4'b1000};
            `endif
        }
    `else
        mode_supported: coverpoint ins.current.csr[12'h180][31] {
            bins sv32 = {1'b1};
        }
    `endif

    VA_i_mode: cross mode_supported, VA_i;
    VA_d_mode: cross mode_supported, VA_d;

endgroup

covergroup VM_sfence_cg with function sample(ins_t ins); //sf.1
    option.per_instance = 0;
    ins: coverpoint ins.current.insn {
        wildcard bins sfence = {32'b0001001_?????_?????_000_00000_1110011};
    }
endgroup

covergroup VM_mstatus_mprv_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    tvm_mstatus: coverpoint ins.current.csr[12'h300][20] {
        bins set = {1};
    }
    Mcause: coverpoint ins.current.csr[12'h342][31:0] {
        bins illegal_ins = {32'd2};
    }
    ins: coverpoint ins.current.insn {
        wildcard bins csrrs  = {32'b000110000000_?????_010_?????_1110011};
        wildcard bins csrrw  = {32'b000110000000_?????_001_?????_1110011};
        wildcard bins csrrc  = {32'b000110000000_?????_011_?????_1110011};
        wildcard bins sfence = {32'b0001001_?????_?????_000_00000_1110011};
    }

    tvm_exception_s: cross tvm_mstatus, priv_mode_s, Mcause, ins; //ms.1

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
        satp_mode: coverpoint ins.current.csr[12'h180][63:60] {
            `ifdef SV57
                bins sv57 = {4'b1010};
            `endif
            `ifdef SV48
                bins sv48 = {4'b1001};
            `endif
            `ifdef SV39
                bins sv39 = {4'b1000};
            `endif
            bins bare = {4'b0000};
        }
    `else
        satp_mode: coverpoint ins.current.csr[12'h180][31] {
            bins sv32 = {1'b1};
            bins bare = {1'b0};
        }
    `endif

    mprv_load:  cross mprv_mstatus, mpp_mstatus, read_acc,  priv_mode_m, satp_mode; //ms.2
    mprv_store: cross mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m, satp_mode; //ms.2
    mprv_ins:   cross mprv_mstatus, mpp_mstatus, exec_acc,  priv_mode_m, satp_mode; //ms.2

    PTE_upage_i: coverpoint ins.current.pte_i[7:0] { //ms.3 & 4
        wildcard bins leaflvl_u = {8'b11?11111};
    }
    PTE_upage_d: coverpoint ins.current.pte_d[7:0] { //ms.3 & 4
        wildcard bins leaflvl_u = {8'b11?11111};
    }

    `ifdef XLEN64
        PageType_i: coverpoint ins.current.page_type_i {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
        PageType_d: coverpoint ins.current.page_type_d {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
    `else
        PageType_i: coverpoint ins.current.page_type_i {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
        }
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
        }
    `endif

    load_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins load_page_fault = {32'd13};
    }
    ins_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins ins_page_fault = {32'd12};
    }
    store_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins store_amo_page_fault = {32'd15};
    }
    sum_sstatus: coverpoint ins.current.csr[12'h100][18]{
        bins notset = {0};
        bins set = {1};
    }

    mprv_upage_smode_sumunset_noread: cross mprv_mstatus, mpp_mstatus, read_acc, priv_mode_m, PTE_upage_d, PageType_d, load_page_fault, sum_sstatus { //ms.3
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig5 = binsof(sum_sstatus.set);
    }
    mprv_upage_smode_sumunset_nowrite: cross mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m, PTE_upage_d, PageType_d, store_page_fault, sum_sstatus { //ms.3
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig5 = binsof(sum_sstatus.set);
    }
    mprv_upage_smode_sumunset_noexec: cross mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m, PageType_i, sum_sstatus { //ms.3
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.set);
    }
    mprv_upage_smode_sumset_exec: cross mprv_mstatus, mpp_mstatus, exec_acc, priv_mode_m, PageType_i, sum_sstatus  { //ms.4
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.notset);
    }
    mprv_upage_smode_sumset_read: cross mprv_mstatus, mpp_mstatus, read_acc, priv_mode_m, PTE_upage_d, PageType_d, sum_sstatus { //ms.4
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.notset);
    }
    mprv_upage_smode_sumset_write: cross mprv_mstatus, mpp_mstatus, write_acc, priv_mode_m, PTE_upage_d, PageType_d, sum_sstatus { //ms.4
        ignore_bins ig1 = binsof(mpp_mstatus.U_mode);
        ignore_bins ig3 = binsof(sum_sstatus.notset);
    }

    PTE_sbe_d: coverpoint ins.current.pte_d[7:0] { //ms.5
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    `ifdef XLEN64
        sbe_mstatus: coverpoint ins.current.csr[12'h300][36] { //ms.5
            bins set = {1};
            bins not_set = {0};
        }
    `else
        sbe_mstatus: coverpoint ins.current.csr[12'h310][4] { //ms.5
            bins set = {1};
            bins not_set = {0};
        }
    `endif

    mstatus_sbe_read: cross read_acc, PTE_sbe_d, PageType_d, sbe_mstatus; //ms.5
    mstatus_sbe_write: cross write_acc, PTE_sbe_d, PageType_d, sbe_mstatus; //ms.5

endgroup

covergroup VM_vm_permissions_cg with function sample(ins_t ins);
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

    `ifdef XLEN64
        PageType_i: coverpoint ins.current.page_type_i {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
        PageType_d: coverpoint ins.current.page_type_d {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
    `else
        PageType_i: coverpoint ins.current.page_type_i {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
        }
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
        }
    `endif

    `ifdef XLEN64
        misaligned_PPN_i: coverpoint ins.current.page_type_i {
            `ifdef SV48
                bins sv48_tera_misaligned = {2'b11} iff ((ins.current.ppn_i[26:0] != 27'b0) && (ins.current.csr[12'h180][63:60] == 4'b1001));
                bins sv48_giga_misaligned = {2'b10} iff ((ins.current.ppn_i[17:0] != 18'b0) && (ins.current.csr[12'h180][63:60] == 4'b1001));
                bins sv48_mega_misaligned = {2'b01} iff ((ins.current.ppn_i[8:0]  !=  9'b0) && (ins.current.csr[12'h180][63:60] == 4'b1001));
            `endif
            `ifdef SV39
                bins sv39_giga_misaligned = {2'b10} iff ((ins.current.ppn_i[17:0] != 18'b0) && (ins.current.csr[12'h180][63:60] == 4'b1000));
                bins sv39_mega_misaligned = {2'b01} iff ((ins.current.ppn_i[8:0]  !=  9'b0) && (ins.current.csr[12'h180][63:60] == 4'b1000));
            `endif
        }
        misaligned_PPN_d: coverpoint ins.current.page_type_d {
            `ifdef SV48
                bins sv48_tera_misaligned = {2'b11} iff ((ins.current.ppn_d[26:0] != 27'b0) && (ins.current.csr[12'h180][63:60] == 4'b1001));
                bins sv48_giga_misaligned = {2'b10} iff ((ins.current.ppn_d[17:0] != 18'b0) && (ins.current.csr[12'h180][63:60] == 4'b1001));
                bins sv48_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[8:0]  !=  9'b0) && (ins.current.csr[12'h180][63:60] == 4'b1001));
            `endif
            `ifdef SV39
                bins sv39_giga_misaligned = {2'b10} iff ((ins.current.ppn_d[17:0] != 18'b0) && (ins.current.csr[12'h180][63:60] == 4'b1000));
                bins sv39_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[8:0]  !=  9'b0) && (ins.current.csr[12'h180][63:60] == 4'b1000));
            `endif
        }
    `else
        misaligned_PPN_i: coverpoint ins.current.page_type_i {
            bins sv32_mega_misaligned = {2'b01} iff ((ins.current.ppn_i[9:0] != 10'b0) && (ins.current.csr[12'h180][31] == 1'b1));
        }
        misaligned_PPN_d: coverpoint ins.current.page_type_d {
            bins sv32_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[9:0] != 10'b0) && (ins.current.csr[12'h180][31] == 1'b1));
        }
    `endif

    // satp.mode for coverage of SV32, SV39, SV48 & SV57
    `ifdef XLEN64
        mode: coverpoint ins.current.csr[12'h180][63:60] {
            `ifdef SV57
                bins sv57 = {4'b1010};
            `endif
            `ifdef SV48
                bins sv48 = {4'b1001};
            `endif
            `ifdef SV39
                bins sv39 = {4'b1000};
            `endif
        }
    `else
        mode: coverpoint ins.current.csr[12'h180][31] {
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
    load_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins load_page_fault = {32'd13};
    }
    ins_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins ins_page_fault = {32'd12};
    }
    store_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
        bins store_amo_page_fault = {32'd15};
    }
    Nopagefault: coverpoint  ins.current.csr[12'h343]{
        bins no_fault  = {64'd0};
    }
    kilo_page_i: coverpoint ins.current.page_type_i {
        bins kilo_page = {2'b00};
    }
    kilo_page_d: coverpoint ins.current.page_type_d {
        bins kilo_page = {2'b00};
    }
    sum_sstatus: coverpoint ins.current.csr[12'h100][18]{
        bins notset = {0};
        bins set = {1};
    }
    mxr_sstatus: coverpoint ins.current.csr[12'h100][19] {
        bins notset = {0};
        bins set = {1};
    }

    PTE_inv_exec_s_i: cross PTE_i_inv, PageType_i, ins_page_fault, priv_mode_s, exec_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_i_inv.leaflvl_u);
    }
    PTE_inv_exec_u_i: cross PTE_i_inv, PageType_i, ins_page_fault, priv_mode_u, exec_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_i_inv.leaflvl_s);
    }

    PTE_inv_read_s_d: cross PTE_d_inv, PageType_d, load_page_fault, priv_mode_s, read_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_u_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_u_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_s_w);
    }
    PTE_inv_read_u_d: cross PTE_d_inv, PageType_d, load_page_fault, priv_mode_u, read_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_s_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_s_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_u_w);
    }

    PTE_inv_write_s_d: cross PTE_d_inv, PageType_d, store_page_fault, priv_mode_s, write_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_u_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_u_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_s_r);
    }
    PTE_inv_write_u_d: cross PTE_d_inv, PageType_d, store_page_fault, priv_mode_u, write_acc { //pte.2
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_s_r);
        ignore_bins ig2 = binsof(PTE_d_inv.leaflvl_s_w);
        ignore_bins ig3 = binsof(PTE_d_inv.leaflvl_u_r);
    }

    PTE_res_rwx_s_i_exec: cross PTE_i_res_rwx, PageType_i, ins_page_fault, priv_mode_s, exec_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_i_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_i_res_rwx.leaflvl_noexec_u);
    }
    PTE_res_rwx_u_i_exec: cross PTE_i_res_rwx, PageType_i, ins_page_fault, priv_mode_u, exec_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_i_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_i_res_rwx.leaflvl_noexec_s);
    }

    PTE_res_rwx_s_d_read: cross PTE_d_res_rwx, PageType_d, load_page_fault, priv_mode_s, read_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_u);
    }
    PTE_res_rwx_u_d_read: cross PTE_d_res_rwx, PageType_d, load_page_fault, priv_mode_u, read_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_s);
    }

    PTE_res_rwx_s_d_write: cross PTE_d_res_rwx, PageType_d, store_page_fault, priv_mode_s, write_acc { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_u);
    }
    PTE_res_rwx_u_d_write: cross PTE_d_res_rwx, PageType_d, store_page_fault, priv_mode_u, write_acc  { //pte.3
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_s);
    }

    PTE_nonleaf_lvl0_s_i_exec: cross PTE_nonleaf_lvl0_i, kilo_page_i, mode, ins_page_fault, priv_mode_s, exec_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_i.lvl0_u);
    }
    PTE_nonleaf_lvl0_u_i_exec: cross PTE_nonleaf_lvl0_i, kilo_page_i, mode, ins_page_fault, priv_mode_u, exec_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_i.lvl0_s);
    }
    PTE_nonleaf_lvl0_s_d_read: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, load_page_fault, priv_mode_s, read_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_u);
    }
    PTE_nonleaf_lvl0_u_d_read: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, load_page_fault, priv_mode_u, read_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_s);
    }
    PTE_nonleaf_lvl0_s_d_write: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, store_page_fault, priv_mode_s, write_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_u);
    }
    PTE_nonleaf_lvl0_u_d_write: cross PTE_nonleaf_lvl0_d, kilo_page_d, mode, store_page_fault, priv_mode_u, write_acc { //pte.4
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_s);
    }

    spage_exec_s_i: cross PTE_x_spage_i, PageType_i, exec_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_x_spage_i.leaflvl_x_0);
    }
    spage_noexec_s_i: cross PTE_x_spage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_x_spage_i.leaflvl_x_1);
    }

    spage_read_s_d: cross PTE_rw_spage_d, PageType_d, read_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_w_1);
    }
    spage_noread_s_d: cross PTE_rw_spage_d, PageType_d, load_page_fault, read_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_1);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_w_1);
    }

    spage_write_s_d: cross PTE_rw_spage_d, PageType_d, write_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_r_1);
    }
    spage_nowrite_s_d: cross PTE_rw_spage_d, PageType_d, store_page_fault, write_acc, priv_mode_s, sum_sstatus { //pte.5 & 6
        ignore_bins ig1 = binsof(PTE_rw_spage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_spage_d.leaflvl_r_1);
        ignore_bins ig3 = binsof(PTE_rw_spage_d.leaflvl_w_1);
    }

    spage_rwx_s_i_noexec:  cross PTE_spage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_u; //pte.7
    spage_rwx_s_d_noread:  cross PTE_spage_d, PageType_d, load_page_fault, read_acc, priv_mode_u; //pte.7
    spage_rwx_s_d_nowrite: cross PTE_spage_d, PageType_d, store_page_fault, write_acc, priv_mode_u; //pte.7

    upage_smode_sumunset_noexec_s: cross PTE_upage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_s, sum_sstatus { //pte.8
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }
    upage_smode_sumunset_noread_s: cross PTE_upage_d, PageType_d, load_page_fault, read_acc, priv_mode_s, sum_sstatus { //pte.8
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }
    upage_smode_sumunset_nowrite_s: cross PTE_upage_d, PageType_d, store_page_fault, write_acc, priv_mode_s, sum_sstatus { //pte.8
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }

    upage_smode_sumset_noexec_s: cross PTE_upage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_s, sum_sstatus  { //pte.9
        ignore_bins ig1 = binsof(sum_sstatus.notset);
    }
    upage_smode_sumset_read_s: cross PTE_upage_d, PageType_d, read_acc, priv_mode_s, sum_sstatus  { //pte.9
        ignore_bins ig1 = binsof(sum_sstatus.notset);
    }
    upage_smode_sumset_write_s: cross PTE_upage_d, PageType_d, write_acc, priv_mode_s, sum_sstatus  { //pte.9
        ignore_bins ig1 = binsof(sum_sstatus.notset);
    }

    upage_umode_exec_u: cross PTE_x_upage_i, PageType_i, exec_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_x_upage_i.leaflvl_x_0);
    }
    upage_umode_noexec_u: cross PTE_x_upage_i, PageType_i, ins_page_fault, exec_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_x_upage_i.leaflvl_x_1);
    }

    upage_umode_read_u: cross PTE_rw_upage_d, PageType_d, read_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_w_1);
    }
    upage_umode_noread_u: cross PTE_rw_upage_d, PageType_d, load_page_fault, read_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_1);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_w_1);
    }

    upage_umode_write_u: cross PTE_rw_upage_d, PageType_d, write_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_w_0);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_r_1);
    }
    upage_umode_nowrite_u: cross PTE_rw_upage_d, PageType_d, store_page_fault, write_acc, priv_mode_u { //pte.10
        ignore_bins ig1 = binsof(PTE_rw_upage_d.leaflvl_r_0);
        ignore_bins ig2 = binsof(PTE_rw_upage_d.leaflvl_r_1);
        ignore_bins ig3 = binsof(PTE_rw_upage_d.leaflvl_w_1);
    }

    xpage_mxrunset_read_s: cross PTE_XnoRW_d, PageType_d, load_page_fault, read_acc, mxr_sstatus, priv_mode_s { //pte.11
        ignore_bins ig1 = binsof(mxr_sstatus.set);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_u);
    }
    xpage_mxrunset_read_u: cross PTE_XnoRW_d, PageType_d, load_page_fault, read_acc, mxr_sstatus, priv_mode_u { //pte.11
        ignore_bins ig1 = binsof(mxr_sstatus.set);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_s);
    }

    xpage_mxrset_read_s: cross PTE_XnoRW_d, PageType_d, mxr_sstatus, read_acc, priv_mode_s { //pte.12
        ignore_bins ig1 = binsof(mxr_sstatus.notset);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_u);
    }
    xpage_mxrset_read_u: cross PTE_XnoRW_d, PageType_d, mxr_sstatus, read_acc, priv_mode_u { //pte.12
        ignore_bins ig1 = binsof(mxr_sstatus.notset);
        ignore_bins ig2 = binsof(PTE_XnoRW_d.leaflvl_s);
    }

    PTE_DAU_nleaf_read_s: cross PTE_DAU_d, PageType_d, load_page_fault, priv_mode_s {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }
    PTE_DAU_nleaf_read_u: cross PTE_DAU_d, PageType_d, load_page_fault, priv_mode_u {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }

    PTE_DAU_nleaf_write_s: cross PTE_DAU_d, PageType_d, store_page_fault, priv_mode_s {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }
    PTE_DAU_nleaf_write_u: cross PTE_DAU_d, PageType_d, store_page_fault, priv_mode_u {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }

    PTE_DAU_nleaf_exec_s: cross PTE_DAU_i, PageType_i, ins_page_fault, priv_mode_s {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_i.sv48_kilo); `endif
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_i.sv32_kilo); `endif
    }
    PTE_DAU_nleaf_exec_u: cross PTE_DAU_i, PageType_i, ins_page_fault, priv_mode_u {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_i.sv48_kilo); `endif
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_i.sv39_kilo); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_i.sv32_kilo); `endif
    }

    misaligned_exec_s: cross PTE_RWX_i, misaligned_PPN_i, ins_page_fault, exec_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_i.leaflvl_u);
    }
    misaligned_exec_u: cross PTE_RWX_i, misaligned_PPN_i, ins_page_fault, exec_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_i.leaflvl_s);
    }

    misaligned_read_s: cross PTE_RWX_d, misaligned_PPN_d, load_page_fault, read_acc { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
    }
    misaligned_read_u: cross PTE_RWX_d, misaligned_PPN_d, load_page_fault, read_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
    }

    misaligned_write_s: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, write_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
    }
    misaligned_write_u: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, write_acc  { //pte.16
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
    }

    `ifdef XLEN64
        canonical_page_d: coverpoint ins.current.page_type_d {
            `ifdef SV48
                bins sv48_tera_canonical = {2'b11} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
                bins sv48_giga_canonical = {2'b10} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
                bins sv48_mega_canonical = {2'b01} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
                bins sv48_kilo_canonical = {2'b00} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_d[63:48] != 0) && (ins.current.virt_adr_d[63:48] != '1));
            `endif
            `ifdef SV39
                bins sv39_giga_canonical = {2'b10} iff ((ins.current.csr[12'h180][63:60] == 4'b1000) && (ins.current.virt_adr_d[63:39] != 0) && (ins.current.virt_adr_d[63:39] != '1));
                bins sv39_mega_canonical = {2'b01} iff ((ins.current.csr[12'h180][63:60] == 4'b1000) && (ins.current.virt_adr_d[63:39] != 0) && (ins.current.virt_adr_d[63:39] != '1));
                bins sv39_kilo_canonical = {2'b00} iff ((ins.current.csr[12'h180][63:60] == 4'b1000) && (ins.current.virt_adr_d[63:39] != 0) && (ins.current.virt_adr_d[63:39] != '1));
            `endif
        }
        canonical_page_i: coverpoint ins.current.page_type_i {
            `ifdef SV48
                bins sv48_tera_canonical = {2'b11} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
                bins sv48_giga_canonical = {2'b10} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
                bins sv48_mega_canonical = {2'b01} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
                bins sv48_kilo_canonical = {2'b00} iff ((ins.current.csr[12'h180][63:60] == 4'b1001) && (ins.current.virt_adr_i[63:48] != 0) && (ins.current.virt_adr_i[63:48] != '1));
            `endif
            `ifdef SV39
                bins sv39_giga_canonical = {2'b10} iff ((ins.current.csr[12'h180][63:60] == 4'b1000) && (ins.current.virt_adr_i[63:39] != 0) && (ins.current.virt_adr_i[63:39] != '1));
                bins sv39_mega_canonical = {2'b01} iff ((ins.current.csr[12'h180][63:60] == 4'b1000) && (ins.current.virt_adr_i[63:39] != 0) && (ins.current.virt_adr_i[63:39] != '1));
                bins sv39_kilo_canonical = {2'b00} iff ((ins.current.csr[12'h180][63:60] == 4'b1000) && (ins.current.virt_adr_i[63:39] != 0) && (ins.current.virt_adr_i[63:39] != '1));
            `endif
        }

        canonical_read_s: cross PTE_canonical_d, canonical_page_d, load_page_fault, read_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_u);
        }
        canonical_read_u: cross PTE_canonical_d, canonical_page_d, load_page_fault, read_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_s);
        }

        canonical_write_s: cross PTE_canonical_d, canonical_page_d, store_page_fault, write_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_u);
        }
        canonical_write_u: cross PTE_canonical_d, canonical_page_d, store_page_fault, write_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_d.leaflvl_s);
        }

        canonical_exec_s: cross PTE_canonical_i, canonical_page_i, ins_page_fault, exec_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_i.leaflvl_u);
        }
        canonical_exec_u: cross PTE_canonical_i, canonical_page_i, ins_page_fault, exec_acc { //va.1
            ignore_bins ig1 = binsof(PTE_canonical_i.leaflvl_s);
        }
    `endif
endgroup

covergroup VM_res_global_pte_cg with function sample(ins_t ins);
    option.per_instance = 0;
    //pte.1
    RSW: coverpoint ins.current.pte_i[9:8] {
        bins all_comb[] = {[2'd0:2'd3]};
    }

    `ifdef XLEN64
        mode: coverpoint ins.current.csr[12'h180][63:60] {
            `ifdef SV57
                bins sv57 = {4'b1010};
            `endif
            `ifdef SV48
                bins sv48 = {4'b1001};
            `endif
            `ifdef SV39
                bins sv39 = {4'b1000};
            `endif
        }
    `else
        mode: coverpoint ins.current.csr[12'h180][31] {
            bins sv32 = {1'b1};
        }
    `endif

    rsw_pte: cross RSW, mode;

    //pte.13
    global_PTE_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins leaflvl_u = {8'b??111111};
        wildcard bins leaflvl_s = {8'b??101111};
    }
    global_PTE_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b??111111};
        wildcard bins leaflvl_s = {8'b??101111};
    }

    `ifdef XLEN64
        PageType_i: coverpoint ins.current.page_type_i {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
        PageType_d: coverpoint ins.current.page_type_d {
            `ifdef SV48
                bins sv48_tera = {2'b11} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
                bins sv48_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1001);
            `endif
            `ifdef SV39
                bins sv39_giga = {2'b10} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_mega = {2'b01} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
                bins sv39_kilo = {2'b00} iff (ins.current.csr[12'h180][63:60] == 4'b1000);
            `endif
        }
    `else
        PageType_i: coverpoint ins.current.page_type_i {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
        }
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
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

    global_read_s: cross global_PTE_d, PageType_d, read_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_u);
    }
    global_read_u: cross global_PTE_d, PageType_d, read_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_s);
    }
    global_write_s: cross global_PTE_d, PageType_d, write_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_u);
    }
    global_write_u: cross global_PTE_d, PageType_d, write_acc {
        ignore_bins ig1 = binsof(global_PTE_d.leaflvl_s);
    }
    global_exec_s: cross global_PTE_i, PageType_i, exec_acc {
        ignore_bins ig1 = binsof(global_PTE_i.leaflvl_u);
    }
    global_exec_u: cross global_PTE_i, PageType_i, exec_acc {
        ignore_bins ig1 = binsof(global_PTE_i.leaflvl_s);
    }
endgroup

covergroup VM_add_feature_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `ifdef XLEN64
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

        PBMTE_unset: coverpoint ins.current.csr[12'h30A][62] {
            bins not_set = {1'b0};
        }
        ADUE_unset: coverpoint  ins.current.csr[12'h30A][61] {
            bins not_set = {1'b0};
        }

        mode: coverpoint ins.current.csr[12'h180][63:60] {
            `ifdef SV57
                bins sv57 = {4'b1010};
            `endif
            `ifdef SV48
                bins sv48 = {4'b1001};
            `endif
            `ifdef SV39
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
        load_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
            bins load_page_fault = {32'd13};
        }
        ins_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
            bins ins_page_fault = {32'd12};
        }
        store_page_fault: coverpoint  ins.current.csr[12'h342][31:0] {
            bins store_amo_page_fault = {32'd15};
        }

        //pte.17
        `ifndef SVNAPOT_SUPPORTED
            svnapot_PTE_i: coverpoint ins.current.pte_i[63] {
                bins svnapot   = {1'b1};
            }
            svnapot_PTE_d: coverpoint ins.current.pte_d[63] {
                bins svnapot   = {1'b1};
            }
            svnapot_read_fault:  cross svnapot_PTE_d, load_page_fault, read_acc, mode;
            svnapot_write_fault: cross svnapot_PTE_d, store_page_fault, write_acc, mode;
            svnapot_exec_fault:  cross svnapot_PTE_i, ins_page_fault, exec_acc, mode;
        `endif

        //pte.19
        svpbmt_read_fault:  cross svpbmt_PTE_d, load_page_fault, read_acc, mode, PBMTE_unset;
        svpbmt_write_fault: cross svpbmt_PTE_d, store_page_fault, write_acc, mode, PBMTE_unset;
        svpbmt_exec_fault:  cross svpbmt_PTE_i, ins_page_fault, exec_acc, mode, PBMTE_unset;

        //pte.20
        reserved_read_fault:  cross reserved_PTE_d, load_page_fault, read_acc, mode;
        reserved_write_fault: cross reserved_PTE_d, store_page_fault, read_acc, mode;
        reserved_exec_fault:  cross reserved_PTE_i, ins_page_fault, read_acc, mode;

        //pte.17&19&20
        read_nofault:  cross zeros_PTE_d, read_acc, mode;
        write_nofault: cross zeros_PTE_d, write_acc, mode;
        exec_nofault:  cross zeros_PTE_i, exec_acc, mode;

        //pte.18
        svadu_disabled: cross ADUE_unset, mode;
    `else

        mode: coverpoint ins.current.csr[12'h180][31] {
            bins sv32 = {1'b1};
        }
        ADUE_unset: coverpoint  ins.current.csr[12'h31A][29] {
            bins not_set = {1'b0};
        }
        svadu_disabled: cross ADUE_unset, mode;

    `endif
endgroup


function void vm_sample(int hart, int issue, ins_t ins);
    VM_PA_VA_cg.sample(ins);
    VM_satp_cg.sample(ins);
    VM_sfence_cg.sample(ins);
    VM_mstatus_mprv_cg.sample(ins);
    VM_vm_permissions_cg.sample(ins);
    VM_res_global_pte_cg.sample(ins);
    VM_add_feature_cg.sample(ins);
endfunction
