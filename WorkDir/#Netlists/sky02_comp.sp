* ============================================================
* Circuit : comp
* Source  : sky130 port of MAGICAL comp (StrongARM latch, IIC-OSIC-TOOLS container)
* File    : /foss/designs/07_comp_magical/comp.spice
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 17
*   Device types : sky130_fd_pr__nfet_01v8 sky130_fd_pr__pfet_01v8
*   Passives     : 0 resistors, 0 capacitors
* Note: PDK sky130 (prefix 'sky' -> 012 generator, --pdk sky130). Sizes copied from
*       07_comp_magical/comp_sized.spice (2026-11-06, rounded to 0.01 um, MC yield
*       >= 97.5 % in 15 corners): W is per copy (all its fingers), nf fingers per copy,
*       M copies. Regular-Vt devices replace the original lvt ones. M0/M22 are MOS caps
*       (gate on INTERN/INTERP, D/S/B on VSS). No schematic dummies yet.
* Split for common centroid (2026-11-07): M5/M6 2x4 -> 4x2 (2D ABBA/BAAB), M3/M4, M13/M14
*       and M7 1x2 -> 2x1 (ABBA, tail halves either side). Finger width and fingers per
*       device unchanged (same model bin and Pelgrom sigma); simulated in 15 corners:
*       delay +2.5 % (588 ps), power +2.1 % (43.2 uW), all specs met (dbg/eval_split.py).
* ============================================================

* --- DEVICE PARAMETERS ---
.param M14_L=0.31 M14_W=1.3 M14_Nf=1 M14_M=2
.param M4_L=0.15 M4_W=0.98 M4_Nf=1 M4_M=2
.param M5_L=0.53 M5_W=5.74 M5_Nf=2 M5_M=4
.param M10_L=0.15 M10_W=0.58 M10_Nf=1 M10_M=1
.param M18_L=0.15 M18_W=0.58 M18_Nf=1 M18_M=1
.param M0_L=0.85 M0_W=0.78 M0_Nf=1 M0_M=1
.param M15_L=0.15 M15_W=1.94 M15_Nf=2 M15_M=1
.param M17_L=0.15 M17_W=0.59 M17_Nf=1 M17_M=1
.param M13_L=0.31 M13_W=1.3 M13_Nf=1 M13_M=2
.param M3_L=0.15 M3_W=0.98 M3_Nf=1 M3_M=2
.param M6_L=0.53 M6_W=5.74 M6_Nf=2 M6_M=4
.param M12_L=0.15 M12_W=0.58 M12_Nf=1 M12_M=1
.param M19_L=0.15 M19_W=0.58 M19_Nf=1 M19_M=1
.param M22_L=0.85 M22_W=0.78 M22_Nf=1 M22_M=1
.param M8_L=0.15 M8_W=1.94 M8_Nf=2 M8_M=1
.param M16_L=0.15 M16_W=0.59 M16_Nf=1 M16_M=1
.param M7_L=0.21 M7_W=1.96 M7_Nf=1 M7_M=2


* --- CIRCUIT DEFINITION ---

.subckt comp CLK INM INP OUTM OUTP VDD VSS
    XM14 CROSSN CROSSP VDD VDD sky130_fd_pr__pfet_01v8 L={M14_L} W={M14_W} nf={M14_Nf} mult={M14_M} m={M14_M}
    XM4 CROSSN CROSSP INTERN VSS sky130_fd_pr__nfet_01v8 L={M4_L} W={M4_W} nf={M4_Nf} mult={M4_M} m={M4_M}
    XM5 INTERN INP tail VSS sky130_fd_pr__nfet_01v8 L={M5_L} W={M5_W} nf={M5_Nf} mult={M5_M} m={M5_M}
    XM10 CROSSN CLK VDD VDD sky130_fd_pr__pfet_01v8 L={M10_L} W={M10_W} nf={M10_Nf} mult={M10_M} m={M10_M}
    XM18 INTERN CLK VDD VDD sky130_fd_pr__pfet_01v8 L={M18_L} W={M18_W} nf={M18_Nf} mult={M18_M} m={M18_M}
    XM0 VSS INTERN VSS VSS sky130_fd_pr__nfet_01v8 L={M0_L} W={M0_W} nf={M0_Nf} mult={M0_M} m={M0_M}
    XM15 OUTP CROSSN VDD VDD sky130_fd_pr__pfet_01v8 L={M15_L} W={M15_W} nf={M15_Nf} mult={M15_M} m={M15_M}
    XM17 OUTP CROSSN VSS VSS sky130_fd_pr__nfet_01v8 L={M17_L} W={M17_W} nf={M17_Nf} mult={M17_M} m={M17_M}
    XM13 CROSSP CROSSN VDD VDD sky130_fd_pr__pfet_01v8 L={M13_L} W={M13_W} nf={M13_Nf} mult={M13_M} m={M13_M}
    XM3 CROSSP CROSSN INTERP VSS sky130_fd_pr__nfet_01v8 L={M3_L} W={M3_W} nf={M3_Nf} mult={M3_M} m={M3_M}
    XM6 INTERP INM tail VSS sky130_fd_pr__nfet_01v8 L={M6_L} W={M6_W} nf={M6_Nf} mult={M6_M} m={M6_M}
    XM12 CROSSP CLK VDD VDD sky130_fd_pr__pfet_01v8 L={M12_L} W={M12_W} nf={M12_Nf} mult={M12_M} m={M12_M}
    XM19 INTERP CLK VDD VDD sky130_fd_pr__pfet_01v8 L={M19_L} W={M19_W} nf={M19_Nf} mult={M19_M} m={M19_M}
    XM22 VSS INTERP VSS VSS sky130_fd_pr__nfet_01v8 L={M22_L} W={M22_W} nf={M22_Nf} mult={M22_M} m={M22_M}
    XM8 OUTM CROSSP VDD VDD sky130_fd_pr__pfet_01v8 L={M8_L} W={M8_W} nf={M8_Nf} mult={M8_M} m={M8_M}
    XM16 OUTM CROSSP VSS VSS sky130_fd_pr__nfet_01v8 L={M16_L} W={M16_W} nf={M16_Nf} mult={M16_M} m={M16_M}
    XM7 tail CLK VSS VSS sky130_fd_pr__nfet_01v8 L={M7_L} W={M7_W} nf={M7_Nf} mult={M7_M} m={M7_M}
.ends comp
