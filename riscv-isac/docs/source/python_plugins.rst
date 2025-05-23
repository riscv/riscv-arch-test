========================
Writing Your Own Plugins
========================

RISCV-ISAC uses the `pluggy <https://pluggy.readthedocs.io/en/latest/>`_ system for supporting plugins. The hooks are predefined and can be accessed by importing the ``riscv_isac.plugins`` module. The template for custom plugins is available :ref:`here.<Templates>`

Two classes of plugins are defined, namely:

* Parser Plugin(``parserHookImpl``): Parse the execution trace file to yield instruction object with updated fields - instruction code, address, register commits, CSR commits and mnemonics, for each instruction. Currently, there are plugins for execution traces from 2 RISC V models - SPIKE and SAIL.
* Decoder Plugin(``decoderHookImpl``): Decodes the information into a common instruction class object. 

.. note:: The name of the python file and the name of the class should be the same.

.. warning:: Coverage reported by ISAC is based on the instructions reported in the trace file. Hence it is imperative that all instructions are reported in the trace file. Currently the coverage reporting using the SPIKE model and parser is inaccurate because instructions which trap are not reported in the trace file. Such problems will exist with all parsers/models which follow similar behaviour.

Function Definitions
=====================

Parser Plugin
~~~~~~~~~~~~~~~~~~

def setup(self, trace, arch):
------------------------------

This function initializes each instance of ``parserclass()`` (a subclass of ``ParserSpec``) of a given mode. 

* Arguments: (``trace``) file path of the execution trace file and (``arch``) architecture of the set. 

.. code-block:: python

    @plugins.parserHookImpl
    def setup(self, trace, arch):
        self.trace = trace
        self.arch = arch

def  __iter__(self):
------------------------

It converts the instance of ``parserclass()`` to an iterator. Thus, given an input trace file to the instance, this function will extract information from it line by line and generate an instruction object ``riscv_isac.InstructionObject.instructionObject`` . An example is shown below from the c_sail parser.

* Arguments: ``self`` instance of the class that contains the input trace file. 
* Returns: Generates instruction object ``instrObj`` on each call. 

.. code-block:: python

    @plugins.parserHookImpl
    def __iter__(self):
        with open(self.trace) as fp:
            content = fp.read()
        instructions = content.split('\n\n')
        for line in instructions:
            instr, mnemonic = self.extractInstruction(line)
            addr = self.extractAddress(line)
            reg_commit = self.extractRegisterCommitVal(line)
            csr_commit = self.extractCsrCommitVal(line)
            instrObj = instructionObject(instr, 'None', addr, reg_commit = reg_commit, csr_commit = csr_commit, mnemonic = mnemonic )
            yield instrObj
 
Decoder Plugin
~~~~~~~~~~~~~~~~~~~~~~~

def setup(self, arch):
------------------------------

This function initializes each instance of ``decoderclass()`` (a subclass of ``DecoderSpec``).

* Arguments- ``self`` instance of the class and ``arch`` architecture of the instruction set

.. code-block:: python

    @plugins.decoderHookImpl
    def setup(self, arch):
        self.arch = arch
        
def decode(self, instr, addr):
--------------------------------

This function decodes the instruction and returns an instruction object ``riscv_isac.InstructionObject.instructionObject``.

* Arguments: ``self`` instance of the class, ``instrObj_temp`` instruction object returned by the parsers.
* Return value:  The instruction object in the standard format - (instr_name, instr_addr, rd, rs1, rs2, rs3, imm, zimm, csr, shamt, reg_commit, csr_commit, mnemonic)

.. code-block:: python

    @plugins.decoderHookImpl
    def decode(self, instrObj_temp):
        ''' Decodes the type of instruction
            Returns: instruction object
        '''
        instr = instrObj_temp.instr
        first_two_bits = self.FIRST2_MASK & instr
        if first_two_bits == 0b11:
            instrObj = self.parseStandardInstruction(instrObj_temp)
            return instrObj

        else:
            instrObj = self.parseCompressedInstruction(instrObj_temp)
            return instrObj

.. ``parseStandardInstruction`` and ``parseCompressedInstruction`` takes in the same arguments and return the instruction object in the
.. above mentioned format.

.. _Custom Plugin Usage:

Using Custom Plugins with RISC-V ISAC
=====================================

* Pass the path of the directory where the custom file is present with ``--parser-path`` or ``--decoder-path`` as needed. 
* The name of the class should be passed using the ``--parser-name`` or ``--decoder-name`` argument. An example setup is shown below.

An example setup is shown below:

.. tabs::

    .. tab:: Directory Structure
    
        .. code-block:: console
        
            ($) tree ./   
            .
            ├── add-01.elf
            ├── add-01.log
            ├── dataset.cgf
            ├── decoder
            │   └── CustomDecoder.py
            ├── parser
            │   └── CustomParser.py
            └── rv32i.cgf
            
            2 directories, 6 files
    
    .. tab:: Coverage Command
    
        .. code-block:: console
        
            riscv_isac --verbose info coverage -d -t add-01.log --parser-path ./parser/ --parser-name CustomParser --decoder-path ./decoder/ --decoder-name CustomDecoder -o coverage.rpt --sig-label begin_signature end_signature --test-label rvtest_code_begin rvtest_code_end -e add-01.elf -c dataset.cgf -c rv32i.cgf -x 32 -l add



.. _Templates:

Templates
=========

Parser Plugin
~~~~~~~~~~~~~

.. code-block:: python

    #CustomParser.py

    import riscv_isac.plugins
    from riscv_isac.InstructionObject import instructionObject

    class CustomParser()
        
        @plugins.parserHookImpl
        def setup(self, trace, arch):
            self.trace = trace
            self.arch = arch

        @plugins.parserHookImpl
        def __iter__(self):
            #extract instruction, mnemonic, addr, commit values and yields instruction object
            yield instr_Obj

Decoder Plugin
~~~~~~~~~~~~~~

.. code-block:: python

    #CustomDecoder.py

    from riscv_isac.plugins import decoderHookImpl

    class CustomDecoder()

        @decoderHookImpl
        def setup(self, arch):
            self.arch = arch

        @decoderHookImpl
        def decode(self, instr_Obj):
            # Update fields of Instruction Object and return
