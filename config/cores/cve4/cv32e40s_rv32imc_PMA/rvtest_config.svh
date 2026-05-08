// rvtest_config.svh
// SPDX-License-Identifier: Apache-2.0
// CV32E40S PMA-enabled config: PMP_NUM_REGIONS=0, PMA_NUM_REGIONS=1

`define XLEN32

// PMP not instantiated in default cv32e40s configuration (PMP_NUM_REGIONS=0)
// `define PMP_16

`define RAM_BASE_ADDR       32'h00000000
`define LARGEST_PROGRAM     32'h00040000

`define ACCESS_FAULT_ADDRESS 64'h80000000
`define CLINT_BASE 64'h02000000
