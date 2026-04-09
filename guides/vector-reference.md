# vector-reference.md — Vector Extension Encoding Reference

Quick-lookup tables for vector coverpoint development. Use this when you need exact encodings, bit positions, or formulas.

## CSR Field Encodings

### vtype Fields

| Field | Bits   | Values                            |
| ----- | ------ | --------------------------------- |
| vill  | XLEN-1 | 0=legal, 1=illegal                |
| vma   | 7      | 0=undisturbed, 1=agnostic         |
| vta   | 6      | 0=undisturbed, 1=agnostic         |
| vsew  | 5:3    | 000=e8, 001=e16, 010=e32, 011=e64 |
| vlmul | 2:0    | See LMUL table below              |

### vlmul Encoding

| LMUL | vlmul[2:0] | Decimal | Registers |
| ---- | ---------- | ------- | --------- |
| mf8  | 101        | 5       | 1 (1/8)   |
| mf4  | 110        | 6       | 1 (1/4)   |
| mf2  | 111        | 7       | 1 (1/2)   |
| m1   | 000        | 0       | 1         |
| m2   | 001        | 1       | 2         |
| m4   | 010        | 2       | 4         |
| m8   | 011        | 3       | 8         |

### vsew Encoding

| SEW | vsew[2:0] | Decimal |
| --- | --------- | ------- |
| e8  | 000       | 0       |
| e16 | 001       | 1       |
| e32 | 010       | 2       |
| e64 | 011       | 3       |

### Common CSR Addresses

| CSR     | Address |
| ------- | ------- |
| vtype   | 0xC21   |
| vl      | 0xC20   |
| vstart  | 0x008   |
| fcsr    | 0x003   |
| fflags  | 0x001   |
| frm     | 0x002   |
| mstatus | 0x300   |
| sstatus | 0x100   |

## Instruction Bit Fields

### Standard Vector Format

```
31    26 25  24   20 19   15 14  12 11    7 6     0
[funct6][vm][  vs2 ][vs1/rs1][funct3][ vd  ][opcode]
```

| Field       | Bits  | Description                   |
| ----------- | ----- | ----------------------------- |
| opcode      | 6:0   | Operation code                |
| vd/rd       | 11:7  | Destination register          |
| funct3      | 14:12 | Operation variant             |
| vs1/rs1/imm | 19:15 | Source 1 / scalar / immediate |
| vs2         | 24:20 | Source 2                      |
| vm          | 25    | 0=masked, 1=unmasked          |
| funct6      | 31:26 | Function code                 |

### Segment Load/Store Format

```
31  29 28 27 26 25  24   20 19   15 14  12 11    7 6     0
[ nf ][mew][mop][vm][lumop][  rs1 ][width][ vd  ][opcode]
```

| Field | Bits  | Description                                           |
| ----- | ----- | ----------------------------------------------------- |
| nf    | 31:29 | NFIELDS-1 (0=1 segment, 7=8 segments)                 |
| mop   | 27:26 | 00=unit, 01=indexed-unord, 10=strided, 11=indexed-ord |
| vm    | 25    | Mask (0=masked, 1=unmasked)                           |
| lumop | 24:20 | rs2 for strided/indexed                               |
| width | 14:12 | EEW: 000=8, 101=16, 110=32, 111=64                    |
| vd    | 11:7  | Destination vector register                           |

### Whole Register Move (vmv<nr>r.v) Encoding

| Instruction | simm[4:0] | NREG | Alignment Requirement  |
| ----------- | --------- | ---- | ---------------------- |
| vmv1r.v     | 00000 (0) | 1    | None                   |
| vmv2r.v     | 00001 (1) | 2    | vd, vs2 divisible by 2 |
| vmv4r.v     | 00011 (3) | 4    | vd, vs2 divisible by 4 |
| vmv8r.v     | 00111 (7) | 8    | vd, vs2 divisible by 8 |

### Instruction Type Encoding (funct3)

