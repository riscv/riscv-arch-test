// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcompress_vstart_report_zero
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Verify vcompress trap always reports vstart of 0
    vcompress_funct6: coverpoint ins.current.insn[31:26] {
        bins vcompress = {6'b010111};
    }

    vcompress_funct3: coverpoint ins.current.insn[14:12] {
        bins opmvv = {3'b010};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    vstart_zero_after: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vstart", "vstart") {
        bins zero = {0};
    }

    cp_ssstrictv_vcompress_vstart_report_zero: cross vcompress_funct6, vcompress_funct3, trap_occurred, vstart_zero_after;

//// end cp_ssstrictv_vcompress_vstart_report_zero ///////////////////////////////////////////////////////////
