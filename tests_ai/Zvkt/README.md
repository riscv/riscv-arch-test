# Zvkt: no rule-derived tests

The Zvkt rules in `src/unpriv/zvk.adoc` (`Zvkt_req`, `Zvkt_diel_def`, `Zvkt_diel_constants_exempt`,
`Zvkt_diel_control_exempt`) require data-independent execution latency. A functional test cannot observe latency, and
a timing test would need a cycle-accurate DUT and a statistical method, so this directory has no tests. The
instructions Zvkt covers are tested functionally in their own directories.
