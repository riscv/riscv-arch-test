
`ifdef H_SUPPORTED
    Sv_H_vsstage_cg = new(); Sv_H_vsstage_cg.set_inst_name("obj_Sv_H_vsstage");
    Sv_H_gstage_cg = new(); Sv_H_gstage_cg.set_inst_name("obj_Sv_H_gstage");
    Sv_H_twostage_cg = new(); Sv_H_twostage_cg.set_inst_name("obj_Sv_H_twostage");
    Sv_H_hlv_cg = new(); Sv_H_hlv_cg.set_inst_name("obj_Sv_H_hlv");
    Sv_H_csr_cg = new(); Sv_H_csr_cg.set_inst_name("obj_Sv_H_csr");
    Sv_H_fence_cg = new(); Sv_H_fence_cg.set_inst_name("obj_Sv_H_fence");
    `ifndef EXCLUDE_SM
        Sv_HSm_mprv_cg = new(); Sv_HSm_mprv_cg.set_inst_name("obj_Sv_HSm_mprv");
        Sv_HSm_trap_cg = new(); Sv_HSm_trap_cg.set_inst_name("obj_Sv_HSm_trap");
    `endif // EXCLUDE_SM
    `ifdef SV_HZICBO_ANY
        Sv_HZicbo_cg = new(); Sv_HZicbo_cg.set_inst_name("obj_Sv_HZicbo");
        Sv_HZicbo_envcfg_cg = new(); Sv_HZicbo_envcfg_cg.set_inst_name("obj_Sv_HZicbo_envcfg");
        `ifndef EXCLUDE_SM
            `ifdef SV_HZICBOSM_PMP
                Sv_HZicboSm_cg = new(); Sv_HZicboSm_cg.set_inst_name("obj_Sv_HZicboSm");
            `endif // SV_HZICBOSM_PMP
        `endif // EXCLUDE_SM
    `endif // SV_HZICBO_ANY
`endif // H_SUPPORTED
