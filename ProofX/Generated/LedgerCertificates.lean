/-
  GENERATED FILE -- DO NOT EDIT BY HAND.

  Regenerate with:
    python -m codebase.cli export lean

  Verify it still matches the ledger with:
    python -m codebase.cli export lean --check

  Provenance
    exporter_version : proofx.lean_export.v1
    ledger_path      : results/ledger.jsonl
    ledger_digest    : sha256:2c5b1935b868905ddfef4c5843d33fa276a912972d7561e59501a09fd0cbeb95
    ledger_rows      : 500
    certificates     : 500 (250 collatz, 250 goldbach)
    claim_level      : kernel_checked_certificate
    est_unfoldings   : 92699
    max_rec_depth    : 444

  The digest covers the ledger facts these certificates are built from
  -- candidate, witness, stopping time, strategy, and seed -- and not
  wall-clock fields or floating-point ranking scores, which differ in
  the last place across platforms without changing any certificate. It
  moves if a certificate would change, and not otherwise.

  Each theorem below is a bounded, finite fact checked by the Lean
  kernel. None of them states or implies the Collatz or Goldbach
  conjecture, and a passing build is not evidence for either. See
  docs/research-standards.md and docs/lean4.md.
-/
import ProofX.Certificates

-- `decide` unfolds `reachesOneWithin` once per step of fuel and
-- `hasDivisorUpTo` once per candidate divisor, and each unfolding costs
-- elaborator recursion depth. The default limit of 512 is exceeded by
-- the deepest certificate here, so the budget is raised to fit it.
-- This is an elaboration limit, not a soundness setting: the kernel
-- still checks every proof.
set_option maxRecDepth 4096

namespace ProofX.Generated

/-! ### Collatz

Each theorem states that the candidate reaches 1 within the exact
number of steps the search recorded. -/

theorem collatz_27_reaches_one :
    reachesOneWithin 111 27 = true := by
  decide

theorem collatz_93_reaches_one :
    reachesOneWithin 17 93 = true := by
  decide

theorem collatz_111_reaches_one :
    reachesOneWithin 69 111 = true := by
  decide

theorem collatz_117_reaches_one :
    reachesOneWithin 20 117 = true := by
  decide

theorem collatz_123_reaches_one :
    reachesOneWithin 46 123 = true := by
  decide

theorem collatz_159_reaches_one :
    reachesOneWithin 54 159 = true := by
  decide

theorem collatz_183_reaches_one :
    reachesOneWithin 93 183 = true := by
  decide

theorem collatz_189_reaches_one :
    reachesOneWithin 106 189 = true := by
  decide

theorem collatz_207_reaches_one :
    reachesOneWithin 88 207 = true := by
  decide

theorem collatz_219_reaches_one :
    reachesOneWithin 52 219 = true := by
  decide

theorem collatz_222_reaches_one :
    reachesOneWithin 70 222 = true := by
  decide

theorem collatz_231_reaches_one :
    reachesOneWithin 127 231 = true := by
  decide

theorem collatz_237_reaches_one :
    reachesOneWithin 34 237 = true := by
  decide

theorem collatz_243_reaches_one :
    reachesOneWithin 96 243 = true := by
  decide

theorem collatz_246_reaches_one :
    reachesOneWithin 47 246 = true := by
  decide

theorem collatz_249_reaches_one :
    reachesOneWithin 47 249 = true := by
  decide

theorem collatz_252_reaches_one :
    reachesOneWithin 109 252 = true := by
  decide

theorem collatz_703_reaches_one :
    reachesOneWithin 170 703 = true := by
  decide

theorem collatz_871_reaches_one :
    reachesOneWithin 178 871 = true := by
  decide

theorem collatz_877_reaches_one :
    reachesOneWithin 54 877 = true := by
  decide

theorem collatz_895_reaches_one :
    reachesOneWithin 98 895 = true := by
  decide

theorem collatz_943_reaches_one :
    reachesOneWithin 36 943 = true := by
  decide

theorem collatz_955_reaches_one :
    reachesOneWithin 28 955 = true := by
  decide

theorem collatz_991_reaches_one :
    reachesOneWithin 98 991 = true := by
  decide

theorem collatz_1003_reaches_one :
    reachesOneWithin 41 1003 = true := by
  decide

theorem collatz_1015_reaches_one :
    reachesOneWithin 36 1015 = true := by
  decide

theorem collatz_1021_reaches_one :
    reachesOneWithin 49 1021 = true := by
  decide

theorem collatz_1406_reaches_one :
    reachesOneWithin 171 1406 = true := by
  decide

theorem collatz_1790_reaches_one :
    reachesOneWithin 99 1790 = true := by
  decide

theorem collatz_1982_reaches_one :
    reachesOneWithin 99 1982 = true := by
  decide

theorem collatz_2030_reaches_one :
    reachesOneWithin 37 2030 = true := by
  decide

theorem collatz_2042_reaches_one :
    reachesOneWithin 50 2042 = true := by
  decide

theorem collatz_3580_reaches_one :
    reachesOneWithin 100 3580 = true := by
  decide

theorem collatz_3964_reaches_one :
    reachesOneWithin 100 3964 = true := by
  decide

theorem collatz_4030_reaches_one :
    reachesOneWithin 95 4030 = true := by
  decide

theorem collatz_8060_reaches_one :
    reachesOneWithin 96 8060 = true := by
  decide

theorem collatz_8126_reaches_one :
    reachesOneWithin 65 8126 = true := by
  decide

theorem collatz_16252_reaches_one :
    reachesOneWithin 66 16252 = true := by
  decide

theorem collatz_16318_reaches_one :
    reachesOneWithin 66 16318 = true := by
  decide

theorem collatz_32636_reaches_one :
    reachesOneWithin 67 32636 = true := by
  decide

theorem collatz_32702_reaches_one :
    reachesOneWithin 147 32702 = true := by
  decide

theorem collatz_65404_reaches_one :
    reachesOneWithin 148 65404 = true := by
  decide

theorem collatz_65470_reaches_one :
    reachesOneWithin 192 65470 = true := by
  decide

theorem collatz_130940_reaches_one :
    reachesOneWithin 193 130940 = true := by
  decide

theorem collatz_131006_reaches_one :
    reachesOneWithin 131 131006 = true := by
  decide

theorem collatz_262012_reaches_one :
    reachesOneWithin 132 262012 = true := by
  decide

theorem collatz_524024_reaches_one :
    reachesOneWithin 133 524024 = true := by
  decide

theorem collatz_524090_reaches_one :
    reachesOneWithin 270 524090 = true := by
  decide

theorem collatz_524126_reaches_one :
    reachesOneWithin 76 524126 = true := by
  decide

theorem collatz_524156_reaches_one :
    reachesOneWithin 226 524156 = true := by
  decide

theorem collatz_1048252_reaches_one :
    reachesOneWithin 77 1048252 = true := by
  decide

theorem collatz_1048270_reaches_one :
    reachesOneWithin 227 1048270 = true := by
  decide

theorem collatz_1048282_reaches_one :
    reachesOneWithin 134 1048282 = true := by
  decide

