# Separating the NMOS current mirror of OTA1 (sky01) from the OTA core

Question: can the NMOS mirror of sky01 (`06_ota1_magical`, final design `ota1_sized.spice`) be
placed away from the rest of the OTA, and what do the extra wires do to the mirror currents
and the OTA?

Mirror: diode M4 (`vbias_n`) → M10 (tail, together with M11 from the CMFB) and M6/M9
(2nd-stage sinks on OUTP/OUTM, 301 µA each). Wires are lumped π models at minimum width:

| Layer | R | C (area + both sidewalls) |
|---|---|---|
| met1 (0.125 Ω/sq, 0.14 µm) | 0.89 Ω/µm | 92 aF/µm |
| li1 (12.8 Ω/sq, 0.17 µm) | 75 Ω/µm | 57 aF/µm |

Cases, lengths 1–100 µm, tt 27 °C (`sweep.py`, results in `results/*.json`):

- **c1a**: diode M4 away from the mirror, R/C on the gate line `vbias_n` → M10/M6/M9.
- **c1b**: c1a plus the VSS line between the diode's ground and the mirror row's sources. The
  ground pin is at the diode, so the whole mirror-row current (~675 µA) returns through the line
  (worst case).
- **c2**: whole mirror row away from the core. Tail line (M10+M11 → pair sources) and output lines
  (M6 → OUTP, M9 → OUTM) have the same length.
- **c3**: as c2, but the tail and output lines have different lengths (5 × 5 grid).
- **corners**: baseline, c1a/c1b/c2 at 100 µm met1, and c3 with a 1 µm tail and 100 µm outputs,
  over 15 corners.

### Schematics

`make_sch.py` derives one xschem schematic per case from `06_ota1_magical/ota1.sch`, and
`export.sh` netlists and draws them. The netlists have the same connectivity as `sweep.py`,
except for the current-sense sources, which are not drawn.

| Case | Schematic |
|---|---|
| c1 (c1a, c1b) | ![c1](ota1_c1.png) |
| c2 | ![c2](ota1_c2.png) |
| c3 | ![c3](ota1_c3.png) |

### Plots (`plot.py` → `plots/`)

![mirror](plots/mirror_vs_length.png)
![ota](plots/ota_vs_length.png)
![c3](plots/c3_grid.png)
![corners](plots/corners.png)

Baseline (no wires, tt 27 °C) reproduces the 06 README: gain 68.45 dB, UGB 191 MHz, PM 64.05°,
CMFB PM 80.2°, 1.348 mW, 11.4 nV/√Hz at 1 MHz, 9.85 ns settling. The tightest device is the tail:
M11 has 89 mV (M10 95 mV) above saturation. At fs −20 °C the margin is only 50.5 mV, against a
50 mV spec.

## Results (tt 27 °C)

| Case, wire | I(M10) / I(M6) µA | Vds M10 / M6 mV | worst sat. mV | VOCM mV | gain dB | UGB MHz | PM ° | settling ns |
|---|---|---|---|---|---|---|---|---|
| baseline | 35.35 / 300.8 | 263 / 887 | 88.7 | −13.2 | 68.45 | 191.1 | 64.05 | 9.85 |
| c1a met1 100 µm | unchanged | unchanged | 88.7 | −13.2 | 68.45 | 191.1 | 64.05 | 9.85 |
| c1a li1 100 µm (7.5 kΩ) | unchanged | unchanged | 88.7 | −13.2 | 68.45 | 191.1 | 64.05 | 9.85 |
| c1b met1 10 µm | 33.3 / 283.9 | 257 / 872 | 78.7 | −21.9 | 68.52 | 185.8 | 63.36 | 9.55 |
| c1b met1 20 µm | 31.6 / 268.9 | 252 / 859 | 69.7 | **−29.9** | 68.57 | 181.0 | 62.68 | 9.25 |
| c1b met1 50 µm | 27.3 / 232.6 | 238 / 824 | **47.2** | **−50.6** | 68.71 | 169.7 | 60.49 | 8.65 |
| c1b met1 100 µm | 22.2 / 190.3 | 220 / 777 | **19.1** | **−79.7** | 68.87 | 155.7 | **56.95** | **194** |
| c1b li1 ≥ 1 µm | −33 % … −100 % | – | fails | fails | fails | | | |
| c2 met1 100 µm | 35.28 / 300.2 | 257 / 859 | 81.9 | −13.8 | 68.44 | 190.0 | 63.93 | 9.85 |
| c2 li1 5 µm | 35.03 / 298.3 | 236 / 772 | 59.6 | −16.2 | 68.41 | 189.9 | 64.07 | 9.85 |
| c2 li1 10 µm | 34.53 / 295.8 | 208 / 656 | **29.6** | −21.1 | 68.35 | 188.6 | 64.10 | 9.75 |
| c2 li1 ≥ 20 µm | | | tail in triode | fails | | | | |

