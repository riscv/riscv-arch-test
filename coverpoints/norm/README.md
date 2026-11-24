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

A rule with no coverpoint, or with a gap in its coverage, has a short explanation instead.
The explanation prefixes are defined in the Normative Rule Explanations section of
`docs/ctp/src/strategy.adoc`.
