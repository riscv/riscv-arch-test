# cp_custom_FpRecipEst_flag_edges — 94.28% Coverage

## Status

94.28% on both rv32 and rv64 for SEW16 and SEW32. SEW64 100%.

## Uncovered Bins (4)

- `vs1_0_pos_sub_tiny` — smallest positive subnormal (SEW16: 0x0001, SEW32: 0x00000001)
- `vs1_0_pos_sub_big` — largest positive subnormal (SEW16: 0x03FF, SEW32: 0x007FFFFF)
- `vs1_0_neg_sub_tiny` — smallest negative subnormal (SEW16: 0x8001, SEW32: 0x80000001)
- `vs1_0_neg_sub_big` — largest negative subnormal (SEW16: 0x83FF, SEW32: 0x807FFFFF)

## Analysis

- Script generates correct data labels with exact hex values matching template bins
- Generated assembly loads correct values via `registerCustomData` + `vs2_val_pointer`
- Data section `.word` values confirmed correct (e.g., `0x00008001` for neg_sub_tiny SEW16)
- `vle16.v` loads element 0 correctly from memory (little-endian, lowest 16 bits)
- `get_vr_element_zero()` logic confirmed correct: `{48'b0, val[15:0]}` for SEW16
- RVVI register file mirror (`v_wdata`) maintains state across instructions correctly
- All non-subnormal bins (normals, zeros, infinities, NaN) covered at 100%

## Possible Root Causes (not yet confirmed)

1. **Sail model subnormal behavior**: Sail might report vector register values differently for subnormal FP inputs (unlikely since it's a load, not FP operation)
2. **RVVI trace parsing**: The sail-to-rvvi converter might truncate or modify vector register hex values in certain cases
3. **Coverage tool sampling**: SystemVerilog coverage sampling might have a timing issue where the subnormal value is overwritten before sampling
4. **Value equality**: Potential bit-width mismatch between the coverpoint bin type and the `get_vr_element_zero()` return value

## Recommended Next Steps

1. Re-run coverage and examine the raw RVVI trace (`*.trace` file) for the subnormal test cases
2. Add `$display` debugging in the coverage template to print the value returned by `get_vr_element_zero()` for each sample
3. Check if the Sail model's `vle16.v` with TA mode correctly reports subnormal values in `v_wdata`
