.. _add_instr:

###################################
Adding Support for new Instructions
###################################

This section details the steps for adding support for new instructions in the native python plugins
of RISCV-ISAC. 

.. note:: An alternative is to add support for the new instructions using the ``riscv/riscv-opcodes`` repository. Refer :here:`rvopcodes` for further information.

Update the Parser-Module
========================

The first step is to update the parser-module to be able to deduce the relevant fields of the new
instruction and create the required :meth:`~riscv_isac.parsers.instructionObject`.

As part of this phase, the contributor will first have to add a function(s) which will decode the 
instruction hexadecimal encoding and extract the parameters of the :meth:`~riscv_isac.parsers.instructionObject`. 
Make sure to follow the same code structure as used by other functions in module.

Currently the top level function that get's called by the coverage module is the
:meth:`~riscv_isac.parsers.parseInstruction` function. This function based on the `instruction length
encoding` scheme defined by the RISC-V ISA spec identifies the length of the instruction. If the
instruction is compressed then the :meth:`~riscv_isac.parsers.parseCompressedInstruction` function 
is called, else the :meth:`~riscv_isac.parsers.parseInstruction` function is called. 

If the new instruction(s) being added belong to the non-compressed opcodes, then the particular
entry in :meth:`~riscv_isac.parsers.OPCODES` needs to be updated to point to the new function(s)
defined earlier. If there are instructions falling into the compressed op-code space then the
functions :meth:`~riscv_isac.parsers.quad0`, :meth:`~riscv_isac.parsers.quad1` or :meth:`~riscv_isac.parsers.quad2`
will need to be updated accordingly.

Update the Architectural
========================

The coverage module maintains its own architectural state : integer register file, program counter,
floating point register file, etc. If the new instruction(s) requires an additional architectural
state, then that needs to be added in :meth:`~riscv_isac.coverage.archStats` and the usage needs to
be updated in :meth:`~riscv_isac.coverage.compute_per_line`.
