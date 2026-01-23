.. _add_instr:

###################################
Adding Support for New instructions
###################################

This section discusses the tasks required to add support of a new instruction generation in CTG.

Update the Attributes YAML
--------------------------

The first step would be to update the attributes YAML to define a node for the new instruction. The
new node must follow the same :ref:`template <attributes>` as defined earlier. 

One must try to use the existing datasets and fields as much as possible and avoid creation of new
redundant datasets unless absolutely required. One can also define abstract functions to generate
the datasets on the go instead of having to elaborate them completely in the YAML itself.

Some of the abstract functions are available in :meth:`~riscv_ctg.constants` for reference.

Create a new format
-------------------

If the instruction uses a new instruction format type, which is not already present in the CTG
currently, then the behavior of that will have to be defined in the :meth:`~riscv_ctg.generator`
class. 

This would involve updating the dictionaries :meth:`~riscv_ctg.generator.OPS` and 
:meth:`~riscv_ctg.generator.VALS` with the new type. Next create a function ``__XX_instr__`` in 
:meth:`~riscv_ctg.generator` similar to the existing ones which defines how the 
:ref:`op_comb and val_comb <opval_comb>` solutions are merged to create the corresponding instruction.

Additional Register Allocations
-------------------------------

Currently the signature register allocation assumes a max of 3 registers being used by an
instruction. However, if your instruction uses more registers then the
:meth:`~riscv_ctg.generator.Generator.swreg` function will also need an update.

Similarly the test register allocation function :meth:`~riscv_ctg.generator.Generator.testreg` function will
also have to be updated.

Adding Instruction Macros
-------------------------

CTG does not generate direct instruction. It rather uses the template field in the attributes YAML
as a template to generate tests. This template is usually an assembly macro. The definition of these
macros must be defined in ``env/arch_test.h`` header file.
