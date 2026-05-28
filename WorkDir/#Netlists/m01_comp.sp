* ============================================================
* Circuit : comp
* Source  : MAGICAL analog layout examples
* File    : MAGICALexamples/comp.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 17
*   Device types : nmos_lvt pmos_lvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from Spectre/HSPICE format to ALIGN SPICE format.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param M0_L=1u M0_W=1.05u M0_M=1 M0_Nf=1
.param M22_L=1u M22_W=1.05u M22_M=1 M22_Nf=1
.param M16_L=40n M16_W=1.44u M16_M=1 M16_Nf=3
.param M17_L=40n M17_W=1.44u M17_M=1 M17_Nf=3
.param M4_L=40n M4_W=1.92u M4_M=1 M4_Nf=4
.param M3_L=40n M3_W=1.92u M3_M=1 M3_Nf=4
.param M7_L=40n M7_W=8.64u M7_M=1 M7_Nf=18
.param M5_L=40n M5_W=9.6u M5_M=1 M5_Nf=10
.param M6_L=40n M6_W=9.6u M6_M=1 M6_Nf=10
.param M8_L=40n M8_W=2.88u M8_M=1 M8_Nf=3
.param M18_L=40n M18_W=1.92u M18_M=1 M18_Nf=2
.param M15_L=40n M15_W=2.88u M15_M=1 M15_Nf=3
.param M19_L=40n M19_W=1.92u M19_M=1 M19_Nf=2
.param M10_L=40n M10_W=1.92u M10_M=1 M10_Nf=2
.param M12_L=40n M12_W=1.92u M12_M=1 M12_Nf=2
.param M14_L=40n M14_W=3.84u M14_M=1 M14_Nf=4
.param M13_L=40n M13_W=3.84u M13_M=1 M13_Nf=4


* --- CIRCUIT DEFINITION ---
.subckt COMPARATOR_PRE_AMP_2018_Modify_test_flow CLK CROSSN CROSSP VSSA INTERN INTERP OUTM OUTP VDDA VIP VIM
M0 VSSA INTERN VSSA VSSA nmos_lvt L={M0_L} W={M0_W} M={M0_M} Nf={M0_Nf}
M22 VSSA INTERP VSSA VSSA nmos_lvt L={M22_L} W={M22_W} M={M22_M} Nf={M22_Nf}
M16 OUTM CROSSP VSSA VSSA nmos_lvt L={M16_L} W={M16_W} M={M16_M} Nf={M16_Nf}
M17 OUTP CROSSN VSSA VSSA nmos_lvt L={M17_L} W={M17_W} M={M17_M} Nf={M17_Nf}
M4 CROSSN CROSSP INTERN VSSA nmos_lvt L={M4_L} W={M4_W} M={M4_M} Nf={M4_Nf}
M3 CROSSP CROSSN INTERP VSSA nmos_lvt L={M3_L} W={M3_W} M={M3_M} Nf={M3_Nf}
M7 net050 CLK VSSA VSSA nmos_lvt L={M7_L} W={M7_W} M={M7_M} Nf={M7_Nf}
M5 INTERN VIP net050 VSSA nmos_lvt L={M5_L} W={M5_W} M={M5_M} Nf={M5_Nf}
M6 INTERP VIM net050 VSSA nmos_lvt L={M6_L} W={M6_W} M={M6_M} Nf={M6_Nf}
M8 OUTM CROSSP VDDA VDDA pmos_lvt L={M8_L} W={M8_W} M={M8_M} Nf={M8_Nf}
M18 INTERN CLK VDDA VDDA pmos_lvt L={M18_L} W={M18_W} M={M18_M} Nf={M18_Nf}
M15 OUTP CROSSN VDDA VDDA pmos_lvt L={M15_L} W={M15_W} M={M15_M} Nf={M15_Nf}
M19 INTERP CLK VDDA VDDA pmos_lvt L={M19_L} W={M19_W} M={M19_M} Nf={M19_Nf}
M10 CROSSN CLK VDDA VDDA pmos_lvt L={M10_L} W={M10_W} M={M10_M} Nf={M10_Nf}
M12 CROSSP CLK VDDA VDDA pmos_lvt L={M12_L} W={M12_W} M={M12_M} Nf={M12_Nf}
M14 CROSSN CROSSP VDDA VDDA pmos_lvt L={M14_L} W={M14_W} M={M14_M} Nf={M14_Nf}
M13 CROSSP CROSSN VDDA VDDA pmos_lvt L={M13_L} W={M13_W} M={M13_M} Nf={M13_Nf}
.ends COMPARATOR_PRE_AMP_2018_Modify_test_flow
