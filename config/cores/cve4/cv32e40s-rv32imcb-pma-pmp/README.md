<!--
Copyright (c) 2026, Harvey Mudd College, Eclipse Foundation and Marin Radic
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E40S (B extensions + PMA + PMP enabled)

Same as `cv32e40s-rv32imc-pma-pmp` but with `B_EXT=ZBA_ZBB_ZBC_ZBS` enabled,
adding the Zba, Zbb, Zbc, Zbs, and Zbkc extensions.

### Testbench RTL parameters

| RTL Parameter   | Value               | Meaning                                             |
| --------------- | ------------------- | --------------------------------------------------- |
| B_EXT           | `ZBA_ZBB_ZBC_ZBS`   | All B sub-extensions + Zbkc (shared clmul hardware) |
| M_EXT           | `M`                 | Full multiply/divide (includes Zmmul)               |
| ZC_EXT          | `1`                 | Zca, Zcb, Zcmp, Zcmt enabled                        |
| PMP_NUM_REGIONS | `16`                | 16 PMP regions                                      |
| PMP_GRANULARITY | `0`                 | G=0, byte-level granularity                         |
| PMP_PMPNCFG_RV  | `'{default: 32'h0}` | All regions OFF at reset                            |
| PMP_PMPADDR_RV  | `'{default: 32'h0}` | All addresses zero at reset                         |
| PMP_MSECCFG_RV  | `32'h0`             | mseccfg: rlb=0, mmwp=0, mml=0                       |

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
$ make CONFIG_FILES=config/cores/cve4/cv32e40s-rv32imcb-pma-pmp/test_config.yaml
```
