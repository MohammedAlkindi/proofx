# PX-COL-004 follow-ups (exploratory)

* `grid.py`: 12 successive-halving schedules against odd32 on the PX-COL-004
  test windows, which became development data once that study finished. It
  uses its own pools (tag 0x50584335). No schedule clearly beats the frozen
  8x / 16-32-64 one; see `docs/research/2026-11-next-steps.md`, item C.
* `walltime.py LOWER...`: local wall time per run for uniform, odd32 and halving,
  vectorized with NumPy. It is timing only; hit counts come from the PX-COL-004
  summaries. Single machine; not a benchmark.
