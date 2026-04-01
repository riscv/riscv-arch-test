
## DUT Configuration for the CV32A65X


The following configuration is provided for the CVA6 core in its 32-bit application-class setup:

| Config        | ISA                                | Notes                                                  |
| ------------- | ---------------------------------  | ------------------------------------------------------ |
| `cv32a65x`    | RV32IMC_Zicsr_Zcb_Zba_Zbb_Zbc_Zbs  | Formal release version of the CVA6 32-bit core         |


This configuration implements a 6-stage in-order, single-issue pipeline compliant with the RISC-V Privileged Architecture v1.13 (Machine-mode only). The specific architectural features, supported exceptions, and parameters for this core version are detailed in the [CV32A65X Design Document](https://docs.openhwgroup.org/projects/cva6-user-manual/04_cv32a65x/design/design.html) . This configuration is intended for high-confidence validation using the ACT 4.0 framework.


To build the UDB configuration, coverage files and ELFs run the following
command from the top of your working copy of this repo:

```
$ make -j$(nproc) CONFIG_FILES=config/cores/cva6/cv32a65x/test_config.yaml
```
