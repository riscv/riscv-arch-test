##################################
# DM.py
#
# Debug Module Non-ISA Tests
#
# David_Harris@hmc.edu 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

from DM_regs import *
from DM_helpers import *

@coverpoint
def cp_dmcontrol_dmactive_reset():
    """Test that dmactive can be cleared and set by writing dmcontrol"""

    # Write dmcontrol to clear dmactive and reset the DM.  Poll for completion
    dm_write(DMCONTROL, 0) # write dmactive to set dmcontrol=0
    dm_poll(DMCONTROL, DMACTIVE, 0, "Timeout waiting for dmactive to clear after writing dmcontrol=0")

    # Write dmcontrol to set dmactive and resume.  Poll for completion
    dm_write(DMCONTROL, 1) # write dmactive = 1, everything else is 0
    dm_poll(DMCONTROL, DMACTIVE, 1, "Timeout waiting for dmactive to set after writing dmcontrol=1")

@coverpoint
def cp_dmcontrol_ndmreset():
    """Test that ndmreset can be set and cleared by writing dmcontrol"""

    dm_write_field(DMCONTROL, ACKHAVERESET, 1) # set ackhavreset to clear allhavreset
    dm_write_field(DMCONTROL, NDMRESET, 1)
    dm_assert(dm_read_field(DMCONTROL, NDMRESET) == 1, "ndmreset did not set after writing dmcontrol.ndmreset=1")

    dm_write_field(DMCONTROL, NDMRESET, 0)
    dm_assert(dm_read_field(DMCONTROL, NDMRESET) == 0, "ndmreset did not clear after writing dmcontrol.ndmreset=0")

    # Check ndmresetpending falls and havreset rises
    dm_poll(DMSTATUS, NDMRESETPENDING, 0, "Timeout waiting for ndmresetpending to clear after writing dmcontrol.ndmreset=0")
    dm_poll(DMSTATUS, ALLHAVERESET, 1, "Timeout waiting for allhavereqset to set after writing dmcontrol.ndmreset=0")

@coverpoint
def cp_dmcontrol_hartsel():
    """Find number of harts and check they exist"""

    # Write dmcontrol.hartsel to select a hart and poll for completion
    dm_write_hartsel(0xFFFFF) # Write all 1s to HARTSEL
    hartsel = dm_read_hartsel()
    DUT.hartsellen = hartsel.bit_length() # position of the most significant 1 bit, plus 1

    # Attempt to write and read back each hartsel value up to hartsellen bits
    hartselexists = [0] * (2**DUT.hartsellen) # array to which harts exist
    for i in range(0, 2**DUT.hartsellen):
        dm_write_hartsel(i)
        selected = (dm_read_hartsel() == i) # read back WARL field and make sure i was accepted
        hartselexists[i] = selected and dm_read_field(DMSTATUS, ANYNONEXISTENT) == 0 # check if hartsel exists
        if (i == 0):
            dm_assert(hartselexists[i] == 1, f"hart 0 must exist but ANYNONEXISTENT is set on hartsel = 0")
        else:
            if (hartselexists[i] == 1):
                dm_assert(hartselexists[i-1] == 1, f"hart {i} exists but hart {i-1} does not exist")
    DUT.numharts = sum(hartselexists) # the harts that exist are numbered 0 to numharts-1

    # Check hartsel can be written to 0
    dm_write_hartsel(0)
    dm_assert(dm_read_hartsel() == 0, "hartsel not written with dmcontrol.hartsel=0")

@coverpoint
def cp_access_register():
    """Test the Access Register abstract command"""

    dm_write_field(DMCONTROL, HALTREQ, 1) # halt the hart
    dm_poll(DMSTATUS, ALLHALTED, 1, "Timeout waiting for hart to halt")
    dm_write_field(DMCONTROL, HALTREQ, 0) # *** shouldn't be necessary; working around https://github.com/riscv-software-src/riscv-isa-sim/issues/2511

    cmderr = dm_access_register(0x1000, 0, 2) # read x0 into data register 0
    val = dm_read(DATA0)
    dm_assert((cmderr == 0) and (val == 0), f"Access Register x0 abstract command failed with cmderr={cmderr}, val={val}")

    dm_write_field(DMCONTROL, RESUMEREQ, 1) # resume the hart
    dm_poll(DMSTATUS, ALLRESUMEACK, 1, "Timeout waiting for hart to resume")
    dm_write_field(DMCONTROL, RESUMEREQ, 0) # *** shouldn't be necessary; spike bug

#######################################
# Main Debug Module test function
#######################################

covergroup("DM_cg")

cp_dmcontrol_dmactive_reset()
cp_dmcontrol_ndmreset()
cp_dmcontrol_hartsel()
cp_access_register()

dm_report()
