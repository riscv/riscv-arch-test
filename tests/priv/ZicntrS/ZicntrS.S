///////////////////////////////////////////
// ZicntrS.S
//
// Written: Ahlyssa Santillana asantillana@hmc.edu 6 March 2025
//
// Purpose: Functional coverage tests for counters in supervisor mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: [I, S, Zicsr, Zicntr]
# MARCH: rv${XLEN}i_zicsr_zicntr_zihpm
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####


.option norvc          # Do not automatically replace uncompressed instructions with compressed instructions

#include "rvtest_config.h"
#include "WALLY-init-lib.h"

main:

/////////////////////////////////
// cp_mcounteren_access_s
/////////////////////////////////

#include "Zicntr-MWalkS.h"

/////////////////////////////////
// cp_scounteren_access_s
/////////////////////////////////

#include "Zicntr-SWalkS.h"

/////////////////////////////////
// cp_scounteren_access_m
/////////////////////////////////

#include "Zicntr-SWalkM.h"

/////////////////////////////////
// cp_scounteren_access_u
/////////////////////////////////

#include "Zicntr-SWalkU.h"

/////////////////////////////////
// cp_mscounteren_access_u
/////////////////////////////////

#include "Zicntr-MSWalkU.h"

finished:
    j done
