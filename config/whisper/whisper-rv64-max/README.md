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
$ make CONFIG_FILES=config/whisper/whisper-rv64-max/test_config.yaml
```
