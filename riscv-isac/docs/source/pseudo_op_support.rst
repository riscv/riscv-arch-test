*********************************
Pseudo-Ops Support for RISCV-ISAC
*********************************

Coverpoints are defined in a CGF file under the ``opcode`` node in the CGF. This is a misnomer as ISAC and CTG
deals with mnemonics of the instruction rather than the actual encoding. In order to deal with mnemonics of pseudo-Ops, 
and its congruent base instruction definition, changes are brought to the CGF format.

Format
######
The ``opcode`` field is renamed to ``mnemonics``. To support pseudo-instructions two new fields ``base_op`` and ``p_op_cond``
are added to the covergroups. The ``base_op`` and ``p_op_cond`` are optional fields which specify the base operation and the
condition over the different fields of the instruction which when satisfied results in the instruction being recognized as the
pseudo-op mentioned in ``mnemonics``. As an example, ``zext.h`` is a pseudo-op of ``pack`` in RV32 and packw in RV64 with ``rs2``
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

The ``expand_cgf`` method defined in ``cgf_normalize.py`` goes through every covergroup in the working cgf dictionary. If it encounters
``opcode`` node, a deprecation warning is printed and ``opcode`` is renamed to ``mnemonics``. The method also facilitates checks to see
if ``base_op`` and ``p_op_cond`` meets required conditions.

While computing the coverage, if the decoded instruction under scrutiny is equal to the instruction mentioned in ``base_op`` of working
covergroup, the conditions mentioned in ``p_op_cond`` are evaluated. If a match is found, the instruction defined in ``mnemonic`` field is
assumed to be hit and the coverpoint hit statistics is updated accordingly. 

Note
####
- The ``p_op_cond`` node is relevant only if the ``base_op`` node has been defined.
- The ``mnemonics`` node is allowed to have multiple entries only if the ``base_op`` node is empty.