| funct3 | Type  | Source 2 | Source 1                       |
| ------ | ----- | -------- | ------------------------------ |
| 000    | OPIVV | vector   | vector                         |
| 001    | OPFVV | vector   | vector (FP)                    |
| 010    | OPMVV | vector   | vector (mask/reduction)        |
| 011    | OPIVI | vector   | immediate                      |
| 100    | OPIVX | vector   | scalar (x reg)                 |
| 101    | OPFVF | vector   | scalar (f reg)                 |
| 110    | OPMVX | vector   | scalar (x reg, mask/reduction) |
| 111    | OPCFG | -        | config instructions            |

## EMUL Formulas and Constraints

```
EMUL = (EEW / SEW) * LMUL

Widening destination:  EMUL_dst = 2 * LMUL  (EEW_dst = 2 * SEW)
Narrowing source:      EMUL_src = 2 * LMUL  (EEW_src = 2 * SEW)
Extension source:      EMUL_src = LMUL / N  (vzext.vfN, vsext.vfN where N=2,4,8)

Constraint: 1/8 <= EMUL <= 8
```

| Operation | LMUL Constraint | Reason                      |
| --------- | --------------- | --------------------------- |
| Widening  | LMUL <= 4       | Dest EMUL = 2\*LMUL <= 8    |
| Narrowing | LMUL <= 4       | Source EMUL = 2\*LMUL <= 8  |
| vzext.vf8 | LMUL >= 1       | Source EMUL = LMUL/8 >= 1/8 |
| vzext.vf4 | LMUL >= 1/2     | Source EMUL = LMUL/4 >= 1/8 |
| vzext.vf2 | LMUL >= 1/4     | Source EMUL = LMUL/2 >= 1/8 |
| Segment N | EMUL\*N <= 8    | Total registers <= 8 groups |

### EMUL \* NFIELDS Constraint

| LMUL | nf (NFIELDS) | EMUL\*NFIELDS | Status   |
| ---- | ------------ | ------------- | -------- |
| 8    | 1 (2)        | 16            | Reserved |
| 4    | 3 (4)        | 16            | Reserved |
| 2    | 7 (8)        | 16            | Reserved |

### VLMAX Formula

```
VLMAX = (VLEN * LMUL) / SEW
// Fractional LMUL: VLMAX = (VLEN * numerator) / (SEW * denominator)
```

## Load/Store EEW

| Instruction      | EEW |
| ---------------- | --- |
| vle8.v, vse8.v   | 8   |
| vle16.v, vse16.v | 16  |
| vle32.v, vse32.v | 32  |
| vle64.v, vse64.v | 64  |

| Instruction | Index EEW | Data EEW |
| ----------- | --------- | -------- |
| vluxei8.v   | 8         | SEW      |
| vluxei16.v  | 16        | SEW      |
| vluxei32.v  | 32        | SEW      |
| vluxei64.v  | 64        | SEW      |

## Element Index Regions

```
Index:    0        vstart       vl        VLMAX
          |           |         |           |
          |--prestart-|--body---|---tail----|

Prestart: i < vstart       -> skip, no exceptions
Body:     vstart <= i < vl -> execute if mask[i]=1
Tail:     vl <= i < VLMAX  -> skip (agnostic if vta=1)

Body Active:   body AND mask[i]=1  -> execute, update dest
Body Inactive: body AND mask[i]=0  -> skip (agnostic if vma=1)
```

## Shift Amount Extraction

| SEW | Bits Used | Mask |
| --- | --------- | ---- |
| 8   | 2:0       | 0x07 |
| 16  | 3:0       | 0x0F |
| 32  | 4:0       | 0x1F |
| 64  | 5:0       | 0x3F |

## Segment Load vd Constraints

Segment loads use NFIELDS consecutive register groups. vd must leave room:

| Segments | Max vd (EMUL=1) |
| -------- | --------------- |
| 2        | 30              |
| 3        | 29              |
| 4        | 28              |
| 5        | 27              |
| 6        | 26              |
| 7        | 25              |
| 8        | 24              |

## Floating-Point Edge Values

### Half-Precision (16-bit)

