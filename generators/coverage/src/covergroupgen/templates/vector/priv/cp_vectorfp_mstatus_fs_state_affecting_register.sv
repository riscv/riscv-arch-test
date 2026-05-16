    //////////////////////////////////////////////////////////////////////////////////
    // cp_vectorfp_mstatus_fs_state_affecting_register
    //
    // Intentionally empty: this coverpoint cannot be expressed in pure functional
    // coverage. The "state-affecting register" case (e.g. vfmv.f.s) requires
    // proving that mstatus.FS *transitioned* to Dirty as a result of the
    // vector-FP instruction writing an architectural f-register. The RISC-V
    // spec permits a legal always-Dirty implementation that hard-wires
    // mstatus.FS, so a coverage sample cannot distinguish "model correctly
    // transitioned FS" from "model is always-Dirty".
    //
    // The corresponding test sequence is still emitted by the priv test
    // generator (see generators/testgen/scripts/priv/cp_vectorfp_mstatus_fs_state_affecting_register.py)
    // so that a transitioning model can be cross-checked against an always-Dirty
    // model via signature comparison.
    //////////////////////////////////////////////////////////////////////////////////

    //// end cp_vectorfp_mstatus_fs_state_affecting_register////////////////////////////////////////////////
