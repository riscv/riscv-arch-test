    //////////////////////////////////////////////////////////////////////////////////
    // cr_vtype_agnostic_e8_emul1max_nomask
    //////////////////////////////////////////////////////////////////////////////////

    // _emul*max is an artifact of test generation necessary to specify to ensure instructs that trap aren't generated

    cp_csr_vtype_vta : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vta")[0]  iff (ins.trap == 0)  {
        // Value of VTYPE.vta (vector tail agnostic)
        // 0: undisturbed, 1: agnostic
    }

    cp_csr_vtype_vma : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vma")[0]  iff (ins.trap == 0)  {
        // Value of VTYPE.vma (vector mask agnostic)
        // 0: undisturbed, 1: agnostic
    }

    not_maskable: coverpoint ins.current.insn[25] {
        // For instructions that cannot be masked (vm = 1)
        bins enabled = {1'b1};
    }

    cr_vtype_agnostic_e8_emul1max_nomask : cross cp_csr_vtype_vta,cp_csr_vtype_vma,not_maskable iff (ins.trap == 0 )  {
        // Cross coverage of vector tail and mask agnostic behaviors
    }

    //// end cr_vtype_agnostic_e8_emul1max_nomask////////////////////////////////////////////////
