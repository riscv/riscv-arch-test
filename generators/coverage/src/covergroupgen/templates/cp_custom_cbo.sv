    // Custom coverpoints for cbo.  Coverpoint just checks that instruction was executed
    // but test is more comprehensive, writing and reading back consecutive words

    cp_custom_cbo : coverpoint ins.current.insn  {
        wildcard bins cbo_op  = {32'b000000000????????010000000001111};
    }
