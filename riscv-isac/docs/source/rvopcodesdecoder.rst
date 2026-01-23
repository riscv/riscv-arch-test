.. _rvopcodes:

Using the encodings from riscv-opcodes
======================================

The `rvopcodesdecoder` is a decoder plugin for RISCV-ISAC, dependent on the official `riscv-opcodes <https://github.com/riscv/riscv-opcodes>`_ repository. The `rvopcodesdecoder` plugin automatically builds the decode tree and decodes instructions based on the encodings specified in the repository. The plugin will support any instruction/extension as long as it is specified in the format adhereing to the official repository.

Usage
~~~~~

Initial Setup
*************
- **Standard version**: This use case is intended for users who want to use the rvopcodes repo as
  is from `riscv/riscv-opcodes <https://github.com/riscv/riscv-opcodes>`_. The command generates a
  ``rvop-plugin`` folder with all the necessary files needed for the plugin. This path will have to
  be passed via the CLI while running coverage. ::

    riscv_isac setup --plugin-path ./rvop-plugin

- **Custom Version**: This use case is intended for users who have a custom/modified version of the 
  rvopcodes encodings locally. The ``<path-to-rvopcodes>`` in the following command should point to
  the path on the system where the custom/modified ``riscv-opcodes`` repository contents are located. 
  The command generates a symlink to the path inside the plugin folder and hence all changes to 
  the encodings are picked up automatically. To add an extension, the user has to create a file
  with the ``rv<xlen>`` prefix followed by the extension name. The file can then be populated with
  the instruction encodings in the appropriate format. Similar steps can be followed for updating
  existing extensions too. ::

    riscv_isac setup --plugin-path ./rvop-plugin --rvop-path <path-to-rvopcodes>

Using the decoder with ISAC for coverage
****************************************

To use `rvopcodesdecoder` as the decoder in RISCV-ISAC, ``rvopcodesdecoder`` should be supplied as argument for ``--decoder-name`` option with the ``--decoder-path`` set to the path of ``rvop-plugin`` generated in the previous step.. For example, ::

  riscv_isac --verbose info coverage --decoder-name rvopcodesdecoder --decoder-path ./rvop-plugin -t trace.log --parser-name spike  -o coverage.rpt -e add-01.out -c rv64i.cgf -x 64
  
.. note:: Pseudo instructions are always decoded into the mnemonics of the base instruction in this plugin. For example, `zext.h` is always decoded as `pack` only.

