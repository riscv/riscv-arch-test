    // Custom coverpoints for cbo.  Coverpoint just checks that instruction was executed
    // but test is more comprehensive, writing and reading back consecutive words

    cp_custom_prefetch : coverpoint ins.current.insn  {
        wildcard bins prefetch = {32'b???????000???????110000000010011};
    }
