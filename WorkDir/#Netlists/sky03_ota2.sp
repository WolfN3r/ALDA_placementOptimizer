* ============================================================
* Circuit : ota2
* Source  : sky130 port of MAGICAL ota2 (IIC-OSIC-TOOLS container)
* File    : /foss/designs/08_ota2_magical/ota2.spice
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 35
*   Device types : sky130_fd_pr__nfet_01v8 sky130_fd_pr__nfet_01v8_lvt sky130_fd_pr__pfet_01v8 sky130_fd_pr__pfet_01v8_hvt sky130_fd_pr__pfet_01v8_lvt
*   Passives     : 6 resistors, 8 capacitors
* Note: PDK sky130 (prefix 'sky' -> 012 generator, --pdk sky130). Sizes copied from
*       08_ota2_magical/ota2_sized.spice (2026-11-09, result.json, rounded to
*       0.01 um, re-simulated): W is per copy (all its fingers), nf fingers per copy,
*       M copies. Bias current IBIAS = 13.2 uA into the IBIAS pin.
*       Matched pairs: M8/M10, M34/M35, M17/M18, M26/M27, M70/M71, M9/M12, M20/M21,
*       M68/M69, M32/M33, R12/R5, C1/C0, R11/R14, C5/C4, C6/C7, C2/C3, R0/R13; mirrors
*       M1/M2/M3/M4/M7 (NBIAS_TAIL), M28/M24/M25 (PCAS). No schematic dummies.
* ============================================================

* --- DEVICE PARAMETERS ---
.param M74_L=0.71 M74_W=10.4 M74_Nf=4 M74_M=2
.param M34_L=1.12 M34_W=22.72 M34_Nf=8 M34_M=4
.param M35_L=1.12 M35_W=22.72 M35_Nf=8 M35_M=4
.param M27_L=0.35 M27_W=40.96 M27_Nf=16 M27_M=2
.param M26_L=0.35 M26_W=40.96 M26_Nf=16 M26_M=2
.param M18_L=0.3 M18_W=3.58 M18_Nf=2 M18_M=2
.param M17_L=0.3 M17_W=3.58 M17_Nf=2 M17_M=2
.param M10_L=0.72 M10_W=16.32 M10_Nf=8 M10_M=4
.param M8_L=0.72 M8_W=16.32 M8_Nf=8 M8_M=4
.param M1_L=1.23 M1_W=1.29 M1_Nf=1 M1_M=6
.param R12_L=3.37
.param C1_L=9 C1_W=9
.param R5_L=3.37
.param C0_L=9 C0_W=9
.param M70_L=0.64 M70_W=9.12 M70_Nf=4 M70_M=12
.param M71_L=0.64 M71_W=9.12 M71_Nf=4 M71_M=12
.param M9_L=0.28 M9_W=19.6 M9_Nf=8 M9_M=2
.param M12_L=0.28 M12_W=19.6 M12_Nf=8 M12_M=2
.param C2_L=27.85 C2_W=27.85
.param R0_L=35
.param C3_L=27.85 C3_W=27.85
.param R13_L=35
.param M50_L=0.3 M50_W=29 M50_Nf=20 M50_M=2
.param R11_L=5.2
.param C5_L=4 C5_W=4
.param C6_L=8.61 C6_W=8.61
.param R14_L=5.2
.param C4_L=4 C4_W=4
.param C7_L=8.61 C7_W=8.61
.param M19_L=0.5 M19_W=7.8 M19_Nf=2 M19_M=1
.param M15_L=0.5 M15_W=4 M15_Nf=2 M15_M=1
.param M4_L=1.23 M4_W=1.29 M4_Nf=1 M4_M=2
.param M36_L=0.5 M36_W=3.36 M36_Nf=8 M36_M=1
.param M28_L=0.35 M28_W=2 M28_Nf=4 M28_M=1
.param M16_L=0.5 M16_W=4 M16_Nf=2 M16_M=1
.param M2_L=1.23 M2_W=1.29 M2_Nf=1 M2_M=2
.param M32_L=1 M32_W=8 M32_Nf=4 M32_M=2
.param M24_L=0.35 M24_W=2 M24_Nf=4 M24_M=1
.param M13_L=0.5 M13_W=4 M13_Nf=2 M13_M=1
.param M3_L=1.23 M3_W=1.29 M3_Nf=1 M3_M=2
.param M33_L=1 M33_W=8 M33_Nf=4 M33_M=2
.param M25_L=0.35 M25_W=2 M25_Nf=4 M25_M=1
.param M14_L=0.28 M14_W=0.71 M14_Nf=1 M14_M=1
.param M6_L=0.3 M6_W=0.82 M6_Nf=1 M6_M=1
.param M69_L=0.5 M69_W=4.5 M69_Nf=2 M69_M=2
.param M68_L=0.5 M68_W=4.5 M68_Nf=2 M68_M=2
.param M21_L=0.5 M21_W=3 M21_Nf=1 M21_M=2
.param M20_L=0.5 M20_W=3 M20_Nf=1 M20_M=2
.param M7_L=1.23 M7_W=1.29 M7_Nf=1 M7_M=4


