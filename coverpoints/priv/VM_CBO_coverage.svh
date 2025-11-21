///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_VM_CBO
covergroup VM_CBO_exceptions_cg with function sample(ins_t ins);
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

    PTE_x_spage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_x_s = {8'b11?01001};
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

    PTE_x_upage_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_x_u = {8'b11?11001};
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

    `ifdef XLEN64
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
        PageType_d: coverpoint ins.current.page_type_d {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
        }
    `endif

    kilo_page: coverpoint ins.current.page_type_d {
        bins kilo_page = {2'b00};
    }

    `ifdef XLEN64
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
        misaligned_PPN_d: coverpoint ins.current.page_type_d {
            bins sv32_mega_misaligned = {2'b01} iff ((ins.current.ppn_d[9:0] != 10'b0) && (ins.current.csr[12'h180][31] == 1'b1));
        }
    `endif

    store_page_fault: coverpoint  ins.current.csr[12'h342] iff (ins.trap == 1) {
        bins store_amo_page_fault = {64'd15};
    }
    store_acc_fault: coverpoint  ins.current.csr[12'h342] iff (ins.trap == 1) {
        bins store_amo_access_fault = {64'd7};
    }
    sum_sstatus: coverpoint ins.current.csr[12'h100][18]{
        bins notset = {0};
        bins set = {1};
    }

    `ifdef XLEN64
        d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[55:2], 2'b00} == `ACCESS_FAULT_ADDRESS) {
            bins non_existent_pa = {1};
        }
    `else
        d_phys_address_nonexistent: coverpoint ({ins.current.phys_adr_d[33:2], 2'b00} == `ACCESS_FAULT_ADDRESS) {
            bins non_existent_pa = {1};
        }
    `endif

    cbo_ins: coverpoint ins.current.insn {
        wildcard bins any_zicbom_ins = {32'b000000000000_?????_010_00000_0001111, 32'b000000000001_?????_010_00000_0001111, 32'b000000000010_?????_010_00000_0001111};
        wildcard bins zicboz_ins = {32'b000000000100_?????_010_00000_0001111};
    }

    PTE_inv_cbo_s: cross PTE_d_inv, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_u_w);
    }
    PTE_inv_cbo_u: cross PTE_d_inv, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_d_inv.leaflvl_s_w);
    }

    PTE_res_rwx_cbo_s: cross PTE_d_res_rwx, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_u);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_u);
    }
    PTE_res_rwx_cbo_u: cross PTE_d_res_rwx, PageType_d, store_page_fault, cbo_ins, priv_mode_u  {
        ignore_bins ig1 = binsof(PTE_d_res_rwx.leaflvl_exec_s);
        ignore_bins ig2 = binsof(PTE_d_res_rwx.leaflvl_noexec_s);
    }

    PTE_nonleaf_lvl0_cbo_s: cross PTE_nonleaf_lvl0_d, kilo_page, mode, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_u);
    }

    PTE_nonleaf_lvl0_cbo_u: cross PTE_nonleaf_lvl0_d, kilo_page, mode, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_nonleaf_lvl0_d.lvl0_s);
    }

    // A Zicbom instruction is allowed if a load or store instruction is permitted to access the corresponding physical addresses
    PTE_r_set_w_unset_zicbom_s: cross PTE_r_set_w_unset_spage_d, PageType_d, cbo_ins, priv_mode_s, sum_sstatus {
        ignore_bins ig1 = binsof(cbo_ins.zicboz_ins);
    }
    PTE_r_set_w_unset_zicbom_u: cross PTE_r_set_w_unset_upage_d, PageType_d, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(cbo_ins.zicboz_ins);
    }
    PTE_rw_unset_zicbom_s: cross PTE_x_spage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(cbo_ins.zicboz_ins);
    }
    PTE_rw_unset_zicbom_u: cross PTE_x_upage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(cbo_ins.zicboz_ins);
    }

    // A Zicboz instruction is allowed if a store instruction is permitted to access the corresponding physical addresses
    PTE_w_unset_zicboz_s: cross PTE_w_unset_spage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s, sum_sstatus {
        ignore_bins ig1 = binsof(cbo_ins.any_zicbom_ins);
    }
    PTE_w_unset_zicboz_u: cross PTE_w_unset_upage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(cbo_ins.any_zicbom_ins);
    }

    spage_rwx_cbo_u: cross PTE_spage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u;

    upage_sumunset_cbo_s: cross PTE_upage_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s, sum_sstatus {
        ignore_bins ig1 = binsof(sum_sstatus.set);
    }

    Abit_unset_cbo_s: cross PTE_Abit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_Abit_unset_d.leaflvl_u);
    }
    Abit_unset_cbo_u: cross PTE_Abit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_Abit_unset_d.leaflvl_s);
    }

    // A Zicbom instruction does not check the dirty bit and neither raises an exception nor sets the bit
    Dbit_unset_zicbom_s: cross PTE_Dbit_unset_d, PageType_d, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_u);
        ignore_bins ig2 = binsof(cbo_ins.zicboz_ins);
    }
    Dbit_unset_zicbom_u: cross PTE_Dbit_unset_d, PageType_d, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_s);
        ignore_bins ig2 = binsof(cbo_ins.zicboz_ins);
    }
    // A Zicboz instruction checks the dirty bit and may raise an exception and set the bit as required
    Dbit_unset_zicboz_s: cross PTE_Dbit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_u);
        ignore_bins ig2 = binsof(cbo_ins.any_zicbom_ins);
    }
    Dbit_unset_zicboz_u: cross PTE_Dbit_unset_d, PageType_d, store_page_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_Dbit_unset_d.leaflvl_s);
        ignore_bins ig2 = binsof(cbo_ins.any_zicbom_ins);
    }

    misaligned_page_cbo_s: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, cbo_ins, priv_mode_s  {
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
    }
    misaligned_page_cbo_u: cross PTE_RWX_d, misaligned_PPN_d, store_page_fault, cbo_ins, priv_mode_u  {
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
    }

    // PTE points to a non existent physical address
    leaf_PTE_to_nonexistent_pa_cbo_s: cross PTE_RWX_d, d_phys_address_nonexistent, PageType_d, store_acc_fault, cbo_ins, priv_mode_s {
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_u);
    }
    leaf_PTE_to_nonexistent_pa_cbo_u: cross PTE_RWX_d, d_phys_address_nonexistent, PageType_d, store_acc_fault, cbo_ins, priv_mode_u {
        ignore_bins ig1 = binsof(PTE_RWX_d.leaflvl_s);
    }

    // Non leaf PTE points to a non existatant phys addr instead of next page table. Store access fault required during walk
    // Example: Setup a giga page in sv48, lvl 3 pte (tera) should point to lvl2 page table, but it points to non existent PA
    nonleaf_PTE_to_nonexistent_pa_cbo: cross pointer_PTE_d, d_phys_address_nonexistent, PageType_d, store_acc_fault, cbo_ins, priv_mode_su {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_d.sv48_tera); `endif     // Here PageType_d will be the page being pointed towards
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_d.sv39_giga); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_d.sv32_mega); `endif
    }

    PTE_nonleaf_DAU_cbo: cross PTE_DAU_d, PageType_d, store_page_fault, cbo_ins, priv_mode_su {
        `ifdef SV48     ignore_bins ig1 = binsof(PageType_d.sv48_kilo); `endif
        `ifdef SV39     ignore_bins ig2 = binsof(PageType_d.sv39_kilo); `endif
        `ifdef XLEN32   ignore_bins ig3 = binsof(PageType_d.sv32_kilo); `endif
    }

endgroup

function void vm_cbo_sample(int hart, int issue, ins_t ins);
    VM_CBO_exceptions_cg.sample(ins);
endfunction