| Name       | Hex    | Description         |
| ---------- | ------ | ------------------- |
| pos0       | 0x0000 | +0.0                |
| neg0       | 0x8000 | -0.0                |
| pos1       | 0x3C00 | +1.0                |
| posInf     | 0x7C00 | +Infinity           |
| negInf     | 0xFC00 | -Infinity           |
| qNaN       | 0x7E00 | Quiet NaN           |
| sNaN       | 0x7D01 | Signaling NaN       |
| maxNorm    | 0x7BFF | Largest normalized  |
| minNorm    | 0x0400 | Smallest normalized |
| maxSubnorm | 0x03FF | Largest subnormal   |
| minSubnorm | 0x0001 | Smallest subnormal  |

### Single-Precision (32-bit)

| Name       | Hex        | Description         |
| ---------- | ---------- | ------------------- |
| pos0       | 0x00000000 | +0.0                |
| neg0       | 0x80000000 | -0.0                |
| pos1       | 0x3F800000 | +1.0                |
| posInf     | 0x7F800000 | +Infinity           |
| negInf     | 0xFF800000 | -Infinity           |
| qNaN       | 0x7FC00000 | Quiet NaN           |
| sNaN       | 0x7F800001 | Signaling NaN       |
| maxNorm    | 0x7F7FFFFF | Largest normalized  |
| minNorm    | 0x00800000 | Smallest normalized |
| maxSubnorm | 0x007FFFFF | Largest subnormal   |
| minSubnorm | 0x00000001 | Smallest subnormal  |

### Double-Precision (64-bit)

| Name       | Hex                | Description         |
| ---------- | ------------------ | ------------------- |
| pos0       | 0x0000000000000000 | +0.0                |
| neg0       | 0x8000000000000000 | -0.0                |
| pos1       | 0x3FF0000000000000 | +1.0                |
| posInf     | 0x7FF0000000000000 | +Infinity           |
| negInf     | 0xFFF0000000000000 | -Infinity           |
| qNaN       | 0x7FF8000000000000 | Quiet NaN           |
| sNaN       | 0x7FF0000000000001 | Signaling NaN       |
| maxNorm    | 0x7FEFFFFFFFFFFFFF | Largest normalized  |
| minNorm    | 0x0010000000000000 | Smallest normalized |
| maxSubnorm | 0x000FFFFFFFFFFFFF | Largest subnormal   |
| minSubnorm | 0x0000000000000001 | Smallest subnormal  |

## Integer Edge Values by SEW

| SEW | Zero       | One        | Max Signed | Min Signed | Max Unsigned |
| --- | ---------- | ---------- | ---------- | ---------- | ------------ |
| 8   | 0x00       | 0x01       | 0x7F       | 0x80       | 0xFF         |
| 16  | 0x0000     | 0x0001     | 0x7FFF     | 0x8000     | 0xFFFF       |
| 32  | 0x00000000 | 0x00000001 | 0x7FFFFFFF | 0x80000000 | 0xFFFFFFFF   |
| 64  | 0x0...0    | 0x0...1    | 0x7F...F   | 0x80...0   | 0xFF...F     |

## Edge Values Reference

### vl Edge Values

| Name     | Value                  | Purpose                 |
| -------- | ---------------------- | ----------------------- |
| vl_one   | 1                      | Minimum active elements |
| vl_vlmax | VLMAX                  | Maximum elements        |
| vl_legal | random in [2, VLMAX-1] | General coverage        |

### vstart Edge Values

| Name           | Value   | Purpose                  |
| -------------- | ------- | ------------------------ |
| vstart_one     | 1       | Skip first element       |
| vstart_vlmaxm1 | VLMAX-1 | Only last element active |
| vstart_vlmaxd2 | VLMAX/2 | Half elements skipped    |

### Mask Edge Values

| Name             | Pattern              | Purpose               |
| ---------------- | -------------------- | --------------------- |
| mask_zero        | All 0s               | No active elements    |
| mask_ones        | All 1s               | All elements active   |
| mask_vlmaxm1ones | (VLMAX-1) 1s, then 0 | Last element inactive |
| mask_random      | Random               | General coverage      |