* --- CIRCUIT DEFINITION ---

.subckt ota2 VIM VIP IBIAS VCM VOM VOP VDD VSS
    XM74 PTAIL net0118 VDD VDD sky130_fd_pr__pfet_01v8 L={M74_L} W={M74_W} nf={M74_Nf} mult={M74_M} m={M74_M}
    XM34 net1 VIM PTAIL VDD sky130_fd_pr__pfet_01v8_lvt L={M34_L} W={M34_W} nf={M34_Nf} mult={M34_M} m={M34_M}
    XM35 net2 VIP PTAIL VDD sky130_fd_pr__pfet_01v8_lvt L={M35_L} W={M35_W} nf={M35_Nf} mult={M35_M} m={M35_M}
    XM27 VO1P PCAS net1 VDD sky130_fd_pr__pfet_01v8_lvt L={M27_L} W={M27_W} nf={M27_Nf} mult={M27_M} m={M27_M}
    XM26 VO1M PCAS net2 VDD sky130_fd_pr__pfet_01v8_lvt L={M26_L} W={M26_W} nf={M26_Nf} mult={M26_M} m={M26_M}
    XM18 VO1P IBIAS net3 VSS sky130_fd_pr__nfet_01v8_lvt L={M18_L} W={M18_W} nf={M18_Nf} mult={M18_M} m={M18_M}
    XM17 VO1M IBIAS net4 VSS sky130_fd_pr__nfet_01v8_lvt L={M17_L} W={M17_W} nf={M17_Nf} mult={M17_M} m={M17_M}
    XM10 net3 VIM NTAIL VSS sky130_fd_pr__nfet_01v8_lvt L={M10_L} W={M10_W} nf={M10_Nf} mult={M10_M} m={M10_M}
    XM8 net4 VIP NTAIL VSS sky130_fd_pr__nfet_01v8_lvt L={M8_L} W={M8_W} nf={M8_Nf} mult={M8_M} m={M8_M}
    XM1 NTAIL NBIAS_TAIL VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M1_L} W={M1_W} nf={M1_Nf} mult={M1_M} m={M1_M}
    XR12 net0118 VO1P VSS sky130_fd_pr__res_xhigh_po_0p69 L={R12_L} mult=1 m=1
    XC1 VO1P net0118 sky130_fd_pr__cap_mim_m3_1 W={C1_W} L={C1_L} MF=1 m=1
    XR5 net0118 VO1M VSS sky130_fd_pr__res_xhigh_po_0p69 L={R5_L} mult=1 m=1
    XC0 VO1M net0118 sky130_fd_pr__cap_mim_m3_1 W={C0_W} L={C0_L} MF=1 m=1
    XM70 VOM VO1P VDD VDD sky130_fd_pr__pfet_01v8 L={M70_L} W={M70_W} nf={M70_Nf} mult={M70_M} m={M70_M}
    XM71 VOP VO1M VDD VDD sky130_fd_pr__pfet_01v8 L={M71_L} W={M71_W} nf={M71_Nf} mult={M71_M} m={M71_M}
    XM9 VOM net5 vs VSS sky130_fd_pr__nfet_01v8_lvt L={M9_L} W={M9_W} nf={M9_Nf} mult={M9_M} m={M9_M}
    XM12 VOP net6 vs VSS sky130_fd_pr__nfet_01v8_lvt L={M12_L} W={M12_W} nf={M12_Nf} mult={M12_M} m={M12_M}
    XC2 net5 VIP sky130_fd_pr__cap_mim_m3_1 W={C2_W} L={C2_L} MF=1 m=1
    XR0 net5 INCM2 VSS sky130_fd_pr__res_xhigh_po_0p35 L={R0_L} mult=1 m=1
    XC3 net6 VIM sky130_fd_pr__cap_mim_m3_1 W={C3_W} L={C3_L} MF=1 m=1
    XR13 net6 INCM2 VSS sky130_fd_pr__res_xhigh_po_0p35 L={R13_L} mult=1 m=1
    XM50 vs vtail VSS VSS sky130_fd_pr__nfet_01v8 L={M50_L} W={M50_W} nf={M50_Nf} mult={M50_M} m={M50_M}
    XR11 net0101 VOM VSS sky130_fd_pr__res_xhigh_po_0p69 L={R11_L} mult=1 m=1
    XC5 VOM net0101 sky130_fd_pr__cap_mim_m3_1 W={C5_W} L={C5_L} MF=1 m=1
    XC6 vtail VOM sky130_fd_pr__cap_mim_m3_1 W={C6_W} L={C6_L} MF=1 m=1
    XR14 net0101 VOP VSS sky130_fd_pr__res_xhigh_po_0p69 L={R14_L} mult=1 m=1
    XC4 VOP net0101 sky130_fd_pr__cap_mim_m3_1 W={C4_W} L={C4_L} MF=1 m=1
    XC7 vtail VOP sky130_fd_pr__cap_mim_m3_1 W={C7_W} L={C7_L} MF=1 m=1
    XM19 IBIAS IBIAS NBIAS_TAIL VSS sky130_fd_pr__nfet_01v8_lvt L={M19_L} W={M19_W} nf={M19_Nf} mult={M19_M} m={M19_M}
    XM15 NBIAS_TAIL VCM net13 VSS sky130_fd_pr__nfet_01v8_lvt L={M15_L} W={M15_W} nf={M15_Nf} mult={M15_M} m={M15_M}
    XM4 net13 NBIAS_TAIL VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M4_L} W={M4_W} nf={M4_Nf} mult={M4_M} m={M4_M}
    XM36 net7 PCAS VDD VDD sky130_fd_pr__pfet_01v8_hvt L={M36_L} W={M36_W} nf={M36_Nf} mult={M36_M} m={M36_M}
    XM28 PCAS PCAS net7 VDD sky130_fd_pr__pfet_01v8_lvt L={M28_L} W={M28_W} nf={M28_Nf} mult={M28_M} m={M28_M}
    XM16 PCAS VCM net14 VSS sky130_fd_pr__nfet_01v8_lvt L={M16_L} W={M16_W} nf={M16_Nf} mult={M16_M} m={M16_M}
    XM2 net14 NBIAS_TAIL VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M2_L} W={M2_W} nf={M2_Nf} mult={M2_M} m={M2_M}
    XM32 net8 net9 VDD VDD sky130_fd_pr__pfet_01v8 L={M32_L} W={M32_W} nf={M32_Nf} mult={M32_M} m={M32_M}
    XM24 net9 PCAS net8 VDD sky130_fd_pr__pfet_01v8_lvt L={M24_L} W={M24_W} nf={M24_Nf} mult={M24_M} m={M24_M}
    XM13 net9 VCM net15 VSS sky130_fd_pr__nfet_01v8_lvt L={M13_L} W={M13_W} nf={M13_Nf} mult={M13_M} m={M13_M}
    XM3 net15 NBIAS_TAIL VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M3_L} W={M3_W} nf={M3_Nf} mult={M3_M} m={M3_M}
    XM33 net10 net9 VDD VDD sky130_fd_pr__pfet_01v8 L={M33_L} W={M33_W} nf={M33_Nf} mult={M33_M} m={M33_M}
    XM25 INCM2 PCAS net10 VDD sky130_fd_pr__pfet_01v8_lvt L={M25_L} W={M25_W} nf={M25_Nf} mult={M25_M} m={M25_M}
    XM14 INCM2 INCM2 net16 VSS sky130_fd_pr__nfet_01v8_lvt L={M14_L} W={M14_W} nf={M14_Nf} mult={M14_M} m={M14_M}
    XM6 net16 INCM2 VSS VSS sky130_fd_pr__nfet_01v8 L={M6_L} W={M6_W} nf={M6_Nf} mult={M6_M} m={M6_M}
    XM69 net11 net11 VDD VDD sky130_fd_pr__pfet_01v8 L={M69_L} W={M69_W} nf={M69_Nf} mult={M69_M} m={M69_M}
    XM68 vtail net11 VDD VDD sky130_fd_pr__pfet_01v8 L={M68_L} W={M68_W} nf={M68_Nf} mult={M68_M} m={M68_M}
    XM21 net11 net0101 net12 VSS sky130_fd_pr__nfet_01v8_lvt L={M21_L} W={M21_W} nf={M21_Nf} mult={M21_M} m={M21_M}
    XM20 vtail VCM net12 VSS sky130_fd_pr__nfet_01v8_lvt L={M20_L} W={M20_W} nf={M20_Nf} mult={M20_M} m={M20_M}
    XM7 net12 NBIAS_TAIL VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M7_L} W={M7_W} nf={M7_Nf} mult={M7_M} m={M7_M}
.ends ota2
