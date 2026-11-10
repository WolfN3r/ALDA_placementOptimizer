* ============================================================
* Circuit : ota1
* Source  : sky130 port of MAGICAL ota1 (IIC-OSIC-TOOLS container)
* File    : /foss/designs/06_ota1_magical/ota1.spice
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 26
*   Device types : sky130_fd_pr__nfet_01v8 sky130_fd_pr__nfet_01v8_lvt sky130_fd_pr__pfet_01v8 sky130_fd_pr__pfet_01v8_lvt
*   Passives     : 4 resistors, 2 capacitors
* Note: PDK sky130 (prefix 'sky' -> 012 generator, --pdk sky130). Sizes copied from
*       06_ota1_magical/ota1_sized.spice (2026-11-04, rounded, re-simulated): W is per copy
*       (all its fingers), nf fingers per copy, M copies. MD*, RD* are the schematic
*       dummies (all terminals on a rail); 012 drops them and adds its own.
* ============================================================

* --- DEVICE PARAMETERS ---
.param MP1b_L=4.535 MP1b_W=13.4 MP1b_Nf=4 MP1b_M=4
.param M0_L=0.6 M0_W=32.82 M0_Nf=4 M0_M=4
.param M1_L=0.54 M1_W=29.94 M1_Nf=4 M1_M=2
.param M9_L=1.93 M9_W=3.48 M9_Nf=1 M9_M=32
.param MP1a_L=4.535 MP1a_W=13.4 MP1a_Nf=4 MP1a_M=4
.param M2_L=0.6 M2_W=32.82 M2_Nf=4 M2_M=4
.param M3_L=0.54 M3_W=29.94 M3_Nf=4 M3_M=2
.param M6_L=1.93 M6_W=3.48 M6_Nf=1 M6_M=32
.param M10_L=1.93 M10_W=3.48 M10_Nf=1 M10_M=4
.param M11_L=1.93 M11_W=3.48 M11_Nf=1 M11_M=4
.param M5_L=4.535 M5_W=13.4 M5_Nf=4 M5_M=2
.param M7_L=4.535 M7_W=13.4 M7_Nf=4 M7_M=2
.param M4_L=1.93 M4_W=3.48 M4_Nf=1 M4_M=2
.param M15_L=0.35 M15_W=13.99 M15_Nf=2 M15_M=2
.param M17_L=0.35 M17_W=13.99 M17_Nf=2 M17_M=2
.param M19_L=0.35 M19_W=13.99 M19_Nf=2 M19_M=2
.param M18_L=0.35 M18_W=13.99 M18_Nf=2 M18_M=2
.param MP1c_L=4.535 MP1c_W=13.4 MP1c_Nf=4 MP1c_M=2
.param M20_L=4.535 M20_W=13.4 M20_Nf=4 M20_M=2
.param M13_L=1.93 M13_W=3.48 M13_Nf=1 M13_M=2
.param M12_L=1.93 M12_W=3.48 M12_Nf=1 M12_M=2
.param MD0_L=0.6 MD0_W=8.205 MD0_Nf=1 MD0_M=4
.param MDN_L=1.93 MDN_W=3.48 MDN_Nf=1 MDN_M=4
.param MDP_L=4.535 MDP_W=6.7 MDP_Nf=1 MDP_M=4
.param MD1_L=0.54 MD1_W=7.485 MD1_Nf=1 MD1_M=2
.param MDCM_L=0.35 MDCM_W=6.995 MDCM_Nf=1 MDCM_M=2
.param R25_L=2.37
.param R23_L=2.37
.param RD1_L=2.37
.param RD2_L=2.37
.param C1_L=19.095 C1_W=19.095
.param C0_L=19.095 C0_W=19.095


* --- CIRCUIT DEFINITION ---

