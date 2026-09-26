//
// Copyright (c) 2023 Imperas Software Ltd., www.imperas.com
// Modified February 2024, jcarlin@hmc.edu
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
// either express or implied.
//
// See the License for the specific language governing permissions and
// limitations under the License.
//
//

function bit is_load_fault(int hart, int issue);
  `XLEN_BITS cause = get_csr_val(hart, issue, `SAMPLE_AFTER, "mcause", "mcause");
  if (cause == LOAD_ACCESS_FAULT || cause == LOAD_PAGE_FAULT) begin
    return 1;
  end
  return 0;
endfunction

function bit is_store_fault(int hart, int issue);
  `XLEN_BITS cause = get_csr_val(hart, issue, `SAMPLE_AFTER, "mcause", "mcause");
  if (cause == STORE_AMO_ACCESS_FAULT || cause == STORE_AMO_PAGE_FAULT) begin
    return 1;
  end
  return 0;
endfunction

function `XLEN_BITS get_fault(int hart, int issue);
  `XLEN_BITS cause = get_csr_val(hart, issue, `SAMPLE_AFTER, "mcause", "mcause");
  return cause;
endfunction
