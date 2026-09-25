    cp_cntr_hpm : coverpoint ins.current.insn[31:20] iff (ins.get_gpr_reg(ins.current.rs1) == x0) {
        `ifdef UDB_HPM_COUNTER_EN_3
            bins hpmcounter3  = {12'hC03};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_4
            bins hpmcounter4  = {12'hC04};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_5
            bins hpmcounter5  = {12'hC05};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_6
            bins hpmcounter6  = {12'hC06};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_7
            bins hpmcounter7  = {12'hC07};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_8
            bins hpmcounter8  = {12'hC08};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_9
            bins hpmcounter9  = {12'hC09};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_10
            bins hpmcounter10 = {12'hC0A};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_11
            bins hpmcounter11 = {12'hC0B};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_12
            bins hpmcounter12 = {12'hC0C};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_13
            bins hpmcounter13 = {12'hC0D};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_14
            bins hpmcounter14 = {12'hC0E};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_15
            bins hpmcounter15 = {12'hC0F};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_16
            bins hpmcounter16 = {12'hC10};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_17
            bins hpmcounter17 = {12'hC11};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_18
            bins hpmcounter18 = {12'hC12};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_19
            bins hpmcounter19 = {12'hC13};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_20
            bins hpmcounter20 = {12'hC14};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_21
            bins hpmcounter21 = {12'hC15};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_22
            bins hpmcounter22 = {12'hC16};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_23
            bins hpmcounter23 = {12'hC17};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_24
            bins hpmcounter24 = {12'hC18};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_25
            bins hpmcounter25 = {12'hC19};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_26
            bins hpmcounter26 = {12'hC1A};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_27
            bins hpmcounter27 = {12'hC1B};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_28
            bins hpmcounter28 = {12'hC1C};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_29
            bins hpmcounter29 = {12'hC1D};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_30
            bins hpmcounter30 = {12'hC1E};
        `endif
        `ifdef UDB_HPM_COUNTER_EN_31
            bins hpmcounter31 = {12'hC1F};
        `endif
        `ifdef UDB_MXLEN_32
            `ifdef UDB_HPM_COUNTER_EN_3
                bins hpmcounter3h  = {12'hC83};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_4
                bins hpmcounter4h  = {12'hC84};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_5
                bins hpmcounter5h  = {12'hC85};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_6
                bins hpmcounter6h  = {12'hC86};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_7
                bins hpmcounter7h  = {12'hC87};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_8
                bins hpmcounter8h  = {12'hC88};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_9
                bins hpmcounter9h  = {12'hC89};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_10
                bins hpmcounter10h = {12'hC8A};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_11
                bins hpmcounter11h = {12'hC8B};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_12
                bins hpmcounter12h = {12'hC8C};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_13
                bins hpmcounter13h = {12'hC8D};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_14
                bins hpmcounter14h = {12'hC8E};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_15
                bins hpmcounter15h = {12'hC8F};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_16
                bins hpmcounter16h = {12'hC90};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_17
                bins hpmcounter17h = {12'hC91};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_18
                bins hpmcounter18h = {12'hC92};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_19
                bins hpmcounter19h = {12'hC93};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_20
                bins hpmcounter20h = {12'hC94};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_21
                bins hpmcounter21h = {12'hC95};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_22
                bins hpmcounter22h = {12'hC96};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_23
                bins hpmcounter23h = {12'hC97};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_24
                bins hpmcounter24h = {12'hC98};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_25
                bins hpmcounter25h = {12'hC99};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_26
                bins hpmcounter26h = {12'hC9A};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_27
                bins hpmcounter27h = {12'hC9B};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_28
                bins hpmcounter28h = {12'hC9C};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_29
                bins hpmcounter29h = {12'hC9D};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_30
                bins hpmcounter30h = {12'hC9E};
            `endif
            `ifdef UDB_HPM_COUNTER_EN_31
                bins hpmcounter31h = {12'hC9F};
            `endif
        `endif
    }
