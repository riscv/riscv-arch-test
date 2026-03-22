    // Custom coverpoints for cbo.  Coverpoint just checks that instruction was executed
    // but test is more comprehensive, writing and reading back consecutive words

    cp_custom_cbo : coverpoint ins.current.insn  {
        wildcard bins prefetch_i = {32'b???????00000?????110000000010011};
        wildcard bins prefetch_r = {32'b???????00000?????110000000010011};
        wildcard bins prefetch_w = {32'b???????00000?????110000000010011};
    }