Case c3 (worst saturation margin in mV; tail length down, output length across):

| met1 | out 1 | 20 | 100 | | li1 | out 1 | 20 | 50 | 100 |
|---|---|---|---|---|---|---|---|---|---|
| tail 1 | 88.7 | 88.7 | 88.7 | | tail 1 | 83.0 | 83.0 (gain 67.9) | sink triode, gain 57 | fails |
| tail 20 | 87.4 | 87.4 | 87.4 | | tail 5 | 59.6 | 59.7 | fails | fails |
| tail 100 | 81.9 | 81.9 | 81.9 | | tail 20 | −38.6 | fails | fails | fails |

Over 15 corners, worst case (spec: gain ≥ 66 dB, UGB ≥ 120 MHz, PM 60–80°, |VOCM| ≤ 30 mV,
sat. ≥ 50 mV):

| Config (met1) | worst sat. mV | PM ° | gain min dB | VOCM mV | passes all specs |
|---|---|---|---|---|---|
| baseline | 50.5 | 61.2–65.1 | 67.04 | −18.5 … −7.2 | yes |
| c1a 100 µm | 50.5 | 61.2–65.1 | 67.04 | −18.5 … −7.2 | yes |
| c1b 100 µm | −18.9 | 52.9–59.1 | 65.49 | −100 … −70 | no: PM, VOCM and sat. in all corners |
| c2 100 µm | 43.5 | 61.3–64.9 | 67.02 | −19.6 … −7.6 | no: sat. at fs −20/27 °C |
| c3 tail 1 µm, outputs 100 µm | 50.5 | 61.3–64.9 | 67.02 | −18.5 … −7.2 | yes |

## What each line does

- **Gate line (c1a)**: no DC current, so the currents and voltages do not change at all, even with
  7.5 kΩ. Its RC (≤ 7.5 kΩ, ~10 fF + mirror gate cap) sits on a CM-only bias node, far above the
  UGB. The only visible change is CMFB PM +0.3° (li1 100 µm).
- **VSS line (c1b)**: this is what separating the diode really costs. The IR drop raises the
  mirror sources (44 mV at met1 100 µm). The mirror then runs at a smaller Vgs than the diode, so
  the currents drop exponentially: −37 % in the sinks, −18 % in the tail. The CMFB has to raise
  M11 to compensate (38 → 51 µA), M11 loses its headroom, VOCM drifts and PM falls because
  gm of the 2nd stage drops. 10 µm of min-width met1 already costs 7 % of the sink current.
- **Tail line (c2/c3)**: 74 µA through R comes straight out of the tail's 89 mV margin (50.5 mV
  at fs −20 °C). It is the limiting line: about 7 µm of min-width met1 already breaks the
  fs −20 °C spec, and li1 is only usable up to about 3 µm.
- **Output lines (c2/c3)**: 301 µA, but the sinks have ~720 mV of margin. Met1 at 100 µm is
  invisible (−0.01 dB, −0.1° PM). li1 is acceptable up to about 20 µm.

## Verdict

Best for performance is **c3 with the tail line short and the output lines long**: keep the
mirror row next to the input pair's tail node and route the long lines to the 2nd-stage sinks
(M6/M9). With met1, 100 µm output lines change nothing measurable and every corner still passes
(the worst saturation margin stays 50.5 mV).

- Separating the diode (c1) is harmless only for the gate line. The ground between diode and
  mirror must not carry mirror current. Keep M4 in the mirror row (it is 2 units), or route
  its source directly to the mirror row's local VSS (Kelvin-style). A shared VSS line costs
  current and fails the specs from ~20 µm of min-width met1.
- c2 (all lines equally long) is fine at tt, but the tail line costs ~7 mV of headroom per
  100 µm met1. That fails fs −20 °C, because this design has no headroom reserve there.
- Never route the tail or the VSS of the mirror in li1.

Limits: lumped π wires to an ideal VSS, min width (a wider wire scales R by 1/W), no coupling to
other nets, no mismatch (Monte Carlo) or gradient effects of the distance, no extracted layout.
