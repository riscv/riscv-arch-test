    //////////////////////////////////////////////////////////////////////////////////
    // cp_vectorfp_mstatus_fs_state_nonaffecting
    //
    // Intentionally empty: this coverpoint cannot be expressed in pure functional
    // coverage. The "nonaffecting" case (e.g. vfadd.vv with vs1_val == vs2_val
    // == 0) requires proving that mstatus.FS *did not* transition out of
    // Initial/Clean as a result of the vector-FP instruction. The RISC-V spec
    // permits a legal always-Dirty implementation that hard-wires mstatus.FS,
    // so a coverage sample of FS after the instruction cannot distinguish
    // "model correctly left FS unchanged" from "model is always-Dirty".
    //
    // The corresponding test sequence is still emitted by the priv test
    // generator (see generators/testgen/scripts/priv/cp_vectorfp_mstatus_fs_state_nonaffecting.py)
    // so that a transitioning model can be cross-checked against an always-Dirty
    // model via signature comparison.
    //////////////////////////////////////////////////////////////////////////////////

    //// end cp_vectorfp_mstatus_fs_state_nonaffecting////////////////////////////////////////////////