theorem collatz_1048294_reaches_one :
    reachesOneWithin 72 1048294 = true := by
  decide

theorem collatz_1048300_reaches_one :
    reachesOneWithin 72 1048300 = true := by
  decide

theorem collatz_1048306_reaches_one :
    reachesOneWithin 227 1048306 = true := by
  decide

theorem collatz_1048312_reaches_one :
    reachesOneWithin 227 1048312 = true := by
  decide

theorem collatz_1048366_reaches_one :
    reachesOneWithin 72 1048366 = true := by
  decide

theorem collatz_1048378_reaches_one :
    reachesOneWithin 152 1048378 = true := by
  decide

theorem collatz_1048414_reaches_one :
    reachesOneWithin 165 1048414 = true := by
  decide

theorem collatz_1048426_reaches_one :
    reachesOneWithin 165 1048426 = true := by
  decide

theorem collatz_1048438_reaches_one :
    reachesOneWithin 72 1048438 = true := by
  decide

theorem collatz_1048444_reaches_one :
    reachesOneWithin 196 1048444 = true := by
  decide

theorem collatz_1048462_reaches_one :
    reachesOneWithin 165 1048462 = true := by
  decide

theorem collatz_1048474_reaches_one :
    reachesOneWithin 165 1048474 = true := by
  decide

theorem collatz_1048486_reaches_one :
    reachesOneWithin 134 1048486 = true := by
  decide

theorem collatz_1048492_reaches_one :
    reachesOneWithin 134 1048492 = true := by
  decide

theorem collatz_1048498_reaches_one :
    reachesOneWithin 165 1048498 = true := by
  decide

theorem collatz_1048504_reaches_one :
    reachesOneWithin 165 1048504 = true := by
  decide

theorem collatz_1048522_reaches_one :
    reachesOneWithin 77 1048522 = true := by
  decide

theorem collatz_1048534_reaches_one :
    reachesOneWithin 178 1048534 = true := by
  decide

theorem collatz_1048540_reaches_one :
    reachesOneWithin 134 1048540 = true := by
  decide

theorem collatz_1048546_reaches_one :
    reachesOneWithin 165 1048546 = true := by
  decide

theorem collatz_1048552_reaches_one :
    reachesOneWithin 134 1048552 = true := by
  decide

theorem collatz_1048564_reaches_one :
    reachesOneWithin 134 1048564 = true := by
  decide

theorem collatz_2096828_reaches_one :
    reachesOneWithin 166 2096828 = true := by
  decide

theorem collatz_2096846_reaches_one :
    reachesOneWithin 153 2096846 = true := by
  decide

theorem collatz_2096858_reaches_one :
    reachesOneWithin 135 2096858 = true := by
  decide

theorem collatz_2096870_reaches_one :
    reachesOneWithin 73 2096870 = true := by
  decide

theorem collatz_2096876_reaches_one :
    reachesOneWithin 73 2096876 = true := by
  decide

theorem collatz_2096882_reaches_one :
    reachesOneWithin 197 2096882 = true := by
  decide

theorem collatz_2096888_reaches_one :
    reachesOneWithin 197 2096888 = true := by
  decide

theorem collatz_2096942_reaches_one :
    reachesOneWithin 166 2096942 = true := by
  decide

theorem collatz_2096954_reaches_one :
    reachesOneWithin 197 2096954 = true := by
  decide

theorem collatz_2096990_reaches_one :
    reachesOneWithin 166 2096990 = true := by
  decide

theorem collatz_2097002_reaches_one :
    reachesOneWithin 166 2097002 = true := by
  decide

theorem collatz_2097014_reaches_one :
    reachesOneWithin 166 2097014 = true := by
  decide

theorem collatz_2097020_reaches_one :
    reachesOneWithin 166 2097020 = true := by
  decide

theorem collatz_2097038_reaches_one :
    reachesOneWithin 73 2097038 = true := by
  decide

theorem collatz_2097050_reaches_one :
    reachesOneWithin 78 2097050 = true := by
  decide

theorem collatz_2097062_reaches_one :
    reachesOneWithin 272 2097062 = true := by
  decide

theorem collatz_2097068_reaches_one :
    reachesOneWithin 179 2097068 = true := by
  decide

theorem collatz_2097074_reaches_one :
    reachesOneWithin 166 2097074 = true := by
  decide

theorem collatz_2097080_reaches_one :
    reachesOneWithin 135 2097080 = true := by
  decide

theorem collatz_2097098_reaches_one :
    reachesOneWithin 166 2097098 = true := by
  decide

theorem collatz_2097110_reaches_one :
    reachesOneWithin 264 2097110 = true := by
  decide

theorem collatz_2097116_reaches_one :
    reachesOneWithin 135 2097116 = true := by
  decide

theorem collatz_2097122_reaches_one :
    reachesOneWithin 135 2097122 = true := by
  decide

theorem collatz_2097128_reaches_one :
    reachesOneWithin 135 2097128 = true := by
  decide

theorem collatz_2097140_reaches_one :
    reachesOneWithin 228 2097140 = true := by
  decide

theorem collatz_4193980_reaches_one :
    reachesOneWithin 167 4193980 = true := by
  decide

theorem collatz_4193998_reaches_one :
    reachesOneWithin 185 4193998 = true := by
  decide

theorem collatz_4194010_reaches_one :
    reachesOneWithin 229 4194010 = true := by
  decide

theorem collatz_4194022_reaches_one :
    reachesOneWithin 167 4194022 = true := by
  decide

theorem collatz_4194028_reaches_one :
    reachesOneWithin 167 4194028 = true := by
  decide

theorem collatz_4194034_reaches_one :
    reachesOneWithin 167 4194034 = true := by
  decide

theorem collatz_4194040_reaches_one :
    reachesOneWithin 167 4194040 = true := by
  decide

theorem collatz_4194094_reaches_one :
    reachesOneWithin 167 4194094 = true := by
  decide

theorem collatz_4194106_reaches_one :
    reachesOneWithin 136 4194106 = true := by
  decide

theorem collatz_4194142_reaches_one :
    reachesOneWithin 79 4194142 = true := by
  decide

theorem collatz_4194154_reaches_one :
    reachesOneWithin 136 4194154 = true := by
  decide

theorem collatz_4194166_reaches_one :
    reachesOneWithin 167 4194166 = true := by
  decide

theorem collatz_4194172_reaches_one :
    reachesOneWithin 273 4194172 = true := by
  decide

theorem collatz_4194190_reaches_one :
    reachesOneWithin 74 4194190 = true := by
  decide

theorem collatz_4194202_reaches_one :
    reachesOneWithin 167 4194202 = true := by
  decide

theorem collatz_4194214_reaches_one :
    reachesOneWithin 273 4194214 = true := by
  decide

theorem collatz_4194220_reaches_one :
    reachesOneWithin 265 4194220 = true := by
  decide

theorem collatz_4194226_reaches_one :
    reachesOneWithin 167 4194226 = true := by
  decide

theorem collatz_4194232_reaches_one :
    reachesOneWithin 136 4194232 = true := by
  decide

theorem collatz_4194250_reaches_one :
    reachesOneWithin 198 4194250 = true := by
  decide

