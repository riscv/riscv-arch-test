# 007 — Sail asserts on unaligned vector register group instead of trapping

## Summary

The Sail RISC-V simulator (`/opt/riscv/bin/sail_riscv_sim`) hits a
hard assertion when a vector instruction encodes a register that is not
a multiple of its EMUL, instead of raising the SsstrictV
illegal-instruction trap.

```
Assertion failed: Invalid register group: group 5 is not a multiple of its EMUL 2.
```

## Affected instructions

Any vector instruction with EMUL ≥ 2 whose **non-target** vs1/vs2/vd/vs3
field is not aligned to its EMUL. Discovered while building
`cp_ssstrictv_lmulgt1_off_group` tests for `vredminu.vs` (and many other
ops) where the random vs2 happened to land on an unaligned register
while we deliberately mis-aligned vd.

## Reproduction

```
make tests
/opt/riscv/bin/sail_riscv_sim --config config/sail/sail-rv64-max/sail.json \
  --test-signature=work/sail-rv64-max/build/priv/SsstrictV/SsstrictV_rv64_p16.sig \
  --signature-granularity 8 \
  work/sail-rv64-max/build/priv/SsstrictV/SsstrictV_rv64_p16.sig.elf
```

The instruction in question (e.g. `vredminu.vs v1, v17, v4` with
`vsetivli ... e8, m2`) encodes vs2=v17, EMUL=2 → unaligned, Sail asserts.

The SsstrictV spec says any unaligned-to-EMUL register field should
raise an illegal-instruction trap; the assertion makes it impossible to
test crosses where the _targeted_ unaligned field is on a different
operand.

## Workaround

`cp_ssstrictv_lmulgt1_off_group` now forces every non-targeted vector
operand to be aligned to `max(EMUL)` (using `2*LMUL` for widening /
narrowing ops) so that only the chosen field violates alignment. See
`generators/testgen/scripts/priv/cp_ssstrictv_lmulgt1_off_group.py
::_emit_one`.

## Long-term fix

Sail should raise an illegal-instruction trap for any reserved-encoding
violation (unaligned register, EMUL out of [1/8,8], reserved fields)
instead of asserting. Same root cause as Issue 006 but for a different
reserved-encoding category.