.subckt ota1 INM INP OUTM OUTP VBIAS_P VDD VREF VSS
    XMP1b intp VBIAS_P VDD VDD sky130_fd_pr__pfet_01v8 L={MP1b_L} W={MP1b_W} nf={MP1b_Nf} mult={MP1b_M} m={MP1b_M}
    XM0 intp INM tail VSS sky130_fd_pr__nfet_01v8 L={M0_L} W={M0_W} nf={M0_Nf} mult={M0_M} m={M0_M}
    XM1 OUTM intp VDD VDD sky130_fd_pr__pfet_01v8_lvt L={M1_L} W={M1_W} nf={M1_Nf} mult={M1_M} m={M1_M}
    XM9 OUTM vbias_n VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M9_L} W={M9_W} nf={M9_Nf} mult={M9_M} m={M9_M}
    XMP1a intm VBIAS_P VDD VDD sky130_fd_pr__pfet_01v8 L={MP1a_L} W={MP1a_W} nf={MP1a_Nf} mult={MP1a_M} m={MP1a_M}
    XM2 intm INP tail VSS sky130_fd_pr__nfet_01v8 L={M2_L} W={M2_W} nf={M2_Nf} mult={M2_M} m={M2_M}
    XM3 OUTP intm VDD VDD sky130_fd_pr__pfet_01v8_lvt L={M3_L} W={M3_W} nf={M3_Nf} mult={M3_M} m={M3_M}
    XM6 OUTP vbias_n VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M6_L} W={M6_W} nf={M6_Nf} mult={M6_M} m={M6_M}
    XM10 tail vbias_n VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M10_L} W={M10_W} nf={M10_Nf} mult={M10_M} m={M10_M}
    XM11 tail vcmfb VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M11_L} W={M11_W} nf={M11_Nf} mult={M11_M} m={M11_M}
    XM5 VBIAS_P VBIAS_P VDD VDD sky130_fd_pr__pfet_01v8 L={M5_L} W={M5_W} nf={M5_Nf} mult={M5_M} m={M5_M}
    XM7 vbias_n VBIAS_P VDD VDD sky130_fd_pr__pfet_01v8 L={M7_L} W={M7_W} nf={M7_Nf} mult={M7_M} m={M7_M}
    XM4 vbias_n vbias_n VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M4_L} W={M4_W} nf={M4_Nf} mult={M4_M} m={M4_M}
    XM15 vcmfb OUTP net020 VDD sky130_fd_pr__pfet_01v8_lvt L={M15_L} W={M15_W} nf={M15_Nf} mult={M15_M} m={M15_M}
    XM17 net025 VREF net020 VDD sky130_fd_pr__pfet_01v8_lvt L={M17_L} W={M17_W} nf={M17_Nf} mult={M17_M} m={M17_M}
    XM19 net025 VREF net028 VDD sky130_fd_pr__pfet_01v8_lvt L={M19_L} W={M19_W} nf={M19_Nf} mult={M19_M} m={M19_M}
    XM18 vcmfb OUTM net028 VDD sky130_fd_pr__pfet_01v8_lvt L={M18_L} W={M18_W} nf={M18_Nf} mult={M18_M} m={M18_M}
    XMP1c net020 VBIAS_P VDD VDD sky130_fd_pr__pfet_01v8 L={MP1c_L} W={MP1c_W} nf={MP1c_Nf} mult={MP1c_M} m={MP1c_M}
    XM20 net028 VBIAS_P VDD VDD sky130_fd_pr__pfet_01v8 L={M20_L} W={M20_W} nf={M20_Nf} mult={M20_M} m={M20_M}
    XM13 vcmfb vcmfb VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M13_L} W={M13_W} nf={M13_Nf} mult={M13_M} m={M13_M}
    XM12 net025 net025 VSS VSS sky130_fd_pr__nfet_01v8_lvt L={M12_L} W={M12_W} nf={M12_Nf} mult={M12_M} m={M12_M}
    XMD0 VSS VSS VSS VSS sky130_fd_pr__nfet_01v8 L={MD0_L} W={MD0_W} nf={MD0_Nf} mult={MD0_M} m={MD0_M}
    XMDN VSS VSS VSS VSS sky130_fd_pr__nfet_01v8_lvt L={MDN_L} W={MDN_W} nf={MDN_Nf} mult={MDN_M} m={MDN_M}
    XMDP VDD VDD VDD VDD sky130_fd_pr__pfet_01v8 L={MDP_L} W={MDP_W} nf={MDP_Nf} mult={MDP_M} m={MDP_M}
    XMD1 VDD VDD VDD VDD sky130_fd_pr__pfet_01v8_lvt L={MD1_L} W={MD1_W} nf={MD1_Nf} mult={MD1_M} m={MD1_M}
    XMDCM VDD VDD VDD VDD sky130_fd_pr__pfet_01v8_lvt L={MDCM_L} W={MDCM_W} nf={MDCM_Nf} mult={MDCM_M} m={MDCM_M}
    XR25 net037 intp VSS sky130_fd_pr__res_high_po_0p69 L={R25_L} mult=1 m=1
    XR23 net047 intm VSS sky130_fd_pr__res_high_po_0p69 L={R23_L} mult=1 m=1
    XRD1 VSS VSS VSS sky130_fd_pr__res_high_po_0p69 L={RD1_L} mult=1 m=1
    XRD2 VSS VSS VSS sky130_fd_pr__res_high_po_0p69 L={RD2_L} mult=1 m=1
    XC1 net037 OUTM sky130_fd_pr__cap_mim_m3_1 W={C1_W} L={C1_L} MF=1 m=1
    XC0 net047 OUTP sky130_fd_pr__cap_mim_m3_1 W={C0_W} L={C0_L} MF=1 m=1
.ends ota1
