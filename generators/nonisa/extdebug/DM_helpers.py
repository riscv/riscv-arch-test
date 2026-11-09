##################################
# DM_helpers.py
#
# Helper functions for DM register access
#
# David_Harris@hmc.edu 8 November 2026
# SPDX-License-Identifier: Apache-2.0
##################################

import functools
import os
import traceback

from DM_regs import *
from EDAL import dmi_read, dmi_write

DM_TIMEOUT = 1000

#######################################
# Test structure: covergroup, coverpoints, and what the tests learn about the DUT
#######################################

class DUT:
  """What the tests have learned about the DUT's Debug Module"""
  hartsellen = 0  # number of writable bits in dmcontrol.hartsel
  numharts = 0    # number of harts that exist

_covergroup = "?"
_coverpoint = "?"

def covergroup(name):
  """Errors report this covergroup until the next covergroup() call"""
  global _covergroup
  _covergroup = name

def coverpoint(test):
  """Decorator: errors while test runs report its function name as the coverpoint"""
  @functools.wraps(test)
  def run(*args, **kwargs):
    global _coverpoint
    _coverpoint = test.__name__
    try:
      return test(*args, **kwargs)
    finally:
      _coverpoint = "?"
  return run

def findfirstone(value):
  """Return the index of the first 1 bit in value, or -1 if none"""
  for i in range(32):
    if (value & (1 << i)) != 0:
      return i
  return -1

def replace_bits(rval, field, value):
  """Replace the bits in rval corresponding to field with value"""
  if isinstance(field, int):
    # single-bit field
    mask = 1 << field
    rval = (rval & ~mask) | ((value << field) & mask)
  else:
    # multi-bit field
    msb, lsb = field
    mask = ((1 << (msb - lsb + 1)) - 1) << lsb
    rval = (rval & ~mask) | ((value << lsb) & mask)
  return rval

def dm_write_field(reg, field, value):
  """Write a Debug Module register field"""
  rval = dm_read(reg) # read the register to get the current value
  wval = replace_bits(rval, field, value) # replace the field bits with the new value
  dmi_write(reg, wval)

def dm_read_field(reg, field):
  """Read a Debug Module register field"""
  rval = dm_read(reg) # read the register to get the current value
  if isinstance(field, int):
    # single-bit field
    return (rval >> field) & 1
  else:
    # multi-bit field
    msb, lsb = field
    mask = (1 << (msb - lsb + 1)) - 1
    return (rval >> lsb) & mask

def dm_write_hartsel(value):
  """Write the HARTSEL field of the DMCONTROL register"""
  # swizzle hartsello and hartselhi to make hartsel
  hartsello = value & 0x3FF # bits 9:0
  hartselhi = (value >> 10) & 0x3FF # bits 19:10
  hartsel = (hartsello << 10) | hartselhi
  dm_write_field(DMCONTROL, HARTSEL, hartsel)

def dm_read_hartsel():
  """Read the HARTSEL field of the DMCONTROL register"""
  # swizzle hartsello and hartselhi to make hartsel
  rval = dm_read_field(DMCONTROL, HARTSEL)
  hartsello = rval & 0x3FF # bits 9:0
  hartselhi = (rval >> 10) & 0x3FF # bits 19:10
  hartsel = (hartsello << 10) | hartselhi
  return hartsel

def dm_write(reg, value):
  """Write a Debug Module register"""
  dmi_write(reg, value)

def dm_read(reg):
  """Read a Debug Module register"""
  return dmi_read(reg)

def dm_assert(condition, msg):
    """Report an error at the caller's line if condition is false"""
    if not condition:
        dm_error(msg, stacklevel=2)

def dm_poll(reg, field, expected_value, error_msg):
    """Poll a Debug Module register field until it matches the expected value or timeout occurs.
    On timeout, report an error at the caller's line.  Returns the last value read."""
    timeout = DM_TIMEOUT # adjust based on reg/field if necessary
    iters = 0
    rval = dm_read_field(reg, field)
    while rval != expected_value:
        rval = dm_read_field(reg, field)
        iters += 1
        if iters >= timeout:
            dm_error(error_msg, stacklevel=2)
            break
    return rval

def dm_abstract_command(command):
    """Write the abstract command and its arguments to the Debug Module, poll for completion, return cmderr"""
    dm_write(COMMAND, command)
    dm_poll(ABSTRACTCS, BUSY, 0, "Timeout waiting for abstract command to complete")
    return dm_read_field(ABSTRACTCS, CMDERR)

def dm_access_register(regno, write, aarsize, data=0):
    """Access a register using the Access Register abstract command.  Return cmderr
    regno is the register number, write is 1 for write and 0 for read,
    aarsize is 2 for 32-bits, 3 for 64-bit, 4 for 128-bits, and data is the value to write.
    Returns the value read from the register (for read accesses)."""
    # Write the arguments to the abstract command registers
    if (aarsize < 2 or aarsize > 4):
        dm_error(f"Invalid aarsize {aarsize} for Access Register command", stacklevel=2)
    cmdtype = 0x0 # Access Register command
    aarpostincrement = 0
    postexec = 0
    transfer = 1
    command = (cmdtype << 24) | (aarsize << 20) | (aarpostincrement << 19) | (postexec << 18) | (transfer << 17) | (write << 16) | regno
    if write:
        if (aarsize == 2):
            dm_write(DATA0, data)
        elif (aarsize == 3):
           dm_write(DATA0, data & 0xFFFFFFFF)
           dm_write(DATA1, (data >> 32) & 0xFFFFFFFF)
        elif (aarsize == 4):
           dm_write(DATA0, data & 0xFFFFFFFF)
           dm_write(DATA1, (data >> 32) & 0xFFFFFFFF)
           dm_write(DATA2, (data >> 64) & 0xFFFFFFFF)
           dm_write(DATA3, (data >> 96) & 0xFFFFFFFF)
    return dm_abstract_command(command)

#######################################
# Errors and reporting
#######################################

class DMError(Exception):
  """A Debug Module test failure, with its covergroup, coverpoint, and the source location that reported it"""

  def __init__(self, cg, cp, msg, filename, lineno):
    super().__init__(f"{filename}:{lineno}: {cg}.{cp}: {msg}")
    self.cg = cg
    self.cp = cp
    self.msg = msg
    self.filename = filename
    self.lineno = lineno

# Errors reported by dm_error during the current test.  run_dm_tests.py calls
# dm_reset before each test and reports every error in the list afterwards.
dm_errors = []

def dm_error(msg, stacklevel=1):
  """Record a DMError for the current covergroup and coverpoint at the file and line
  of the caller, and continue the test.

  stacklevel works like warnings.warn: 1 reports the line that called dm_error;
  2 reports that function's caller, for use inside helper functions.
  """
  caller = traceback.extract_stack(limit=stacklevel + 1)[0]
  dm_errors.append(DMError(_covergroup, _coverpoint, msg, os.path.basename(caller.filename), caller.lineno))

def dm_error_count():
  """Number of errors reported so far in this test"""
  return len(dm_errors)

def dm_report():
  """Print what the tests learned about the DUT and the number of errors"""
  print(f"      hartsellen = {DUT.hartsellen}, numharts = {DUT.numharts}, errors = {dm_error_count()}", flush=True)

def dm_reset():
  """Start a new test: clear the errors and what was learned about the DUT"""
  global _covergroup, _coverpoint
  dm_errors.clear()
  DUT.hartsellen = 0
  DUT.numharts = 0
  _covergroup = "?"
  _coverpoint = "?"
