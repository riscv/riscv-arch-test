    //////////////////////////////////////////////////////////////////////////////////
    // cp_vectorfp_mstatus_fs_state_affecting_csr
    //
    // Intentionally empty: this coverpoint cannot be expressed in pure functional
    // coverage. The "state-affecting CSR" case (e.g. vfdiv.vv 1.0/0.0 raising
    // the DZ flag in fflags) requires proving that mstatus.FS *transitioned*
    // to Dirty as a result of the vector-FP instruction modifying a fp CSR.
    // The RISC-V spec permits a legal always-Dirty implementation that
    // hard-wires mstatus.FS, so a coverage sample cannot distinguish "model
    // correctly transitioned FS" from "model is always-Dirty".
    //
    // The corresponding test sequence is still emitted by the priv test
    // generator (see generators/testgen/scripts/priv/cp_vectorfp_mstatus_fs_state_affecting_csr.py)
    // so that a transitioning model can be cross-checked against an always-Dirty
    // model via signature comparison.
    //////////////////////////////////////////////////////////////////////////////////

    //// end cp_vectorfp_mstatus_fs_state_affecting_csr////////////////////////////////////////////////
