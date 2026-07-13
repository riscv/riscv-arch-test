// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_vcompress_vstart_nonzero
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // vcompress with non-zero vstart must raise illegal instruction exception
    vstart_nonzero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        bins nonzero = {[1:$]};
    }


    vcompress_funct6_dea7bb: coverpoint ins.current.insn[31:26] {
        bins vcompress = {6'b010111};
    }

    vcompress_funct3_dea7bb: coverpoint ins.current.insn[14:12] {
        bins opmvv = {3'b010};
    }

    cp_ssstrictv_vcompress_vstart_nonzero: cross vstart_nonzero, vcompress_funct6_dea7bb, vcompress_funct3_dea7bb;

//// end cp_ssstrictv_vcompress_vstart_nonzero ///////////////////////////////////////////////////////////////