theorem collatz_4194262_reaches_one :
    reachesOneWithin 167 4194262 = true := by
  decide

theorem collatz_4194268_reaches_one :
    reachesOneWithin 136 4194268 = true := by
  decide

theorem collatz_4194274_reaches_one :
    reachesOneWithin 136 4194274 = true := by
  decide

theorem collatz_4194280_reaches_one :
    reachesOneWithin 229 4194280 = true := by
  decide

theorem collatz_4194292_reaches_one :
    reachesOneWithin 229 4194292 = true := by
  decide

theorem collatz_8388284_reaches_one :
    reachesOneWithin 80 8388284 = true := by
  decide

theorem collatz_8388302_reaches_one :
    reachesOneWithin 305 8388302 = true := by
  decide

theorem collatz_8388314_reaches_one :
    reachesOneWithin 168 8388314 = true := by
  decide

theorem collatz_8388326_reaches_one :
    reachesOneWithin 168 8388326 = true := by
  decide

theorem collatz_8388332_reaches_one :
    reachesOneWithin 168 8388332 = true := by
  decide

theorem collatz_8388338_reaches_one :
    reachesOneWithin 274 8388338 = true := by
  decide

theorem collatz_8388344_reaches_one :
    reachesOneWithin 274 8388344 = true := by
  decide

theorem collatz_8388398_reaches_one :
    reachesOneWithin 168 8388398 = true := by
  decide

theorem collatz_8388410_reaches_one :
    reachesOneWithin 80 8388410 = true := by
  decide

theorem collatz_8388446_reaches_one :
    reachesOneWithin 168 8388446 = true := by
  decide

theorem collatz_8388458_reaches_one :
    reachesOneWithin 137 8388458 = true := by
  decide

theorem collatz_8388494_reaches_one :
    reachesOneWithin 168 8388494 = true := by
  decide

theorem collatz_8388506_reaches_one :
    reachesOneWithin 199 8388506 = true := by
  decide

theorem collatz_8388518_reaches_one :
    reachesOneWithin 274 8388518 = true := by
  decide

theorem collatz_8388524_reaches_one :
    reachesOneWithin 168 8388524 = true := by
  decide

theorem collatz_8388530_reaches_one :
    reachesOneWithin 137 8388530 = true := by
  decide

theorem collatz_8388536_reaches_one :
    reachesOneWithin 137 8388536 = true := by
  decide

theorem collatz_8388554_reaches_one :
    reachesOneWithin 243 8388554 = true := by
  decide

theorem collatz_8388584_reaches_one :
    reachesOneWithin 230 8388584 = true := by
  decide

theorem collatz_16776892_reaches_one :
    reachesOneWithin 169 16776892 = true := by
  decide

theorem collatz_16776910_reaches_one :
    reachesOneWithin 138 16776910 = true := by
  decide

theorem collatz_16776922_reaches_one :
    reachesOneWithin 81 16776922 = true := by
  decide

theorem collatz_16776934_reaches_one :
    reachesOneWithin 169 16776934 = true := by
  decide

theorem collatz_16776940_reaches_one :
    reachesOneWithin 169 16776940 = true := by
  decide

theorem collatz_16776946_reaches_one :
    reachesOneWithin 262 16776946 = true := by
  decide

theorem collatz_16776952_reaches_one :
    reachesOneWithin 81 16776952 = true := by
  decide

theorem collatz_16777006_reaches_one :
    reachesOneWithin 169 16777006 = true := by
  decide

theorem collatz_16777018_reaches_one :
    reachesOneWithin 275 16777018 = true := by
  decide

theorem collatz_33553784_reaches_one :
    reachesOneWithin 170 33553784 = true := by
  decide

theorem collatz_33553850_reaches_one :
    reachesOneWithin 82 33553850 = true := by
  decide

theorem collatz_67107700_reaches_one :
    reachesOneWithin 83 67107700 = true := by
  decide

theorem collatz_67107706_reaches_one :
    reachesOneWithin 78 67107706 = true := by
  decide

theorem collatz_67107742_reaches_one :
    reachesOneWithin 171 67107742 = true := by
  decide

theorem collatz_67107754_reaches_one :
    reachesOneWithin 140 67107754 = true := by
  decide

theorem collatz_67107766_reaches_one :
    reachesOneWithin 140 67107766 = true := by
  decide

theorem collatz_67107772_reaches_one :
    reachesOneWithin 140 67107772 = true := by
  decide

theorem collatz_67107790_reaches_one :
    reachesOneWithin 171 67107790 = true := by
  decide

theorem collatz_67107796_reaches_one :
    reachesOneWithin 83 67107796 = true := by
  decide

theorem collatz_67107802_reaches_one :
    reachesOneWithin 171 67107802 = true := by
  decide

theorem collatz_67107814_reaches_one :
    reachesOneWithin 83 67107814 = true := by
  decide

theorem collatz_67107820_reaches_one :
    reachesOneWithin 83 67107820 = true := by
  decide

theorem collatz_67107826_reaches_one :
    reachesOneWithin 83 67107826 = true := by
  decide

theorem collatz_67107832_reaches_one :
    reachesOneWithin 264 67107832 = true := by
  decide

theorem collatz_134215412_reaches_one :
    reachesOneWithin 79 134215412 = true := by
  decide

theorem collatz_134215418_reaches_one :
    reachesOneWithin 79 134215418 = true := by
  decide

theorem collatz_134215454_reaches_one :
    reachesOneWithin 84 134215454 = true := by
  decide

theorem collatz_134215478_reaches_one :
    reachesOneWithin 84 134215478 = true := by
  decide

theorem collatz_134215484_reaches_one :
    reachesOneWithin 172 134215484 = true := by
  decide

theorem collatz_134215502_reaches_one :
    reachesOneWithin 141 134215502 = true := by
  decide

theorem collatz_134215514_reaches_one :
    reachesOneWithin 84 134215514 = true := by
  decide

theorem collatz_134215526_reaches_one :
    reachesOneWithin 172 134215526 = true := by
  decide

theorem collatz_134215532_reaches_one :
    reachesOneWithin 141 134215532 = true := by
  decide

theorem collatz_134215538_reaches_one :
    reachesOneWithin 141 134215538 = true := by
  decide

theorem collatz_134215544_reaches_one :
    reachesOneWithin 141 134215544 = true := by
  decide

theorem collatz_134215574_reaches_one :
    reachesOneWithin 265 134215574 = true := by
  decide

theorem collatz_134215580_reaches_one :
    reachesOneWithin 172 134215580 = true := by
  decide

theorem collatz_134215598_reaches_one :
    reachesOneWithin 84 134215598 = true := by
  decide

theorem collatz_134215604_reaches_one :
    reachesOneWithin 172 134215604 = true := by
  decide

theorem collatz_134215610_reaches_one :
    reachesOneWithin 172 134215610 = true := by
  decide

theorem collatz_134215622_reaches_one :
    reachesOneWithin 84 134215622 = true := by
  decide

theorem collatz_134215628_reaches_one :
    reachesOneWithin 84 134215628 = true := by
  decide

