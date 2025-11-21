///////////////////////////////////////////
// ZicntrU.S
//
// Written: Ahlyssa Santillana asantillana@hmc.edu 3 March 2025
//
// Purpose: Functional coverage tests for counters in user mode
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

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
