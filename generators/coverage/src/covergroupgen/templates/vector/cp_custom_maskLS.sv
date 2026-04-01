    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_maskLS
    //////////////////////////////////////////////////////////////////////////////////

    // Mask load/store with EMUL >= 16 (LMUL > 1 and SEW > 8)

    vtype_all_sewgt8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
          `ifdef COVER_VLSCUSTOM16
          bins sixteen    = {1};
          `endif
          `ifdef COVER_VLSCUSTOM32
          bins thirtytwo  = {2};
          `endif
          `ifdef COVER_VLSCUSTOM64
          bins sixtyfour  = {3};
          `endif

          `ifndef COVER_VLSCUSTOM16
          `ifndef COVER_VLSCUSTOM32
          `ifndef COVER_VLSCUSTOM64
          bins sew_not_supported  = {[1:3]};
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

    //// end cp_custom_maskLS////////////////////////////////////////////////
