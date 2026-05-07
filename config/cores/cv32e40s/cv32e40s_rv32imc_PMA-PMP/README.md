<!--
Copyright (c) 2026, OpenHW Foundation
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E40S (PMA + PMP enabled)

Same as `cv32e40s_rv32imc_PMA` but with PMP_NUM_REGIONS=16 so the core enforces
physical memory protection in addition to physical memory attributes.

### Testbench PMP requirements

Instantiate the core with **PMP_NUM_REGIONS = 16** and **PMP_GRANULARITY = 0**:

| RTL Parameter     | Value                    | Meaning                             |
|-------------------|--------------------------|-------------------------------------|
| PMP_NUM_REGIONS   | `16`                     | 16 PMP regions                      |
| PMP_GRANULARITY   | `0`                      | G=0, byte-level granularity         |
| PMP_PMPNCFG_RV    | `'{default: 32'h0}`      | All regions OFF at reset            |
| PMP_PMPADDR_RV    | `'{default: 32'h0}`      | All addresses zero at reset         |
| PMP_MSECCFG_RV    | `32'h0`                  | mseccfg: rlb=0, mmwp=0, mml=0      |

### Testbench PMA requirements

Instantiate the core with **PMA_NUM_REGIONS = 1** and the following region:

| Field            | Value            | Meaning                               |
|------------------|------------------|---------------------------------------|
| word_addr_low    | `32'h00000000`   | Region start: `0x00000000`            |
| word_addr_high   | `32'h00100000`   | Region end:   `0x00400000` (4 MB)     |
| main             | `1'b1`           | Main memory (exec + misaligned OK)    |
| bufferable       | `1'b0`           |                                       |
| cacheable        | `1'b0`           |                                       |
| integrity        | `1'b0`           |                                       |

### I/O peripherals (outside PMA, handled by mm_ram.sv)

| Address        | mm_ram name       | Purpose                                |
|----------------|-------------------|----------------------------------------|
| `0x10000000`   | MMADDR_PRINT      | Virtual printer                        |
| `0x15000000`   | MMADDR_TIMERREG   | Timer config register                  |
| `0x15000004`   | MMADDR_TIMERVAL   | Timer value register                   |
| `0x20000000`   | MMADDR_TESTSTATUS | Write 123456789 = pass, 1 = fail       |
| `0x20000004`   | MMADDR_EXIT       | Signal halt to testbench               |
| `0x20000008`   | MMADDR_SIGBEGIN   | Signature start address                |
| `0x2000000C`   | MMADDR_SIGEND     | Signature end address                  |
| `0x20000010`   | MMADDR_SIGDUMP    | Dump signature and halt                |
| `0x80000000`   | (unmapped)        | ACCESS_FAULT_ADDRESS -- must return OBI bus error |

### Build

```
$ make CONFIG_FILES=config/cores/cv32e40s/cv32e40s_rv32imc_PMA-PMP/test_config.yaml
```
