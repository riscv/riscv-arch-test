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

typedef enum {
  INST_CAT_UNKNOWN = 0,
  INST_CAT_LOAD,
  INST_CAT_STORE
} inst_category_t;

typedef enum {
  NO_HAZARD = 0,
  RAW_HAZARD,
  WAW_HAZARD,
  WAR_HAZARD
} hazards_t;

typedef enum {
  HAZARD_FIELD_NONE = 0,
  HAZARD_FIELD_RS1,
  HAZARD_FIELD_RS2,
  HAZARD_FIELD_RS3
} hazard_field_t;

function hazard_field_t check_gpr_hazard_field(int hart, int issue, int depth = 0);
  int producer_idx;
  producer_idx = depth + 1;
  if (traceDataQ[hart][issue][producer_idx].has_rd) begin
    if (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rs1 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].rs1 == traceDataQ[hart][issue][producer_idx].rd)) begin
      return HAZARD_FIELD_RS1;
    end else if (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rs2 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].rs2 == traceDataQ[hart][issue][producer_idx].rd)) begin
      return HAZARD_FIELD_RS2;
    end else if (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rs3 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].rs3 == traceDataQ[hart][issue][producer_idx].rd)) begin
      return HAZARD_FIELD_RS3;
    end
  end
  return HAZARD_FIELD_NONE;
endfunction

function hazards_t check_fpr_hazards(int hart, int issue, int depth = 0);
  int producer_idx;
  producer_idx = depth + 1;
  if (traceDataQ[hart][issue][producer_idx].has_fd) begin
    if ((traceDataQ[hart][issue][`SAMPLE_CURRENT].has_fs1 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].fs1 == traceDataQ[hart][issue][producer_idx].fd))
     || (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_fs2 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].fs2 == traceDataQ[hart][issue][producer_idx].fd))
     || (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_fs3 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].fs3 == traceDataQ[hart][issue][producer_idx].fd))) begin
      return RAW_HAZARD;
    end else if (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_fd && (traceDataQ[hart][issue][`SAMPLE_CURRENT].fd == traceDataQ[hart][issue][producer_idx].fd)) begin
      return WAW_HAZARD;
    end else if (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_fd && ((traceDataQ[hart][issue][producer_idx].has_fs1 && (traceDataQ[hart][issue][producer_idx].fs1 == traceDataQ[hart][issue][`SAMPLE_CURRENT].fd))
                                                                  || (traceDataQ[hart][issue][producer_idx].has_fs2 && (traceDataQ[hart][issue][producer_idx].fs2 == traceDataQ[hart][issue][`SAMPLE_CURRENT].fd))
                                                                  || (traceDataQ[hart][issue][producer_idx].has_fs3 && (traceDataQ[hart][issue][producer_idx].fs3 == traceDataQ[hart][issue][`SAMPLE_CURRENT].fd)))) begin
      return WAR_HAZARD;
    end
  end
  return NO_HAZARD;
endfunction

function hazards_t check_gpr_hazards(int hart, int issue, int depth = 0);
  int producer_idx;
  producer_idx = depth + 1;
  if (traceDataQ[hart][issue][producer_idx].has_rd) begin
    if ((traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rs1 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].rs1 == traceDataQ[hart][issue][producer_idx].rd))
     || (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rs2 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].rs2 == traceDataQ[hart][issue][producer_idx].rd))
     || (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rs3 && (traceDataQ[hart][issue][`SAMPLE_CURRENT].rs3 == traceDataQ[hart][issue][producer_idx].rd))) begin
      return RAW_HAZARD;
    end else if (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rd && (traceDataQ[hart][issue][`SAMPLE_CURRENT].rd == traceDataQ[hart][issue][producer_idx].rd)) begin
      return WAW_HAZARD;
    end else if (traceDataQ[hart][issue][`SAMPLE_CURRENT].has_rd && ((traceDataQ[hart][issue][producer_idx].has_rs1 && (traceDataQ[hart][issue][producer_idx].rs1 == traceDataQ[hart][issue][`SAMPLE_CURRENT].rd))
                                                                  || (traceDataQ[hart][issue][producer_idx].has_rs2 && (traceDataQ[hart][issue][producer_idx].rs2 == traceDataQ[hart][issue][`SAMPLE_CURRENT].rd))
                                                                  || (traceDataQ[hart][issue][producer_idx].has_rs3 && (traceDataQ[hart][issue][producer_idx].rs3 == traceDataQ[hart][issue][`SAMPLE_CURRENT].rd)))) begin
      return WAR_HAZARD;
    end
  end
  return NO_HAZARD;
endfunction

function bit is_unaligned_mem_access(int hart, int issue);
  if ((traceDataQ[hart][issue][`SAMPLE_CURRENT].inst_name inside {"lwu", "ld", "sd", "c_ld", "c_sd"}) && (traceDataQ[hart][issue][`SAMPLE_CURRENT].mem_addr % 8 != 0)) begin
    return 1'b1;
  end else if ((traceDataQ[hart][issue][`SAMPLE_CURRENT].inst_name inside {"lw", "sw", "c_lw", "c_sw"}) && (traceDataQ[hart][issue][`SAMPLE_CURRENT].mem_addr % 4 != 0)) begin
    return 1'b1;
  end else if ((traceDataQ[hart][issue][`SAMPLE_CURRENT].inst_name inside {"lh", "lhu", "sh"}) && (traceDataQ[hart][issue][`SAMPLE_CURRENT].mem_addr % 2 != 0)) begin
    return 1'b1;
  end else begin
    return 1'b0;
  end
endfunction
