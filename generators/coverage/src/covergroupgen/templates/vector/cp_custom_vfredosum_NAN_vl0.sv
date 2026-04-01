
        // Positive qNaN range: sign=0, exponent all 1s, mantissa MSB=1
        // SEW16: 0x7E00..0x7FFF, SEW32: 0x7FC00000..0x7FFFFFFF, SEW64: 0x7FF8000000000000..0x7FFFFFFFFFFFFFFF
        //
        // For non-widening (vfredosum), vs1 is at SEW — get_vr_element_zero matches.
        // For widening (vfwredosum), vs1 accumulator is at 2*SEW — get_vr_element_zero_widen matches.
        // We check both; either matching satisfies the bin.
        // Note: no widen check for VFCUSTOM64 (no SEW=128 exists).

`ifndef COVER_VFCUSTOM64
        vs1_0_qNAN : coverpoint
        `ifdef COVER_VFCUSTOM16
                (get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) >= 64'h0000_0000_0000_7E00
                 && get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) <= 64'h0000_0000_0000_7FFF)
                || (get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs1_val) >= 64'h0000_0000_7FC0_0000
                    && get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs1_val) <= 64'h0000_0000_7FFF_FFFF)
        `elsif COVER_VFCUSTOM32
                (get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) >= 64'h0000_0000_7FC0_0000
                 && get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) <= 64'h0000_0000_7FFF_FFFF)
                || (get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs1_val) >= 64'h7FF8_0000_0000_0000
                    && get_vr_element_zero_widen(ins.hart, ins.issue, ins.current.vs1_val) <= 64'h7FFF_FFFF_FFFF_FFFF)
        `endif
        {
                bins posQNaN = {1};
        }

        fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fflags", "fflags") {
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
`else
        `ifdef FLEN64
        vs1_0_qNAN : coverpoint
                (get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val) inside {
                        [64'h7FF8_0000_0000_0000:64'h7FFF_FFFF_FFFF_FFFF]
                })
        {
                bins posQNaN = {1};
        }

        fp_flags_clear : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fflags", "fflags") {
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
        `endif
`endif
