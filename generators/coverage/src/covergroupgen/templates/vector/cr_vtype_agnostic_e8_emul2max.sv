    //////////////////////////////////////////////////////////////////////////////////
    // cr_vtype_agnostic_e8_emul2max
    //////////////////////////////////////////////////////////////////////////////////

    // _emul*max is an artifact of test generation necessary to specify to ensure instructs that trap aren't generated

    cp_csr_vtype_vta : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vta")[0]  iff (ins.trap == 0)  {
        // Value of VTYPE.vta (vector tail agnostic)
    }

    cp_csr_vtype_vma : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vma")[0]  iff (ins.trap == 0)  {
        // Value of VTYPE.vma (vector mask agnostic)
    }

    mask_enabled_agnostic: coverpoint ins.current.insn[25] {
        bins enabled = {1'b0};
    }

    cr_vtype_agnostic_e8_emul2max : cross cp_csr_vtype_vta,cp_csr_vtype_vma,mask_enabled_agnostic iff (ins.trap == 0 )  {
        // Cross coverage of vector tail and mask agnostic behaviors
    }

    //// end cr_vtype_agnostic_e8_emul2max////////////////////////////////////////////////
