# Normative-rule mappings

Each YAML record identifies one rule with `name`, or several rules with `names`.
Its `coverpoint` list contains covergroup/coverpoint references and, where needed,
short explanations of coverage gaps. Keep comments to the relevant requirement;
extract the applicable rows or fields instead of copying a large specification table.

A resolving reference establishes a mapping, not complete coverage of every clause.
Preserve existing references when explaining a remaining gap. Use these prefixes
for prose entries:

| Prefix                       | Meaning                                                                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `No independent assertion:`  | A definition, permission, recommendation, or unspecified outcome adds no independently required behavior. State which clause this applies to.                  |
| `Configuration requirement:` | An extension dependency or platform/configuration constraint. Identify the validator and its scope, or explicitly say it is not yet checked.                   |
| `Software requirement:`      | An obligation on generated tests, system software, or test setup. State the obligation and whether it is checked.                                              |
| `Needs test:`                | Observable architectural behavior needs a directed test or coverpoint. Describe the missing check.                                                             |
| `Needs infrastructure:`      | Testing needs additional stimulus, observation, or methodology, such as concurrent harts, devices, reset capture, or timing measurement. Name what is missing. |
| `Out of scope:`              | The rule cannot apply to the named profile or test configuration. Explain the exclusion; do not use this for behavior merely lacking a test.                   |

Avoid bare `TODO`, `Implicit`, `Untested`, and `Untestable`. Implementation-defined
choices and optional features can still have testable constraints. Check the allowed
set of results rather than requiring one implementation's choice. An unspecified
choice among legal values does not remove the requirement that the result be legal.

For configuration requirements, write `checked by UDB` only when an actual UDB
validation rule enforces the stated constraint. Cite the source file, validation
key, and pinned revision. Use AsciiDoc links inside YAML strings so the CTP renders
them, for example `https://.../ext/F.yaml#L17[F.requirements]`. Keep the explanation
to a short paragraph even when a rule has several dependencies.

The current citations use UDB 0.1.18, pinned in the framework Gemfile. Its
[configuration validator](https://github.com/riscv/riscv-unified-db/blob/25c483067a6575b7c9592094b13cc0c9d0c75bab/tools/ruby-gems/udb/lib/udb/cfg_arch.rb#L305)
checks extension requirements, parameter requirements, and parameter schemas.
For example, [F.requirements](https://github.com/riscv/riscv-unified-db/blob/25c483067a6575b7c9592094b13cc0c9d0c75bab/spec/std/isa/ext/F.yaml#L17)
requires Zicsr. This validates the declared configuration; it does not prove that
the hardware implements that configuration correctly.

Use `not yet checked by UDB` when UDB is the appropriate validator but lacks the
needed check. Use `not yet checked` when another mechanism is needed, and name it.
A parameter's existence, a matching reference-model configuration, or successful
test execution is not by itself a validation rule. For partial validation, state
both what UDB checks and what remains unchecked.

For I/O-related gaps, distinguish supplying attributes from observing behavior.
Svpbmt can give RAM non-cacheable attributes (PBMT=NC/IO), or non-idempotent,
channel 0 I/O attributes (PBMT=IO). Ordering checks still need concurrent harts or
an access monitor; speculative or redundant RAM reads may leave no signature
evidence. PBMT does not portably select other ordering channels, access-width
restrictions, AMO support levels, or LR/SC reservability. These need suitable
platform regions. PBMT tests exercise effective attributes; native PMA decoding
and accesses outside the mapping need separate coverage.

Use the same explanation wherever the same rule appears. Split a `names` record
when its rules need different explanations. The initial cleanup covers existing
prose-only entries in the RVA23 mandatory/optional rule audit; entries outside that
scope should follow these conventions when updated.
