# Custom Scripts — Full API Reference

Read `GUIDE.md` first for the core patterns. This file has the complete lookup tables.

## Additional Patterns

### VL/LMUL Sweep

```python
for l_exp in range(4):
    for vl in ["vlmax", 1, "random"]:
        cur_lmul = 2 ** l_exp
        data = randomizeVectorInstructionData(test, sew, getLengthSuiteTestCount(), suite="length", lmul=cur_lmul)
        writeTest(f"lmul={cur_lmul} vl={vl}", test, data, sew=sew, lmul=cur_lmul, vl=vl)
        incrementLengthtestCount()
        vsAddressCount("length")
```

### Overlap Test (widening — vd overlaps vs2 top)

```python
import math
emul = 2 * lmul
vd = randint(0, math.floor((vreg_count - 1) / emul)) * emul
vs2 = vd + lmul
vs1 = randomizeOngroupVectorRegister(test, vs2, vd, lmul=lmul)
data = randomizeVectorInstructionData(test, sew, getBaseSuiteTestCount(), vd=vd, vs2=vs2, vs1=vs1, lmul=lmul)
writeTest(f"overlap lmul={lmul}", test, data, sew=sew, lmul=lmul)
incrementBasetestCount()
vsAddressCount()
```

### Edge Value Test

```python
from vector_testgen_common import vedgesemul1
for v in vedgesemul1:
    data = randomizeVectorInstructionData(test, sew, getBaseSuiteTestCount(), lmul=1, vs2_val_pointer=v)
    writeTest(f"edge {v}", test, data, sew=sew, vl=1, lmul=1)
    incrementBasetestCount()
    vsAddressCount()
```

### registerCustomData()

```python
from vector_testgen_common import registerCustomData
registerCustomData("my_label", [0x47F0000000000000], element_size=64)
# Then use: vs2_val_pointer="my_label"
```

Creates a data label in `.data` section. Values replicated to fill maxVLEN. Labels cleared between files automatically.

## Edge Value Sets

Import from `vector_testgen_common`:

| Name                                  | Description                               |
| ------------------------------------- | ----------------------------------------- |
| `vedgesemul1` through `vedgesemul8`   | Integer vector corners at various EMUL    |
| `vedgesemulf2` through `vedgesemulf8` | Integer corners for fractional EMUL       |
| `vedgeseew1`                          | Mask (EEW=1) corners                      |
| `v_edges_ls`                          | Load/store address corners                |
| `vfedgesemul1`, `vfedgesemul2`        | FP vector corners                         |
| `fedges`, `fedgesD`, `fedgesH`        | Scalar FP corners (32/64/16-bit) as dicts |
| `vxrmList`                            | Fixed-point rounding modes dict           |
| `frmList`                             | FP rounding modes dict                    |

## FP Vector Data Labels

Pre-defined labels (append `_emul1` for EMUL=1): `vs_corner_f_pos0`, `vs_corner_f_neg0`, `vs_corner_f_pos1`, `vs_corner_f_neg1`, `vs_corner_f_posminnorm`, `vs_corner_f_negmaxnorm`, `vs_corner_f_posinfinity`, `vs_corner_f_neginfinity`, `vs_corner_f_pos0p5`, `vs_corner_f_pos1p5`, `vs_corner_f_neg2`, `vs_corner_f_pi`, `vs_corner_f_twoToEmax`, `vs_corner_f_onePulp`, `vs_corner_f_largestsubnorm`, `vs_corner_f_negSubnormLeadingOne`, `vs_corner_f_min_subnorm`, `vs_corner_f_canonicalQNaN`, `vs_corner_f_negNoncanonicalQNaN`, `vs_corner_f_sNaN_payload1`

## Instruction Category Lists

Import from `vector_testgen_common`:

| List                               | Content                         |
| ---------------------------------- | ------------------------------- |
| `vvvmtype`, `vvxmtype`, `vvimtype` | VV/VX/VI arithmetic             |
| `vs1ins`                           | Instructions using vs1          |
| `narrowins`                        | Narrowing instructions          |
| `vd_widen_ins`, `vs2_widen_ins`    | Widening sub-categories         |
| `vfloattypes`                      | All FP vector instructions      |
| `vector_loads`, `vector_stores`    | Load/store instructions         |
| `indexed_loads`, `indexed_stores`  | Indexed load/store              |
| `maskins`, `mmins`                 | Mask instructions               |
| `imm_31`                           | Unsigned 5-bit immediate (0-31) |
| `vextins`                          | Extension instructions          |

## Suite Convention

- **"base"**: Register encodings, edge values, overlaps. Usually `vl=1`.
- **"length"**: VL/LMUL, masking, agnostic bits. Usually `vl="vlmax"` or `"random"`.
