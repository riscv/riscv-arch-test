///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: James Kaden Cassidy jacassidy@hmc.edu June 12 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSVF

// NOTE on misa.V: a legal RISC-V implementation may report misa as all-zero
// (read-only). We therefore do NOT cross any coverpoint here with misa.V — the
// PRIV-mode test framework still drives the underlying tests and any model
// that hard-wires misa=0 will still produce a comparable signature.
//
// NOTE on the "nonaffecting" mstatus.FS state-transition coverpoint
// (vfadd.vv with vs1_val == vs2_val == 0): the spec permits a legal
// always-dirty implementation, so we cannot directly observe whether FS
// transitioned or stayed put. Such a coverpoint would be unimplementable in
// pure functional coverage. The corresponding test case still runs (see
// generators/testgen/src/testgen/priv/extensions/ExceptionsVf.py) so a
// transitioning model can be cross-checked against an always-dirty one via
// signature comparison. Same caveat applies to "state_affecting_register"
// and "state_affecting_csr": we cannot prove FS *changed*, only that the
// vector-FP instruction was sampled under each starting FS state.

covergroup ExceptionsVf_cg with function sample(ins_t ins);
    option.per_instance = 0;

    //////////////////////////////////////////////////////////////////////////////////
    // cp_mstatus_vs_off / cp_mstatus_fs_off
    // A vector floating-point instruction must raise illegal-instruction when
    // mstatus.VS = Off (V ext disabled) or when mstatus.FS = Off (FP ext disabled).
    // Each cross pins the *other* status field to non-Off so the trap can only be
    // attributed to the field under test.
    //////////////////////////////////////////////////////////////////////////////////

    vector_fp_instruction : coverpoint {ins.current.insn[14:12], ins.current.insn[6:0]} {
        bins fp_arithmetic_vv_opcode = {10'b001_1010111};
    }

    mstatus_vs_inactive : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins inactive = {0};
    }

    mstatus_vs_active : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
        bins active = {[1:3]};
    }

    mstatus_fs_inactive : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins inactive = {0};
    }

    mstatus_fs_active : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins active = {[1:3]};
    }

    cp_mstatus_vs_off : cross mstatus_vs_inactive, mstatus_fs_active, vector_fp_instruction;
    cp_mstatus_fs_off : cross mstatus_fs_inactive, mstatus_vs_active, vector_fp_instruction;

    //////////////////////////////////////////////////////////////////////////////////
    // cp_vectorfp_mstatus_fs_state
    // Sample a vector-FP instruction under each non-Off mstatus.FS starting state
    // (Initial=01, Clean=10, Dirty=11) with VS != Off. We cannot observe the FS
    // state transition directly (legal impls may hard-wire FS=Dirty), so this
    // coverpoint only ensures the test exercises every FS state. Combined with
    // signature-based cross-model checking, it catches transitioning-model bugs.
    //////////////////////////////////////////////////////////////////////////////////

    mstatus_fs_state : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins first = {1};
        bins clean   = {2};
        bins dirty   = {3};
    }

    cp_vectorfp_mstatus_fs_state : cross mstatus_fs_state, mstatus_vs_active, vector_fp_instruction;

endgroup


function void exceptionsvf_sample(int hart, int issue, ins_t ins);
    ExceptionsVf_cg.sample(ins);
endfunction
