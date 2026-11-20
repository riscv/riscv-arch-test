##################################
# SdtrigSm.py
#
# Sdtrig M-mode test generator.
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.priv.extensions.SdtrigCommon import SDTRIG_DEFINES, register_sdtrig_suite

register_sdtrig_suite("Sm", ["Sm", "Sdtrig"], [*SDTRIG_DEFINES, "#define BOOT_TO_MMODE"])
