************************************************
Test Generation using Cross Coverage Coverpoints
************************************************

Coverpoints constituting multiple instructions can help identify interesting instruction
sequences which have architectural significance such as structural hazards and data hazards.
The coverpoint node associated with the test generation is ``cross_comb`` defined `here <https://riscv-isac.readthedocs.io/en/stable/cgf.html>`_.

The test generator employs a constraint solver to generate relevant instruction sequence for a
``cross_comb`` coverpoint.

Example
-------

    **Coverpoint Definition**

    An example cross combination coverpoint is given below: ::

        add:
            cross_comb:
                "[add : ? : rv32i_arith : ? : sub] :: [a=rd : ? : ? : ? : ?] :: [? : rs1==a or rs2==a : rs1==a or rs2==a : rs1==a or rs2==a : rd==a]"

    **Possible assembly sequence**

    A possible sequence of instructions CTG would generate is: ::
    
        add x3, x3, x4
        addi x5, x3, 1
        sub x6, x4, x3
        addi x4, x3, -3
        sub x3, x5, x6

The test generator also embeds appropriate macros for initialization of registers and signature region pointing registers.

Note: The cross-combination test generator as of now, does not support load, store and branch instructions