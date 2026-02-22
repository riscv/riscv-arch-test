    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_maskLS
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector mask load/store operations

    v0_eq_1: coverpoint unsigned'(ins.current.v0_val) {
        bins one = {1};
    }

    rs1_at_fault_addr: coverpoint (unsigned'(ins.current.rs1_val) == `RVMODEL_ACCESS_FAULT_ADDRESS) {
        bins not_fault_addr = {1'b1};
    }

    vl_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins one = {1};
    }

    vl_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        bins two = {2};
    }

    vstart_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        bins one = {1};
    }

    no_trap : coverpoint (ins.trap == 0) {
        bins zero = {0};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins unmasked = {1'b0};
    }

    v0_eq_2: coverpoint unsigned'(ins.current.v0_val) {
        bins two = {2};
    }

    vtype_prev_vill_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins vill_not_set = {0};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_all_sewgt8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
          `ifdef SEW16_SUPPORTED
          bins sixteen    = {1};
          `endif
          `ifdef SEW32_SUPPORTED
          bins thirtytwo  = {2};
          `endif
          `ifdef SEW64_SUPPORTED
          bins sixtyfour  = {3};
          `endif

          // Make sure bin is always hit if the sew isn't supported
          `ifndef SEW16_SUPPORTED
          `ifndef SEW32_SUPPORTED
          `ifndef SEW64_SUPPORTED
          bins sew_not_supported  = {111:000};
          `endif
          `endif
          `endif

      }

    vtype_all_lmulgt1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_custom_maskLS_emul_ge_16             : cross std_vec, vtype_all_lmulgt1, vtype_all_sewgt8;
    cp_custom_maskLS_tail_no_exception      : cross std_vec, vtype_lmul_2, vl_1, mask_enabled, v0_eq_1, rs1_at_fault_addr;
    cp_custom_maskLS_prestart_no_exception  : cross vtype_prev_vill_clear, vtype_lmul_2, vl_2, vstart_1, mask_enabled, rs1_at_fault_addr, no_trap, v0_eq_2;

    //// end cp_custom_maskLS////////////////////////////////////////////////
