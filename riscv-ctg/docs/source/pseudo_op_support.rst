********************************
Pseudo-Ops Support for RISCV-CTG
********************************

Coverpoints are defined in a CGF file under the ``opcode`` node in the CGF. This is a misnomer as ISAC and CTG
deals with mnemonics of the instruction rather than the actual encoding. In order to deal with mnemonics of pseudo-Ops, 
and its congruent base instruction definition, changes are brought to the CGF format.

Format
######
The ``opcode`` field is renamed to ``mnemonics``. To support pseudo-instructions two new fields ``base_op`` and ``p_op_cond``
are added to the covergroups. The ``base_op`` and ``p_op_cond`` are optional fields which specify the base operation and the
condition over the different fields of the instruction which when satisfied results in the instruction being recognized as the
pseudo-op mentioned in ``mnemonics``. As an example, ``zext.h`` is a pseudo-op of ``pack`` in RV32 and ``packw`` in RV64 with ``rs2``
equal to ``x0``. Covergroup for ``zext.h`` pseudo-op can be expressed as follows: ::

    zext.h_32:
        config: 
          - check ISA:=regex(.*RV32.*B.*)
          - check ISA:=regex(.*RV32.*Zbb.*)
        mnemonics: 
          zext.h: 0
        base_op: packw
        p_op_cond: rs2 == x0
        ...

    zext.h_64:
        config: 
          - check ISA:=regex(.*RV64.*B.*)
          - check ISA:=regex(.*RV64.*Zbb.*)
        mnemonics: 
          zext.h: 0
        base_op: pack
        p_op_cond: rs2 == x0
        ...

During CTG runtime, the ``base_op`` field is checked for in every covergroup. The template corresponding to the instruction found 
in ``base_op`` node is extracted to generate the test. If ``base_op`` node does not exist, the instruction found in ``mnemonics``
is used to extract the required template. ``p_op_cond`` fields are not used as additional constraints for the corresponding pseudo-op.
This is due to the assumption that test generation for a base-op encompasses all pseudo-ops associated with the base-op.

Note
####
- The ``p_op_cond`` node is relevant only if the ``base_op`` node has been defined.
- The ``mnemonics`` node is allowed to have multiple entries only if the ``base_op`` node is empty.
