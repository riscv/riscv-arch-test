///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups for Hypervisor Extension (H-extension)
//
// Written: Vikram Krishna vkrishna@hmc.edu October 9 2025
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
//
// Licensed under the Solderpad Hardware License v 2.1 (the “License”); you may not use this file
// except in compliance with the License, or, at your option, the Apache License version 2.0. You
// may obtain a copy of the License at
//
// https://solderpad.org/licenses/SHL-2.1/
//
// Unless required by applicable law or agreed to in writing, any work distributed under the
// License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
// either express or implied. See the License for the specific language governing permissions
// and limitations under the License.
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICSRH

// Covergroup for H-extension CSR access testing
covergroup ZicsrH_csr_access_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    // Machine H-Extension CSRs
    mhcsrname: coverpoint ins.current.insn[31:20] {
        bins mtval2  = {12'h34B};
        bins mtinst  = {12'h34A};
    }

    // HS H-Extension CSRs
    hscsrname: coverpoint ins.current.insn[31:20] {
        bins hstatus    = {12'h600};
        bins hedeleg    = {12'h602};
        bins hideleg    = {12'h603};
        bins hie        = {12'h604};
        bins hcounteren = {12'h606};
        bins hgeie      = {12'h607};
        bins henvcfg    = {12'h60A};
        bins htval      = {12'h643};
        bins hip        = {12'h644};
        bins hvip       = {12'h645};
        bins htinst     = {12'h64A};
        bins hgatp      = {12'h680};
        bins hgeip      = {12'hE12};  // Read-only
        bins htimedelta = {12'h605};
        `ifdef XLEN32
            bins hedelegh   = {12'h612};
            bins htimedeltah = {12'h615};
            bins henvcfgh   = {12'h61A};
        `endif
    }

    // VS H-Extension CSRs
    vscsrname: coverpoint ins.current.insn[31:20] {
        bins vsstatus  = {12'h200};
        bins vsie      = {12'h204};
        bins vstval    = {12'h243};
        bins vsip      = {12'h244};
        bins vstvec    = {12'h205};
        bins vsscratch = {12'h240};
        bins vsepc     = {12'h241};
        bins vscause   = {12'h242};
        bins vsatp     = {12'h280};
    }

    // S CSRs with VS replicas
    scsrname_replica: coverpoint ins.current.insn[31:20] {
        bins sstatus  = {12'h100};
        bins sie      = {12'h104};
        bins stvec    = {12'h105};
        bins sscratch = {12'h140};
        bins sepc     = {12'h141};
        bins scause   = {12'h142};
        bins stval    = {12'h143};
        bins sip      = {12'h144};
        bins satp     = {12'h180};
    }

    // S CSRs without VS replicas
    scsrname_noreplica: coverpoint ins.current.insn[31:20] {
        bins scounteren    = {12'h106};
        bins senvcfg       = {12'h10A};
        bins scountinhibit = {12'h320};
    }

    // RV64 only: h-half CSRs (should be illegal)
    `ifdef XLEN64
        hhalfcsrname: coverpoint ins.current.insn[31:20] {
            bins hedelegh    = {12'h612};
            bins htimedeltah = {12'h615};
            bins henvcfgh    = {12'h61A};
        }
    `endif

    // CSR operations
    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrw = {3'b001};
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
        bins csrrwi = {3'b101};
        bins csrrsi = {3'b110};
        bins csrrci = {3'b111};
    }

    // HSTATUS.V bit to distinguish between HS and VS mode
    hstatus_v_bit: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 20) & 1 {
        bins hs_mode = {0};
        bins vs_mode = {1};
    }

    // Write patterns for access testing
    write_pattern: coverpoint ins.current.rs1_val {
        bins all_zeros = {'0};
        bins all_ones  = {'1};
    }

    // Exception check
    exception: coverpoint ins.trap {
        bins trapped = {1};
        bins no_trap = {0};
    }

    // Main coverpoints: M-mode access to all H-extension CSRs
    cp_mhcsr_access_m: cross priv_mode_m, mhcsrname, csrop, write_pattern;
    cp_hscsr_access_m: cross priv_mode_m, hscsrname, csrop, write_pattern;
    cp_vscsr_access_m: cross priv_mode_m, vscsrname, csrop, write_pattern;

    // HS-mode access to HS and VS CSRs (hstatus.V=0)
    cp_hscsr_access_hs: cross priv_mode_s, hscsrname, csrop, write_pattern, hstatus_v_bit {
        ignore_bins not_hs_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode}; // Exclude VS mode (hstatus.V=1)
    }
    // HS-mode (hstatus.V=0) access to VS CSRs
    cp_vscsr_access_hs: cross priv_mode_s, vscsrname, csrop, write_pattern, hstatus_v_bit {
        ignore_bins not_hs_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode}; // Exclude VS mode (hstatus.V=1)
    }
    // VS-mode (hstatus.V=1) access to VS CSRs
    cp_vscsr_access_vs: cross priv_mode_s, vscsrname, csrop, write_pattern, hstatus_v_bit {
        ignore_bins not_vs_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode}; // Exclude HS mode (hstatus.V=0)
    }

    // M-mode CSRs should be inaccessible from HS-mode (hstatus.V=0), expecting an illegal instruction trap
    cp_mhcsr_inaccessible_hs: cross priv_mode_s, mhcsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_hs_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode}; // Exclude VS mode (hstatus.V=1)
        ignore_bins no_illegal_instr_trap = binsof(exception) intersect {0}; // Expect a trap (illegal instruction)
    }

    // VS-mode: HS and VS CSRs should cause virtual instruction fault
    // In VS-mode (hstatus.V=1), accesses to HS CSRs (cp_hscsr_virtualinstructionfault_vs) should cause a virtual instruction fault
    cp_hscsr_virtualinstructionfault_vs: cross priv_mode_s, hscsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_vs_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode}; // Exclude HS mode (hstatus.V=0)
        ignore_bins no_virtual_instr_fault_trap = binsof(exception) intersect {0}; // Expect a trap (virtual instruction fault)
    }
    // In VS-mode (hstatus.V=1), accesses to VS CSRs (cp_vscsr_virtualinstructionfault_vs) should cause a virtual instruction fault
    cp_vscsr_virtualinstructionfault_vs: cross priv_mode_s, vscsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_vs_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode}; // Exclude HS mode (hstatus.V=0)
        ignore_bins no_virtual_instr_fault_trap = binsof(exception) intersect {0}; // Expect a trap (virtual instruction fault)
    }

    // VS-mode (hstatus.V=1): M-mode CSRs should cause virtual instruction fault
    cp_mhcsr_virtualinstructionfault_vs: cross priv_mode_s, mhcsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_vs_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode}; // Exclude HS mode (hstatus.V=0)
        ignore_bins no_virtual_instr_fault_trap = binsof(exception) intersect {0}; // Expect a trap (virtual instruction fault)
    }

    // U-mode: All H-extension CSRs should be inaccessible
    // U-mode (hstatus.V=0): M-H-extension CSRs should be inaccessible
    cp_hcsr_inaccessible_u: cross priv_mode_u, mhcsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_actual_u_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode}; // Exclude VU mode (hstatus.V=1)
        ignore_bins no_trap = binsof(exception) intersect {0};
    }
    // U-mode (hstatus.V=0): HS-H-extension CSRs should be inaccessible
    cp_hscsr_inaccessible_u: cross priv_mode_u, hscsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_actual_u_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode}; // Exclude VU mode (hstatus.V=1)
        ignore_bins no_trap = binsof(exception) intersect {0};
    }
    // U-mode (hstatus.V=0): VS-H-extension CSRs should be inaccessible
    cp_vscsr_inaccessible_u: cross priv_mode_u, vscsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_actual_u_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode}; // Exclude VU mode (hstatus.V=1)
        ignore_bins no_trap = binsof(exception) intersect {0};
    }

    // VU-mode (hstatus.V=1): All H-extension CSRs should be inaccessible
    cp_hcsr_inaccessible_vu: cross priv_mode_u, mhcsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_actual_vu_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode}; // Exclude U mode (hstatus.V=0)
        ignore_bins no_trap = binsof(exception) intersect {0};
    }
    // VU-mode (hstatus.V=1): HS-H-extension CSRs should be inaccessible
    cp_hscsr_inaccessible_vu: cross priv_mode_u, hscsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_actual_vu_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode}; // Exclude U mode (hstatus.V=0)
        ignore_bins no_trap = binsof(exception) intersect {0};
    }
    // VU-mode (hstatus.V=1): VS-H-extension CSRs should be inaccessible
    cp_vscsr_inaccessible_vu: cross priv_mode_u, vscsrname, csrop, hstatus_v_bit, exception {
        ignore_bins not_actual_vu_mode = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode}; // Exclude U mode (hstatus.V=0)
        ignore_bins no_trap = binsof(exception) intersect {0};
    }

    // RV64: h-half CSRs should be illegal in all modes
    `ifdef XLEN64
        cp_hhalf_illegal_vs: cross priv_mode_s, hhalfcsrname, csrop, exception {
            ignore_bins no_trap = binsof(exception) intersect {0};
        }
        cp_hhalf_illegal_u: cross priv_mode_u, hhalfcsrname, csrop, exception {
            ignore_bins no_trap = binsof(exception) intersect {0};
        }
    `endif
endgroup

// Covergroup for CSR bit walking tests
covergroup ZicsrH_csr_walk_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    // Machine H-Extension CSRs
    mhcsrname: coverpoint ins.current.insn[31:20] {
        bins mtval2  = {12'h34B};
        bins mtinst  = {12'h34A};
    }

    // HS H-Extension CSRs (excluding hstatus - tested separately due to WPRI bits)
    hscsrname_walk: coverpoint ins.current.insn[31:20] {
        bins hedeleg    = {12'h602};
        bins hideleg    = {12'h603};
        bins hie        = {12'h604};
        bins hcounteren = {12'h606};
        bins hgeie      = {12'h607};
        bins henvcfg    = {12'h60A};
        bins htval      = {12'h643};
        bins hip        = {12'h644};
        bins hvip       = {12'h645};
        bins htinst     = {12'h64A};
        bins hgatp      = {12'h680};
        bins hgeip      = {12'hE12};
        bins htimedelta = {12'h605};
        `ifdef XLEN32
            bins hedelegh   = {12'h612};
            bins htimedeltah = {12'h615};
            bins henvcfgh   = {12'h61A};
        `endif
    }

    // VS H-Extension CSRs (excluding vsstatus - tested separately due to WPRI bits)
    vscsrname_walk: coverpoint ins.current.insn[31:20] {
        bins vsie      = {12'h204};
        bins vstval    = {12'h243};
        bins vsip      = {12'h244};
        bins vstvec    = {12'h205};
        bins vsscratch = {12'h240};
        bins vsepc     = {12'h241};
        bins vscause   = {12'h242};
        bins vsatp     = {12'h280};
    }

    // Walking ones pattern
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:XLEN-1] };
    }

    // Walking zeros pattern
    walking_zeros: coverpoint $clog2(~ins.current.rs1_val) iff ($onehot(~ins.current.rs1_val)) {
        bins b_0[] = { [0:XLEN-1] };
    }

    // CSR set/clear operations for walking
    csrop_walk: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }

    // HSTATUS.V bit to distinguish between HS and VS mode
    hstatus_v_bit: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 20) & 1 {
        bins hs_mode = {0};
        bins vs_mode = {1};
    }

    // Main coverpoints: Bit walking in M-mode
    cp_mhcsrwalk_m: cross priv_mode_m, mhcsrname, csrop_walk, walking_ones;
    cp_mhcsrwalk_zeros_m: cross priv_mode_m, mhcsrname, csrop_walk, walking_zeros;

    cp_hscsrwalk_m: cross priv_mode_m, hscsrname_walk, csrop_walk, walking_ones;
    cp_hscsrwalk_zeros_m: cross priv_mode_m, hscsrname_walk, csrop_walk, walking_zeros;

    cp_vscsrwalk_m: cross priv_mode_m, vscsrname_walk, csrop_walk, walking_ones;
    cp_vscsrwalk_zeros_m: cross priv_mode_m, vscsrname_walk, csrop_walk, walking_zeros;

    // Bit walking in HS-mode (hstatus.V=0)
    cp_hscsrwalk_hs: cross priv_mode_s, hscsrname_walk, csrop_walk, walking_ones, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }
    cp_hscsrwalk_zeros_hs: cross priv_mode_s, hscsrname_walk, csrop_walk, walking_zeros, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }

    // Bit walking in VS-mode (hstatus.V=1)
    cp_vscsrwalk_vs: cross priv_mode_s, vscsrname_walk, csrop_walk, walking_ones, hstatus_v_bit {
        ignore_bins not_vs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode};
    }
    cp_vscsrwalk_zeros_vs: cross priv_mode_s, vscsrname_walk, csrop_walk, walking_zeros, hstatus_v_bit {
        ignore_bins not_vs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode};
    }
endgroup

// Covergroup for VS CSR replica testing
covergroup ZicsrH_replica_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    // S CSRs with VS replicas
    scsrname_replica: coverpoint ins.current.insn[31:20] {
        bins sstatus  = {12'h100};
        bins sie      = {12'h104};
        bins stvec    = {12'h105};
        bins sscratch = {12'h140};
        bins sepc     = {12'h141};
        bins scause   = {12'h142};
        bins stval    = {12'h143};
        bins sip      = {12'h144};
        bins satp     = {12'h180};
    }

    // VS replicas
    vscsrname_replica: coverpoint ins.current.insn[31:20] {
        bins vsstatus  = {12'h200};
        bins vsie      = {12'h204};
        bins vstvec    = {12'h205};
        bins vsscratch = {12'h240};
        bins vsepc     = {12'h241};
        bins vscause   = {12'h242};
        bins vstval    = {12'h243};
        bins vsip      = {12'h244};
        bins vsatp     = {12'h280};
    }

    // S CSRs without replicas
    scsrname_noreplica: coverpoint ins.current.insn[31:20] {
        bins scounteren    = {12'h106};
        bins senvcfg       = {12'h10A};
        bins scountinhibit = {12'h320};
    }

    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrw = {3'b001};
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }

    // HSTATUS.V bit to distinguish between HS and VS mode
    hstatus_v_bit: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 20) & 1 {
        bins hs_mode = {0};
        bins vs_mode = {1};
    }

    // Test that S and VS CSRs are independent in M-mode and HS-mode
    cp_replica_independent_m: cross priv_mode_m, scsrname_replica, csrop;
    cp_replica_independent_hs: cross priv_mode_s, scsrname_replica, csrop, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }

    // Test that in VS-mode, accessing S CSRs affects VS replicas
    cp_replica_redirect_vs: cross priv_mode_s, scsrname_replica, csrop, hstatus_v_bit {
        ignore_bins not_vs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode};
    }

    // Test that non-replicated S CSRs behave normally in VS-mode
    cp_nonreplica_vs: cross priv_mode_s, scsrname_noreplica, csrop, hstatus_v_bit {
        ignore_bins not_vs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode};
    }
endgroup

// Covergroup for hstatus.VGEIN field testing
covergroup ZicsrH_hstatus_vgein_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    csrrw_hstatus: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b011000000000_?????_001_?????_1110011};  // csrrw to hstatus
    }

    // VGEIN field is bits [17:12] of hstatus
    vgein_value: coverpoint ins.current.rs1_val[17:12] {
        bins zero        = {0};
        bins one         = {1};
        bins geilen_m1   = {6'd62};  // GEILEN-1 (assuming GEILEN can be up to 63)
        bins geilen      = {6'd63};  // GEILEN (max value)
        bins all_ones    = {6'd63};  // 63 is max 6-bit value
        bins mid_range[] = {[2:61]};
    }

    // HSTATUS.V bit to distinguish between HS and VS mode
    hstatus_v_bit: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 20) & 1 {
        bins hs_mode = {0};
        bins vs_mode = {1};
    }

    // Exception check
    exception: coverpoint ins.trap {
        bins trapped = {1};
        bins no_trap = {0};
    }

    cp_vgein_write: cross priv_mode_m, csrrw_hstatus, vgein_value;
    cp_vgein_write_hs: cross priv_mode_s, csrrw_hstatus, vgein_value, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }

    // Write from VS mode (should trap)
    cp_vgein_write_vs: cross priv_mode_s, csrrw_hstatus, vgein_value, hstatus_v_bit, exception {
        ignore_bins not_vs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode};
        ignore_bins no_trap = binsof(exception) intersect {0};
    }
endgroup

// Covergroup for vscause testing
covergroup ZicsrH_vscause_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    csrrw_vscause: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b001001000010_?????_001_?????_1110011};  // csrrw to vscause
    }

    vscause_interrupt: coverpoint ins.current.rs1_val[XLEN-1] {
        bins interrupt = {1};
    }

    vscause_exception: coverpoint ins.current.rs1_val[XLEN-1] {
        bins exception = {0};
    }

    // HSTATUS.V bit to distinguish between HS and VS mode
    hstatus_v_bit: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 20) & 1 {
        bins hs_mode = {0};
        bins vs_mode = {1};
    }

    vscause_exception_values: coverpoint ins.current.rs1_val[XLEN-2:0] {
        bins b_0_instruction_address_misaligned = {0};
        bins b_1_instruction_address_fault = {1};
        bins b_2_illegal_instruction = {2};
        bins b_3_breakpoint = {3};
        bins b_4_load_address_misaligned = {4};
        bins b_5_load_access_fault = {5};
        bins b_6_store_address_misaligned = {6};
        bins b_7_store_access_fault = {7};
        bins b_8_ecall_u = {8};
        bins b_9_ecall_vs = {9};
        bins b_10_ecall_reserved = {10};
        bins b_11_ecall_reserved = {11};
        bins b_12_instruction_page_fault = {12};
        bins b_13_load_page_fault = {13};
        bins b_14_reserved = {14};
        bins b_15_store_page_fault = {15};
        bins b_17_16_reserved = {[17:16]};
        bins b_18_software_check = {18};
        bins b_19_hardware_error = {19};
        bins b_20_instruction_guest_page_fault = {20};
        bins b_21_load_guest_page_fault = {21};
        bins b_22_virtual_instruction = {22};
        bins b_23_store_guest_page_fault = {23};
        bins b_31_24_custom = {[31:24]};
        bins b_47_32_reserved = {[47:32]};
        bins b_63_48_custom = {[63:48]};
    }

    vscause_interrupt_values: coverpoint ins.current.rs1_val[XLEN-2:0] {
        bins b_0_reserved = {0};
        bins b_1_supervisor_software = {1};
        bins b_2_virtual_supervisor_software = {2};
        bins b_3_reserved = {3};
        bins b_4_reserved = {4};
        bins b_5_supervisor_timer = {5};
        bins b_6_virtual_supervisor_timer = {6};
        bins b_7_reserved = {7};
        bins b_8_reserved = {8};
        bins b_9_supervisor_external = {9};
        bins b_10_virtual_supervisor_external = {10};
        bins b_11_reserved = {11};
        bins b_12_reserved = {12};
        bins b_13_counter_overflow = {13};
        bins b_14_reserved = {14};
        bins b_15_reserved = {15};
    }

    // Main coverpoints for vscause writes in different modes
    cp_vscause_write_exception_m: cross csrrw_vscause, priv_mode_m, vscause_exception_values, vscause_exception;
    cp_vscause_write_interrupt_m: cross csrrw_vscause, priv_mode_m, vscause_interrupt_values, vscause_interrupt;

    cp_vscause_write_exception_hs: cross csrrw_vscause, priv_mode_s, vscause_exception_values, vscause_exception, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }
    cp_vscause_write_interrupt_hs: cross csrrw_vscause, priv_mode_s, vscause_interrupt_values, vscause_interrupt, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }
endgroup

// Covergroup for vsstatus.SD testing
covergroup ZicsrH_vsstatus_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    csrrw_vsstatus: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b001000000000_?????_001_?????_1110011};  // csrrw to vsstatus
    }

    // SD bit
    cp_vsstatus_sd: coverpoint ins.current.rs1_val[XLEN-1] {
    }

    // FS field [14:13]
    cp_vsstatus_fs: coverpoint ins.current.rs1_val[14:13] {
    }

    // VS field [10:9]
    cp_vsstatus_vs: coverpoint ins.current.rs1_val[10:9] {
    }

    // XS field [16:15] - read-only, reflects extension state
    cp_vsstatus_xs: coverpoint ins.current.rs1_val[16:15] {
    }

    // HSTATUS.V bit to distinguish between HS and VS mode
    hstatus_v_bit: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 20) & 1 {
        bins hs_mode = {0};
        bins vs_mode = {1};
    }

    // Test SD affected by FS/VS in M-mode
    cp_vsstatus_sd_write_m: cross priv_mode_m, csrrw_vsstatus, cp_vsstatus_sd, cp_vsstatus_fs, cp_vsstatus_vs, cp_vsstatus_xs;

    // Test SD affected by FS/VS in HS-mode
    cp_vsstatus_sd_write_hs: cross priv_mode_s, csrrw_vsstatus, cp_vsstatus_sd, cp_vsstatus_fs, cp_vsstatus_vs, cp_vsstatus_xs, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }
endgroup

// Covergroup for TVM/VTVM trap testing
covergroup ZicsrH_tvm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    // satp and hgatp CSR accesses
    csr_tvm: coverpoint ins.current.insn[31:20] {
        bins satp  = {12'h180};
        bins hgatp = {12'h680};
    }

    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrw = {3'b001};
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }

    // mstatus.TVM bit [20]
    mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "mstatus", "tvm") {
        bins tvm_clear = {0};
        bins tvm_set = {1};
    }

    hstatus_vtvm: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 7) & 1 {
        bins vtvm_clear = {0};
        bins vtvm_set   = {1};
    }

    // HSTATUS.V bit to distinguish between HS and VS mode
    hstatus_v_bit: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_PREV, "hstatus") >> 20) & 1 {
        bins hs_mode = {0};
        bins vs_mode = {1};
    }

    // TVM trap in HS-mode accessing satp/hgatp
    cp_tvm_hs: cross priv_mode_s, csr_tvm, csrop, hstatus_vtvm, hstatus_v_bit {
        ignore_bins not_hs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.vs_mode};
    }

    // VTVM trap in VS-mode accessing satp
    cp_vtvm_vs: cross priv_mode_s, csr_tvm, csrop, mstatus_tvm, hstatus_v_bit {
        ignore_bins not_satp = binsof(csr_tvm) intersect {12'h680};  // Only satp for VTVM
        ignore_bins not_vs = binsof(hstatus_v_bit) intersect {hstatus_v_bit.hs_mode};
    }
endgroup

// Covergroup for mtval non-zero test
covergroup ZicsrH_mtval_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    csrrw_mtval: coverpoint ins.current.insn {
        wildcard bins csrrw = {32'b001101000011_?????_001_?????_1110011};  // csrrw to mtval
    }

    mtval_ones: coverpoint ins.current.rs1_val {
        bins all_ones = {'1};
    }

    // Verify mtval is writable (not read-only zero)
    cp_mtval_nonzero: cross priv_mode_m, csrrw_mtval, mtval_ones;
endgroup

// Covergroup for hypervisor privileged instructions
covergroup ZicsrH_hprivinst_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "../general/RISCV_coverage_standard_coverpoints.svh"

    // Hypervisor load/store instructions
    hv_loadstore: coverpoint {ins.current.insn[31:25], ins.current.insn[24:20]} iff (ins.current.insn[6:0] == 7'b1110011 && ins.current.insn[14:12] == 3'b100) {
        bins hlv_b   = {7'b0110000, 5'b00000};
        bins hlv_bu  = {7'b0110000, 5'b00001};
        bins hlv_h   = {7'b0110000, 5'b00010};
        bins hlv_hu  = {7'b0110000, 5'b00011};
        bins hsv_b   = {7'b0110000, 5'b00100};
        bins hsv_h   = {7'b0110000, 5'b00110};
        bins hlvx_hu = {7'b0110000, 5'b00111};
        bins hlv_w   = {7'b0110000, 5'b01000};
        `ifdef XLEN64
        bins hlv_wu  = {7'b0110000, 5'b01001};
        `endif
        bins hsv_w   = {7'b0110000, 5'b01010};
        bins hlvx_wu = {7'b0110000, 5'b01011};
        `ifdef XLEN64
        bins hlv_d   = {7'b0110000, 5'b01100};
        bins hsv_d   = {7'b0110000, 5'b01110};
        `endif
    }

    // HFENCE instructions
    hfence: coverpoint ins.current.insn {
        bins hfence_vvma = {32'h22000073};  // rs1=x0, rs2=x0
        bins hfence_gvma = {32'h62000073};  // rs1=x0, rs2=x0
    }

    // Test HV instructions in different privilege modes
    cp_hv_loadstore_m: cross priv_mode_m, hv_loadstore;
    cp_hv_loadstore_hs: cross priv_mode_s, hv_loadstore {
        ignore_bins not_hs = binsof(priv_mode_s) intersect {2'b00, 2'b11};
    }

    cp_hfence_m: cross priv_mode_m, hfence;
    cp_hfence_hs: cross priv_mode_s, hfence {
        ignore_bins not_hs = binsof(priv_mode_s) intersect {2'b00, 2'b11};
    }
endgroup

// Main sampling function for Hypervisor Zicsr
function void zicsrh_sample(int hart, int issue, ins_t ins);
    ZicsrH_csr_access_cg.sample(ins);
    ZicsrH_csr_walk_cg.sample(ins);
    ZicsrH_replica_cg.sample(ins);
    ZicsrH_hstatus_vgein_cg.sample(ins);
    ZicsrH_vscause_cg.sample(ins);
    ZicsrH_vsstatus_cg.sample(ins);
    ZicsrH_tvm_cg.sample(ins);
    ZicsrH_mtval_cg.sample(ins);
    ZicsrH_hprivinst_cg.sample(ins);
endfunction
