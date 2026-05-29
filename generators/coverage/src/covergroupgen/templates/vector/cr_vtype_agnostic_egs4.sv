    //////////////////////////////////////////////////////////////////////////////////
    // cr_vtype_agnostic_egs4
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_vta_egs4 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vta")  iff (ins.trap == 0)  {
        bins undisturbed = {0};
        bins agnostic    = {1};
    }

    cp_csr_vtype_vma_egs4 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vma")  iff (ins.trap == 0)  {
        bins undisturbed = {0};
        bins agnostic    = {1};
    }

    mask_enabled_agnostic_egs4: coverpoint ins.current.insn[25] {
        bins enabled = {1'b1};
    }

    cr_vtype_agnostic_egs4 : cross cp_csr_vtype_vta_egs4, cp_csr_vtype_vma_egs4, mask_enabled_agnostic_egs4  iff (ins.trap == 0)  {
        // Cross coverage of vector tail and mask agnostic behaviors (EGS=4)
    }

    //// end cr_vtype_agnostic_egs4////////////////////////////////////////////////