theorem collatz_134215634_reaches_one :
    reachesOneWithin 141 134215634 = true := by
  decide

theorem collatz_134215640_reaches_one :
    reachesOneWithin 84 134215640 = true := by
  decide

theorem collatz_134215652_reaches_one :
    reachesOneWithin 84 134215652 = true := by
  decide

theorem collatz_134215658_reaches_one :
    reachesOneWithin 265 134215658 = true := by
  decide

theorem collatz_134215664_reaches_one :
    reachesOneWithin 265 134215664 = true := by
  decide

theorem collatz_268430836_reaches_one :
    reachesOneWithin 80 268430836 = true := by
  decide

theorem collatz_268430842_reaches_one :
    reachesOneWithin 142 268430842 = true := by
  decide

theorem collatz_268431196_reaches_one :
    reachesOneWithin 85 268431196 = true := by
  decide

theorem collatz_268431214_reaches_one :
    reachesOneWithin 142 268431214 = true := by
  decide

theorem collatz_268431220_reaches_one :
    reachesOneWithin 173 268431220 = true := by
  decide

theorem collatz_268431226_reaches_one :
    reachesOneWithin 142 268431226 = true := by
  decide

theorem collatz_268431262_reaches_one :
    reachesOneWithin 266 268431262 = true := by
  decide

theorem collatz_268431274_reaches_one :
    reachesOneWithin 85 268431274 = true := by
  decide

theorem collatz_268431286_reaches_one :
    reachesOneWithin 173 268431286 = true := by
  decide

theorem collatz_268431292_reaches_one :
    reachesOneWithin 372 268431292 = true := by
  decide

theorem collatz_268431310_reaches_one :
    reachesOneWithin 85 268431310 = true := by
  decide

theorem collatz_268431316_reaches_one :
    reachesOneWithin 266 268431316 = true := by
  decide

theorem collatz_268431322_reaches_one :
    reachesOneWithin 266 268431322 = true := by
  decide

theorem collatz_268431334_reaches_one :
    reachesOneWithin 142 268431334 = true := by
  decide

theorem collatz_268431340_reaches_one :
    reachesOneWithin 142 268431340 = true := by
  decide

theorem collatz_268431346_reaches_one :
    reachesOneWithin 266 268431346 = true := by
  decide

theorem collatz_268431352_reaches_one :
    reachesOneWithin 186 268431352 = true := by
  decide

theorem collatz_536861684_reaches_one :
    reachesOneWithin 143 536861684 = true := by
  decide

theorem collatz_536861690_reaches_one :
    reachesOneWithin 143 536861690 = true := by
  decide

theorem collatz_536862428_reaches_one :
    reachesOneWithin 143 536862428 = true := by
  decide

theorem collatz_536862452_reaches_one :
    reachesOneWithin 143 536862452 = true := by
  decide

theorem collatz_536862494_reaches_one :
    reachesOneWithin 143 536862494 = true := by
  decide

theorem collatz_536862518_reaches_one :
    reachesOneWithin 174 536862518 = true := by
  decide

theorem collatz_536862524_reaches_one :
    reachesOneWithin 267 536862524 = true := by
  decide

theorem collatz_536862542_reaches_one :
    reachesOneWithin 143 536862542 = true := by
  decide

theorem collatz_536862554_reaches_one :
    reachesOneWithin 143 536862554 = true := by
  decide

theorem collatz_536862566_reaches_one :
    reachesOneWithin 86 536862566 = true := by
  decide

theorem collatz_536862572_reaches_one :
    reachesOneWithin 174 536862572 = true := by
  decide

theorem collatz_536862578_reaches_one :
    reachesOneWithin 86 536862578 = true := by
  decide

theorem collatz_536862584_reaches_one :
    reachesOneWithin 373 536862584 = true := by
  decide

theorem collatz_536862614_reaches_one :
    reachesOneWithin 86 536862614 = true := by
  decide

theorem collatz_536862620_reaches_one :
    reachesOneWithin 86 536862620 = true := by
  decide

theorem collatz_536862644_reaches_one :
    reachesOneWithin 267 536862644 = true := by
  decide

theorem collatz_536862662_reaches_one :
    reachesOneWithin 267 536862662 = true := by
  decide

theorem collatz_536862668_reaches_one :
    reachesOneWithin 143 536862668 = true := by
  decide

theorem collatz_536862674_reaches_one :
    reachesOneWithin 143 536862674 = true := by
  decide

theorem collatz_536862680_reaches_one :
    reachesOneWithin 143 536862680 = true := by
  decide

theorem collatz_536862692_reaches_one :
    reachesOneWithin 267 536862692 = true := by
  decide

theorem collatz_536862704_reaches_one :
    reachesOneWithin 187 536862704 = true := by
  decide

theorem collatz_1073723380_reaches_one :
    reachesOneWithin 144 1073723380 = true := by
  decide

theorem collatz_2147446760_reaches_one :
    reachesOneWithin 145 2147446760 = true := by
  decide

theorem collatz_2147446772_reaches_one :
    reachesOneWithin 269 2147446772 = true := by
  decide

theorem collatz_4294893544_reaches_one :
    reachesOneWithin 270 4294893544 = true := by
  decide

theorem collatz_4294893556_reaches_one :
    reachesOneWithin 270 4294893556 = true := by
  decide

theorem collatz_8589787112_reaches_one :
    reachesOneWithin 271 8589787112 = true := by
  decide

theorem collatz_8589787124_reaches_one :
    reachesOneWithin 439 8589787124 = true := by
  decide

theorem collatz_17179574248_reaches_one :
    reachesOneWithin 440 17179574248 = true := by
  decide

theorem collatz_17179574260_reaches_one :
    reachesOneWithin 440 17179574260 = true := by
  decide

theorem collatz_34359148520_reaches_one :
    reachesOneWithin 441 34359148520 = true := by
  decide

theorem collatz_34359148532_reaches_one :
    reachesOneWithin 441 34359148532 = true := by
  decide

theorem collatz_68718297064_reaches_one :
    reachesOneWithin 442 68718297064 = true := by
  decide

theorem collatz_137436594128_reaches_one :
    reachesOneWithin 443 137436594128 = true := by
  decide

theorem collatz_137436594146_reaches_one :
    reachesOneWithin 443 137436594146 = true := by
  decide

theorem collatz_137436594152_reaches_one :
    reachesOneWithin 443 137436594152 = true := by
  decide

theorem collatz_274873188292_reaches_one :
    reachesOneWithin 444 274873188292 = true := by
  decide

theorem collatz_274873188298_reaches_one :
    reachesOneWithin 152 274873188298 = true := by
  decide

theorem collatz_274873188328_reaches_one :
    reachesOneWithin 245 274873188328 = true := by
  decide

theorem collatz_549746376596_reaches_one :
    reachesOneWithin 153 549746376596 = true := by
  decide

theorem collatz_549746376656_reaches_one :
    reachesOneWithin 246 549746376656 = true := by
  decide

/-! ### Goldbach

Each theorem states that the recorded prime pair sums to the
candidate, with both summands verified prime against the bound
carried in the certificate. -/

theorem goldbach_4_has_pair :
    goldbachPair 4 2 2 2 2 = true := by
  decide

