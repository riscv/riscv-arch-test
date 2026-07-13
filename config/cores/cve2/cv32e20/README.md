<!--
Copyright (c) 2026, Eclipse Foundation
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E20

The [CV32E20](https://github.com/openhwgroup/cve2) ([docs](https://docs.openhwgroup.org/projects/cve2-user-manual)) is a small 32 bit RISC-V CPU core (RV32IMC/EMC)
with a two stage pipeline, based on the original zero-riscy work from ETH Zurich and Ibex work
from lowRISC.

To build the UDB configuration, coverage files and ELFs run the following
command from the top of your working copy of this repo:

```
$ make CONFIG_FILES=config/cores/cve2/cv32e20/test_config.yaml
```

<!--
### Developer Info
COVERAGE_CONFIG_FILES is used to generate, collect and merge functional coverage.
It is not needed to generate the tests, so the above command excludes it.
It may make sense to keep using it locally to review the generated coverage files,
but can be omitted for generating the tests themselves.

Similarly EXTENSIONS can be omitted.
If you leave EXTENSIONS blank it will only compile the tests relevant to your DUT based on your config.

```
$ make CONFIG_FILES=config/cores/cve2/cv32e20/test_config.yaml \
       EXTENSIONS=I,M,C,Zca,Zics,Zifencei
```
--->
