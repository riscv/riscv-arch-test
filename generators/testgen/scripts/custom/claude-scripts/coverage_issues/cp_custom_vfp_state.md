# Coverage Issue: cp_custom_vfp_state (cp_custom_f_freg_write_vl0)

## Template: `generators/coverage/templates/vector/cp_custom_vfp_state.sv`

## Status: 0% on both crosses, 5/8 individual bins covered

## Individual Bin Coverage

| Bin                       | Status | Notes                                                       |
| ------------------------- | ------ | ----------------------------------------------------------- |
| cp_asm_count              | 100%   | Covered                                                     |
| std_vec                   | 100%   | Covered (vl=1 test)                                         |
| fd_changed_value          | 100%   | Covered (fd changes from vs2 data)                          |
| fp_flags_clear            | 100%   | Covered (fflags=0 before instruction)                       |
| vfp_state_vfsqrt_flag_set | 0%     | **Impossible** for vfmv.f.s — checks `insn == "vfrsqrt7.v"` |
| mstatus_prev_clean        | 0%     | **Impossible** — see below                                  |

## Root Cause: `mstatus_prev_clean` is impossible to satisfy

The template defines:

```sv
mstatus_prev_clean : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
    bins clear = {0};
}
```

This checks `mstatus.VS == 0`, which means the vector extension is **Off**. Per RISC-V spec, when VS=Off, all vector instructions (including `vfmv.f.s`) cause an illegal instruction trap. But `std_vec` requires `ins.trap == 0`. So the cross:

```sv
cp_custom_vfp_register_state_mstatus_dirty : cross std_vec, fd_changed_value, mstatus_prev_clean;
```

...requires both "no trap" and "VS=Off", which is contradictory.

## Possible Fix

The bin name suggests the intent is to check for VS=**Clean** (value 2), not VS=**Off** (value 0):

```sv
mstatus_prev_clean : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") {
    bins clean = {2};  // Was: bins clear = {0};
}
```

Even with this fix, hitting `mstatus.vs == 2` (Clean) requires special setup: the test must execute some vector instruction to move VS from Initial(1) to Dirty(3), then write mstatus.VS=2 via CSR write, then execute vfmv.f.s. The current test framework doesn't support this kind of multi-step CSR manipulation.

## Second Cross Also Impossible

`cp_custom_vfp_csr_state_mstatus_dirty` requires `vfp_state_vfsqrt_flag_set` which checks `insn == "vfrsqrt7.v"`. Since this template is used for `vfmv.f.s`, this bin can never be hit.
