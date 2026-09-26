    // Custom coverpoints for fence

    // Encodings with a nonzero fm, rd or rs1 field. fm = 0, rd = rs1 = x0 is cp_custom_fence_pred_succ.
    cp_custom_fence_reserved : coverpoint ins.current.insn  {
        bins fence_tso_rw_rw  = {32'h8330000f}; // fence.tso
        bins fence_nonzerors1 = {32'h0331000f}; // nonzero rs should behave as fence
        bins fence_nonzerord  = {32'h0330008f}; // nonzero rd should behave as fence
        bins fence_fm         = {32'h1330000f}; // reserved fm should behave as fence
        bins fence_hint0a     = {32'h0031000f}; // fence with rd = x0, rs1 != x0, fm = 0, pred = 0 is a hint
        bins fence_hint0b     = {32'h0301000f}; // fence with rd = x0, rs1 != x0, fm = 0, succ = 0 is a hint
        bins fence_hint1a     = {32'h0030008f}; // fence with rd != x0, rs1 = x0, fm = 0, pred = 0 is a hint
        bins fence_hint1b     = {32'h0300008f}; // fence with rd != x0, rs1 = x0, fm = 0, succ = 0 is a hint
        bins fence_tso_r_r    = {32'h8110000f}; // fence.tso with r, r should behave as fence
    }

    // Every pred x succ combination with fm = 0 and rd = rs1 = x0.
    // Reserved settings execute as a fence; pred = 0 or succ = 0 are HINTs (pred = W, succ = 0 is PAUSE).
    cp_custom_fence_pred_succ : coverpoint ins.current.insn[27:20] iff (ins.current.insn[31:28] == 4'b0000 &
                                                                        ins.current.insn[19:15] == 5'b00000 &
                                                                        ins.current.insn[11:7] == 5'b00000 &
                                                                        ins.trap == 0) {
        bins pred_succ[] = {[0:255]}; // insn[27:24] = pred (IORW), insn[23:20] = succ (IORW)
    }
