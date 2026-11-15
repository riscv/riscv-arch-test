    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_address_fault
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Helper: valid vector type (vill=0)
    vtype_valid_20000f: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins valid = {1'b0};
    }

    illegal_address: coverpoint ins.current.rs1_val {
        bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }

    // Cross: valid vtype AND trap occurred
    cp_exceptionsv_address_fault: cross vtype_valid_20000f, illegal_address;

//// end cp_exceptionsv_address_fault ///////////////////////////////////////////////////////////////////////////
