    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_exceptionsv_address_fault_store
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS_STORE
        // Helper: valid vector type (vill=0)
        vtype_valid_20000f: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") {
            bins valid = {1'b0};
        }

        illegal_address: coverpoint ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS_STORE};
        }

        // Cross: valid vtype AND trap occurred
        cp_exceptionsv_address_fault: cross vtype_valid_20000f, illegal_address;
    `endif

//// end cp_exceptionsv_address_fault_store ///////////////////////////////////////////////////////////////////////////
