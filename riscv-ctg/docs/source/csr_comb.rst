*************************************************
Test Generation using CSR Combination Coverpoints
*************************************************

CSR Combination Coverpoints can help checking for some basic compliance with the privileged
part of the RISC-V spec by specifying conditions on the CSR values.
The coverpoint node associated with the test generation is ``csr_comb`` defined `here <https://riscv-isac.readthedocs.io/en/stable/cgf.html>`_.

Currently, the test generation is only possible for the coverpoints that test for the values of subfields in CSRs.
Thus, the only supported coverpoints are the form ``csr_reg & mask == val``, where:

* ``mask`` and ``val`` are allowed to be any valid python expressions.
* ``csr_reg`` is allowed to be operated by a bit shift operator, i.e., ``(csr_reg >> shift) & mask == val`` is allowed where ``shift`` is a valid python expression.
* functions ``old("csr_name")`` and ``write("csr_name")`` are allowed to be used in the place of ``csr_reg`` to access the old value and write value of a CSR respectively.
* combination of multiple conditions with ``and`` and ``or`` is allowed.

Example
-------

    **Coverpoint Definition**

    An example CSR combination coverpoint is given below: ::

        misa:
            csr_comb:
                'old("misa") & 0x4 == 0 and (write("misa") >> 12) & 1 == 0 and misa & 0x1000 == 0x1000': 0