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
Unprivileged tests require a [CSV testplan](#creating-new-csv-testplans), [coverpoint generators](#adding-new-coverpoints), and [instruction formatters](#adding-new-instruction-formats).

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

### Adding New Coverpoints

Addings a new coverpoint requires adding a template for the coverpoint itself along with a
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

##### Standard Generators

##### Special Generators

### Adding New Instruction Formats

## Spreadsheet-Driven Privileged Tests
