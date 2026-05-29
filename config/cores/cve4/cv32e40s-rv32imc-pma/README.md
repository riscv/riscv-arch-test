<!--
Copyright (c) 2026, Harvey Mudd College, Eclipse Foundation and Marin Radic
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E40S (PMA enabled)

Same as `cv32e40s-rv32imc` but with PMA_NUM_REGIONS=1 so the core enforces
physical memory attributes. All unprivileged tests (I, M, C, Zc\*, ...) run
unchanged — the PMA region covers the entire code/data address range.

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

Everything outside this region defaults to I/O (no instruction fetch, no
misaligned access, no modified transactions, no PUSH/POP).

### Build

```
$ make CONFIG_FILES=config/cores/cve4/cv32e40s-rv32imc-pma/test_config.yaml
```
