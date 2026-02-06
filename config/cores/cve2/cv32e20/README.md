<!--
Copyright (c) 2026, OpenHW Foundation
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E20
To build the UDB configuration, coverage files and ELFs run the following
command from the top of your working copy of this repo:
```
$ make CONFIG_FILES=config/cores/cve2/cv32e20/test_config.yaml \
       REF_CONFIG_FILES=config/sail/sail-RVI20U32/test_config.yaml \
       EXTENSIONS=I,M,C
```
