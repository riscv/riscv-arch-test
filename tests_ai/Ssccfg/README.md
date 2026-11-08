# Ssccfg: supervisor counter configuration

The Ssccfg tests are generated with the Smcdeleg tests by `tests_ai/gen/gen_Smcdeleg.py`.
[`../Smcdeleg/README.md`](../Smcdeleg/README.md) describes both suites:

- how they are tested;
- the rules not tested;
- the subtleties;
- how to enable the extensions on each DUT;
- the model bugs found.

The rules about M-level state (`Ssccfg_lcofi_mvip_mvien`) are in `Smcdeleg/`. Sail does not implement
Smcdeleg/Ssccfg, so these tests were checked on QEMU, Whisper, Spike and Imperas.
