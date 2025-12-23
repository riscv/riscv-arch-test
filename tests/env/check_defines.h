# model_test_check.h
# Ensures all trickbox macros are defined
# Jordan Carlin jcarlin@hmc.edu December 2025
# SPDX-License-Identifier: BSD-3-Clause

########## test.S CHECKS ##########

#ifndef TEST_FILE
  #error "TEST_FILE not defined. It should be defined at the beginning of the test file."
#endif

#ifndef SIGUPD_COUNT
  #error "SIGUPD_COUNT not defined. It should be defined at the beginning of the test file."
#endif

########## model_test.h CHECKS ##########

#ifndef RVMODEL_DATA_SECTION
  #error "RVMODEL_DATA_SECTION not defined. Make sure to define it in model_test.h."
#endif

##### STARTUP #####

#ifndef RVMODEL_BOOT
  #error "RVMODEL_BOOT not defined. Make sure to define it in model_test.h."
#endif

##### TERMINATION #####

#ifndef RVMODEL_HALT_PASS
  #error "RVMODEL_HALT_PASS not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_HALT_FAIL
  #error "RVMODEL_HALT_FAIL not defined. Make sure to define it in model_test.h."
#endif

##### IO #####

#ifndef RVMODEL_IO_INIT
  #error "RVMODEL_IO_INIT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_IO_WRITE_STR
  #error "RVMODEL_IO_WRITE_STR not defined. Make sure to define it in model_test.h."
#endif

##### Machine Interrupts #####

#ifndef RVMODEL_SET_MEXT_INT
  #error "RVMODEL_SET_MEXT_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_CLR_MEXT_INT
  #error "RVMODEL_CLR_MEXT_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_SET_MTIMER_INT
  #error "RVMODEL_SET_MTIMER_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_CLR_MTIMER_INT
  #error "RVMODEL_CLR_MTIMER_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_SET_MTIMER_INT_SOON
  #error "RVMODEL_SET_MTIMER_INT_SOON not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_SET_MSW_INT
  #error "RVMODEL_SET_MSW_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_CLR_MSW_INT
  #error "RVMODEL_CLR_MSW_INT not defined. Make sure to define it in model_test.h."
#endif

##### Supervisor Interrupts #####

#ifndef RVMODEL_SET_SEXT_INT
  #error "RVMODEL_SET_MEXT_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_CLR_SEXT_INT
  #error "RVMODEL_CLR_MEXT_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_SET_STIMER_INT
  #error "RVMODEL_SET_MTIMER_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_CLR_STIMER_INT
  #error "RVMODEL_CLR_MTIMER_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_SET_STIMER_INT_SOON
  #error "RVMODEL_SET_MTIMER_INT_SOON not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_SET_SSW_INT
  #error "RVMODEL_SET_MSW_INT not defined. Make sure to define it in model_test.h."
#endif

#ifndef RVMODEL_CLR_SSW_INT
  #error "RVMODEL_CLR_MSW_INT not defined. Make sure to define it in model_test.h."
#endif

##### Hypervisor Interrupts #####

#ifndef RVMODEL_WRITE_GEIP
  #error "RVMODEL_WRITE_GEIP not defined. Make sure to define it in model_test.h."
#endif
