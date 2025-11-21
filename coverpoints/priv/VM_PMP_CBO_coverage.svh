///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_VM_PMP_CBO
covergroup VM_PMP_CBO_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    // All PTE permissions
    PTE_s: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_s = {8'b11?01111};
    }
    PTE_u: coverpoint ins.current.pte_d[7:0] {
        wildcard bins leaflvl_u = {8'b11?11111};
    }

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

    store_acc_fault: coverpoint  ins.current.csr[12'h342] {
        bins store_acc_fault = {64'd7};
    }

    cbo_ins: coverpoint ins.current.insn {
        wildcard bins any_zicbom_ins = {32'b000000000000_?????_010_00000_0001111, 32'b000000000001_?????_010_00000_0001111, 32'b000000000010_?????_010_00000_0001111};
        wildcard bins zicboz_ins     = {32'b000000000100_?????_010_00000_0001111};
    }

    PMP_perm: coverpoint  ins.current.csr[12'h3A0][7:0] {
        wildcard bins rw_unset   = {8'b?????100};
    }


    PA_PMP_rw_unset_cbo_s:  cross PTE_s, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_s;
    PA_PMP_rw_unset_cbo_u:  cross PTE_u, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_u;
    PTE_PMP_rw_unset_cbo_s: cross PTE_s, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_s;
    PTE_PMP_rw_unset_cbo_u: cross PTE_u, PageType_d, PMP_perm, cbo_ins, store_acc_fault, priv_mode_u;

endgroup

function void vm_pmp_cbo_sample(int hart, int issue, ins_t ins);
    VM_PMP_CBO_cg.sample(ins);
endfunction