theorem goldbach_8_has_pair :
    goldbachPair 8 3 5 2 3 = true := by
  decide

theorem goldbach_16_has_pair :
    goldbachPair 16 3 13 2 4 = true := by
  decide

theorem goldbach_32_has_pair :
    goldbachPair 32 3 29 2 6 = true := by
  decide

theorem goldbach_64_has_pair :
    goldbachPair 64 3 61 2 8 = true := by
  decide

theorem goldbach_128_has_pair :
    goldbachPair 128 19 109 5 11 = true := by
  decide

theorem goldbach_256_has_pair :
    goldbachPair 256 5 251 3 16 = true := by
  decide

theorem goldbach_452_has_pair :
    goldbachPair 452 3 449 2 22 = true := by
  decide

theorem goldbach_512_has_pair :
    goldbachPair 512 3 509 2 23 = true := by
  decide

theorem goldbach_662_has_pair :
    goldbachPair 662 3 659 2 26 = true := by
  decide

theorem goldbach_692_has_pair :
    goldbachPair 692 19 673 5 26 = true := by
  decide

theorem goldbach_1024_has_pair :
    goldbachPair 1024 3 1021 2 32 = true := by
  decide

theorem goldbach_2012_has_pair :
    goldbachPair 2012 13 1999 4 45 = true := by
  decide

theorem goldbach_2048_has_pair :
    goldbachPair 2048 19 2029 5 46 = true := by
  decide

theorem goldbach_2072_has_pair :
    goldbachPair 2072 3 2069 2 46 = true := by
  decide

theorem goldbach_2282_has_pair :
    goldbachPair 2282 13 2269 4 48 = true := by
  decide

theorem goldbach_2552_has_pair :
    goldbachPair 2552 3 2549 2 51 = true := by
  decide

theorem goldbach_2822_has_pair :
    goldbachPair 2822 3 2819 2 54 = true := by
  decide

theorem goldbach_3482_has_pair :
    goldbachPair 3482 13 3469 4 59 = true := by
  decide

theorem goldbach_3572_has_pair :
    goldbachPair 3572 13 3559 4 60 = true := by
  decide

theorem goldbach_3722_has_pair :
    goldbachPair 3722 3 3719 2 61 = true := by
  decide

theorem goldbach_3752_has_pair :
    goldbachPair 3752 13 3739 4 62 = true := by
  decide

theorem goldbach_4096_has_pair :
    goldbachPair 4096 3 4093 2 64 = true := by
  decide

theorem goldbach_4382_has_pair :
    goldbachPair 4382 19 4363 5 67 = true := by
  decide

theorem goldbach_5462_has_pair :
    goldbachPair 5462 13 5449 4 74 = true := by
  decide

theorem goldbach_5852_has_pair :
    goldbachPair 5852 3 5849 2 77 = true := by
  decide

theorem goldbach_6062_has_pair :
    goldbachPair 6062 19 6043 5 78 = true := by
  decide

theorem goldbach_6662_has_pair :
    goldbachPair 6662 3 6659 2 82 = true := by
  decide

theorem goldbach_7622_has_pair :
    goldbachPair 7622 19 7603 5 88 = true := by
  decide

theorem goldbach_7682_has_pair :
    goldbachPair 7682 13 7669 4 88 = true := by
  decide

theorem goldbach_7742_has_pair :
    goldbachPair 7742 19 7723 5 88 = true := by
  decide

theorem goldbach_7892_has_pair :
    goldbachPair 7892 13 7879 4 89 = true := by
  decide

theorem goldbach_8192_has_pair :
    goldbachPair 8192 13 8179 4 91 = true := by
  decide

theorem goldbach_8642_has_pair :
    goldbachPair 8642 13 8629 4 93 = true := by
  decide

theorem goldbach_9332_has_pair :
    goldbachPair 9332 13 9319 4 97 = true := by
  decide

theorem goldbach_9992_has_pair :
    goldbachPair 9992 19 9973 5 100 = true := by
  decide

theorem goldbach_10172_has_pair :
    goldbachPair 10172 3 10169 2 101 = true := by
  decide

theorem goldbach_10442_has_pair :
    goldbachPair 10442 13 10429 4 103 = true := by
  decide

theorem goldbach_11252_has_pair :
    goldbachPair 11252 13 11239 4 107 = true := by
  decide

theorem goldbach_11312_has_pair :
    goldbachPair 11312 13 11299 4 107 = true := by
  decide

theorem goldbach_11672_has_pair :
    goldbachPair 11672 79 11593 9 108 = true := by
  decide

theorem goldbach_12332_has_pair :
    goldbachPair 12332 3 12329 2 112 = true := by
  decide

theorem goldbach_12572_has_pair :
    goldbachPair 12572 3 12569 2 113 = true := by
  decide

theorem goldbach_12842_has_pair :
    goldbachPair 12842 13 12829 4 114 = true := by
  decide

theorem goldbach_13502_has_pair :
    goldbachPair 13502 3 13499 2 117 = true := by
  decide

theorem goldbach_13862_has_pair :
    goldbachPair 13862 3 13859 2 118 = true := by
  decide

theorem goldbach_14942_has_pair :
    goldbachPair 14942 3 14939 2 123 = true := by
  decide

theorem goldbach_15992_has_pair :
    goldbachPair 15992 19 15973 5 127 = true := by
  decide

theorem goldbach_16384_has_pair :
    goldbachPair 16384 3 16381 2 128 = true := by
  decide

theorem goldbach_16862_has_pair :
    goldbachPair 16862 19 16843 5 130 = true := by
  decide

theorem goldbach_17732_has_pair :
    goldbachPair 17732 3 17729 2 134 = true := by
  decide

theorem goldbach_19712_has_pair :
    goldbachPair 19712 3 19709 2 141 = true := by
  decide

theorem goldbach_20132_has_pair :
    goldbachPair 20132 3 20129 2 142 = true := by
  decide

theorem goldbach_20282_has_pair :
    goldbachPair 20282 13 20269 4 143 = true := by
  decide

theorem goldbach_20432_has_pair :
    goldbachPair 20432 43 20389 7 143 = true := by
  decide

theorem goldbach_20582_has_pair :
    goldbachPair 20582 19 20563 5 144 = true := by
  decide

theorem goldbach_20642_has_pair :
    goldbachPair 20642 3 20639 2 144 = true := by
  decide

theorem goldbach_21062_has_pair :
    goldbachPair 21062 3 21059 2 146 = true := by
  decide

theorem goldbach_21092_has_pair :
    goldbachPair 21092 3 21089 2 146 = true := by
  decide

theorem goldbach_22382_has_pair :
    goldbachPair 22382 13 22369 4 150 = true := by
  decide

theorem goldbach_23162_has_pair :
    goldbachPair 23162 3 23159 2 153 = true := by
  decide

theorem goldbach_23252_has_pair :
    goldbachPair 23252 43 23209 7 153 = true := by
  decide

theorem goldbach_23312_has_pair :
    goldbachPair 23312 19 23293 5 153 = true := by
  decide

theorem goldbach_23432_has_pair :
    goldbachPair 23432 61 23371 8 153 = true := by
  decide

