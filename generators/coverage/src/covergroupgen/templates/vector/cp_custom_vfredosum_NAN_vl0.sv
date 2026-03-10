
        vs1_0_qNAN : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1) {
                `ifdef COVER_VFCUSTOM16
                bins posQNaN          = {[64'h07E00:64'h07FFF]};
                `endif
                `ifdef COVER_VFCUSTOM32
                bins posQNaN          = {[64'h0ffef_7E00:64'h0feef_7FFF]};
                `endif
                `ifdef COVER_VFCUSTOM64
                bins posQNaN          = {[64'hfffeffffffff_7E00:64'hffffffefffff_7FFF]};
                `endif
        }

        vfredosum : coverpoint ins.current.insn == "vfredosum.vs" {
                bins true = {1};
        }

        // vwfredosum : coverpoint ins.current.insn == "vwfredosum.vs" {
        //         bins true = {1};
        // }

        fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") {
                bins clear = {0};
        }

        vtype_prev_vill_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
                bins vill_not_set = {0};
        }

        vl_zero : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") == 0 {
                bins zero = {1};
        }

        vstart_zero : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 {
                bins zero = {1};
        }

        cp_custom_vfredosum_NAN_vl0 : cross fp_flags_clear, vtype_prev_vill_clear, vl_zero, vstart_zero, vs1_0_qNAN iff (ins.trap == 0);
