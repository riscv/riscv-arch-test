.. See LICENSE.incore for details

.. _cgf:

=================
CGF Specification
=================

A cgf file is a file which is written in the *yaml* format. The higher level node type in a cgf file is a dictionary. 

Covergroup
==========
A covergroup is a dictionary based on the following template. These dictionaries constitute the nodes in a cgf file. Each cover group contains the following type of coverpoints:

* Mnemonics (Used in conjunction with a `base_op` and a condtion `p_op_cond` node to describe a pseudo-instruction)
* Register
* Register Operand Combinations
* Register/Immediate Value Combinations
* Control and Status Registers Value Combinations
* Cross coverage nodes

Template
--------

The template for defining a non pseudo-op covergroup is as follows:

.. code-block:: yaml

    <label>:
        config:
            - <config-str>
        mnemonics:
            <mnemonics-str>: 0
            <mnemonics-str>: 0
            ...
        rs1:
            <reg-str>: 0
            <reg-str>: 0
            ...
        rs2:
            <reg-str>: 0
            <reg-str>: 0
            ...
        rd:
            <reg-str>: 0
            <reg-str>: 0
            ...
        op_comb:
            <opcomb-str>: 0
            <opcomb-str>: 0
            ...
        val_comb:
            <valcomb-str>: 0
            <valcomb-str>: 0
            abstract_comb:
                <abscomb-str>: 0
                <abscomb-str>: 0
            ...
        csr_comb:
            <csrcomb-str>: 0
            <csrcomb-str>: 0
            ...
        cross_comb:
            <crosscomb_str>:0
            <crosscomb_str>:0
           
The template for defining a covergroup pertaining to a pseudo-op is as follows:

.. code-block:: yaml

    <label>:
        config:
            - <config-str>
        mnemonics:
            <mnemonics-str>: 0
        base_op:
            <base_op-str>
        p_op_cond:
            <p_op_cond-str>
        ...
    
Explanation
-----------
The key corresponding to identifying a covergroup uniquely in the cgf is called the *label*. Nodes labelled as *datasets* will be ignored and not be treated as covergroups. This node can be used to define aliases and anchors to enable easy maintenance and keep the cgf file small.

A covergroup contains the following nodes:

* **config**
    *This node is optional.*
    
    This node specifies the configurations under which this particular covergroup is applicable. This node exists to enable correct *RVTEST_CASE* macro generations and covergroup filtering in reports produced by `riscof`_.

        * **config-str**
            The format followed is similar to the `RVTEST_CASE Condition Formating`_ followed in `riscof`_.


.. _RVTEST_CASE Condition Formating: https://riscof.readthedocs.io/en/latest/testformat.html?highlight=Macro#rvtest-case-condition-formating  
.. _riscof: https://riscof.readthedocs.io/en/latest/index.html 