theorem goldbach_24212_has_pair :
    goldbachPair 24212 31 24181 6 156 = true := by
  decide

theorem goldbach_24272_has_pair :
    goldbachPair 24272 43 24229 7 156 = true := by
  decide

theorem goldbach_24782_has_pair :
    goldbachPair 24782 19 24763 5 158 = true := by
  decide

theorem goldbach_25352_has_pair :
    goldbachPair 25352 3 25349 2 160 = true := by
  decide

theorem goldbach_25412_has_pair :
    goldbachPair 25412 3 25409 2 160 = true := by
  decide

theorem goldbach_25832_has_pair :
    goldbachPair 25832 13 25819 4 161 = true := by
  decide

theorem goldbach_26582_has_pair :
    goldbachPair 26582 43 26539 7 163 = true := by
  decide

theorem goldbach_27752_has_pair :
    goldbachPair 27752 3 27749 2 167 = true := by
  decide

theorem goldbach_27902_has_pair :
    goldbachPair 27902 19 27883 5 167 = true := by
  decide

theorem goldbach_29192_has_pair :
    goldbachPair 29192 13 29179 4 171 = true := by
  decide

theorem goldbach_29342_has_pair :
    goldbachPair 29342 3 29339 2 172 = true := by
  decide

theorem goldbach_29792_has_pair :
    goldbachPair 29792 3 29789 2 173 = true := by
  decide

theorem goldbach_29942_has_pair :
    goldbachPair 29942 61 29881 8 173 = true := by
  decide

theorem goldbach_30092_has_pair :
    goldbachPair 30092 3 30089 2 174 = true := by
  decide

theorem goldbach_30212_has_pair :
    goldbachPair 30212 31 30181 6 174 = true := by
  decide

theorem goldbach_30872_has_pair :
    goldbachPair 30872 3 30869 2 176 = true := by
  decide

theorem goldbach_31052_has_pair :
    goldbachPair 31052 13 31039 4 177 = true := by
  decide

theorem goldbach_31382_has_pair :
    goldbachPair 31382 3 31379 2 178 = true := by
  decide

theorem goldbach_31442_has_pair :
    goldbachPair 31442 109 31333 11 178 = true := by
  decide

theorem goldbach_31712_has_pair :
    goldbachPair 31712 13 31699 4 179 = true := by
  decide

theorem goldbach_32252_has_pair :
    goldbachPair 32252 19 32233 5 180 = true := by
  decide

theorem goldbach_32768_has_pair :
    goldbachPair 32768 19 32749 5 181 = true := by
  decide

theorem goldbach_33422_has_pair :
    goldbachPair 33422 13 33409 4 183 = true := by
  decide

theorem goldbach_34592_has_pair :
    goldbachPair 34592 3 34589 2 186 = true := by
  decide

theorem goldbach_35162_has_pair :
    goldbachPair 35162 3 35159 2 188 = true := by
  decide

theorem goldbach_35222_has_pair :
    goldbachPair 35222 73 35149 9 188 = true := by
  decide

theorem goldbach_35912_has_pair :
    goldbachPair 35912 13 35899 4 190 = true := by
  decide

theorem goldbach_36152_has_pair :
    goldbachPair 36152 43 36109 7 191 = true := by
  decide

theorem goldbach_36272_has_pair :
    goldbachPair 36272 3 36269 2 191 = true := by
  decide

theorem goldbach_36422_has_pair :
    goldbachPair 36422 79 36343 9 191 = true := by
  decide

theorem goldbach_36662_has_pair :
    goldbachPair 36662 19 36643 5 192 = true := by
  decide

theorem goldbach_37082_has_pair :
    goldbachPair 37082 43 37039 7 193 = true := by
  decide

theorem goldbach_37292_has_pair :
    goldbachPair 37292 19 37273 5 194 = true := by
  decide

theorem goldbach_37712_has_pair :
    goldbachPair 37712 13 37699 4 195 = true := by
  decide

theorem goldbach_38312_has_pair :
    goldbachPair 38312 13 38299 4 196 = true := by
  decide

theorem goldbach_39812_has_pair :
    goldbachPair 39812 13 39799 4 200 = true := by
  decide

theorem goldbach_39842_has_pair :
    goldbachPair 39842 3 39839 2 200 = true := by
  decide

theorem goldbach_40082_has_pair :
    goldbachPair 40082 19 40063 5 201 = true := by
  decide

theorem goldbach_40322_has_pair :
    goldbachPair 40322 109 40213 11 201 = true := by
  decide

theorem goldbach_40382_has_pair :
    goldbachPair 40382 31 40351 6 201 = true := by
  decide

theorem goldbach_40622_has_pair :
    goldbachPair 40622 13 40609 4 202 = true := by
  decide

theorem goldbach_41702_has_pair :
    goldbachPair 41702 43 41659 7 205 = true := by
  decide

theorem goldbach_41732_has_pair :
    goldbachPair 41732 3 41729 2 205 = true := by
  decide

theorem goldbach_42422_has_pair :
    goldbachPair 42422 13 42409 4 206 = true := by
  decide

theorem goldbach_42572_has_pair :
    goldbachPair 42572 3 42569 2 207 = true := by
  decide

theorem goldbach_44132_has_pair :
    goldbachPair 44132 3 44129 2 211 = true := by
  decide

theorem goldbach_44672_has_pair :
    goldbachPair 44672 31 44641 6 212 = true := by
  decide

theorem goldbach_45332_has_pair :
    goldbachPair 45332 3 45329 2 213 = true := by
  decide

theorem goldbach_47042_has_pair :
    goldbachPair 47042 109 46933 11 217 = true := by
  decide

theorem goldbach_47912_has_pair :
    goldbachPair 47912 31 47881 6 219 = true := by
  decide

theorem goldbach_48032_has_pair :
    goldbachPair 48032 3 48029 2 220 = true := by
  decide

theorem goldbach_48302_has_pair :
    goldbachPair 48302 3 48299 2 220 = true := by
  decide

theorem goldbach_48422_has_pair :
    goldbachPair 48422 13 48409 4 221 = true := by
  decide

theorem goldbach_48872_has_pair :
    goldbachPair 48872 3 48869 2 222 = true := by
  decide

theorem goldbach_48932_has_pair :
    goldbachPair 48932 43 48889 7 222 = true := by
  decide

theorem goldbach_49022_has_pair :
    goldbachPair 49022 3 49019 2 222 = true := by
  decide

theorem goldbach_50222_has_pair :
    goldbachPair 50222 103 50119 11 224 = true := by
  decide

theorem goldbach_50252_has_pair :
    goldbachPair 50252 31 50221 6 225 = true := by
  decide

theorem goldbach_50492_has_pair :
    goldbachPair 50492 31 50461 6 225 = true := by
  decide

theorem goldbach_51332_has_pair :
    goldbachPair 51332 3 51329 2 227 = true := by
  decide

theorem goldbach_51752_has_pair :
    goldbachPair 51752 3 51749 2 228 = true := by
  decide

theorem goldbach_52292_has_pair :
    goldbachPair 52292 3 52289 2 229 = true := by
  decide

