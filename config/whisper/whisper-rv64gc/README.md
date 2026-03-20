<!--
Copyright 2026 Tenstorrent Corporation.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
--->

## DUT Configuration for the Whisper simulator

To build the UDB configuration, coverage files and ELFs run the following
command from the top of your working copy of this repo:

```
$ make CONFIG_FILES=config/whisper/whisper-rv64gc/test_config.yaml
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
       EXTENSIONS=I,M,C,A,F,D,V,Zca,Zics,Zifencei
```
--->
