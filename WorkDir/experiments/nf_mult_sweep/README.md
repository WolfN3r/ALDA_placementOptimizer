# nf / M sweep of sky01 (OTA1, sky130) at constant total width

Circuit: `06_ota1_magical/ota1_sized.spice` (= `#Netlists/sky01_ota1.sp`), testbench as
`06_ota1_magical/tb.inc` (Xd differential, Xl CMFB loop), tt, 27 °C, ngspice-47 in
`iic-osic-tools_xvnc_uid_501`. Swept, both halves alike, W_tot = W_copy·M fixed:

| Target | Devices | W_tot per half | Sized split (nf × M) | Finger W |
|---|---|---|---|---|
| pair | M0/M2 nfet_01v8, L 0.6 | 131.28 µm | 4 × 4 | 8.21 µm |
| load mirror | MP1a/b pfet_01v8, L 4.535 (ref. M5: 2 × 2, 6.7 µm) | 53.6 µm | 2 × 4 | 6.70 µm |
| sink mirror | M6/M9 nfet_01v8_lvt, L 1.93 (ref. M4: 1 × 2, 3.48 µm) | 111.36 µm | 1 × 32 | 3.48 µm |

Run (in the container, from `/foss/designs/10_nf_mult_sweep`):
`python3 sweep.py results` (83 runs + 3 × 120 MC, ~1 min) then `python3 plot.py results`.
Results: `results/sweep.csv`, `results/mc.csv`, `results/fig_device.png`, `results/fig_circuit.png`.

## How nf and M enter the sky130 schematic model

- ngspice selects the BSIM4 bin and computes the intrinsic device from the **finger width
  W/nf**; `m` scales the copy. So every (nf, M) with the same finger width W_tot/(nf·M) gives
  identical Id, gm, gds, Vth, Cgg (rows of `sweep.csv` coincide to all printed digits).
- **nf alone** changes only the drain/source junctions (ad/as/pd/ps, shared diffusions):
  nf = 1 → nf ≥ 2 halves Cdb (pair 56 → 34 fF), Csb drops with nf (75 → 50 fF).
- Mismatch: σVth = slope/√(L·W·mult) is split-invariant. MC (120 samples, tt_mm) of the total
  input offset: σ = 1.056 mV for 32 × 1 and 1 × 32 (identical samples), 1.115 mV for 4 × 4.
- Not modelled here: LOD/STI stress (sa = sb = sd = 0), WPE, gate resistance, layout
  parasitics and gradients — the effects that make nf vs M matter in silicon.

## Results (baseline: gain 68.45 dB, UGBW 190.8 MHz, PM 64.1°, 1.348 mW, VOCM −13.2 mV)

| Target | Lever | Device effect | Circuit effect |
|---|---|---|---|
| pair | finger W 65.6 → 0.5 µm (bins 5 → 23 → 32 → 59 → 158) | Vth 640 → 688 mV, gm/Id 23.2 → 21.1, gm/gds 134–179 (non-monotonic, jumps at bin edges) | gain 67.9–70.2 dB, UGBW 179–199 MHz, noise@1k 137 → 152 nV/√Hz; power, VOCM unchanged |
| pair | nf = 1 vs ≥ 2 at same finger W | Cdb on intp +22 fF | PM ≈ −1.4°, UGBW −2.4…−2.8 MHz |
| load | finger W ≠ reference M5 (6.7 µm) | mirror ratio off: Id 35.0 µA (53.6 µm) … 45.2 µA (1.68 µm) vs 36.8 | VOCM +1.6 … −93 mV (spec ±30), PM 65 → 58°, UGBW 181 → 233 MHz; at 0.84 µm the OTA loses its operating point (gain −19 dB) |
| sink | finger W ≠ reference M4 (3.48 µm) | Id 330 µA (≥ 6.96 µm) … 265 µA (0.87 µm) vs 301 | power 1.45 … 1.22 mW, UGBW 180–201 MHz, PM 63.0–65.4° |
| sink | nf = 1 vs ≥ 2 | Cdb on OUT +18 fF | PM −0.25°, UGBW −1.6 MHz |

Take-aways: (1) a current mirror keeps its ratio only if all devices use the same finger
width (unit-cell design); changing M of one side at constant W_tot changes the finger width
and therefore the ratio. (2) For the pair, the finger width moves gain and noise by up to
~2 dB / ~10 % through the model's narrow-width behaviour and bin edges. (3) nf ≥ 2 (shared
drain) is the only split choice the schematic model rewards (≈ 1.5° PM on the pair).
