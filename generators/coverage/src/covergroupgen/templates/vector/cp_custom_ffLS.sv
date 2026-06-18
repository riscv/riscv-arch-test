    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ffLS
    //////////////////////////////////////////////////////////////////////////////////

    // Fault-only-first load: fault on non-first element updates VL without trapping.
    // Per V spec §7.7: "If element 0 raises an exception, vl is not modified, and
    // the trap is taken. If an element > 0 raises an exception, the corresponding
    // trap is not taken, and the vector length vl is reduced to the index of the
    // element that would have raised an exception."
    //
    // Strategy: mask OFF element 0 (v0 bit 0 = 0) so element 0 does NOT access
    // memory. Element 1+ are active and access the fault address region, triggering
    // the vl-trimming behavior without trapping.

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS

    ffLS_valid: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0
    } {
        bins true = {1'b1};
    }

    ffLS_v0_eq_2: coverpoint unsigned'(ins.current.v0_val) {
        bins two = {2};
    }

    ffLS_mask_enabled: coverpoint ins.current.insn[25] {
        bins masked = {1'b0};
    }

    ffLS_vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    ffLS_vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }

    ffLS_rs1_at_fault_addr: coverpoint (unsigned'(ins.current.rs1_val) == `RVMODEL_ACCESS_FAULT_ADDRESS) {
        bins at_fault_addr = {1'b1};
    }

    cp_custom_ffLS_fault_addr : cross ffLS_valid, ffLS_vtype_lmul_2, ffLS_vl_max, ffLS_mask_enabled, ffLS_v0_eq_2, ffLS_rs1_at_fault_addr;

    `endif

    //// end cp_custom_ffLS////////////////////////////////////////////////
