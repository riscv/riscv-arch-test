    // Custom coverpoints for Store Conditional

    cp_prev_lr : coverpoint ({ins.prev.inst_name == "lr.w", ins.prev.inst_name == "lr.d"}) {
        bins lr_w = {2'b10};  // previous instruction was load reserved
        `ifdef XLEN64
            bins lr_d = {2'b01};
        `endif
    }

    cp_sc_fail : coverpoint (ins.current.rd_val) {
        bins pass = {0};
        bins fail = {[1:$]};
    }
    cp_address_difference : coverpoint {ins.current.rs1_val - ins.prev.rs1_val}[7:3] iff (ins.current.rs1_val[31:8] == ins.prev.rs1_val[31:8]) {
        // difference between lr and sc address may or may not fall in reservation set size
    }
    cp_custom_aqrl : coverpoint ins.current.insn[26:25]  iff (ins.trap == 0 )  {
        // Combinations of acquire and release
        ignore_bins aq_norl = {2'b10};
    }
    cp_custom_sc_after_sc : coverpoint (ins.prev.inst_name == "sc.w" | ins.prev.inst_name == "sc.d") {
        // previous instruction was store conditional
    }
    cp_custom_sc_after_store : coverpoint (ins.prev.insn[14:12]) iff (ins.prev.insn[6:0] == 7'b0100011) {
        // previous instruction was a store
        bins sb = {3'b000};
        bins sh = {3'b001};
        bins sw = {3'b010};
        `ifdef XLEN64
            bins sd = {3'b011};
        `else
            ignore_bins b3 = {3'b011};
        `endif
        wildcard ignore_bins badbin = {3'b1??};
    }
    cp_custom_sc_after_load : coverpoint (ins.prev.insn[14:12]) iff (ins.prev.insn[6:0] == 7'b0000011) {
        // previous instruction was a store
        bins lb  = {3'b000};
        bins lh  = {3'b001};
        bins lhu = {3'b101};
        bins lw  = {3'b010};
        `ifdef XLEN64
            bins lwu = {3'b110};
            bins ld  = {3'b011};
        `endif
    }
    cp_custom_sc_lrsc : cross cp_prev_lr, cp_sc_fail;
    cp_custom_sc_addresses : cross cp_prev_lr, cp_address_difference;
