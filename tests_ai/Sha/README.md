# Sha: rule-derived tests for the augmented hypervisor extension

Sha has one rule, `Sha_dep` (`src/priv/sha.adoc`): Sha comprises H, Ssstateen, Shcounterenw, Shvstvala, Shtvala,
Shvstvecd, Shvsatpa and Shgatpa. The generator is `tests_ai/gen/gen_Sx.py`, which writes no test here.

## How the extension is tested

Sha adds no behavior of its own. Each member's behavior is tested by that member's suite: `tests_ai/H`,
`tests_ai/Shvstvala`, `Shtvala`, `Shvstvecd`, `Shvsatpa`, `Shgatpa`, and the Ssstateen and Shcounterenw suites. Those
suites run on a configuration that lists the member.

## Rules not tested here

- `Sha_dep` is a membership rule. Whether a configuration that lists Sha also lists every member is a property of
  the configuration file, not of the hart, so no test can observe it. A hart that claims Sha but lacks a member fails
  that member's suite.

## Subtleties

- None.
