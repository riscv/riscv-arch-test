# Normative rule mappings

Each file in this directory maps the normative rules of one extension, as tagged in the
ISA manual, to the coverpoints that test them. The CTP builds each extension's normative
rule table from these files.

An entry names one rule with `name`, or several rules with the same coverage with `names`.
Its `coverpoint` list gives each coverpoint as `covergroup/coverpoint`:

```yaml
- name: fsw_flw_bits_maintained
  coverpoint: ["F_flw_cg/cp_memval_fp_single", "F_fsw_cg/cp_fs2_edges"]
```

When a rule has no coverpoint, or its coverpoints miss part of the rule, the list holds an
explanation instead, or as well. Each explanation starts with one of these prefixes:

| Prefix                       | Use when                                                                                                                       |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `No independent assertion:`  | The rule is a definition, permission, recommendation, or UNSPECIFIED behavior, so there is nothing to test.                    |
| `Configuration requirement:` | The rule constrains the configuration, such as an extension dependency. Say whether UDB checks it.                             |
| `Software requirement:`      | The rule constrains software. Say whether the tests are checked to follow it.                                                  |
| `Needs test:`                | The behavior can be tested, but no test checks it yet. Say what the test should do.                                            |
| `Needs infrastructure:`      | Testing the rule needs something the framework does not have, such as multiple harts, devices, or timing measurement. Name it. |
| `Out of scope:`              | The rule does not apply to the configurations the tests support.                                                               |

For example:

```yaml
- name: F_depends_Zicsr
  coverpoint: ["Configuration requirement: F requires Zicsr; checked by UDB."]
```

Write a short explanation about the specific rule. When the same rule appears in more than
one file, use the same explanation, and split a `names` entry if its rules need different
explanations.

An implementation-defined result can usually still be tested: the test checks that the
result is one of the legal values. Use `No independent assertion:` only when the rule itself
rules out no behavior.

Write `checked by UDB` only when UDB rejects a configuration that breaks the rule.
