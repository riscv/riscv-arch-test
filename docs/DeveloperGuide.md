# RISC-V Architectural Certification Test Developer's Guide: Developing Certification Test Plan, Coverpoints, and Tests

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
  - [Creating New Spreadsheet Testplans](#creating-new-spreadsheet-testplans)
  - [Adding New Privileged Coverpoints](#adding-new-privileged-coverpoints)
  - [Adding New Privileged Tests](#adding-new-privileged-tests)
- [Debugging Coverage](#debugging-coverage)

## Certification Test Plan

Each test suite needs a section in the CTP describing the coverpoints, the
mapping of normative rules to coverpoints, and any UDB parameters that affect
the suite.

For unprivileged suites, only non-standard coverpoints need to be defined.
See the CTP section "C Compressed Extension" for examples. For privileged
suites, there are no standard coverpoints and instead the testplan links to
a Google Sheet. See the CTP Section "Sm Machine-Mode CSRs and Instructions"
for an example.

### Normative Rule - Coverpoint Mapping

Both privileged and unprivileged suites need a mapping between the normative
rules and coverpoints. This mapping is a YAML file in `coverpoints/norm`
containing a list of rule names and the coverpoints that exercise them. There
should be one YAML for each test suite.

Instead of typing this YAML from scratch, it is easier to make an outline
from the normative rules already in the `riscv-isa-manual` repo. Make sure
you have a current copy of `riscv-isa-manual` and have run `make` successfully in that repo
to build the `normative_rule_defs` subdirectory and `build/norm-rules.json`.
Then invoke `generators/ctp/generate_norm_rule_coverpoint_templates.py` to
create one yaml file per ISA manual chapter in `coverpoints/norm/yaml/chapters`.
(You may need to edit `riscv_isa_manual_dir` in the Python file to point to
its location in your tree). Then copy the yaml from the chapter related to the
test suite up two levels (e.g. `cp coverpoints/norm/yaml/chapters/machine.yaml coverpoints/norm/Sm.yaml`) and edit it.

When you run `make` in the `ctp` directory, the YAML file is parsed to build an
ASCIIDoc file (in `ctp/norm`) with a table of normative rule names, definitions, and associated coverpoints. Include this file in the CTP with
`include::norm/Sm_norm_rules.adoc[]`

### Parameter Lists

Similar YAML files in coverpoints/param are used to make a list of the UDB parameters that apply to a test suite. Each parameter has a name (corresponding to the UDB), coverpoint (one or more coverpoints that it affects), and effect (string summarizing what it does, such as coverpoint only applying to certain parameter values, or result depending on the parameter value).

The `generate_param_table.py` script turns these into .adoc files in ctp/src/param listing the parameter name, description (from UDB), coverpoints it applies to, and effect on the coverpoints. If there is a yaml for normative rules but not for parameters, the parameter adoc just indicates no parameters. The script also makes a summary.adoc table listing all of the UDB parameters used anywhere in the test plan, and UDB parameters not yet mentioned in the test plan.

This script is also run automatically when making the CTP. Hence, all the developer must do is create YAML files in `coverpoints/param` for test suites with parameters.

## Table-Driven Unprivileged Coverpoints and Tests

Unprivileged tests are tests that exercise individual instructions and do not trap.
Unprivileged tests always require a [CSV testplan](#creating-new-csv-testplans) and [updates to the instruction decoder](#adding-instructions-to-the-decoder). They may also require new [coverpoint generators](#adding-new-coverpoints) and/or [instruction formatters](#adding-new-instruction-formats).

Unprivileged tests do not set up a trap handler (because they must run without any machine mode features, including `mtvec`). Therefore, they will enter an infinite loop if they trap. Halt the simulation and look at the log file to find the root cause. Tests that might trap must be written in the privileged style described later in this document.

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
These templates should be named `<coverpoint_name>.sv` or
`<coverpoint_name>_<variant>.sv`.
The coverpoint templates are directly included in a larger covergroup,
so they must contain a complete and valid SystemVerilog coverpoint.
See the [`generators/coverage/templates`](../generators/coverage/templates)
directory for example coverpoints. A few hints are included below:

- All data about the instruction is accessed using the `ins` object.
- There are many pre-built functions to make writing coverpoints for RISC-V easier. Be sure to look through some of the example coverpoints before implementing any complex logic from scratch. TODO: Add documentation of the riscvISACOV functions/enums/etc.
- If no `bins` are specified for a coverpoint, bins will automatically be created for all possible states of the sampled signal.
- All unprivileged coverpoints should have an `iff (ins.trap == 0)` check to ensure they are only satisfied when the hart is not trapping.

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
Standard generators use the [instruction formatters](#python-instruction-formatters) and can be applied to a wide range
of instructions. Examples include `cp_rs1`, `cp_imm_edges`, and `cr_rs1_rs2_edges`.
Special generators include all of the test code inline and are used for coverpoints
that apply to only a small set of instructions. Examples include `cp_custom_fence`
and `cp_align`.

##### Standard Generators

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
    # the difference between variants is minor (e.g. just the register values).
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
    # A common pattern is to use a loop to iterate over some value that is being tested
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

    # The final list of assembly lines is returned. It will be concatenated with newlines
    # when the test is written to a file.
    return test_lines
```

Additional documentation for all of these functions (and many other helper functions) is
available as docstrings in the Python files where they are defined. Other standard
coverpoint generators can also be used as examples.

##### Special Generators

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
These templates should be named `sample_<INSTRUCTION_TYPE>.sv`.
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

The standard coverpoint generators rely on instruction formatters to produce the necessary
assembly to test each instruction. Each instruction type needs a Python generator that produces an assembly language test.

The following applies to all instruction formatters:

- All instruction formatters must go in [`generators/testgen/src/testgen/formatters/types`](../generators/testgen/src/testgen/formatters/types). All Python files in that directory are automatically discovered and imported.
- All instruction formatter functions must be decorated with the `@add_instruction_formatter("<TYPE_NAME>", <type_name>_config)` decorator. This tells the framework which instruction type to use this generator for and how to generate the parameters for it.
  - The `<type_name>_config` argument is an `InstructionTypeConfig` object that contains the `required_params` for an instruction type along with constraints on those parameters, like `reg_range`, `imm_range`, etc. See the `InstructionTypeConfig` docstring in [`generators/testgen/src/testgen/formatters/registry.py`](../generators/testgen/src/testgen/formatters/registry.py) for more details.
- All instruction formatter functions must use the following signature:

  ```py
    def format_name_type(instr_name: str, test_data: TestData, params: InstructionParams) -> tuple[list[str], list[str], list[str]]:
  ```

  - `instr_name` is the instruction currently being tested. This allows instruction formatters to be reused for multiple instructions of the same type.
  - `test_data` is a dataclass that is passed to all parts of the test generation process and stores the signature count, test values, debug strings, etc.
  - `params` is a dataclass containing values for all of the instruction arguments (rs1, rs1val, immval, etc.). See its definition in [`generators/testgen/src/testgen/data/params.py`](../generators/testgen/src/testgen/data/params.py) for all of the options.
  - The generator must return a tuple of three lists of strings:
    - Code to set up the test.
    - The test itself (usually just the instruction being tested).
    - Code to check the results of the test (usually signature checks).

A good example to get familiar with the structure of an instruction formatter is the
[`r_type`](../generators/testgen/src/testgen/formatters/types/r_type.py).
It is also included below with many additional comments added to explain how it works.

```py
# The InstructionTypeConfig object is used when generating random parameters.
# At a minimum, it specifies the `required_params` that must be populated with values.
# It can also optionally specify constraints or additional details for these parameters,
# including reg_range, imm_bits, imm_signed, etc.
r_config = InstructionTypeConfig(required_params={"rd", "rs1", "rs1val", "rs2", "rs2val"})

# All instruction formatters use the add_instruction_formatter decorator to specify
# what instruction type it applies to and what configuration object to use.
@add_instruction_formatter("R", r_config)
# Instruction formatters all use the standard signature described above
def format_r_type(instr_name: str, test_data: TestData, params: InstructionParams) -> tuple[list[str], list[str], list[str]]:
    """Format R-type instruction."""
    # The assert statements are used to satisfy the type checker and help ensure
    # none of the necessary params are left out of the required_params above.
    assert params.rs1 is not None and params.rs1val is not None
    assert params.rs2 is not None and params.rs2val is not None
    assert params.rd is not None
    # setup is a list of strings of assembly code that should be run before the test.
    # The most common thing to do here is populate registers with specified values.
    # The load_int_reg and load_float_reg helper functions load values from memory
    # to ensure the instruction sequence is consistent and to simplify the process
    # of populating floating-point values. The functions will automatically include
    # the values in the data section at the end of the test.
    setup = [
        load_int_reg("rs1", params.rs1, params.rs1val, test_data),
        load_int_reg("rs2", params.rs2, params.rs2val, test_data),
    ]
    # test is a (usually one item) list of strings with the assembly to actually
    # run the test. Note that all of the arguments to the instruction come from
    # the params object that is passed to the formatter. This allows the coverpoint
    # generators to customize the instruction arguments as needed.
    test = [
        f"{instr_name} x{params.rd}, x{params.rs1}, x{params.rs2} # perform operation",
    ]
    # check is a list of strings of assembly code that validate the results of the test.
    # While check can contain anything, it is usually made up of calls to the
    # write_sigupd helper function. This function inserts a RVTEST_SIGUPD macro with
    # all of the appropriate arguments populated.
    check = [write_sigupd(params.rd, test_data, "int")]
    # The three lists of strings are returned as a tuple. They are usually joined
    # with newlines and then passed back to the coverpoint generator.
    return (setup, test, check)
```

Additional documentation for all of these functions (and many other helper functions) is
available as docstrings in the Python files where they are defined. Other instruction formatters
can also be used as examples.

## Spreadsheet-Driven Privileged Tests

Privileged tests are much less structured than unprivileged instruction tests. Therefore, their testsplans are expressed in English on spreadsheets. They are described with hand-written SystemVerilog coverpoints using RVVI to access architectural state. The tests are generated with Python scripts that insert the necessary signature handling to be self-checking.

Although most unprivileged tests involve instructions that are easiest to automatically test through CSV tables described above, unstructured unprivileged tests can be generated with the privileged test approach. See ZicsrF for an unprivileged example.

Privileged tests should be partitioned into suites that generally can run for a certain combination of extensions (e.g. ExceptionsZc requires Sm for general exception capability + Zca for compressed instructions). Putting exceptions for compressed instructions in ExceptionsSm would not be a good organization because one would attempt to run them on all systems with machine mode, even if compressed instructions did not exist, and the behavior of running a compressed instruction on a machine without Zca is Unspecified.

Privileged tests should work for both RV32 and RV64 so there is not a need for separate suites based on XLEN. The testplan, coverpoints, and tests can call out portions of a test that differ based on XLEN.

### Creating New Spreadsheet Testplans

Privileged tests are described with Google Sheets spreadsheets hosted in [CSC/WorkGroups/TestPlan](https://drive.google.com/drive/u/0/folders/1Xr7oKLSGBmO78lVZIFQl62xrQ1xHT6R3) accessible to RVI CSC members. There should be one spreadsheet for each category of test suites (e.g. Exceptions, Interrupts), with one tab per test suite (e.g. ExceptionsS, [ExceptionsZc](https://docs.google.com/spreadsheets/d/1W95I4jPbuQBnXzDdIZtOG4kae8vi7djpKtJXWCXPxMU/edit?gid=538759067#gid=538759067), ExceptionsZaamo).

Each tab should have the following columns:

- Coverpoint: the name that will be consistently used across coverpoints, tests, and linkage to normative rules.
- Goal: brief summary. Avoid words like "test."
- Description: a precise statement of the conditions being checked, suitable for somebody other than the author to turn into coverpoints and tests.
- Expectation: what will happen (e.g. trap, CSR takes on a value, etc.)
- Bins: Number of bins, expressed as a product of independent states where possible to help the test writer confirm the intended number of possibilities have been exercised. (e.g. "2 MIE \* 2 TW", where each of these signals has two possibilities, giving 4 bins).
- Normative Rule: (optional) name of associated normative rule. Not all coverpoints have to be driven by normative rules; some may exercise combinations of features.

### Adding New Privileged Coverpoints

There should be one coverage file for each tab of a testplan spreadsheet. Create `coverpoints/priv/<suite>_coverage.svh` and `coverpoints/priv/<suite>_coverage_init.svh`. Look at `ExceptionsZc_coverage.svh` and `ExceptionsZc_coverage_init.svh` for reference. Use the same idioms; don't get creative. Names should exactly match, subject to capitalization restrictions.

Write SystemVerilog coverpoints. Complex coverpoints are normally a cross-product of simpler coverpoints.

The coverpoints use architectural state conveyed over Extended RVVI (see Certification Test Plan for signals available). It is easiest to write coverpoints in terms of `ins.current` and `ins.prev`, the current and previous instructions. If the test is too complicated to express just in terms of these, it may be necessary to leave out some conditions. For example, virtual memory coverpoints don't specify all of the page table entries.

As with unprivileged tests, add a YAML file with the [Normative Rule - Coverpoint Mapping](#normative-rule---coverpoint-mapping).

#### Standard Coverpoints

The `<suite>_coverage.svh` file can include

```SystemVerilog
`include "general/RISCV_coverage_standard_coverpoints.svh"
```

that defines useful standard coverpoints such as `priv_mode_m` applicable to many suites.

#### Instructions and Fields

The preferred idiom to check the current instruction or instruction field is

```SystemVerilog
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    mcause: coverpoint ins.current.insn[31:20] {
        bins mcause = {CSR_MCAUSE};
    }
```

There is a complete listing of instruction and CSR names in `framework/src/fcov/coverage/RISCV_imported_decode_pkg.svh`. Do not modify that file by hand. It is generated using [`riscv-opcodes`](https://github.com/riscv/riscv-opcodes). To add new instructions or CSRs, add them to `riscv-opcodes` and then regenerate the file.

An alternate idiom is to specify bitfields directly. For example, this is necessary for compressed instructions that are not in `RISCV_imported_decode_pkg.svh`. Observe how the coverpoint uses `insn[15:0]` and `wildcard bins` with `?` for don't care in some bitfields of the instruction. Also observe how the coverpoint uses `` `ifdef `` to define bins that only apply to a certain XLEN or if a certain extension or parameter is supported. <!-- TODO: compressed instructions should be using the named version as well. -->

```SystemVerilog
    storeops: coverpoint ins.current.insn[15:0] {
        wildcard bins c_sw    = {16'b110_???_???_??_???_00};
        wildcard bins c_swsp  = {16'b110_??????_?????_10};
        `ifdef ZCB_SUPPORTED
            wildcard bins c_sb    = {16'b100010_???_??_???_00};
            wildcard bins c_sh    = {16'b100011_???_0?_???_00};
        `endif
        `ifdef XLEN64
            wildcard bins c_sd   = {16'b111_???_???_??_???_00};
            wildcard bins c_sdsp = {16'b111_??????_?????_10};
        `endif

    }
```

#### CSR Values

The preferred idiom to check the value of a CSR bitfield is to use the `get_csr_val` function, specifying the CSR name and bitfield (`mstatus` and `tsr`). `` `SAMPLE_BEFORE `` means to get the value before the instruction retires, while `` `SAMPLE_AFTER `` means to get the value after the instruction retires. The CSR names and fields match the ISA manual, and are listed in `framework/src/act/fcov/coverage/RISCV_coverage_csr.svh`.

```SystemVerilog
    old_mstatus_tsr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tsr")[0] {
    }
```

`get_csr_val` returns an XLEN bit vector with the relevant value in the least significant bits. If you are planning to use implicit bins, make sure to extract the relevant bits so that it doesn't try to fill in bins for all XLEN bits.

CSRs with no bitfields can be accessed by passing the CSR name again as the field name.

An alternate idiom is to refer to the RVVI structure, which holds the value of the CSR before (`ins.prev`) or after (`ins.current`) the instruction.

```SystemVerilog
    mtvec_stvec_ne: coverpoint {ins.current.csr[CSR_MTVEC] != ins.current.csr[CSR_STVEC]} {
        bins notequal = {1};
    }
```

#### Cross-Products

The coverpoints given in the spreadsheet are usually cross-products of simpler coverpoints. The following example shows how to define coverpoints for the three lsbs of the address, and for whether an address is illegal, and then cross them with the storeops defined above to create up to 6 bins of store ops \* 8 bins of address lsbs for cp_store_address_misaligned, for a total of 48 bins.

```SystemVerilog

    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0]  {
        // auto fills 000 through 111
    }
    illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
        bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }

    cp_store_address_misaligned:             cross storeops, adr_LSBs;
    cp_store_access_fault:                   cross storeops, illegal_address;
```

#### Extending RVVI

If additional state is absolutely necessary, it could be added to the Extended RVVI specification. This involves changing the spec and tools that read and write it, so should not be done if there is any other reasonable way to write a "good enough" coverpoint. Open an issue to discuss other potential options before proceeding down this route.

### Adding New Privileged Tests

Each privileged test needs a Python generator that produces an assembly language test
that exercises the relevant behaviors. Privileged test generators use similar methods to [Special Generators](#special-generators), so make sure to read that portion of this guide first.

The following applies to all privileged test generators:

- All privileged test generators must go in [`generators/testgen/src/testgen/priv/extensions`](../generators/testgen/src/testgen/priv/extensions/). All Python files in that directory are automatically discovered and imported.
- All privileged generator functions must be decorated with the `@add_priv_test_generator("<test_name>", required_extensions=["<extension_name>", "<extension_name>"])` decorator. This tells the framework what to name the test and which extensions are required to run it on a target. Optionally, `march_extensions=["<extension_name>", "<extension_name>"]` can also be specified to indicate which extensions should be passed in the `march` string to the compiler. If not specified, this defaults to the list from `required_extensions`.
- All privileged generator functions must use the following signature:

  ```py
  def make_name(test_data: TestData) -> list[str]:

  ```

  - `test_data` is a dataclass that is passed to all parts of the test generation process and stores the signature count, debug strings, etc.
  - The generator must return a list of strings. They will be combined with newlines separating each string in the final output test.

The body of most privileged test generator functions is a series of calls to other functions that generate the code for each coverpoint. For example, the main generator from [`Sm.py`](../generators/testgen/src/testgen/priv/extensions/Sm.py) is included below:

```py
# All priv test generators use the @add_priv_test_generator decorator to specify the
# name and required extensions.
@add_priv_test_generator("Sm", required_extensions=["Sm", "Zicsr"])
# All priv test generators must use the standard function signature.
def make_sm(test_data: TestData) -> list[str]:
    """Generate tests for Sm machine-mode testsuite."""
    lines: list[str] = []
    # Priv test generators call other internal functions to build up the test
    lines.extend(_generate_mcause_tests(test_data))
    lines.extend(_generate_mstatus_sd_tests(test_data))
    lines.extend(_generate_priv_inst_tests(test_data))
    lines.extend(_generate_mret_tests(test_data))
    lines.extend(_generate_sret_tests(test_data))
    lines.extend(_generate_mcsr_tests(test_data))
    lines.extend(_generate_mcsr_cntr_tests(test_data))
    # A list of assembly strings is returned. These strings will be joined together
    # with newlines in the final output file.
    return lines
```

There are a few important gotchas to keep in mind when writing privileged tests:

- There should be no loops in the assembly code. Loops make debugging difficult and prevent testcases from being uniquely associated with debug strings. Instead, use loops in the Python generator to emit repetitive assembly.
- The trap handler skips 4 bytes when returning to the test. This means that every instruction that could trap must be followed by a `nop` (or two `c.nop` if compressed instructions are supported). Alternatively, this skipped instruction can be used to change a counter/indicator of some kind to detect if a trap was taken. This is generally not necessary because the total number of traps is always checked at the end of a test.
- Different implementations may trap on different CSRs, so always assume a CSR access could trap. The `CSRRW`, `CSRRS`, `CSRR`, etc. macros include a `nop` after the CSR access and should always be used in place of raw CSR instructions.

For examples of how to write the individual coverpoint helper functions for privileged test generators, review [`Sm.py`](../generators/testgen/src/testgen/priv/extensions/Sm.py) and [`ExceptionsZc.py`](../generators/testgen/src/testgen/priv/extensions/ExceptionsZc.py). Here are a few additional notes that apply to all privileged test helper functions:

- Do not hardcode register numbers. Instead use the register allocator described above for unprivileged coverpoints (`test_data.int_regs.get_registers(3)`, etc.).
- Begin each coverpoint with a call to `comment_banner(coverpoint, "comments")` to add a descriptive marker to the generated test.
- Include a call to `test_data.add_testcase` before each testcase within a coverpoint. This creates the appropriate labels and debug strings.
- To the extent possible, reuse functions and define new helper functions if a snippet of assembly seems like it will be useful in multiple tests. See [`csr.py`](../generators/testgen/src/testgen/asm/csr.py) for a few examples including `gen_csr_read_sigupd`, `gen_csr_write_sigupd`, and `csr_walk_test`.

## Debugging Coverage

After writing initial drafts of coverpoints and tests, run them with `make coverage EXTENSIONS=ExceptionsZc`. Omit the `--jobs` flag so they run in order and it is easier to localize which one failed. By giving the name of the test suite (e.g. ExceptionsZc), you only run the new suite of interest, saving runtime.

You can expect syntax errors in the tests that are easy to locate based on the compiler messages.

Once those are resolved, you may have bugs that cause an infinite loop. If the test is taking a long time to run, halt it. Look at the log file in (e.g.) `work/sail-rv64-max/build/priv/ExceptionsZc/ExceptionsZc.sig.trace`. Scroll through until you find the misbehavior that put the system into an infinite loop.

You can expect syntax errors in the coverpoints that are easy to locate based on the filename and line number reported by the HDL simulator. Look in `work/sail-rv64-max/coverage/priv/ExceptionsZc/ExceptionsZc.ucdb.log` for messages.

Once these are resolved, look in a coverage report directory such as `work/sail-rv64-max/reports/_overall_summary.txt`. Expect to have less than 100% coverage on the new coverpoints on the first try. Look in the same directory at `<suite>_report.txt` and `<suite>_uncovered.txt` for details about the coverpoint bins being hit and missed.

Diagnosing missing coverage can be difficult. The bug could be in the coverpoint or the tests. It is helpful to add a statement to display RVVI signals relevant to the coverpoint after each instruction executes, so you can compare them against expectation and localize the problem. In (e.g.) the `exceptionszc_sample` function of `coverpoints/priv/ExceptionsZc_coverage.svh`, add a statement like:

```SystemVerilog
$display("mode: %b, medel: %b, funct3: %b, rs1_1_0: %b, pc_1: %b, offset: %b ",
     ins.current.mode,
     ins.current.csr[12'h302],
     ins.current.insn[14:12],
     ins.current.rs1_val[1:0],
     ins.current.pc_rdata[1],
     ins.current.imm[1:0]);
```

Then look in the `work/sail-rv64-max/coverage/priv/ExceptionsZc/ExceptionsZc.ucdb.log` file to see how these RVVI signals change after each instruction. Find the instruction that should have hit a bin, and see which coverpoint input(s) aren't taking on the necessary values. It is often useful to compare the `*.ucdb.log` file with the `*.trace` file in `work/sail-rv64-max/coverage/priv/ExceptionsZc`.
