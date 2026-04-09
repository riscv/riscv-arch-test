# User Preferences — General

- .md files: bullet points over prose, tight structure, no padding. Only include what is necessary.
- When updating any .md file, actively look for content to delete — if you're not occasionally removing/refactoring something, you're not changing enough.
- Always run `make` with `-j16` for broad regression/build work.
- Do NOT read make/build run logs inline — they contain too much noise. Check log files directly only when there is an error to diagnose.
- Always use `timeout Xs` AND `--inst-limit N` when running `sail_riscv_sim` manually. Trapping tests loop forever; the trace file gets deleted on failure. Keep inst-limit small (e.g. 500) to get a short readable trace before the trap loop.
  - Example: `timeout 2s sail_riscv_sim --config sail.json --trace-instr --trace-exception --trace-output /tmp/trace.txt --inst-limit 500 test.elf`
- For isolated coverpoint debug loops, run coverage as `timeout 120s make coverage` so hangs are cut quickly and the stuck test name is visible in terminal output.
- **"save for wipe"** = check `progress.json`, restore the current CSV, isolate the next untested coverpoint, and update any stale md files — preparing for a context clear.
