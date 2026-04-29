    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_address_fault
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Helper: valid vector type (vill=0)
    vtype_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    // Main condition: instruction trapped (load/store access or page fault detected via mcause).
    // For indexed instructions with unsupported EEW (exceeds MAXINDEXEEW), the instruction
    // traps at decode with illegal instruction (mcause=2), not during memory access.
    // Accept mcause=2 for these cases. mop field insn[27:26]: 01=indexed-unordered, 11=indexed-ordered.&&
           ins.current.insn[14:12] inside {3'b111
               `ifndef MAXINDEXEEW_GE32
               , 3'b110
               `ifndef MAXINDEXEEW_GE16
               , 3'b101
               `endif
               `endif
           } &&
           get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mcause", "int") == 2)  // illegal instruction
        `endif
    ) {
        bins trapped = {1'b1};
    }

    // Cross: valid vtype AND trap occurred
    cp_exceptionsv_address_fault: cross vtype_valid, trap_occurred;

//// end cp_exceptionsv_address_fault ///////////////////////////////////////////////////////////////////////////
