///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_VM_PMP
covergroup VM_PMP_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"
    //pte permission for leaf PTEs
    PTE_i: coverpoint ins.current.pte_i[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_d: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
        wildcard bins leaflvl_s = {8'b11?01111};
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
    `else
        PageType_i: coverpoint ins.current.page_type_i {
            bins sv32_mega = {2'b01} iff (ins.current.csr[12'h180][31] == 1'b1);
            bins sv32_kilo = {2'b00} iff (ins.current.csr[12'h180][31] == 1'b1);
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

    // satp.mode for coverage of SV32, SV39, SV48 & SV57
        `ifdef XLEN64
        mode: coverpoint  ins.current.csr[12'h180][63:60] {
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
        mode: coverpoint  ins.current.csr[12'h180][31] {
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
    write_acc: coverpoint ins.current.write_access {
        bins set = {1};
    }

    load_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins load_acc_fault = {64'd5};
    }
    store_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins store_acc_fault = {64'd7};
    }
    ins_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins ins_acc_fault  = {64'd1};
    }

    lw: coverpoint ins.current.insn {
        wildcard bins lw = {32'b????????????_?????_010_?????_0000011};
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
    }
    jalr: coverpoint ins.prev.insn {
        wildcard bins jalr = {32'b????????????_?????_000_?????_1100111};
    }

    PMP0_PTE: coverpoint  ins.current.csr[12'h3A0][7:0] {        // PMP permissions of PTE
        wildcard bins noread   = {8'b?????100};
    }

    // pmp.2
    pmp0_pte_noread_s:  cross PageType_d, PMP0_PTE, load_acc_fault, priv_mode_s, lw;
    pmp0_pte_noread_u:  cross PageType_d, PMP0_PTE, load_acc_fault, priv_mode_u, lw;
    pmp0_pte_nowrite_s: cross PageType_d, PMP0_PTE, store_acc_fault, priv_mode_s, sw;
    pmp0_pte_nowrite_u: cross PageType_d, PMP0_PTE, store_acc_fault, priv_mode_u, sw;
    pmp0_pte_noexec_s:  cross PageType_i, PMP0_PTE, ins_acc_fault, priv_mode_s, jalr;
    pmp0_pte_noexec_u:  cross PageType_i, PMP0_PTE, ins_acc_fault, priv_mode_u, jalr;


    PMP0_PA: coverpoint  ins.current.csr[12'h3A0][15:8] {       // PMP permissions of (translated) phys addr region
        wildcard bins noread   = {8'b?????100};
        wildcard bins nowrite  = {8'b?????101};
        wildcard bins noexe    = {8'b?????011};
    }

    // pmp.1
    pmp0_PA_noread_s: cross PTE_d, PageType_d, PMP0_PA, load_acc_fault, priv_mode_s, read_acc {
        ignore_bins ig1 = binsof(PMP0_PA.nowrite);
        ignore_bins ig2 = binsof(PMP0_PA.noexe);
        ignore_bins ig3 = binsof(PTE_d.leaflvl_u);
    }
    pmp0_PA_noread_u: cross PTE_d, PageType_d, PMP0_PA, load_acc_fault, priv_mode_u, read_acc {
        ignore_bins ig1 = binsof(PMP0_PA.nowrite);
        ignore_bins ig2 = binsof(PMP0_PA.noexe);
        ignore_bins ig3 = binsof(PTE_d.leaflvl_s);
    }
    pmp0_PA_nowrite_s: cross PTE_d, PageType_d, PMP0_PA, store_acc_fault, priv_mode_s, write_acc {
        ignore_bins ig1 = binsof(PMP0_PA.noread);
        ignore_bins ig2 = binsof(PMP0_PA.noexe);
        ignore_bins ig3 = binsof(PTE_d.leaflvl_u);
    }
    pmp0_PA_nowrite_u: cross PTE_d, PageType_d, PMP0_PA, store_acc_fault, priv_mode_u, write_acc {
        ignore_bins ig1 = binsof(PMP0_PA.noread);
        ignore_bins ig2 = binsof(PMP0_PA.noexe);
        ignore_bins ig3 = binsof(PTE_d.leaflvl_s);
    }
    pmp0_PA_noexec_s: cross PTE_i, PageType_i, PMP0_PA, ins_acc_fault, priv_mode_s, exec_acc {
        ignore_bins ig1 = binsof(PMP0_PA.nowrite);
        ignore_bins ig2 = binsof(PMP0_PA.noread);
        ignore_bins ig3 = binsof(PTE_i.leaflvl_u);
    }
    pmp0_PA_noexec_u: cross PTE_i, PageType_i, PMP0_PA, ins_acc_fault, priv_mode_u, exec_acc {
        ignore_bins ig1 = binsof(PMP0_PA.nowrite);
        ignore_bins ig2 = binsof(PMP0_PA.noread);
        ignore_bins ig3 = binsof(PTE_i.leaflvl_s);
    }
endgroup

function void vm_pmp_sample(int hart, int issue, ins_t ins);
    VM_PMP_cg.sample(ins);
endfunction
