<!--
Copyright (c) 2026, OpenHW Foundation
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for the CV32E20
To build the UDB configuration, coverage files and ELFs run the following
command from the top of your working copy of this repo:
```
$ make CONFIG_FILES=config/cores/cve2/cv32e20/test_config.yaml \
       EXTENSIONS=I,M,C,Zca,Zics,Zifencei
```
<!--
### Developer Info
REF_CONFIG_FILES is used to generate, collect and merge functional coverage.
It is not needed to generate the tests, so the above command excludes it.
It may make sense to keep using it locally to review the generated coverage files,
but can be omitted for generating the tests themselves.

TODO: are these two statements true?
Similarily EXTENSIONS can be omitted.
If you leave EXTENSIONS blank it will only compile the tests relevant to your DUT based on your config.

```
$ make CONFIG_FILES=config/cores/cve2/cv32e20/test_config.yaml \
       REF_CONFIG_FILES=config/sail/sail-RVI20U32/test_config.yaml \
       EXTENSIONS=I,M,C,Zca,Zics,Zifencei
```
--->
