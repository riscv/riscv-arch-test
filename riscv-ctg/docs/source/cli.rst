.. See LICENSE.incore for details

=====
Usage
=====
Once you have RISCV-CTG installed, executing ``riscv_ctg --help`` should print the following on the terminal. ::

  Usage: riscv_ctg [OPTIONS]
  
  Options:
    --version                       Show the version and exit.
    -v, --verbose [info|error|debug]
                                    Set verbose level
    -d, --out-dir PATH              Output directory path
    -r, --randomize                 Randomize Outputs.
    -cf, --cgf PATH                 Path to the cgf file(s). Multiple allowed.
    -p, --procs INTEGER             Max number of processes to spawn
    -bi, --base-isa [rv32e|rv32i|rv64i]
                                    Base ISA string for the tests.
    --help                          Show this message and exit.

To use RISC-V Compatibility Test Generator in a project::

    import riscv_ctg

Running the Test generator
==========================

In order to generate the tests for **RV32I** the following command is used. ::
   
    $ mkdir tests/
    $ riscv_ctg -v debug -d ./tests/ -r -cf ./sample_cgfs/dataset.cgf -cf ./sample_cgfs/rv32i.cgf -bi rv32i -p2 

Suite Characteristics
=====================

Directory structure
-------------------

The various `.S` files are the tests themselves.

.. code-block:: console 
    
    .
    ├── Addi.S
    ├── Add.S
    ├── Andi.S
    ├── And.S
    ├── Auipc.S
    ├── Beq.S
    ├── Bge.S
    ├── Bgeu.S
    ├── Blt.S
    ├── Bltu.S
    ├── Bne.S
    ├── env                             # Contains the necessary environment files
    │   ├── arch_test.h                 # Header file containing the macros used in tests
    │   └── encoding.h                  # Header file containing varios encodings required
    ├── Jalr.S
    ├── Jal.S
    ├── Lb-align.S
    ├── Lbu-align.S
    ├── Lh-align.S
    ├── Lhu-align.S
    ├── Lui.S
    ├── Lw-align.S
    ├── Ori.S
    ├── Or.S
    ├── Sb-align.S
    ├── Sh-align.S
    ├── Slli.S
    ├── Sll.S
    ├── Slti.S
    ├── Sltiu.S
    ├── Slt.S
    ├── Sltu.S
    ├── Srai.S
    ├── Sra.S
    ├── Srli.S
    ├── Srl.S
    ├── Sub.S
    ├── Sw-align.S
    ├── Xori.S
    └── Xor.S

Test Structure
--------------

All tests follow the test-spec format available here: `Test Spec Format`_

.. _Test Spec Format: https://riscof.readthedocs.io/en/latest/testformat.html#test-format-spec
