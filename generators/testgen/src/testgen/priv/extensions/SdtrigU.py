##################################
# SdtrigU.py
#
# Sdtrig U-mode test generator.
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.priv.extensions.SdtrigCommon import UDB_DEFINES, register_sdtrig_suite

register_sdtrig_suite("U", ["U", "Sdtrig"], [*UDB_DEFINES])
