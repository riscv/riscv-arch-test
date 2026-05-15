// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_reserved_vcsrs
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Access to reserved vector CSR addresses 0x00B-0x00E must raise illegal instruction trap
    reserved_vcsr_addr: coverpoint ins.current.insn[31:20] {
        bins csr_00B = {12'h00B};
        bins csr_00C = {12'h00C};
        bins csr_00D = {12'h00D};
        bins csr_00E = {12'h00E};
    }

    trap_occurred: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_reserved_vcsrs: cross reserved_vcsr_addr, trap_occurred;

//// end cp_ssstrictv_reserved_vcsrs /////////////////////////////////////////////////////////////////////
