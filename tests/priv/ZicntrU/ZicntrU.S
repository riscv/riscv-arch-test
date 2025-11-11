///////////////////////////////////////////
// ZicntrU.S
//
// Written: Ahlyssa Santillana asantillana@hmc.edu 3 March 2025
//
// Purpose: Functional coverage tests for counters in user mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: [I, U, Zicsr, Zicntr, Zihpm]
# MARCH: rv${XLEN}i_zicsr_zicntr_zihpm
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

#include "WALLY-init-lib.h"

main:

/////////////////////////////////
// cp_mcounteren_access_u
/////////////////////////////////

#include "Zicntr-MWalkU.h"

/////////////////////////////////
// cp_mcounteren_access_m
/////////////////////////////////
#include "Zicntr-MWalkM.h"

finished:
    j done
