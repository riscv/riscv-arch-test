    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_address_fault
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Helper: valid vector type (vill=0)
    vtype_valid_20000f: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    // Main condition: instruction trapped (load/store access or page fault detected via mcause).
    // For indexed instructions with unsupported EEW (exceeds MAXINDEXEEW), the instruction
    // traps at decode with ILLEGAL_INSTRUCTION, not during memory access.
    // Accept ILLEGAL_INSTRUCTION for these cases. mop field insn[27:26]: 01=indexed-unordered, 11=indexed-ordered.
    trap_occurred_20000f: coverpoint (
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == LOAD_ACCESS_FAULT |
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == STORE_AMO_ACCESS_FAULT |
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == LOAD_PAGE_FAULT |
        get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == STORE_AMO_PAGE_FAULT
        `ifndef MAXINDEXEEW_GE64
        | (ins.current.insn[27:26] inside {2'b01, 2'b11} &&
           ins.current.insn[14:12] inside {3'b111
               `ifndef MAXINDEXEEW_GE32
               , 3'b110
               `ifndef MAXINDEXEEW_GE16
               , 3'b101
               `endif
               `endif
           } &&
           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == ILLEGAL_INSTRUCTION)
        `endif
    ) {
        bins trapped = {1'b1};
    }

    // Cross: valid vtype AND trap occurred
    cp_exceptionsv_address_fault: cross vtype_valid_20000f, trap_occurred_20000f;

//// end cp_exceptionsv_address_fault ///////////////////////////////////////////////////////////////////////////
