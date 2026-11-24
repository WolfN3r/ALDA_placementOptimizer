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

---

## Mismatch, gradient and heat source with the diode far away (`mismatch.py`, `plot_mismatch.py`)

Case c1a (gate line only, so there is no ground drop), diode M4 1–100 µm from the mirror row.

**Step 1: mirror alone.** IB → M5 → M7 → M4, then the gate line → M10, M6, M9. The drains are
held at the OTA's operating point. This bench reproduces the full OTA exactly (35.35 / 300.8 µA,
gate line at 652.3 mV).

- **Random**: sky130 mismatch models, tt_mm 27 °C, 200 samples. Each _mm corner also gets
  100 samples.
- **Gradient**: the diode's Vth is shifted by G × d, with G = 0.5 … 5 µV/µm (literature range;
  sky130 gives none).
- **Temperature**: the bias block (M5, M7, M4) sits at T + ΔT and the mirror at T. ngspice ignores
  `dtemp` on the sky130 devices, so the bias block is solved at T + ΔT first and its gate voltage
  then drives the mirror at T. This is exact at DC because the gates draw no current.
- **Heat source**: 20 mW (e.g. a small output buffer or LDO pass device) in a 50 × 50 µm block,
  10 µm from the near element, with ΔT(r) = P/(2πkr). H1: mirror next to the source (diode
  cooler). H2: diode next to the source (diode hotter). At 100 µm the diode–mirror ΔT is 0.46 K.

**Step 2: whole OTA.** The mean ± 3σ mirror currents are referred to gate offsets on
M10/M6/M9 and injected into the full OTA at tt 27 °C and fs −20 °C (the tightest corner). This
is done twice: random only, and random + heat + 5 µV/µm at 100 µm in the same direction.

### Mirror currents (tt_mm 27 °C, 200 samples)

| | expected (ratio × IB) | nominal | MC mean | σ | min / max (vs nominal) |
|---|---|---|---|---|---|
| input I(M7) | 18.51 µA | 18.48 (−0.14 %) | 18.48 | 0.54 % | −1.3 / +1.4 % |
| I(M10) tail | 37.01 µA | 35.35 (−4.5 %) | 35.34 | 1.82 % | −4.3 / +5.4 % |
| I(M6) | 296.1 µA | 300.8 (+1.6 %) | 301.0 | 1.61 % | −3.6 / +4.8 % |
| I(M9) | 296.1 µA | 300.8 (+1.6 %) | 300.8 | 1.62 % | −3.9 / +4.4 % |
| gate line V | – | 652.3 mV | – | 1.68 mV | – |
| I(M6) − I(M9) | 0 | 0 | – | 0.50 % | – |

- The gap between expected and nominal is systematic (Vds: tail 263 mV, sinks 887 mV, diode
  652 mV), not mismatch.
- The outputs are strongly correlated (r = 0.8–0.95) because the small diode M4 (2 units) sets
  most of the random error, and all outputs share it.
- The process corners barely change this: σ is 1.8–2.0 % (tail) and 1.5–1.6 % (sinks) at every
  _mm corner, and the error vs expected stays −4.3 … −5.4 % (tail) and +1.3 … +1.9 % (sinks).

### Effect of distance (systematic, added on top of the random spread)

| at 100 µm | ΔI (all outputs) | gate line |
|---|---|---|
| heat source 20 mW (H1/H2) | ±0.12 % | ±0.12 mV |
| gradient 1 / 5 µV/µm | ±0.09 / ±0.47 % | ±0.10 / ±0.50 mV |
| heat + 5 µV/µm, same direction | ±0.58 % | ±0.62 mV |
| (random 1σ, for scale) | 1.6 % | 1.7 mV |

- At 10 µm everything stays below 0.09 %.
- The diode-vs-mirror temperature sensitivity is −0.25 %/K at tt 27 °C (−0.14 … −0.34 %/K over
  corners). The diode's Vgs drifts only −0.27 mV/K at this bias, close to its zero-TC point.
- A heat source would need to make the diode about 6 K hotter or cooler than the mirror to equal
  1σ of the random mismatch.

### Whole OTA with the worst case injected

| | tt 27 °C nominal | −3σ random | −3σ, 100 µm | fs −20 °C nominal | −3σ random | −3σ, 100 µm |
|---|---|---|---|---|---|---|
| I(M6) µA | 300.8 | 286.1 | 284.4 | 299.9 | 284.0 | 282.1 |
| sat. margin mV (≥ 50) | 88.7 | 85.0 | 84.6 | 50.5 | **47.0** | **46.6** |
| VOCM mV (±30) | −13.2 | −21.4 | −22.2 | −18.5 | −26.9 | −27.8 |
| power mW | 1.348 | 1.295 | 1.288 | 1.345 | 1.287 | 1.280 |
| UGB MHz | 191.1 | 186.5 | 185.9 | 219.4 | 212.9 | 212.1 |
| PM ° | 64.1 | 63.5 | 63.4 | 62.8 | 62.3 | 62.3 |
| gain dB | 68.45 | 68.51 | 68.52 | 69.14 | 69.19 | 69.20 |

- In the +3σ direction everything improves except power (1.41 mW, still under 1.5).
- The M6/M9 split at 3σ (±1.5 %) gives an input offset of only 18 µV and costs 0.6 dB of the
  CMRR proxy.
- Moving the diode 100 µm away adds about 0.4 mV of saturation margin loss, 0.9 mV of VOCM and
  0.6 MHz of UGB on top of the random worst case.
- At fs −20 °C the random −3σ alone already breaks the 50 mV saturation spec (47.0 mV). That is
  a pre-existing margin issue of the design (README 06: 50.5 mV nominal), not a result of the
  separation.

**Verdict:** with the diode 1–100 µm away and only the gate line between, random mismatch
dominates by a wide margin. The distance adds at most 0.6 % (≈ 0.35σ) with a 20 mW heat source
and a 5 µV/µm gradient together. Separating the diode costs nothing measurable at the OTA
level, provided the ground is not shared (case c1b).

![currents](plots/mm_currents.png)
![distance](plots/mm_distance.png)
![corners](plots/mm_corners.png)
![ota](plots/mm_ota.png)

Limits: the gradient value and the heat-spreading formula are assumptions (no thermal simulation,
no package); only the bias block is heated, not a temperature gradient across the mirror row
itself; the worst cases are injected as gate offsets (DC-equivalent), not as full Monte Carlo of
the whole OTA.
