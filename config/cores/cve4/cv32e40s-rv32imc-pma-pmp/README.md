<!--
Copyright (c) 2026, Harvey Mudd College, Eclipse Foundation and Marin Radic
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E40S (PMA + PMP enabled)

Same as `cv32e40s-rv32imc-pma` but with PMP_NUM_REGIONS=16 so the core enforces
physical memory protection in addition to physical memory attributes.

### Testbench PMP requirements

Instantiate the core with **PMP_NUM_REGIONS = 16** and **PMP_GRANULARITY = 0**:

| RTL Parameter   | Value               | Meaning                       |
| --------------- | ------------------- | ----------------------------- |
| PMP_NUM_REGIONS | `16`                | 16 PMP regions                |
| PMP_GRANULARITY | `0`                 | G=0, byte-level granularity   |
| PMP_PMPNCFG_RV  | `'{default: 32'h0}` | All regions OFF at reset      |
| PMP_PMPADDR_RV  | `'{default: 32'h0}` | All addresses zero at reset   |
| PMP_MSECCFG_RV  | `32'h0`             | mseccfg: rlb=0, mmwp=0, mml=0 |

### Testbench PMA requirements

Instantiate the core with **PMA_NUM_REGIONS = 1** and the following region:

| Field          | Value          | Meaning                            |
| -------------- | -------------- | ---------------------------------- |
| word_addr_low  | `32'h00000000` | Region start: `0x00000000`         |
| word_addr_high | `32'h00100000` | Region end: `0x00400000` (4 MB)    |
| main           | `1'b1`         | Main memory (exec + misaligned OK) |
| bufferable     | `1'b0`         |                                    |
| cacheable      | `1'b0`         |                                    |
| integrity      | `1'b0`         |                                    |

### Build

```
$ make CONFIG_FILES=config/cores/cve4/cv32e40s-rv32imc-pma-pmp/test_config.yaml
```
