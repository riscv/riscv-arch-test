# Hypervisor test ELFs for whisper-rv64-max

`elfs/priv/<Suite>/` holds the self-checking ELFs of the 31 hypervisor suites, built for
`config/whisper/whisper-rv64-max` (180 ELFs). SvHZicboSm has none, because it needs a PMP granularity of at most
1 KiB and this configuration has 4 KiB. The sources are in `tests/priv/<Suite>/`.

Run every ELF from the top of the repository:

```
for e in work/whisper-rv64-max/elfs/priv/*/*.elf; do
  whisper --maxinst 100000000:f --config config/whisper/whisper-rv64-max/whisper.json "$e" >/dev/null 2>&1 \
    && echo "PASS $e" || echo "FAIL $e"
done
```

Each ELF exits with status 0 when it passes. Add `--log --logfile trace.log` to trace one ELF.

To rebuild them instead:

```
EXTENSIONS=H,HSm,ExceptionsH,ExceptionsHSm,ExceptionsHF,ExceptionsHV,InterruptsH,InterruptsHSm,InterruptsHGei,SstcH,SstcHSm,ZicntrH,ZicntrHSm,SmcntrpmfH,Shcounterenw,SvH,SvHSm,SvHZicbo,SvHZicboSm,Shgatpa,Shvsatpa,PMPH,SvinvalH,SvinvalHSm,Shtvala,Shvstvala,Shvstvecd,SsstateenH,SmstateenH,SsnpmH,ZicfilpH make whisper-rv64-max
```

With Whisper b09a6ea (the CI pin), 176 of 180 pass. The failures are Whisper bugs:

- SmstateenH_hs-00: reserved hstateen0 bit 53 is writable (fixed upstream in 656b8edd)
- SsnpmH_sv48x4_hlv-00, SsnpmH_sv57x4_hlv-00: hstatus.HUPMM is read-only zero (tenstorrent/whisper#86)
- ZicfilpH-00: SRET in VS-mode takes the landing-pad enable from hstatus.SPV (tenstorrent/whisper#85)