theorem goldbach_53072_has_pair :
    goldbachPair 53072 3 53069 2 231 = true := by
  decide

theorem goldbach_53192_has_pair :
    goldbachPair 53192 3 53189 2 231 = true := by
  decide

theorem goldbach_53282_has_pair :
    goldbachPair 53282 3 53279 2 231 = true := by
  decide

theorem goldbach_53432_has_pair :
    goldbachPair 53432 13 53419 4 232 = true := by
  decide

theorem goldbach_53612_has_pair :
    goldbachPair 53612 3 53609 2 232 = true := by
  decide

theorem goldbach_53702_has_pair :
    goldbachPair 53702 3 53699 2 232 = true := by
  decide

theorem goldbach_53732_has_pair :
    goldbachPair 53732 13 53719 4 232 = true := by
  decide

theorem goldbach_54062_has_pair :
    goldbachPair 54062 3 54059 2 233 = true := by
  decide

theorem goldbach_54092_has_pair :
    goldbachPair 54092 43 54049 7 233 = true := by
  decide

theorem goldbach_54302_has_pair :
    goldbachPair 54302 109 54193 11 233 = true := by
  decide

theorem goldbach_54332_has_pair :
    goldbachPair 54332 13 54319 4 234 = true := by
  decide

theorem goldbach_55172_has_pair :
    goldbachPair 55172 151 55021 13 235 = true := by
  decide

theorem goldbach_55352_has_pair :
    goldbachPair 55352 13 55339 4 236 = true := by
  decide

theorem goldbach_55532_has_pair :
    goldbachPair 55532 3 55529 2 236 = true := by
  decide

theorem goldbach_55592_has_pair :
    goldbachPair 55592 3 55589 2 236 = true := by
  decide

theorem goldbach_55712_has_pair :
    goldbachPair 55712 31 55681 6 236 = true := by
  decide

theorem goldbach_56462_has_pair :
    goldbachPair 56462 19 56443 5 238 = true := by
  decide

theorem goldbach_56732_has_pair :
    goldbachPair 56732 19 56713 5 239 = true := by
  decide

theorem goldbach_56792_has_pair :
    goldbachPair 56792 13 56779 4 239 = true := by
  decide

theorem goldbach_56972_has_pair :
    goldbachPair 56972 31 56941 6 239 = true := by
  decide

theorem goldbach_57092_has_pair :
    goldbachPair 57092 3 57089 2 239 = true := by
  decide

theorem goldbach_58472_has_pair :
    goldbachPair 58472 19 58453 5 242 = true := by
  decide

theorem goldbach_58532_has_pair :
    goldbachPair 58532 79 58453 9 242 = true := by
  decide

theorem goldbach_59552_has_pair :
    goldbachPair 59552 13 59539 4 245 = true := by
  decide

theorem goldbach_60422_has_pair :
    goldbachPair 60422 79 60343 9 246 = true := by
  decide

theorem goldbach_60512_has_pair :
    goldbachPair 60512 3 60509 2 246 = true := by
  decide

theorem goldbach_60902_has_pair :
    goldbachPair 60902 3 60899 2 247 = true := by
  decide

theorem goldbach_61352_has_pair :
    goldbachPair 61352 13 61339 4 248 = true := by
  decide

theorem goldbach_61922_has_pair :
    goldbachPair 61922 13 61909 4 249 = true := by
  decide

theorem goldbach_62132_has_pair :
    goldbachPair 62132 3 62129 2 250 = true := by
  decide

theorem goldbach_62282_has_pair :
    goldbachPair 62282 139 62143 12 250 = true := by
  decide

theorem goldbach_62312_has_pair :
    goldbachPair 62312 13 62299 4 250 = true := by
  decide

theorem goldbach_62342_has_pair :
    goldbachPair 62342 19 62323 5 250 = true := by
  decide

theorem goldbach_62672_has_pair :
    goldbachPair 62672 13 62659 4 251 = true := by
  decide

theorem goldbach_63602_has_pair :
    goldbachPair 63602 3 63599 2 253 = true := by
  decide

theorem goldbach_64022_has_pair :
    goldbachPair 64022 3 64019 2 254 = true := by
  decide

theorem goldbach_64262_has_pair :
    goldbachPair 64262 31 64231 6 254 = true := by
  decide

theorem goldbach_64442_has_pair :
    goldbachPair 64442 3 64439 2 254 = true := by
  decide

theorem goldbach_64922_has_pair :
    goldbachPair 64922 3 64919 2 255 = true := by
  decide

theorem goldbach_65012_has_pair :
    goldbachPair 65012 43 64969 7 255 = true := by
  decide

theorem goldbach_65252_has_pair :
    goldbachPair 65252 13 65239 4 256 = true := by
  decide

theorem goldbach_65536_has_pair :
    goldbachPair 65536 17 65519 5 256 = true := by
  decide

theorem goldbach_65552_has_pair :
    goldbachPair 65552 13 65539 4 257 = true := by
  decide

theorem goldbach_65792_has_pair :
    goldbachPair 65792 3 65789 2 257 = true := by
  decide

theorem goldbach_66902_has_pair :
    goldbachPair 66902 13 66889 4 259 = true := by
  decide

theorem goldbach_66932_has_pair :
    goldbachPair 66932 13 66919 4 259 = true := by
  decide

theorem goldbach_67352_has_pair :
    goldbachPair 67352 3 67349 2 260 = true := by
  decide

theorem goldbach_67682_has_pair :
    goldbachPair 67682 3 67679 2 261 = true := by
  decide

theorem goldbach_67772_has_pair :
    goldbachPair 67772 13 67759 4 261 = true := by
  decide

theorem goldbach_67802_has_pair :
    goldbachPair 67802 13 67789 4 261 = true := by
  decide

theorem goldbach_68492_has_pair :
    goldbachPair 68492 3 68489 2 262 = true := by
  decide

theorem goldbach_68582_has_pair :
    goldbachPair 68582 43 68539 7 262 = true := by
  decide

theorem goldbach_70292_has_pair :
    goldbachPair 70292 3 70289 2 266 = true := by
  decide

theorem goldbach_70502_has_pair :
    goldbachPair 70502 13 70489 4 266 = true := by
  decide

theorem goldbach_70892_has_pair :
    goldbachPair 70892 13 70879 4 267 = true := by
  decide

theorem goldbach_71372_has_pair :
    goldbachPair 71372 13 71359 4 268 = true := by
  decide

theorem goldbach_71762_has_pair :
    goldbachPair 71762 43 71719 7 268 = true := by
  decide

theorem goldbach_71822_has_pair :
    goldbachPair 71822 13 71809 4 268 = true := by
  decide

theorem goldbach_72452_has_pair :
    goldbachPair 72452 31 72421 6 270 = true := by
  decide

theorem goldbach_73172_has_pair :
    goldbachPair 73172 31 73141 6 271 = true := by
  decide

theorem goldbach_74402_has_pair :
    goldbachPair 74402 19 74383 5 273 = true := by
  decide

theorem goldbach_74702_has_pair :
    goldbachPair 74702 3 74699 2 274 = true := by
  decide