* **mnemonics**
    *This node is mandatory for all covergroups except covergroups pertaining to CSR coverpoints (it's optional in this case).*
    
    This node describes the *mnemonics coverpoints* necessary for the covergroup. Multiple entries are not allowed under this node when the `base_op` node is defined. Each mnemonic defined under *mnemonics* is treated as a valid coverpoint and the arguments of the corresponding instruction are used to update the rest of the coverpoint types.  

        * **mnemonics-str**
            A valid instruction or pseudoinstruction *mnemonic* in the RISCV Instruction Set.

* **base_op**
    *This node is optional and should be used only when the mnemonics node has a singular entry which is a pseudo-instruction.*

    If the instruction defined in mnemonics is a pseudo-op, *base_op* field can be used to provide its corresponding base instruction.

    Note that when *base_op* node is defined, the *mnemonics* node should only hold the pseudo-instruction.

        * **base_op-str**
            The base instruction corresponding to the pseudoinstruction defined in *mnemonics*

* **p_op_cond**
    *This node is mandatory when the ``base_op`` node is defined.*
    
    This node is used to supply the requisite conditions for the *base_op* to be identified as the pseudo-instruction in *mnemonics* node i.e describe th e instance of the base instruction corresponding to the pseudo-instruction.

        * **p_op_cond-str**
            Conditions required for the base instruction to be congruent to the pseudoinstruction in *mnemonics*. Multiple conditions are joined using ``and``. For example, ``rs1 == x0 and imm == 3``
            
    Example: ``zext.h`` is a pseudo-instruction based on the ``pack`` instruction in ``RV32``. The node for ``zext.h`` will look like the following.
    
    .. code-block:: yaml
    
        zext.h_32:
          config: 
            - check ISA:=regex(.*RV32.*B.*)
            - check ISA:=regex(.*RV32.*Zbb.*)
          mnemonics: 
            zext.h: 0
          base_op: pack
          p_op_cond: rs2 == x0
          ...
        

* **rs1**
    *This node is optional.*

    This node describes the *register coverpoints* for the *rs1* field in instructions. If the opcode of an instruction is present in the *opcode* node, its *rs1* field is used to evaluate the coverpoints in this node. 

        * **reg-str**
            This string correspond to a valid RISCV register. 

            Note - ABI register names aren't supported currently.

* **rs2**
    *This node is optional.*
    
    This node describes the *register coverpoints* for the *rs2* field in instructions. If the opcode of an instruction is present in the *opcode* node, its *rs2* field is used to evaluate the coverpoints in this node. 

        * **reg-str**
            This string correspond to a valid RISCV register. 

            Note - ABI register names aren't supported currently.

* **rd**
    *This node is optional.*
    
    This node describes the *register coverpoints* for the *rd* field in instructions. If the opcode of an instruction is present in the *opcode* node, its *rd* field is used to evaluate the coverpoints in this node. 

        * **reg-str**
            This string correspond to a valid RISCV register. 

            Note - ABI register names aren't supported currently.

* **op_comb**
    *This node is optional.*

    This node describes the *register operand combination coverpoints* for the covergroup. The field values in the eligible instructions are available for use to describe the coverpoints.

        * **opcomb-str**  
            This string is interpreted as a valid python statement/expression which evaluates to a Boolean value. The variables available for use in the expressions are as follows:
                
                * ``rs1`` : The register number specified in the *rs1* field of the instruction.
                * ``rs2`` : The register number specified in the *rs2* field of the instruction.
                * ``rd`` : The register number specified in the *rd* field of the instruction.

            Along with the above mentioned variables any valid python comparison operators can be used. A few example coverpoints are elaborated below.

            **Examples**
        
            1. A coverpoint where the source and destination registers have to be same.
            
                .. code-block:: python
    
                    rs1 == rs2 == rd

            2. A coverpoint where the destination register is a specific register(x10).
    
                .. code-block:: python

                    rd == 10

            3. A coverpoint where the destination register and the first source register have to be specific registers(x12 and x14).

                .. code-block:: python

                    rs1 == 14 and rd == 12

            4. A coverpoint where one of the source registers has to be same as the destination register.

                .. code-block:: python
                    
                    rs1 == rd or rs2 == rd

* **val_comb**
    *This node is optional.*
    
    This node describes the *register/immediate value combination coverpoints* for the covergroup. The values of the registers specified in the instruction or the value specified immediate field of the instruction are available for use to describe the coverpoints.

        * **valcomb-str**  
            This string is interpreted as a valid python statement/expression which evaluates to a Boolean value. The variables available for use in the expression are as follows:
                
                * ``rs1_val`` : The value(as of the end of previous instruction) in the register specified in the *rs1* field of the instruction.
                * ``rs2_val`` : The value(as of the end of previous instruction) in the register specified in the *rs2* field of the instruction.
                * ``rd_val`` : The value(as of the end of previous instruction) in the register specified in the *rd* field of the instruction.
                * ``imm_val`` : The value in the *immediate* field of the instruction.
                * ``ea_align`` : The alignment of the effective address calculated(for relevant instructions). It is calculated according to the instruction in consideration.
                * ``mode`` : The variable for the mode in which the current instruction is executed.
                * ``mnemonic`` : The variable for the name of current instruction.
                * ``ieva`` : The instruction access virtual address variable
                * ``iepa`` : The instruction access physical address variable
                * ``depa`` : The data access phyiscal address variable
                * ``ieva_align`` : The alignment of the effective address calculated for ieva(for relevant instructions)
                * ``iepa_align`` : The alignment of the effective address calculated for iepa(for relevant instructions)
                * ``depa_align`` : The alignment of the effective address calculated for depa(for relevant instructions)
                * ``iptw0a,iptw1a,iptw2a,iptw3a,iptw4a`` : Variables for the address being accessed by the page table walk (ptw) in the translation of effective instruction access from va to pa.
                * ``iptw0cont,iptw1cont,iptw2cont,iptw3cont,iptw4cont`` : Variables for the content stored at the address being accessed by the page table walk (ptw) in the translation of effective instruction access from va to pa.
                * ``len_iptw`` : Total number of page table walks done in the translation of effective instruction access from va to pa
                * ``dptw0a,dptw1a,dptw2a,dptw3a,dptw4a`` : Variables for the address being accessed by the page table walk (ptw) in the translation of effective data access from va to pa.
                * ``dptw0cont,dptw1cont,dptw2cont,dptw3cont,dptw4cont`` : Variables for the content stored at the address being accessed by the page table walk (ptw) in the translation of effective data access from va to pa.
                * ``len_dptw`` : Total number of page table walks done in the translation of effective data access from va to pa
                * ``get_addr("label")`` : This function is used to get the address of any label from the test.

                            * **label**
                                The label of which the address is to be fetched.

                * ``get_mem_val(address)`` : This function is used to get the value at the memory address.

                            * **address**
                                The address in hex/int at which the content is to fetched.

                * ``get_pte_prop("permission_bit", "physical_address", "PTE_address", "Page_Table_Address")`` : This function is used to check whether the PTE has a specific permission like Read, Write or not.

                            * **permission_bit**
                                The permission bit that has to be tested for the PTE. For instance, 'R' for read or 'A' for access bit.

                            * **phyiscal_address**
                                The physical address at which the PTE is stored.

                            * **PTE_address**
                                The address for the Page Table Entry.

                            * **Page_Table_Address**
                                The page table address

            Along with the above mentioned variables any valid python comparison operators can be used. A few example coverpoints are elaborated below.

            **Examples**
        
            1. A coverpoint where the value in both of the source registers are the same.
            
                .. code-block:: python
    
                    rs1_val == rs2_val

            2. A coverpoint where the immediate value is specific(32) and the effective address alignment is 4.
    
                .. code-block:: python

                    imm_val == 32 and ea_align == 4

            3. A coverpoint where the value in both the source registers are specific(1024 and 10).

                .. code-block:: python

                    rs1_val == 1024 and rs2_val == 0x0a
            
            Note: Hexadecimal numbers can be used by using the prefix ``0x`` before the hex string.

            4. A coverpoint to check whether the 'U' bit is set for the pte.

                .. code-block:: python

                    get_pte_prop('U',get_addr("begin_signature"), rs1_val + imm_val, get_addr("rvtest_slvl1_pg_tbl")) == 1: 0


        * **abstract_comb**
            *This node is optional.*

            This node contains functions/lists which are evaluated to produce coverpoints of the type *register/immediate value combination*.

            * **abscomb-str**
                This string is interpreted as a valid python statement/expression which evalates to a list of coverpoints of type *register/immediate value combination*. The expression can be a valid list comprehension or a function call for a set of predefined funtions which return a list. The function prototypes of the predefined functions and their uses are listed below. 

                    * ``walking_ones(var, size, signed=True, fltr_func=None, scale_func=None)`` 
                        
                        This function generates a set of values based on a walking one pattern.

                            * **var**
                                The name of the variable which should be present in the coverpoint. Any valid variables avaliable in the *valcomb-str* can be specified here.
                            * **size**
                                The bit-width of the values to be generated.
                            * **signed**
                                Whether the binary value of width *bit-width* should be interpreted as a signed(Twos complement) or unsigned.
                            * **fltr_func**
                                A lambda function which takes an integer and returns a boolean value. This function is used to filter the output set after scaling. 
                            * **scale_func**
                                A lambda function which takes an integer and returns an integer. This function is used to scale the generated values.

                    * ``walking_zeros(var, size, signed=True, fltr_func=None, scale_func=None)``
                        
                        This function generates a set of values based on a walking zero pattern.

                            * **var**
                                The name of the variable which should be present in the coverpoint. Any valid variables avaliable in the *valcomb-str* can be specified here.
                            * **size**
                                The bit-width of the values to be generated.
                            * **signed**
                                Whether the binary value of width *bit-width* should be interpreted as a signed(Twos complement) or unsigned.
                            * **fltr_func**
                                A lambda function which takes an integer and returns a boolean value. This function is used to filter the output set after scaling. 
                            * **scale_func**
                                A lambda function which takes an integer and returns an integer. This function is used to scale the generated values.

                    * ``alternate(var, size, signed=True, fltr_func=None,scale_func=None)``
                        
                        This function generates a set of values based on a checkerboard pattern.

                            * **var**
                                The name of the variable which should be present in the coverpoint. Any valid variables avaliable in the *valcomb-str* can be specified here.
                            * **size**
                                The bit-width of the values to be generated.
                            * **signed**
                                Whether the binary value of width *bit-width* should be interpreted as a signed(Twos complement) or unsigned.
                            * **fltr_func**
                                A lambda function which takes an integer and returns a boolean value. This function is used to filter the output set after scaling. 
                            * **scale_func**
                                A lambda function which takes an integer and returns an integer. This function is used to scale the generated values.

                Note: The variable ``xlen`` can be used in expressions to refer to the system width.

                **Examples**

                1. Walking ones for an unsigned immediate field 6 bits wide.

                    .. code-block:: python
                        
                        walking_ones("imm_val",6,signed=False)

                2. Walking zeroes for an signed immediate field 12 bits wide.

                    .. code-block:: python
                        
                        walking_zeros("imm_val",12)

                3. Checkerboard pattern for the first source register where a valid value is only a multiple of 4 and the values are interpreted as signed numbers.
                
                    .. code-block:: python

                        alternate("rs1_val", xlen-2, scale_func = lambda x: x * 4)

                4. The value of the first source register is a multiple of 2 and not a multiple of 8.


                    .. code-block:: python

                        ["rs1_val=="+str(x) for x in filter(lambda x:x%8!=0,range(2,xlen,2))]
* **csr_comb**
    *This node is optional.*
    
    This node describes the *CSRs value combination coverpoints* for a covergroup. ISAC maintains a copy of the architectural csrs, which thereby allows the user to describe the coverpoints based on csrs and their values. All the *Machine level* and *Supervisor level* CSRs are currently supported. If for a particular covergroup, the opcode node is present/not-empty, then the CSR coverpoints are evaluated and updated only for instructions in the log whose opcode matches. If however, the opcode node is not-present/empty in a covergroup, then the csrs coverpoints are evaluated and updated for any event/instruction. 

        * **csrcomb-str**  
            This string is interpreted as a valid python statement/expression which evaluates to a Boolean value. The variables available for use in the expression are as follows:
                
                * ``csr_name`` : The value (as of the end of current instruction) in the CSR whose name is specified by csr_name.

                * ``old("csr_name")`` : The value (as of the end of previous instruction) in the CSR whose name is specified by csr_name.

                * ``write("csr_name")`` : The value being written to the CSR in the current instruction whose name is specified by csr_name.

                * ``xlen`` : The length of the regsiters in the machine.

                * ``mode`` : The mode in which the current instruction is executed

                * ``mnemonic`` : The name of current instruction

                * ``get_addr("label")`` : To get the address of any label from the test

                * ``get_mem_val(address)`` : To get the value at the memory address

            Along with the above mentioned variable any valid python comparison operators can be used. An example coverpoint is elaborated below.

            .. note:: The csr coverage reporting is accurate only if a change in the csr is captured in the log.    

            .. tip:: Bit masks and shifts can be used to access the subfields in the csrs. 

            **Examples**
        
            1. A coverpoint where the value in *mcycle* register is 0.
            
                .. code-block:: python
    
                    mcycle == 0x0
                    
            Note: Hexadecimal numbers can be used by using the prefix ``0x`` before the hex string.

            2. A coverpoint which checks whether the *mxl* field of *misa* register is 1.
        
                .. code-block:: python

                    misa >> (xlen-2) == 0x01
                   

            3. A coverpoint which checks whether the *mie* field of *mstatus* register is 1.

                .. code-block:: python

                    mstatus && (0x8) == 0x8

            4. A coverpoint which checks whether the *M* bit of the value being written to *misa* register is unset and the final value that the register assumes has that bit still set.

                .. code-block:: python

                    (write("misa") >> 12) & 1 == 0 and misa & 0x1000 == 0x1000

* **cross_comb**
    *This node is optional.*
    
    This node describes the *Cross combination coverpoints* for a covergroup. Cross coverage can identify potential data hazards between instructions - Read after Write, Write after Write, Write after Read.

        * **crosscomb-str**  
            This string is divided into three parts - opcode list, assign list and condition list separated by :: symbol. It is parsed and all the three lists are obtained separately. The variables available for use in the expression are as follows:
                
                * ``instr_name`` : The instruction names in the  opcode list
                
                * ``instruction_alias``: The instruction alias for a set of instructions as defined in ``/riscv_isac/data/instr_alias.yaml`` 

                * ``rs1`` : The register number of source register 1 of the current instruction in the assign list.
                
                * ``rs2`` : The register number of source register 2 of the current instruction in the assign list.
                
                * ``rd`` : The register number of destination register of the current instruction in the assign list.

            Instruction aliases when used will be expanded into a tuple of instruction under the given alias.
            Along with the above mentioned variable any valid python comparison operators can be used in the condition list. 


            **Examples**
        
            The window size is fixed and equal to 5.
        
            1. RAW for an add instruction followed immediately by a subtract instruction.
            
                .. code-block:: python
    
                    [(add,sub) : (add,sub) ] :: [a=rd : ? ] :: [? : rs1==a or rs2==a]

            2. RAW on x10 register for an add instruction followed by a subtract instruction with one non-consuming/non-updating instruction in between. 
               No update happens to the rd register in between.
    
                .. code-block:: python

                    [(add,sub) : rv32i_arith : (add,sub) ] :: [a=rd : ? : ? ] :: [rd==x10 : rd!=a and rs1!=a and rs2!=a : rs1==a or rs2==a ]

            3. WAW for an add instruction followed by a subtract instruction with 3 non-consuming instructions in between.

                .. code-block:: python

                    [add : ? : ? : ? : sub] :: [a=rd : ? : ? : ? : ?] :: [? : ? : ? : ? : rd==a]
                    
            4. WAW for add followed by subtract with 3 consuming instructions in between.
            
                .. code-block:: python
    
                    [(add,sub) : ? : ? : ? : (add,sub)] :: [a=rd : ? : ? : ? : ?] :: [? : rs1==a or rs2==a : rs1==a or rs2==a : rs1==a or rs2==a : rd==a]
           
            5. WAR for an add instruction followed immediately by a subtract instruction.
            
                .. code-block:: python
    
                    [(add,sub) : (add,sub) ] :: [a=rs1; b=rs2 : ? ] :: [? : rd==a or rd==b]



Using the Translator for the CGF
==========
Overview
--------

The Translator feature enhances the coverpoint writing process in CGF files. Anything enclosed within curly brackets **{-}** is considered part of the translation process and is processed according to the specified guidelines.

            .. tip:: Use the translator feature when the number of lines for the coverpoints can be reduced upto 2x 

syntax for the Translator:
-------------------------
        1. **Comma based Coverpoints**
            Comma-based seperator syntax is used to write multiple coverpoints in one line. For instance, consider the following example:

                .. code-block:: python

                    mnemonics:
                        "{csrrs, csrrw, lw, sw}" : 0

            Each of the instruction will be divided into 4 seperate coverpoint as:

                .. code-block:: python

                    mnemonics:
                        csrrs: 0
                        csrrw: 0
                        lw: 0
                        sw: 0

            .. note:: In scenarios where {-} encloses the outermost part of the coverpoint, inverted commas should be placed outside the {-}. This adjustment is necessary due to the presence of {} within YAML's syntax.

        2. **Range based Coverpoints**
            When the user wants to define a range of registers or numbers, it is not practical to write every coverpoint independently by hand. Instead, they may use the following pattern:

                .. code-block:: python

                    csr_comb:
                        "pmpcfg{0 ... 3} != 0" : 0

            This will be translated to:

                .. code-block:: python

                    csr_comb:
                        pmpcfg0 != 0: 0
                        pmpcfg1 != 0: 0
                        pmpcfg2 != 0: 0
                        pmpcfg3 != 0: 0

        3. **Mutliple braces expansion**
            This feature helps to use mutliple braces in a single coverpoint. Consider the following example:

                .. code-block:: python

                    csr_comb:
                        (register{0,1} != 0 and register{0 ... 3} != 0): 0

            This will be translated to :

                .. code-block:: python

                    csr_comb:
                        (register0 != 0 and register0 != 0): 0
                        (register0 != 0 and register1 != 0): 0
                        (register0 != 0 and register2 != 0): 0
                        (register0 != 0 and register3 != 0): 0
                        (register1 != 0 and register0 != 0): 0
                        (register1 != 0 and register1 != 0): 0
                        (register1 != 0 and register2 != 0): 0
                        (register1 != 0 and register3 != 0): 0

            .. note:: The total number of coverpoints generated when using mutltiple braces in a coverpoint is equal to the product of the length of every brace exculding lists in that coverpoint.

        4. **Value Placeholder**
            The Value Placeholder is a feature of the Translator in CGF files that allows for the insertion of changing values within braces during translation. The syntax for this feature is given as:

                .. code-block:: python

                    csr_comb:
                        ((pmpcfg0 >> 8) & {0x99, 0x9A, 0x9C}) == (0xF9 & $1): 0

            In this syntax, ``$1`` serves as the placeholder for the current value inside the *{0x99, 0x9A, 0x9C}* brace. During translation, each occurrence of ``$1`` will be replaced with the corresponding value from the comma-based brace.

            Above coverpoint will be translated to the following:

                .. code-block:: python

                    csr_comb:
                        ((pmpcfg0 >> 8) & 0x99) == (0xF9 & 0x99): 0
                        ((pmpcfg0 >> 8) & 0x9A) == (0xF9 & 0x9A): 0
                        ((pmpcfg0 >> 8) & 0x9C) == (0xF9 & 0x9C): 0

            If there are multiple braces in a single coverpoint, each one have its own placeholder. Consider the following example:

                .. code-block:: python

                    csr_comb:
                        (register{0 ... 3} != $1) and (register{10,11} == $2): 0

                This will be translated to:

                .. code-block:: python

                    csr_comb:
                        (register0 != 0) and (register10 == 10): 0
                        (register0 != 0) and (register11 == 11): 0
                        (register1 != 1) and (register10 == 10): 0
                        (register1 != 1) and (register11 == 11): 0
                        (register2 != 2) and (register10 == 10): 0
                        (register2 != 2) and (register11 == 11): 0
                        (register3 != 3) and (register10 == 10): 0
                        (register3 != 3) and (register11 == 11): 0

        5. **Operations on range-based brace**
            Custom operations can be performed on the range-based braces. The syntax is **{{** *start_range* ... *end_range* **}** <<*required_operation*>> <<*number*>> **}**. In this syntax, internal brace has $1 as its placeholder and external brace that generates a value after the required operation has $2 as its placeholder. Consider the following example:

                .. code-block:: python

                    csr_comb:
                        pmpcfg{{0 ... 7} >> 2} != 0 and pmpaddr$1 != 0 and old(pmpcfg$2) != pmpcfg$2: 0  

            The above coverpoint will be translated to:

                .. code-block:: python

                    csr_comb:
                        pmpcfg0 != 0 and pmpaddr0 != 0 and old(pmpcfg0) != pmpcfg0: 0
                        pmpcfg0 != 0 and pmpaddr1 != 0 and old(pmpcfg0) != pmpcfg0: 0
                        pmpcfg0 != 0 and pmpaddr2 != 0 and old(pmpcfg0) != pmpcfg0: 0
                        pmpcfg0 != 0 and pmpaddr3 != 0 and old(pmpcfg0) != pmpcfg0: 0
                        pmpcfg1 != 0 and pmpaddr4 != 0 and old(pmpcfg1) != pmpcfg1: 0
                        pmpcfg1 != 0 and pmpaddr5 != 0 and old(pmpcfg1) != pmpcfg1: 0
                        pmpcfg1 != 0 and pmpaddr6 != 0 and old(pmpcfg1) != pmpcfg1: 0
                        pmpcfg1 != 0 and pmpaddr7 != 0 and old(pmpcfg1) != pmpcfg1: 0

        6. **Lists in a coverpoint**
            Lists is also a feature available that can be used when the user does not want to evaluate the braces as in the **Multiple brace expansion**. The syntax of Lists feature is **{** <<*any_range*>>, <<*number*>>, <<*value*>> **}{[** <<*number_placeholder_index*>> **]}**. Consider the following example:
            *number_placeholder_index* refers to the current index of that number_placeholder being refered. This is done to avoid out of range problems in case of large values.

                .. code-block:: python

                    csr_comb:
                        register{0 ... 3} != 0 and register{5 ... 8}{[$1]} == 0: 0  

            The above coverpoint will be translated to:

                .. code-block:: python

                    csr_comb:
                        register0 != 0 and register5 == 0: 0
                        register1 != 0 and register6 == 0: 0
                        register2 != 0 and register7 == 0: 0
                        register3 != 0 and register8 == 0: 0

            .. note:: You may note here again that The total number of coverpoints generated when using mutltiple braces in a coverpoint is equal to the product of the length of every brace **exculding** lists in that coverpoint.

            Operations can be performed on the *number_placeholder_index* to get the required value. Consider another example:

            .. tip:: Use the modulus operator represented by % in python if you want to traverse over the length of the list !!! 

                .. code-block:: python

                    csr_comb:
                        register{0 ... 3} != 0 and register{5 ... 8}{[$1%2]} == 0: 0  

            *%* refers to the mod operator in python. The above coverpoint will be translated to:

                .. code-block:: python

                    csr_comb:
                        register0 != 0 and register5 == 0: 0
                        register1 != 0 and register6 == 0: 0
                        register2 != 0 and register5 == 0: 0
                        register3 != 0 and register6 == 0: 0

            comma-based brace option can also be used. Consider the following example:

                .. code-block:: python

                    csr_comb:
                        register1 == {0x0F, 0x07, 0x03} and register{5 ... 8}{[$1%2]} == 0: 0  

            The above coverpoint will be translated to:

                .. code-block:: python

                    csr_comb:
                        register1 == 0x03 and register5 == 0: 0
                        register1 == 0x07 and register6 == 0: 0
                        register1 == 0x0F and register5 == 0: 0

            For lists, range-based and comma-based options can be used simulatenously. Consider the following:

                .. code-block:: python

                    csr_comb:
                        register1 == {0 ... 5} and register{0 ... 3, 29, 31}{[$1]} == 0: 0  

            The above coverpoint will be translated to:

                .. code-block:: python

                    csr_comb:
                        register1 == 0 and register0 == 0: 0
                        register1 == 1 and register1 == 0: 0
                        register1 == 2 and register2 == 0: 0
                        register1 == 3 and register3 == 0: 0
                        register1 == 4 and register29 == 0: 0
                        register1 == 5 and register31 == 0: 0

Using Macros for the CGF
==========
Overview
--------
    Macros functionality is used in the RISC-V architectural tests to eliminate redundancy and enhance the test writing process. Those macros are written
    in RISC-V Assembly, accessible `here <https://github.com/riscv-non-isa/riscv-arch-test/blob/main/riscv-test-suite/env/encoding.h>`_.

    .. note:: In the RISC-V ISAC flow, translator is employed before the macros resolver. 

    Similarly, macros can be used when writing the coverpoints to enhance readability. These macros are written using YAML format to align with the YAML
    format of coverpoints. Macros are structured as follows and can be stored in any <*file_name*>.yaml 

    Any macro written under the ``common`` label will be used by all the covergroups that have included the *macro_file/header_file*. Users may also employ specific macros tailored for particular tests. 
    
    In the example below, ``pmp_napot_r`` is a label specifically intended for the covergroup ``PMP_NAPOT_r`` that will explicitly utilize this label.

        .. code-block:: python

            common:
                CAUSE_FETCH_ACCESS: 0x01
                CAUSE_LOAD_ACCESS: 0x05
                CAUSE_STORE_ACCESS: 0x07
            pmp_napot_r:
                mcause_check_not_fault: 0x05

    Consider the following covergroup written using the above macros:

        .. code-block:: python

            PMP_NAPOT_r:
              config:
              - check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*);  def rvtest_mtrap_routine=True;
              mnemonics:
                "{csrrs, csrrw, lw, sw}" : 0
              val_comb:
                #Test for exceptions
                mode == {'M','S','U'} and (mcause != ${mcause_check_not_fault}): 0
                mode == 'M' and (mcause == {${CAUSE_FETCH_ACCESS}, ${CAUSE_STORE_ACCESS}}): 0

    The resultant covergroup after being passed through the translator and then through the macros resolver is given below:

        .. code-block:: python

            PMP_NAPOT_r:
            config:
            - check ISA:=regex(.*32.*); check ISA:=regex(.*I.*Zicsr.*);  def rvtest_mtrap_routine=True;
            mnemonics:
                csrrs: 0
                csrrw: 0
                lw: 0
                sw: 0
            val_comb:
                mode == 'M' and (mcause != 5): 0
                mode == 'S' and (mcause != 5): 0
                mode == 'U' and (mcause != 5): 0
                mode == 'M' and (mcause == 1): 0
                mode == 'M' and (mcause == 7): 0
                mode == 'S' and (mcause == 1): 0
                mode == 'S' and (mcause == 7): 0
                mode == 'U' and (mcause == 1): 0
                mode == 'U' and (mcause == 7): 0

Command to include Macros for the coverage:
-----------
    To use the macros, user may use the ``h`` flag and pass the location of *header_file.yaml*. Then, the ``cm`` refering to *cgf macros* flag can be used and the label of custom macros to be used in the required coverpoint can be passed. In
    this case, we are using ``pmp_napot_r`` as our custom macro. Following command can be used in our case:

        .. code-block:: shell-session

            $  riscv_isac --verbose info coverage -d -t test_trace_file.log --parser-name c_sail -o coverage.rpt --sig-label begin_signature  end_signature --test-label rvtest_code_begin rvtest_code_end  -e ref.elf -c dataset.cgf -c testing_coverpoint.cgf -x32   -l PMP_NAPOT_r -h header_file.yaml -cm pmp_napot_r

