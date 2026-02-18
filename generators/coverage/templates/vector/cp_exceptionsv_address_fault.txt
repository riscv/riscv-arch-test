// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_exceptionsv_address_fault
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Helper: valid vector type (vill=0)
    vtype_valid: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    // Main condition: instruction trapped
    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    // Cross: valid vtype AND trap occurred
    cp_exceptionsv_address_fault: cross vtype_valid, trap_occurred;

//// end cp_exceptionsv_address_fault ///////////////////////////////////////////////////////////////////////////
