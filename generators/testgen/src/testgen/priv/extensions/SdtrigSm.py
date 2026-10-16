##################################
# SdtrigSm.py
#
# Sdtrig M-mode test generator.
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.priv.extensions.SdtrigCommon import UDB_DEFINES, register_sdtrig_suite

register_sdtrig_suite("Sm", ["Sm", "Sdtrig"], [*UDB_DEFINES, "#define BOOT_TO_MMODE"])
