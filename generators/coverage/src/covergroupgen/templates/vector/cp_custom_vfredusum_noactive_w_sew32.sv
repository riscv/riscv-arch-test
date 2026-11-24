    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfredusum_noactive_w_sew32
    // Unordered sum reductions with no active elements: vs1[0] edges (cp_vs1_edges_f_emul2_sew32) x frm
    //////////////////////////////////////////////////////////////////////////////////

    vfredusum_noactive_mask : coverpoint vred_mask_class(ins.hart, ins.issue, ins.current.vm, ins.prev.v_wdata[0]) {
        bins none_active = {vred_none_active};
    }

    vfredusum_noactive_frm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_FRM) {
        bins rne = {3'b000};
        bins rdn = {3'b010};
    }

    cp_custom_vfredusum_noactive_w_sew32 : cross std_vec, cp_vs1_edges_f_emul2_sew32, vfredusum_noactive_mask, vfredusum_noactive_frm iff (ins.trap == 0);

    //// end cp_custom_vfredusum_noactive_w_sew32 ////////////////////////////////////////////////