theorem goldbach_75722_has_pair :
    goldbachPair 75722 13 75709 4 276 = true := by
  decide

theorem goldbach_75812_has_pair :
    goldbachPair 75812 19 75793 5 276 = true := by
  decide

theorem goldbach_76892_has_pair :
    goldbachPair 76892 19 76873 5 278 = true := by
  decide

theorem goldbach_76982_has_pair :
    goldbachPair 76982 19 76963 5 278 = true := by
  decide

theorem goldbach_77222_has_pair :
    goldbachPair 77222 31 77191 6 278 = true := by
  decide

theorem goldbach_77882_has_pair :
    goldbachPair 77882 19 77863 5 280 = true := by
  decide

theorem goldbach_78182_has_pair :
    goldbachPair 78182 3 78179 2 280 = true := by
  decide

theorem goldbach_78242_has_pair :
    goldbachPair 78242 13 78229 4 280 = true := by
  decide

theorem goldbach_78422_has_pair :
    goldbachPair 78422 139 78283 12 280 = true := by
  decide

theorem goldbach_78452_has_pair :
    goldbachPair 78452 13 78439 4 281 = true := by
  decide

theorem goldbach_78482_has_pair :
    goldbachPair 78482 3 78479 2 281 = true := by
  decide

theorem goldbach_79322_has_pair :
    goldbachPair 79322 3 79319 2 282 = true := by
  decide

theorem goldbach_79832_has_pair :
    goldbachPair 79832 3 79829 2 283 = true := by
  decide

theorem goldbach_79922_has_pair :
    goldbachPair 79922 19 79903 5 283 = true := by
  decide

theorem goldbach_80222_has_pair :
    goldbachPair 80222 13 80209 4 284 = true := by
  decide

theorem goldbach_80372_has_pair :
    goldbachPair 80372 3 80369 2 284 = true := by
  decide

theorem goldbach_80642_has_pair :
    goldbachPair 80642 13 80629 4 284 = true := by
  decide

theorem goldbach_80672_has_pair :
    goldbachPair 80672 3 80669 2 285 = true := by
  decide

theorem goldbach_81782_has_pair :
    goldbachPair 81782 13 81769 4 286 = true := by
  decide

theorem goldbach_82262_has_pair :
    goldbachPair 82262 31 82231 6 287 = true := by
  decide

theorem goldbach_82322_has_pair :
    goldbachPair 82322 43 82279 7 287 = true := by
  decide

theorem goldbach_82382_has_pair :
    goldbachPair 82382 31 82351 6 287 = true := by
  decide

theorem goldbach_83012_has_pair :
    goldbachPair 83012 3 83009 2 289 = true := by
  decide

theorem goldbach_83192_has_pair :
    goldbachPair 83192 103 83089 11 289 = true := by
  decide

theorem goldbach_83252_has_pair :
    goldbachPair 83252 19 83233 5 289 = true := by
  decide

theorem goldbach_83822_has_pair :
    goldbachPair 83822 31 83791 6 290 = true := by
  decide

theorem goldbach_84122_has_pair :
    goldbachPair 84122 61 84061 8 290 = true := by
  decide

theorem goldbach_84962_has_pair :
    goldbachPair 84962 43 84919 7 292 = true := by
  decide

theorem goldbach_85862_has_pair :
    goldbachPair 85862 19 85843 5 293 = true := by
  decide

theorem goldbach_86462_has_pair :
    goldbachPair 86462 73 86389 9 294 = true := by
  decide

theorem goldbach_86882_has_pair :
    goldbachPair 86882 13 86869 4 295 = true := by
  decide

theorem goldbach_87242_has_pair :
    goldbachPair 87242 19 87223 5 296 = true := by
  decide

theorem goldbach_87362_has_pair :
    goldbachPair 87362 3 87359 2 296 = true := by
  decide

theorem goldbach_87752_has_pair :
    goldbachPair 87752 13 87739 4 297 = true := by
  decide

theorem goldbach_89852_has_pair :
    goldbachPair 89852 3 89849 2 300 = true := by
  decide

theorem goldbach_90602_has_pair :
    goldbachPair 90602 3 90599 2 301 = true := by
  decide

theorem goldbach_90722_has_pair :
    goldbachPair 90722 13 90709 4 302 = true := by
  decide

theorem goldbach_92252_has_pair :
    goldbachPair 92252 19 92233 5 304 = true := by
  decide

theorem goldbach_92342_has_pair :
    goldbachPair 92342 31 92311 6 304 = true := by
  decide

theorem goldbach_92462_has_pair :
    goldbachPair 92462 3 92459 2 305 = true := by
  decide

theorem goldbach_93812_has_pair :
    goldbachPair 93812 3 93809 2 307 = true := by
  decide

theorem goldbach_93932_has_pair :
    goldbachPair 93932 19 93913 5 307 = true := by
  decide

theorem goldbach_94562_has_pair :
    goldbachPair 94562 3 94559 2 308 = true := by
  decide

theorem goldbach_94592_has_pair :
    goldbachPair 94592 19 94573 5 308 = true := by
  decide

theorem goldbach_95012_has_pair :
    goldbachPair 95012 3 95009 2 309 = true := by
  decide

theorem goldbach_95162_has_pair :
    goldbachPair 95162 19 95143 5 309 = true := by
  decide

theorem goldbach_95522_has_pair :
    goldbachPair 95522 43 95479 7 309 = true := by
  decide

theorem goldbach_95552_has_pair :
    goldbachPair 95552 3 95549 2 310 = true := by
  decide

theorem goldbach_95702_has_pair :
    goldbachPair 95702 73 95629 9 310 = true := by
  decide

theorem goldbach_96212_has_pair :
    goldbachPair 96212 13 96199 4 311 = true := by
  decide

theorem goldbach_96542_has_pair :
    goldbachPair 96542 73 96469 9 311 = true := by
  decide

theorem goldbach_96752_has_pair :
    goldbachPair 96752 3 96749 2 312 = true := by
  decide

theorem goldbach_96812_has_pair :
    goldbachPair 96812 13 96799 4 312 = true := by
  decide

theorem goldbach_96992_has_pair :
    goldbachPair 96992 3 96989 2 312 = true := by
  decide

theorem goldbach_97202_has_pair :
    goldbachPair 97202 31 97171 6 312 = true := by
  decide

theorem goldbach_97232_has_pair :
    goldbachPair 97232 19 97213 5 312 = true := by
  decide

theorem goldbach_97352_has_pair :
    goldbachPair 97352 139 97213 12 312 = true := by
  decide

theorem goldbach_98192_has_pair :
    goldbachPair 98192 13 98179 4 314 = true := by
  decide

theorem goldbach_99782_has_pair :
    goldbachPair 99782 61 99721 8 316 = true := by
  decide

theorem goldbach_99902_has_pair :
    goldbachPair 99902 31 99871 6 317 = true := by
  decide

theorem goldbach_99962_has_pair :
    goldbachPair 99962 61 99901 8 317 = true := by
  decide

theorem goldbach_99992_has_pair :
    goldbachPair 99992 3 99989 2 317 = true := by
  decide

end ProofX.Generated
