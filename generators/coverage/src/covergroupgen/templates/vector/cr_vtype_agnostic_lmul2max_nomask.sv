    cp_csr_vtype_vta : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vta")[0]  iff (ins.trap == 0)  {
    // Value of VTYPE.vta (vector tail agnostic)
    }

    cp_csr_vtype_vma : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vma")[0]  iff (ins.trap == 0)  {
        // Value of VTYPE.vma (vector mask agnostic)
    }

    cr_vtype_agnostic_lmul2max_nomask : cross cp_csr_vtype_vta,cp_csr_vtype_vma iff (ins.trap == 0 )  {
    // Cross coverage of vector tail and mask agnostic behaviors
    }
