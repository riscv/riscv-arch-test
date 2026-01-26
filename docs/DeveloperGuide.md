# RISC-V Architectural Certification Test Developer's Guide

# Developing Certification Test Plan, Coverpoints, and Tests

All extensions require a Certification Test Plan (CTP), coverpoints, and tests.
The process of developing the CTP, coverpoints, and tests for a new suite differs
for table-driven unprivileged tests and for spreadsheet-driven privileged tests.
Each is described below.

## Table of Contents

- [Certification Test Plan](#certification-test-plan)
- [Table-Driven Unprivileged Coverpoints and Tests](#table-driven-unprivileged-coverpoints-and-tests)
  - [Creating New CSV Testplans](#creating-new-csv-testplans)
  - [Adding New Coverpoints](#adding-new-coverpoints)
  - [Adding New Instruction Formats](#adding-new-instruction-formats)
- [Spreadsheet-Driven Privileged Tests](#spreadsheet-driven-privileged-tests)

## Certification Test Plan

Each test suite needs a section in the CTP describing the coverpoints, the
mapping of normative rules to coverpoints, and any UDB parameters that affect
the suite.

For unprivileged suites, only non-standard coverpoints need to be defined.
See the CTP section "C Compressed Extension" for examples. For privileged
suites, there are no standard coverpoints and instead the testplan links to
a Google Sheet. See the CTP Section "Sm Machine-Mode CSRs and Instructions"
for an example.

Both privileged and unprivileged suites need a mapping between the normative
rules and coverpoints. This mapping is a YAML file in coverpoints/norm/yaml
containing a list of rule names and the coverpoints that exercise them. There
should be one YAML for each test suite.

Instead of typing this YAML from scratch, it is easier to make an outline
from the normative rules already in the `riscv-isa-manual` repo. Make sure
you have a current copy of `riscv-isa-manual` and have run `make` successfully
to build the `normative_rule_defs` subdirectory and `build/norm-rules.json`.
Then invoke `generators/ctp/generate_norm_rule_coverpoint_templates.py` to
create one yaml file per ISA manual chapter in `coverpoints/norm/yaml/chapters`.
(You may need to edit `riscv_isa_manual_dir` in the Python file to point to
its location in your tree). Then copy the yaml from the chapter related to the
test suite up one level
(e.g. `cp coverpoints/norm/yaml/chapters/machine.yaml coverpoints/norm/yaml/Sm.yaml`)
and edit it to include the coverpoints for each normative rule.

When you run `make` in the `ctp` directory, the YAML file is parsed to build an
ASCIIDoc file (in `ctp/norm`) with a table of normative rule names, definitions, and associated coverpoints. Include this file in the CTP with
`include::norm/Sm_norm_rules.adoc[]`

## Table-Driven Unprivileged Coverpoints and Tests

Unprivileged tests are tests that exercise individual instructions and do not trap.
Unprivileged tests always require a [CSV testplan](#creating-new-csv-testplans) and [updates to the instruction decoder](#adding-instructions-to-the-decoder). They may also require new [coverpoint generators](#adding-new-coverpoints) and/or [instruction formatters](#adding-new-instruction-formats).

### Creating New CSV Testplans

Unprivileged test generation is driven by a CSV testplan that specifies all instructions
in the extension along with the coverpoints that apply to each instruction. Each extension
should have a testplan named `<extension_name>.csv` in the [`testplans`](../testplans/) directory.

All testplan CSVs must include the following keys:

- `Instruction`: The instruction mnemonic. For example, `add`, `mul`, `fadd.d`, etc.
- `Type`: The instruction type. Note that these types are more specific than the ISA manual types and take the kind of register, size of immediate, etc. into account. For example, `R`, `I`, `IS`, `ISW`. TODO: Document the list of instruction types?
- `RV32`/`RV64`: Which XLENs the instruction exists for. Place an `x` in the relevant columns.
- coverpoints: Which coverpoints apply to the instruction. Place an `x` in the column corresponding to the relevant coverpoints in each instruction's row.
  - Some coverpoints have multiple variants. To indicate that a variant of the coverpoint should be used for a particular instruction, use the variant's suffix in the CSV instead of an `x`. See the `20bit` variant of the `cp_imm_edges` coverpoint for the `auipc` instruction below.

An example of a few instructions from the I extension is included below:

```csv
Instruction,Type,RV32,RV64,cp_asm_count,cp_rs1,cp_rs2,cp_rd,cp_rs1_edges,cp_rs2_edges,cr_rs1_imm_edges,cr_rs1_rs2_edges,cmp_rs1_rs2,cmp_rd_rs1,cmp_rd_rs2,cmp_rd_rs1_rs2,cp_offset,cp_uimm,cp_imm_edges,cp_align,cp_memval,cp_custom
add,R,x,x,x,x,x,x,x,x,,x,x,x,x,x,,,,,,
addi,I,x,x,x,x,,x,x,,x,,,x,,,,,x,,,
auipc,U,x,x,x,,,x,,,,,,,,,,,20bit,,,
...
```

See [`I.csv`](../testplans/I.csv) for a complete example.

Most new extension testplans will be able to reuse existing coverpoints and instruction formats. If any new coverpoints, coverpoint variants, or instruction formats are added, make sure to follow [adding new coverpoints](#adding-new-coverpoints) or [adding new instruction formats](#adding-new-instruction-formats) respectively.

### Adding Instructions to the Decoder

Unprivileged instructions are decoded in [`disassemble.svh`](../framework/src/act/fcov/disassemble.svh).
All new instructions need to be added to the case statement.
[`disassemble.svh`](../framework/src/act/fcov/disassemble.svh) translates the encoding
into an instruction mnemonic and instruction arguments. The encodings themselves come
from the auto-generated [`RISCV_imported_decode_pkg.svh`](../framework/src/act/fcov/coverage/RISCV_imported_decode_pkg.svh) header.
This header is generated using [riscv-opcodes](https://github.com/riscv/riscv-opcodes)
and should not be manually modified. <!-- TODO: Update this to use a header generated from UDB -->

### Adding New Coverpoints

Adding a new coverpoint requires adding a template for the coverpoint itself along with a
Python generator to generate tests for that coverpoint.

#### Coverpoint SystemVerilog Templates

All coverpoints (and coverpoint variants) need a template file in
[`generators/coverage/templates`](../generators/coverage/templates).
These templates should be named `<coverpoint_name>.txt` or
`<coverpoint_name>_<variant>.txt`.
The coverpoint templates are directly included in a larger covergroup,
so they must contain a complete and valid SystemVerilog coverpoint.
See the [`generators/coverage/templates`](../generators/coverage/templates)
directory for example coverpoints. A few hints are included below:

- All data about the instruction is accessed using the `ins` object.
- There are many pre-built functions to make writing coverpoints for RISC-V easier. Be sure to look through some of the example coverpoints before implementing any complex logic from scratch. TODO: Add documentation of the riscvISACOV functions/enums/etc.
- If no `bins` are specified for a coverpoint, bins will automatically be created for all possible states of the sampled signal.
- All unprivileged coverpoints should have an `iff (ins.trap == 0)` check to ensure they are only measured when the hart is not trapping.

#### Coverpoint Test Generators

Each coverpoint needs a Python generator that produces an assembly language test
that exercises the relevant behaviors.

The following applies to all coverpoint test generators:

- All coverpoint test generators must go in [`generators/testgen/src/testgen/coverpoints`](../generators/testgen/src/testgen/coverpoints). All Python files in that directory are automatically discovered and imported.
- All coverpoint generator functions must be decorated with the `@add_coverpoint_generator("<coverpoint_name>")` decorator. This tells the framework which coverpoints to use this generator for. Multiple comma-separated coverpoints can be specified if necessary.
- All coverpoint generator functions must use the following signature:

  ```py
  def make_cp_name(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
  ```

  - `instr_name` is the instruction currently being tested. This allows coverpoint test generators to be reused for multiple instructions.
  - `instr_type` is the type of the instruction currently being tested. This allows the correct instruction formatter (see below) to be selected.
  - `coverpoint` is the full name of the coverpoint, including any variant suffix. Coverpoint test generators can match multiple variants of a coverpoint. This argument allows different values, registers, etc. to be selected based on the variant.
  - `test_data` is a dataclass that is passed to all parts of the test generation process and stores the signature count, test values, debug strings, etc.
  - The generator must return a list of strings. They will be combined with newlines separating each string in the final output test.

Coverpoint test generators can largely be broken into two categories: standard and special.
Standard generators use the [instruction formatters]() and can be applied to a wide range
of instructions. Examples include `cp_rs1`, `cp_imm_edges`, and `cr_rs1_rs2_edges`.
Special generators include all of the test code inline and are used for coverpoints
that apply to only a small set of instructions. Examples include `cp_custom_fence`
and `cp_align`.

##### _Standard Generators_

Standard coverpoint generators are used for many instructions and make up the majority
of the coverpoint generators. A good example to get familiar with the structure of a
coverpoint generator is the `cp_rd` generator in
[`cp_regs.py`](../generators/testgen/src/testgen/coverpoints/cp_regs.py).
It is also included below with many additional comments added to explain how it works.

```py
# All coverpoint generators use the add_coverpoint_generator decorator to specify
# which coverpoints they apply to.
@add_coverpoint_generator("cp_rd")
# Coverpoint generators all use the standard signature described above.
def make_rd(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[str]:
    """Generate tests for destination register coverpoints."""
    # Determine which rd registers to test based on the coverpoint variant.
    # Multiple variants can match to the same generator. This is useful when
    # the difference between variants in minor (e.g. just the register values).
    if coverpoint == "cp_rd":
        rd_regs = list(range(test_data.int_regs.reg_count))
    elif coverpoint.endswith("_nx0"):
        rd_regs = list(range(1, test_data.int_regs.reg_count))  # Exclude x0
    elif coverpoint.endswith("rd_p"):
        rd_regs = list(range(8, 16))  # x8-x15 for compressed instructions
    else:
        # Raise an error if an unexpected variant was matched to this coverpoint
        # to make debugging easy.
        raise ValueError(f"Unknown cp_rd coverpoint variant: {coverpoint} for {instr_name}")

    # Initialize a list of strings to build up the test
    test_lines: list[str] = []

    # Generate tests
    # A common pattern is to use a loop to iterate over some value that is being testing
    # in a particular coverpoint. This could be register numbers, register values,
    # immediate values, etc.
    for rd in rd_regs:
        # Each testcase needs to include a call to the test_data.add_testcase function.
        # This adds a label for the test to the generated file and adds the appropriate
        # debugging string.
        test_lines.append(test_data.add_testcase(coverpoint))
        # Any registers that are explicitly used must be marked as used using the
        # test_data.int_regs.consume_registers function. This will automatically move
        # any reserved registers to ensure the desired register is free.
        test_lines.append(test_data.int_regs.consume_registers([rd]))
        # The generate_random_params function will populate any instruction parameters
        # used by the provided instruction type that are not explicitly specified with
        # random (legal) values. In this case, only rd is specified, so rs1, rs2, imm, etc.
        # will get random values.
        params = generate_random_params(test_data, instr_type, rd=rd)
        desc = f"{coverpoint} (Test destination rd = x{rd})"
        # format_single_test is the key part of standard coverpoint generators. It takes
        # the provided instruction parameters (created above) and produces the assembly
        # sequence necessary to test the given instruction.
        test_lines.append(format_single_test(instr_name, instr_type, test_data, params, desc))
        # Once registers are no longer in use, they need to be marked as available again
        # so that the register allocator knows that they can be reused.
        return_test_regs(test_data, params)

    # The final list of assembly lines is returned. It will be concatendated with newlines
    # when the test is written to a file.
    return test_lines
```

Additional documentation for all of these functions (and many other helper functions) is
available as docstrings in the Python files where they are defined. Other standard
coverpoint generators can also be used as examples.

##### _Special Generators_

Special coverpoint generators should only be used when the coverpoint being tested requires
a more complex sequence of instructions or requires a different pattern than most other
coverpoints that apply to a particular instruction. They use significantly more handwritten
assembly and need support to be explicitly added for each instruction type (or in some
cases each individual instruction).

Special coverpoint generators vary widely, so it is impossible to provide a complete guide,
but they usually follow the same initial flow as a standard coverpoint and then diverge
where the call to `format_single_test` would be. Instead of calling `format_single_test`,
special coverpoint generators manually add assembly code to the `test_lines` list. While
most of this code is handwritten, you are still encouraged to use helper Python functions.
The most useful helpers for special coverpoints tends to be `load_int_reg` and
`write_sigupd`. See [Python Instruction Formatters](#python-instruction-formatters) for
details on those functions.

If you are writing a new special coverpoint generator, it is highly encouraged to look at
several examples from the [`generators/testgen/src/testgen/coverpoints/special`](../generators/testgen/src/testgen/coverpoints/special/) directory.

### Adding New Instruction Formats

Adding a new instruction format requires adding a new SystemVerilog sample template and a
Python instruction formatter.

#### Instruction Format Sample Templates

All instruction formats need a template file in
[`generators/coverage/templates`](../generators/coverage/templates).
These templates should be named `sample_<INSTRUCTION_TYPE>.txt`.
The instruction format templates are directly included in a SystemVerilog
case statement.

All instruction sample templates must match the following format:

```sv
        "INSTR"     : begin
            ins.add_rd(0);
            ins.add_rs1(1);
            ins.add_rs2(2);
        end
```

- `INSTR` will be replaced by the instruction name and is the key in a case statement.
- `ins` is a data structure that holds all information about the current instruction. The purpose of the sample function is to populate the data structure.
- The various `add_*` functions assign parameters from the instruction's assembly string to variables. The number indicates which parameter from the assembly string should be assigned to the specified variable. For example, in the code above, the first parameter is assigned to `rd`, the second to `rs1`, and the third to `rs2`.
- For a full list of all the `add_*` functions, see [`RISCV_instruction_base.svh`](../framework/src/act/fcov/coverage/RISCV_instruction_base.svh).

See the [`generators/coverage/templates`](../generators/coverage/templates)
directory for example instruction format sample sequences.

#### Python Instruction Formatters

## Spreadsheet-Driven Privileged Tests
