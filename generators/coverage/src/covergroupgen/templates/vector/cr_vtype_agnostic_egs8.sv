    //////////////////////////////////////////////////////////////////////////////////
    // cr_vtype_agnostic_egs8
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_vta_egs8 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vta")[0]  iff (ins.trap == 0)  {
        // 0: undisturbed, 1: agnostic
    }

    cp_csr_vtype_vma_egs8 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vma")[0]  iff (ins.trap == 0)  {
        // 0: undisturbed, 1: agnostic
    }

    mask_enabled_agnostic_egs8: coverpoint ins.current.insn[25] {
        bins enabled = {1'b1};
    }

    cr_vtype_agnostic_egs8 : cross cp_csr_vtype_vta_egs8, cp_csr_vtype_vma_egs8, mask_enabled_agnostic_egs8  iff (ins.trap == 0)  {
        // Cross coverage of vector tail and mask agnostic behaviors (EGS=8)
    }

    //// end cr_vtype_agnostic_egs8 ////////////////////////////////////////////////
