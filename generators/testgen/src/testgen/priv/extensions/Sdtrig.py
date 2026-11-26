##################################
# Sdtrig.py
#
# Sdtrig test generators: one group per mode the tests run in (Sm, S, U).
# pclark@hmc.edu Jul 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from testgen.priv.extensions.SdtrigCommon import SDTRIG_DEFINES, register_sdtrig_group

register_sdtrig_group("Sm", ["Sm", "Sdtrig"], [*SDTRIG_DEFINES, "#define BOOT_TO_MMODE"])
register_sdtrig_group("S", ["S", "Sdtrig"], [*SDTRIG_DEFINES, "#define BOOT_TO_SMODE"])
register_sdtrig_group("U", ["U", "Sdtrig"], [*SDTRIG_DEFINES])
