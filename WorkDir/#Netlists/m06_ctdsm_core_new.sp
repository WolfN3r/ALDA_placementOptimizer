* ============================================================
* Circuit : ctdsm_core_new
* Source  : MAGICAL analog layout examples
* File    : MAGICALexamples/CTDSM_CORE_NEW_hspice.sp
* ============================================================
* Stats:
*   Subcircuits  : 21
*   Devices (M)  : 182
*   Device types : nmos_hvt nmos_lvt nmos_rvt pmos_lvt pmos_rvt
*   Passives     : 13 resistors, 47 capacitors
* Note: Converted from Spectre/HSPICE format to ALIGN SPICE format.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param Gm2_v5_Practice_schematic_Mm20_L=3.6e-6 Gm2_v5_Practice_schematic_Mm20_W=2.8e-6 Gm2_v5_Practice_schematic_Mm20_M=1 Gm2_v5_Practice_schematic_Mm20_Nf=1
.param Gm2_v5_Practice_schematic_Mm18_L=3.6e-6 Gm2_v5_Practice_schematic_Mm18_W=2.8e-6 Gm2_v5_Practice_schematic_Mm18_M=1 Gm2_v5_Practice_schematic_Mm18_Nf=1
.param Gm2_v5_Practice_schematic_Mm0_L=160e-9 Gm2_v5_Practice_schematic_Mm0_W=700e-9 Gm2_v5_Practice_schematic_Mm0_M=1 Gm2_v5_Practice_schematic_Mm0_Nf=2
.param Gm2_v5_Practice_schematic_Mm24_L=160e-9 Gm2_v5_Practice_schematic_Mm24_W=700e-9 Gm2_v5_Practice_schematic_Mm24_M=1 Gm2_v5_Practice_schematic_Mm24_Nf=2
.param Gm2_v5_Practice_schematic_Mm23_L=160e-9 Gm2_v5_Practice_schematic_Mm23_W=1.4e-6 Gm2_v5_Practice_schematic_Mm23_M=1 Gm2_v5_Practice_schematic_Mm23_Nf=4
.param Gm2_v5_Practice_schematic_Mm14_L=160e-9 Gm2_v5_Practice_schematic_Mm14_W=1.4e-6 Gm2_v5_Practice_schematic_Mm14_M=1 Gm2_v5_Practice_schematic_Mm14_Nf=4
.param Gm2_v5_Practice_schematic_Mm22_L=160e-9 Gm2_v5_Practice_schematic_Mm22_W=3.12e-6 Gm2_v5_Practice_schematic_Mm22_M=1 Gm2_v5_Practice_schematic_Mm22_Nf=4
.param Gm2_v5_Practice_schematic_Mm12_L=2.2e-6 Gm2_v5_Practice_schematic_Mm12_W=2.1e-6 Gm2_v5_Practice_schematic_Mm12_M=1 Gm2_v5_Practice_schematic_Mm12_Nf=1
.param Gm2_v5_Practice_schematic_Mm11_L=2.2e-6 Gm2_v5_Practice_schematic_Mm11_W=2.1e-6 Gm2_v5_Practice_schematic_Mm11_M=1 Gm2_v5_Practice_schematic_Mm11_Nf=1
.param Gm2_v5_Practice_schematic_Mm13_L=160e-9 Gm2_v5_Practice_schematic_Mm13_W=1.16e-6 Gm2_v5_Practice_schematic_Mm13_M=1 Gm2_v5_Practice_schematic_Mm13_Nf=4
.param Gm2_v5_Practice_schematic_Mm21_L=160e-9 Gm2_v5_Practice_schematic_Mm21_W=1.16e-6 Gm2_v5_Practice_schematic_Mm21_M=1 Gm2_v5_Practice_schematic_Mm21_Nf=4
.param Gm1_v5_Practice_schematic_Mm8_L=120e-9 Gm1_v5_Practice_schematic_Mm8_W=3.22e-6 Gm1_v5_Practice_schematic_Mm8_M=1 Gm1_v5_Practice_schematic_Mm8_Nf=4
.param Gm1_v5_Practice_schematic_Mm2_L=3.3e-6 Gm1_v5_Practice_schematic_Mm2_W=2.95e-6 Gm1_v5_Practice_schematic_Mm2_M=1 Gm1_v5_Practice_schematic_Mm2_Nf=1
.param Gm1_v5_Practice_schematic_Mm4_L=3.3e-6 Gm1_v5_Practice_schematic_Mm4_W=2.95e-6 Gm1_v5_Practice_schematic_Mm4_M=1 Gm1_v5_Practice_schematic_Mm4_Nf=1
.param Gm1_v5_Practice_schematic_Mm12_L=120e-9 Gm1_v5_Practice_schematic_Mm12_W=585e-9 Gm1_v5_Practice_schematic_Mm12_M=1 Gm1_v5_Practice_schematic_Mm12_Nf=1
.param Gm1_v5_Practice_schematic_Mm11_L=120e-9 Gm1_v5_Practice_schematic_Mm11_W=2.34e-6 Gm1_v5_Practice_schematic_Mm11_M=1 Gm1_v5_Practice_schematic_Mm11_Nf=4
.param Gm1_v5_Practice_schematic_Mm15_L=120e-9 Gm1_v5_Practice_schematic_Mm15_W=585e-9 Gm1_v5_Practice_schematic_Mm15_M=1 Gm1_v5_Practice_schematic_Mm15_Nf=1
.param Gm1_v5_Practice_schematic_Mm14_L=120e-9 Gm1_v5_Practice_schematic_Mm14_W=2.34e-6 Gm1_v5_Practice_schematic_Mm14_M=1 Gm1_v5_Practice_schematic_Mm14_Nf=4
.param Gm1_v5_Practice_schematic_Mm3_L=2.2e-6 Gm1_v5_Practice_schematic_Mm3_W=2.5e-6 Gm1_v5_Practice_schematic_Mm3_M=1 Gm1_v5_Practice_schematic_Mm3_Nf=1
.param Gm1_v5_Practice_schematic_Mm0_L=2.2e-6 Gm1_v5_Practice_schematic_Mm0_W=2.5e-6 Gm1_v5_Practice_schematic_Mm0_M=1 Gm1_v5_Practice_schematic_Mm0_Nf=1
.param Gm1_v5_Practice_schematic_Mm26_L=240e-9 Gm1_v5_Practice_schematic_Mm26_W=3.4e-6 Gm1_v5_Practice_schematic_Mm26_M=1 Gm1_v5_Practice_schematic_Mm26_Nf=8
.param Gm1_v5_Practice_schematic_Mm27_L=240e-9 Gm1_v5_Practice_schematic_Mm27_W=3.4e-6 Gm1_v5_Practice_schematic_Mm27_M=1 Gm1_v5_Practice_schematic_Mm27_Nf=8
.param DFCNQD2BWP_LVT_M0_L=40e-9 DFCNQD2BWP_LVT_M0_W=155e-9 DFCNQD2BWP_LVT_M0_M=1 DFCNQD2BWP_LVT_M0_Nf=1
.param DFCNQD2BWP_LVT_Mmi4_L=40e-9 DFCNQD2BWP_LVT_Mmi4_W=310e-9 DFCNQD2BWP_LVT_Mmi4_M=1 DFCNQD2BWP_LVT_Mmi4_Nf=1
.param DFCNQD2BWP_LVT_M1_L=40e-9 DFCNQD2BWP_LVT_M1_W=210e-9 DFCNQD2BWP_LVT_M1_M=1 DFCNQD2BWP_LVT_M1_Nf=1
.param DFCNQD2BWP_LVT_M2_L=40e-9 DFCNQD2BWP_LVT_M2_W=150e-9 DFCNQD2BWP_LVT_M2_M=1 DFCNQD2BWP_LVT_M2_Nf=1
.param DFCNQD2BWP_LVT_Mmi29_L=40e-9 DFCNQD2BWP_LVT_Mmi29_W=120e-9 DFCNQD2BWP_LVT_Mmi29_M=1 DFCNQD2BWP_LVT_Mmi29_Nf=1
.param DFCNQD2BWP_LVT_Mmi15_L=40e-9 DFCNQD2BWP_LVT_Mmi15_W=150e-9 DFCNQD2BWP_LVT_Mmi15_M=1 DFCNQD2BWP_LVT_Mmi15_Nf=1
.param DFCNQD2BWP_LVT_M3_L=40e-9 DFCNQD2BWP_LVT_M3_W=210e-9 DFCNQD2BWP_LVT_M3_M=1 DFCNQD2BWP_LVT_M3_Nf=1
.param DFCNQD2BWP_LVT_M4_L=40e-9 DFCNQD2BWP_LVT_M4_W=210e-9 DFCNQD2BWP_LVT_M4_M=1 DFCNQD2BWP_LVT_M4_Nf=1
.param DFCNQD2BWP_LVT_M5_L=40e-9 DFCNQD2BWP_LVT_M5_W=155e-9 DFCNQD2BWP_LVT_M5_M=1 DFCNQD2BWP_LVT_M5_Nf=1
.param DFCNQD2BWP_LVT_Mmi5_L=40e-9 DFCNQD2BWP_LVT_Mmi5_W=310e-9 DFCNQD2BWP_LVT_Mmi5_M=1 DFCNQD2BWP_LVT_Mmi5_Nf=1
.param DFCNQD2BWP_LVT_Mmi49_L=40e-9 DFCNQD2BWP_LVT_Mmi49_W=120e-9 DFCNQD2BWP_LVT_Mmi49_M=1 DFCNQD2BWP_LVT_Mmi49_Nf=1
.param DFCNQD2BWP_LVT_M6_L=40e-9 DFCNQD2BWP_LVT_M6_W=210e-9 DFCNQD2BWP_LVT_M6_M=1 DFCNQD2BWP_LVT_M6_Nf=1
.param DFCNQD2BWP_LVT_Mmi26_L=40e-9 DFCNQD2BWP_LVT_Mmi26_W=120e-9 DFCNQD2BWP_LVT_Mmi26_M=1 DFCNQD2BWP_LVT_Mmi26_Nf=1
.param DFCNQD2BWP_LVT_Mmi48_L=40e-9 DFCNQD2BWP_LVT_Mmi48_W=120e-9 DFCNQD2BWP_LVT_Mmi48_M=1 DFCNQD2BWP_LVT_Mmi48_Nf=1
.param DFCNQD2BWP_LVT_M7_L=40e-9 DFCNQD2BWP_LVT_M7_W=310e-9 DFCNQD2BWP_LVT_M7_M=1 DFCNQD2BWP_LVT_M7_Nf=1
.param DFCNQD2BWP_LVT_M8_L=40e-9 DFCNQD2BWP_LVT_M8_W=310e-9 DFCNQD2BWP_LVT_M8_M=1 DFCNQD2BWP_LVT_M8_Nf=1
.param DFCNQD2BWP_LVT_Mmi47_L=40e-9 DFCNQD2BWP_LVT_Mmi47_W=120e-9 DFCNQD2BWP_LVT_Mmi47_M=1 DFCNQD2BWP_LVT_Mmi47_Nf=1
.param DFCNQD2BWP_LVT_Mmi33_L=40e-9 DFCNQD2BWP_LVT_Mmi33_W=120e-9 DFCNQD2BWP_LVT_Mmi33_M=1 DFCNQD2BWP_LVT_Mmi33_Nf=1
.param DFCNQD2BWP_LVT_M9_L=40e-9 DFCNQD2BWP_LVT_M9_W=410e-9 DFCNQD2BWP_LVT_M9_M=1 DFCNQD2BWP_LVT_M9_Nf=1
.param DFCNQD2BWP_LVT_M10_L=40e-9 DFCNQD2BWP_LVT_M10_W=370e-9 DFCNQD2BWP_LVT_M10_M=1 DFCNQD2BWP_LVT_M10_Nf=1
.param DFCNQD2BWP_LVT_Mmi43_L=40e-9 DFCNQD2BWP_LVT_Mmi43_W=120e-9 DFCNQD2BWP_LVT_Mmi43_M=1 DFCNQD2BWP_LVT_Mmi43_Nf=1
.param DFCNQD2BWP_LVT_Mmi6_L=40e-9 DFCNQD2BWP_LVT_Mmi6_W=340e-9 DFCNQD2BWP_LVT_Mmi6_M=1 DFCNQD2BWP_LVT_Mmi6_Nf=1
.param DFCNQD2BWP_LVT_M11_L=40e-9 DFCNQD2BWP_LVT_M11_W=410e-9 DFCNQD2BWP_LVT_M11_M=1 DFCNQD2BWP_LVT_M11_Nf=1
.param DFCNQD2BWP_LVT_M12_L=40e-9 DFCNQD2BWP_LVT_M12_W=370e-9 DFCNQD2BWP_LVT_M12_M=1 DFCNQD2BWP_LVT_M12_Nf=1
.param DFCNQD2BWP_LVT_M13_L=40e-9 DFCNQD2BWP_LVT_M13_W=370e-9 DFCNQD2BWP_LVT_M13_M=1 DFCNQD2BWP_LVT_M13_Nf=1
.param DFCNQD2BWP_LVT_Mmi44_L=40e-9 DFCNQD2BWP_LVT_Mmi44_W=120e-9 DFCNQD2BWP_LVT_Mmi44_M=1 DFCNQD2BWP_LVT_Mmi44_Nf=1
.param DFCNQD2BWP_LVT_M14_L=40e-9 DFCNQD2BWP_LVT_M14_W=370e-9 DFCNQD2BWP_LVT_M14_M=1 DFCNQD2BWP_LVT_M14_Nf=1
.param DFCNQD2BWP_LVT_M15_L=40e-9 DFCNQD2BWP_LVT_M15_W=180e-9 DFCNQD2BWP_LVT_M15_M=1 DFCNQD2BWP_LVT_M15_Nf=1
.param DFCNQD2BWP_LVT_M16_L=40e-9 DFCNQD2BWP_LVT_M16_W=205e-9 DFCNQD2BWP_LVT_M16_M=1 DFCNQD2BWP_LVT_M16_Nf=1
.param DFCNQD2BWP_LVT_Mmi16_L=40e-9 DFCNQD2BWP_LVT_Mmi16_W=180e-9 DFCNQD2BWP_LVT_Mmi16_M=1 DFCNQD2BWP_LVT_Mmi16_Nf=1
.param DFCNQD2BWP_LVT_M17_L=40e-9 DFCNQD2BWP_LVT_M17_W=205e-9 DFCNQD2BWP_LVT_M17_M=1 DFCNQD2BWP_LVT_M17_Nf=1
.param DFCNQD2BWP_LVT_Mmi32_L=40e-9 DFCNQD2BWP_LVT_Mmi32_W=120e-9 DFCNQD2BWP_LVT_Mmi32_M=1 DFCNQD2BWP_LVT_Mmi32_Nf=1
.param DFCNQD2BWP_LVT_Mmi45_L=40e-9 DFCNQD2BWP_LVT_Mmi45_W=120e-9 DFCNQD2BWP_LVT_Mmi45_M=1 DFCNQD2BWP_LVT_Mmi45_Nf=1
.param DFCNQD2BWP_LVT_Mmi7_L=40e-9 DFCNQD2BWP_LVT_Mmi7_W=340e-9 DFCNQD2BWP_LVT_Mmi7_M=1 DFCNQD2BWP_LVT_Mmi7_Nf=1
.param DFCNQD2BWP_LVT_schematic_M0_L=40e-9 DFCNQD2BWP_LVT_schematic_M0_W=155e-9 DFCNQD2BWP_LVT_schematic_M0_M=1 DFCNQD2BWP_LVT_schematic_M0_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi4_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi4_W=310e-9 DFCNQD2BWP_LVT_schematic_Mmi4_M=1 DFCNQD2BWP_LVT_schematic_Mmi4_Nf=1
.param DFCNQD2BWP_LVT_schematic_M1_L=40e-9 DFCNQD2BWP_LVT_schematic_M1_W=210e-9 DFCNQD2BWP_LVT_schematic_M1_M=1 DFCNQD2BWP_LVT_schematic_M1_Nf=1
.param DFCNQD2BWP_LVT_schematic_M2_L=40e-9 DFCNQD2BWP_LVT_schematic_M2_W=150e-9 DFCNQD2BWP_LVT_schematic_M2_M=1 DFCNQD2BWP_LVT_schematic_M2_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi29_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi29_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi29_M=1 DFCNQD2BWP_LVT_schematic_Mmi29_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi15_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi15_W=150e-9 DFCNQD2BWP_LVT_schematic_Mmi15_M=1 DFCNQD2BWP_LVT_schematic_Mmi15_Nf=1
.param DFCNQD2BWP_LVT_schematic_M3_L=40e-9 DFCNQD2BWP_LVT_schematic_M3_W=210e-9 DFCNQD2BWP_LVT_schematic_M3_M=1 DFCNQD2BWP_LVT_schematic_M3_Nf=1
.param DFCNQD2BWP_LVT_schematic_M4_L=40e-9 DFCNQD2BWP_LVT_schematic_M4_W=210e-9 DFCNQD2BWP_LVT_schematic_M4_M=1 DFCNQD2BWP_LVT_schematic_M4_Nf=1
.param DFCNQD2BWP_LVT_schematic_M5_L=40e-9 DFCNQD2BWP_LVT_schematic_M5_W=155e-9 DFCNQD2BWP_LVT_schematic_M5_M=1 DFCNQD2BWP_LVT_schematic_M5_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi5_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi5_W=310e-9 DFCNQD2BWP_LVT_schematic_Mmi5_M=1 DFCNQD2BWP_LVT_schematic_Mmi5_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi49_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi49_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi49_M=1 DFCNQD2BWP_LVT_schematic_Mmi49_Nf=1
.param DFCNQD2BWP_LVT_schematic_M6_L=40e-9 DFCNQD2BWP_LVT_schematic_M6_W=210e-9 DFCNQD2BWP_LVT_schematic_M6_M=1 DFCNQD2BWP_LVT_schematic_M6_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi26_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi26_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi26_M=1 DFCNQD2BWP_LVT_schematic_Mmi26_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi48_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi48_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi48_M=1 DFCNQD2BWP_LVT_schematic_Mmi48_Nf=1
.param DFCNQD2BWP_LVT_schematic_M7_L=40e-9 DFCNQD2BWP_LVT_schematic_M7_W=310e-9 DFCNQD2BWP_LVT_schematic_M7_M=1 DFCNQD2BWP_LVT_schematic_M7_Nf=1
.param DFCNQD2BWP_LVT_schematic_M8_L=40e-9 DFCNQD2BWP_LVT_schematic_M8_W=310e-9 DFCNQD2BWP_LVT_schematic_M8_M=1 DFCNQD2BWP_LVT_schematic_M8_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi47_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi47_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi47_M=1 DFCNQD2BWP_LVT_schematic_Mmi47_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi33_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi33_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi33_M=1 DFCNQD2BWP_LVT_schematic_Mmi33_Nf=1
.param DFCNQD2BWP_LVT_schematic_M9_L=40e-9 DFCNQD2BWP_LVT_schematic_M9_W=410e-9 DFCNQD2BWP_LVT_schematic_M9_M=1 DFCNQD2BWP_LVT_schematic_M9_Nf=1
.param DFCNQD2BWP_LVT_schematic_M10_L=40e-9 DFCNQD2BWP_LVT_schematic_M10_W=370e-9 DFCNQD2BWP_LVT_schematic_M10_M=1 DFCNQD2BWP_LVT_schematic_M10_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi43_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi43_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi43_M=1 DFCNQD2BWP_LVT_schematic_Mmi43_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi6_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi6_W=340e-9 DFCNQD2BWP_LVT_schematic_Mmi6_M=1 DFCNQD2BWP_LVT_schematic_Mmi6_Nf=1
.param DFCNQD2BWP_LVT_schematic_M11_L=40e-9 DFCNQD2BWP_LVT_schematic_M11_W=410e-9 DFCNQD2BWP_LVT_schematic_M11_M=1 DFCNQD2BWP_LVT_schematic_M11_Nf=1
.param DFCNQD2BWP_LVT_schematic_M12_L=40e-9 DFCNQD2BWP_LVT_schematic_M12_W=370e-9 DFCNQD2BWP_LVT_schematic_M12_M=1 DFCNQD2BWP_LVT_schematic_M12_Nf=1
.param DFCNQD2BWP_LVT_schematic_M13_L=40e-9 DFCNQD2BWP_LVT_schematic_M13_W=370e-9 DFCNQD2BWP_LVT_schematic_M13_M=1 DFCNQD2BWP_LVT_schematic_M13_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi44_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi44_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi44_M=1 DFCNQD2BWP_LVT_schematic_Mmi44_Nf=1
.param DFCNQD2BWP_LVT_schematic_M14_L=40e-9 DFCNQD2BWP_LVT_schematic_M14_W=370e-9 DFCNQD2BWP_LVT_schematic_M14_M=1 DFCNQD2BWP_LVT_schematic_M14_Nf=1
.param DFCNQD2BWP_LVT_schematic_M15_L=40e-9 DFCNQD2BWP_LVT_schematic_M15_W=180e-9 DFCNQD2BWP_LVT_schematic_M15_M=1 DFCNQD2BWP_LVT_schematic_M15_Nf=1
.param DFCNQD2BWP_LVT_schematic_M16_L=40e-9 DFCNQD2BWP_LVT_schematic_M16_W=205e-9 DFCNQD2BWP_LVT_schematic_M16_M=1 DFCNQD2BWP_LVT_schematic_M16_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi16_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi16_W=180e-9 DFCNQD2BWP_LVT_schematic_Mmi16_M=1 DFCNQD2BWP_LVT_schematic_Mmi16_Nf=1
.param DFCNQD2BWP_LVT_schematic_M17_L=40e-9 DFCNQD2BWP_LVT_schematic_M17_W=205e-9 DFCNQD2BWP_LVT_schematic_M17_M=1 DFCNQD2BWP_LVT_schematic_M17_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi32_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi32_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi32_M=1 DFCNQD2BWP_LVT_schematic_Mmi32_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi45_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi45_W=120e-9 DFCNQD2BWP_LVT_schematic_Mmi45_M=1 DFCNQD2BWP_LVT_schematic_Mmi45_Nf=1
.param DFCNQD2BWP_LVT_schematic_Mmi7_L=40e-9 DFCNQD2BWP_LVT_schematic_Mmi7_W=340e-9 DFCNQD2BWP_LVT_schematic_Mmi7_M=1 DFCNQD2BWP_LVT_schematic_Mmi7_Nf=1
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm0_L=1e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm0_W=1.05e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm0_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm0_Nf=1
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm22_L=1e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm22_W=1.05e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm22_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm22_Nf=1
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm16_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm16_W=1.44e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm16_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm16_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm17_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm17_W=1.44e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm17_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm17_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm4_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm4_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm4_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm4_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm3_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm3_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm3_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm3_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm7_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm7_W=6.9e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm7_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm7_Nf=15
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm5_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm5_W=14.4e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm5_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm5_Nf=15
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm6_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm6_W=14.4e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm6_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm6_Nf=15
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm8_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm8_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm8_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm8_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm18_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm18_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm18_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm18_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm15_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm15_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm15_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm15_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm2_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm2_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm2_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm2_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm1_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm1_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm1_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm1_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm12_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm12_W=1.92e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm12_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm12_Nf=4
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm14_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm14_W=3.84e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm14_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm14_Nf=8
.param myComparator_v3_CTDSM_DEC2016_schematic_Mm13_L=40e-9 myComparator_v3_CTDSM_DEC2016_schematic_Mm13_W=3.84e-6 myComparator_v3_CTDSM_DEC2016_schematic_Mm13_M=1 myComparator_v3_CTDSM_DEC2016_schematic_Mm13_Nf=8
.param NR2D8BWP_LVT_M0_L=80e-9 NR2D8BWP_LVT_M0_W=4.96e-6 NR2D8BWP_LVT_M0_M=1 NR2D8BWP_LVT_M0_Nf=2
.param NR2D8BWP_LVT_M1_L=80e-9 NR2D8BWP_LVT_M1_W=4.96e-6 NR2D8BWP_LVT_M1_M=1 NR2D8BWP_LVT_M1_Nf=2
.param NR2D8BWP_LVT_M2_L=80e-9 NR2D8BWP_LVT_M2_W=6.56e-6 NR2D8BWP_LVT_M2_M=1 NR2D8BWP_LVT_M2_Nf=2
.param NR2D8BWP_LVT_M3_L=80e-9 NR2D8BWP_LVT_M3_W=6.56e-6 NR2D8BWP_LVT_M3_M=1 NR2D8BWP_LVT_M3_Nf=2
.param INVD4BWP_LVT_m0_L=40e-9 INVD4BWP_LVT_m0_W=310e-9 INVD4BWP_LVT_m0_M=1 INVD4BWP_LVT_m0_Nf=1
.param INVD4BWP_LVT_m1_L=40e-9 INVD4BWP_LVT_m1_W=310e-9 INVD4BWP_LVT_m1_M=1 INVD4BWP_LVT_m1_Nf=1
.param INVD4BWP_LVT_m2_L=40e-9 INVD4BWP_LVT_m2_W=410e-9 INVD4BWP_LVT_m2_M=1 INVD4BWP_LVT_m2_Nf=1
.param INVD4BWP_LVT_m3_L=40e-9 INVD4BWP_LVT_m3_W=410e-9 INVD4BWP_LVT_m3_M=1 INVD4BWP_LVT_m3_Nf=1
.param C2_BANK_Mm17_L=40e-9 C2_BANK_Mm17_W=6e-6 C2_BANK_Mm17_M=1 C2_BANK_Mm17_Nf=12
.param C2_BANK_Mm15_L=40e-9 C2_BANK_Mm15_W=400e-9 C2_BANK_Mm15_M=1 C2_BANK_Mm15_Nf=1
.param C2_BANK_Mm13_L=40e-9 C2_BANK_Mm13_W=6e-6 C2_BANK_Mm13_M=1 C2_BANK_Mm13_Nf=12
.param C2_BANK_Mm12_L=40e-9 C2_BANK_Mm12_W=400e-9 C2_BANK_Mm12_M=1 C2_BANK_Mm12_Nf=1
.param C2_BANK_Mm10_L=40e-9 C2_BANK_Mm10_W=3e-6 C2_BANK_Mm10_M=1 C2_BANK_Mm10_Nf=6
.param C2_BANK_Mm8_L=40e-9 C2_BANK_Mm8_W=400e-9 C2_BANK_Mm8_M=1 C2_BANK_Mm8_Nf=1
.param C2_BANK_Mm20_L=40e-9 C2_BANK_Mm20_W=400e-9 C2_BANK_Mm20_M=1 C2_BANK_Mm20_Nf=1
.param C2_BANK_Mm18_L=40e-9 C2_BANK_Mm18_W=12e-6 C2_BANK_Mm18_M=1 C2_BANK_Mm18_Nf=24
.param C2_BANK_Mm23_L=40e-9 C2_BANK_Mm23_W=400e-9 C2_BANK_Mm23_M=1 C2_BANK_Mm23_Nf=1
.param C2_BANK_Mm11_L=40e-9 C2_BANK_Mm11_W=400e-9 C2_BANK_Mm11_M=1 C2_BANK_Mm11_Nf=1
.param C2_BANK_Mm6_L=40e-9 C2_BANK_Mm6_W=3e-6 C2_BANK_Mm6_M=1 C2_BANK_Mm6_Nf=6
.param C2_BANK_Mm2_L=40e-9 C2_BANK_Mm2_W=1.5e-6 C2_BANK_Mm2_M=1 C2_BANK_Mm2_Nf=3
.param C2_BANK_Mm4_L=40e-9 C2_BANK_Mm4_W=400e-9 C2_BANK_Mm4_M=1 C2_BANK_Mm4_Nf=1
.param C2_BANK_Mm5_L=40e-9 C2_BANK_Mm5_W=400e-9 C2_BANK_Mm5_M=1 C2_BANK_Mm5_Nf=1
.param C2_BANK_Mm0_L=40e-9 C2_BANK_Mm0_W=1.5e-6 C2_BANK_Mm0_M=1 C2_BANK_Mm0_Nf=3
.param C2_BANK_Mm22_L=40e-9 C2_BANK_Mm22_W=12e-6 C2_BANK_Mm22_M=1 C2_BANK_Mm22_Nf=24
.param C2_BANK_Mm16_L=40e-9 C2_BANK_Mm16_W=12e-6 C2_BANK_Mm16_M=1 C2_BANK_Mm16_Nf=12
.param C2_BANK_Mm14_L=40e-9 C2_BANK_Mm14_W=12e-6 C2_BANK_Mm14_M=1 C2_BANK_Mm14_Nf=12
.param C2_BANK_Mm9_L=40e-9 C2_BANK_Mm9_W=6e-6 C2_BANK_Mm9_M=1 C2_BANK_Mm9_Nf=6
.param C2_BANK_Mm7_L=40e-9 C2_BANK_Mm7_W=6e-6 C2_BANK_Mm7_M=1 C2_BANK_Mm7_Nf=6
.param C2_BANK_Mm19_L=40e-9 C2_BANK_Mm19_W=24e-6 C2_BANK_Mm19_M=1 C2_BANK_Mm19_Nf=24
.param C2_BANK_Mm1_L=40e-9 C2_BANK_Mm1_W=3e-6 C2_BANK_Mm1_M=1 C2_BANK_Mm1_Nf=3
.param C2_BANK_Mm21_L=40e-9 C2_BANK_Mm21_W=24e-6 C2_BANK_Mm21_M=1 C2_BANK_Mm21_Nf=24
.param C2_BANK_Mm3_L=40e-9 C2_BANK_Mm3_W=3e-6 C2_BANK_Mm3_M=1 C2_BANK_Mm3_Nf=3
.param C1_BANK_Mm17_L=40e-9 C1_BANK_Mm17_W=40e-6 C1_BANK_Mm17_M=1 C1_BANK_Mm17_Nf=80
.param C1_BANK_Mm15_L=40e-9 C1_BANK_Mm15_W=400e-9 C1_BANK_Mm15_M=1 C1_BANK_Mm15_Nf=1
.param C1_BANK_Mm13_L=40e-9 C1_BANK_Mm13_W=40e-6 C1_BANK_Mm13_M=1 C1_BANK_Mm13_Nf=80
.param C1_BANK_Mm12_L=40e-9 C1_BANK_Mm12_W=400e-9 C1_BANK_Mm12_M=1 C1_BANK_Mm12_Nf=1
.param C1_BANK_Mm10_L=40e-9 C1_BANK_Mm10_W=20e-6 C1_BANK_Mm10_M=1 C1_BANK_Mm10_Nf=40
.param C1_BANK_Mm8_L=40e-9 C1_BANK_Mm8_W=400e-9 C1_BANK_Mm8_M=1 C1_BANK_Mm8_Nf=1
.param C1_BANK_Mm20_L=40e-9 C1_BANK_Mm20_W=400e-9 C1_BANK_Mm20_M=1 C1_BANK_Mm20_Nf=1
.param C1_BANK_Mm18_L=40e-9 C1_BANK_Mm18_W=80e-6 C1_BANK_Mm18_M=1 C1_BANK_Mm18_Nf=160
.param C1_BANK_Mm23_L=40e-9 C1_BANK_Mm23_W=400e-9 C1_BANK_Mm23_M=1 C1_BANK_Mm23_Nf=1
.param C1_BANK_Mm11_L=40e-9 C1_BANK_Mm11_W=400e-9 C1_BANK_Mm11_M=1 C1_BANK_Mm11_Nf=1
.param C1_BANK_Mm6_L=40e-9 C1_BANK_Mm6_W=20e-6 C1_BANK_Mm6_M=1 C1_BANK_Mm6_Nf=40
.param C1_BANK_Mm2_L=40e-9 C1_BANK_Mm2_W=10e-6 C1_BANK_Mm2_M=1 C1_BANK_Mm2_Nf=20
.param C1_BANK_Mm4_L=40e-9 C1_BANK_Mm4_W=400e-9 C1_BANK_Mm4_M=1 C1_BANK_Mm4_Nf=1
.param C1_BANK_Mm5_L=40e-9 C1_BANK_Mm5_W=400e-9 C1_BANK_Mm5_M=1 C1_BANK_Mm5_Nf=1
.param C1_BANK_Mm0_L=40e-9 C1_BANK_Mm0_W=10e-6 C1_BANK_Mm0_M=1 C1_BANK_Mm0_Nf=20
.param C1_BANK_Mm22_L=40e-9 C1_BANK_Mm22_W=80e-6 C1_BANK_Mm22_M=1 C1_BANK_Mm22_Nf=160
.param C1_BANK_Mm16_L=40e-9 C1_BANK_Mm16_W=80e-6 C1_BANK_Mm16_M=1 C1_BANK_Mm16_Nf=80
.param C1_BANK_Mm14_L=40e-9 C1_BANK_Mm14_W=80e-6 C1_BANK_Mm14_M=1 C1_BANK_Mm14_Nf=80
.param C1_BANK_Mm9_L=40e-9 C1_BANK_Mm9_W=40e-6 C1_BANK_Mm9_M=1 C1_BANK_Mm9_Nf=40
.param C1_BANK_Mm7_L=40e-9 C1_BANK_Mm7_W=40e-6 C1_BANK_Mm7_M=1 C1_BANK_Mm7_Nf=40
.param C1_BANK_Mm19_L=40e-9 C1_BANK_Mm19_W=160e-6 C1_BANK_Mm19_M=1 C1_BANK_Mm19_Nf=160
.param C1_BANK_Mm1_L=40e-9 C1_BANK_Mm1_W=20e-6 C1_BANK_Mm1_M=1 C1_BANK_Mm1_Nf=20
.param C1_BANK_Mm21_L=40e-9 C1_BANK_Mm21_W=160e-6 C1_BANK_Mm21_M=1 C1_BANK_Mm21_Nf=160
.param C1_BANK_Mm3_L=40e-9 C1_BANK_Mm3_W=20e-6 C1_BANK_Mm3_M=1 C1_BANK_Mm3_Nf=20
.param DIGITAL_TOP_flat_Mm0_L=1e-6 DIGITAL_TOP_flat_Mm0_W=1.05e-6 DIGITAL_TOP_flat_Mm0_M=1 DIGITAL_TOP_flat_Mm0_Nf=1
.param DIGITAL_TOP_flat_Mm22_L=1e-6 DIGITAL_TOP_flat_Mm22_W=1.05e-6 DIGITAL_TOP_flat_Mm22_M=1 DIGITAL_TOP_flat_Mm22_Nf=1
.param DIGITAL_TOP_flat_Mm16_L=40e-9 DIGITAL_TOP_flat_Mm16_W=1.44e-6 DIGITAL_TOP_flat_Mm16_M=1 DIGITAL_TOP_flat_Mm16_Nf=4
.param DIGITAL_TOP_flat_Mm17_L=40e-9 DIGITAL_TOP_flat_Mm17_W=1.44e-6 DIGITAL_TOP_flat_Mm17_M=1 DIGITAL_TOP_flat_Mm17_Nf=4
.param DIGITAL_TOP_flat_Mm4_L=40e-9 DIGITAL_TOP_flat_Mm4_W=1.92e-6 DIGITAL_TOP_flat_Mm4_M=1 DIGITAL_TOP_flat_Mm4_Nf=4
.param DIGITAL_TOP_flat_Mm3_L=40e-9 DIGITAL_TOP_flat_Mm3_W=1.92e-6 DIGITAL_TOP_flat_Mm3_M=1 DIGITAL_TOP_flat_Mm3_Nf=4
.param DIGITAL_TOP_flat_Mm7_L=40e-9 DIGITAL_TOP_flat_Mm7_W=6.9e-6 DIGITAL_TOP_flat_Mm7_M=1 DIGITAL_TOP_flat_Mm7_Nf=15
.param DIGITAL_TOP_flat_Mm5_L=40e-9 DIGITAL_TOP_flat_Mm5_W=14.4e-6 DIGITAL_TOP_flat_Mm5_M=1 DIGITAL_TOP_flat_Mm5_Nf=15
.param DIGITAL_TOP_flat_Mm6_L=40e-9 DIGITAL_TOP_flat_Mm6_W=14.4e-6 DIGITAL_TOP_flat_Mm6_M=1 DIGITAL_TOP_flat_Mm6_Nf=15
.param DIGITAL_TOP_flat_Mm8_L=40e-9 DIGITAL_TOP_flat_Mm8_W=1.92e-6 DIGITAL_TOP_flat_Mm8_M=1 DIGITAL_TOP_flat_Mm8_Nf=4
.param DIGITAL_TOP_flat_Mm18_L=40e-9 DIGITAL_TOP_flat_Mm18_W=1.92e-6 DIGITAL_TOP_flat_Mm18_M=1 DIGITAL_TOP_flat_Mm18_Nf=4
.param DIGITAL_TOP_flat_Mm15_L=40e-9 DIGITAL_TOP_flat_Mm15_W=1.92e-6 DIGITAL_TOP_flat_Mm15_M=1 DIGITAL_TOP_flat_Mm15_Nf=4
.param DIGITAL_TOP_flat_Mm2_L=40e-9 DIGITAL_TOP_flat_Mm2_W=1.92e-6 DIGITAL_TOP_flat_Mm2_M=1 DIGITAL_TOP_flat_Mm2_Nf=4
.param DIGITAL_TOP_flat_Mm1_L=40e-9 DIGITAL_TOP_flat_Mm1_W=1.92e-6 DIGITAL_TOP_flat_Mm1_M=1 DIGITAL_TOP_flat_Mm1_Nf=4
.param DIGITAL_TOP_flat_Mm12_L=40e-9 DIGITAL_TOP_flat_Mm12_W=1.92e-6 DIGITAL_TOP_flat_Mm12_M=1 DIGITAL_TOP_flat_Mm12_Nf=4
.param DIGITAL_TOP_flat_Mm14_L=40e-9 DIGITAL_TOP_flat_Mm14_W=3.84e-6 DIGITAL_TOP_flat_Mm14_M=1 DIGITAL_TOP_flat_Mm14_Nf=8
.param DIGITAL_TOP_flat_Mm13_L=40e-9 DIGITAL_TOP_flat_Mm13_W=3.84e-6 DIGITAL_TOP_flat_Mm13_M=1 DIGITAL_TOP_flat_Mm13_Nf=8
.param wrapper_m1_L=280e-9 wrapper_m1_W=280e-9 wrapper_m1_M=1 wrapper_m1_Nf=1
.param wrapper_m0_L=280e-9 wrapper_m0_W=280e-9 wrapper_m0_M=1 wrapper_m0_Nf=1


* --- CIRCUIT DEFINITION ---
** Generated for: hspiceD
** Generated on: Mar 24 14:26:23 2020
** Design library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Design cell name: CTDSM_CORE_NEW
** Design view name: schematic


** .TEMP 25.0
** .OPTION
** +    ARTIST=2
** +    INGOLD=2
** +    PARHIER=LOCAL
** +    PSF=2
** .LIB "/usr/local/packages/tsmc_40/pdk/models/hspice/toplevel.l" top_tt

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: Gm2_v5_Practice
** View name: schematic
.subckt Gm2_v5_Practice_schematic ibias vdd vim vip vom vop vss
Mm20 vdd ibias vdd vdd pmos_lvt L={Gm2_v5_Practice_schematic_Mm20_L} W={Gm2_v5_Practice_schematic_Mm20_W} M={Gm2_v5_Practice_schematic_Mm20_M} Nf={Gm2_v5_Practice_schematic_Mm20_Nf}
Mm18 vdd ibias vdd vdd pmos_lvt L={Gm2_v5_Practice_schematic_Mm18_L} W={Gm2_v5_Practice_schematic_Mm18_W} M={Gm2_v5_Practice_schematic_Mm18_M} Nf={Gm2_v5_Practice_schematic_Mm18_Nf}
xc0 ntail2 vop cfmom_2t nr=46 lr=1e-6 w=70e-9 s=70e-9 stm=2 spm=6 multi=1 ftip=140e-9
xc1 ntail2 vom cfmom_2t nr=46 lr=1e-6 w=70e-9 s=70e-9 stm=2 spm=6 multi=1 ftip=140e-9
Mm0 ibias ibias vdd vdd pmos_rvt L={Gm2_v5_Practice_schematic_Mm0_L} W={Gm2_v5_Practice_schematic_Mm0_W} M={Gm2_v5_Practice_schematic_Mm0_M} Nf={Gm2_v5_Practice_schematic_Mm0_Nf}
Mm24 ibias ibias vdd vdd pmos_rvt L={Gm2_v5_Practice_schematic_Mm24_L} W={Gm2_v5_Practice_schematic_Mm24_W} M={Gm2_v5_Practice_schematic_Mm24_M} Nf={Gm2_v5_Practice_schematic_Mm24_Nf}
Mm23 vop ibias vdd vdd pmos_rvt L={Gm2_v5_Practice_schematic_Mm23_L} W={Gm2_v5_Practice_schematic_Mm23_W} M={Gm2_v5_Practice_schematic_Mm23_M} Nf={Gm2_v5_Practice_schematic_Mm23_Nf}
Mm14 vom ibias vdd vdd pmos_rvt L={Gm2_v5_Practice_schematic_Mm14_L} W={Gm2_v5_Practice_schematic_Mm14_W} M={Gm2_v5_Practice_schematic_Mm14_M} Nf={Gm2_v5_Practice_schematic_Mm14_Nf}
**Series configuration of R11
xr11 vom ntail2 vss rppolywo_m lr=6.6e-6 wr=400e-9 multi=1 m=1 series=9 segspace=250e-9
**End of R11

**Series configuration of R12
xr12 ntail2 vop vss rppolywo_m lr=6.6e-6 wr=400e-9 multi=1 m=1 series=9 segspace=250e-9
**End of R12

Mm22 net100 ntail2 vss vss nmos_rvt L={Gm2_v5_Practice_schematic_Mm22_L} W={Gm2_v5_Practice_schematic_Mm22_W} M={Gm2_v5_Practice_schematic_Mm22_M} Nf={Gm2_v5_Practice_schematic_Mm22_Nf}
Mm12 vss ntail2 vss vss nmos_lvt L={Gm2_v5_Practice_schematic_Mm12_L} W={Gm2_v5_Practice_schematic_Mm12_W} M={Gm2_v5_Practice_schematic_Mm12_M} Nf={Gm2_v5_Practice_schematic_Mm12_Nf}
Mm11 vss ntail2 vss vss nmos_lvt L={Gm2_v5_Practice_schematic_Mm11_L} W={Gm2_v5_Practice_schematic_Mm11_W} M={Gm2_v5_Practice_schematic_Mm11_M} Nf={Gm2_v5_Practice_schematic_Mm11_Nf}
Mm13 vop vim net100 vss nmos_lvt L={Gm2_v5_Practice_schematic_Mm13_L} W={Gm2_v5_Practice_schematic_Mm13_W} M={Gm2_v5_Practice_schematic_Mm13_M} Nf={Gm2_v5_Practice_schematic_Mm13_Nf}
Mm21 vom vip net100 vss nmos_lvt L={Gm2_v5_Practice_schematic_Mm21_L} W={Gm2_v5_Practice_schematic_Mm21_W} M={Gm2_v5_Practice_schematic_Mm21_M} Nf={Gm2_v5_Practice_schematic_Mm21_Nf}
.ends Gm2_v5_Practice_schematic
** End of subcircuit definition.


** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: Gm1_v5_Practice
** View name: schematic
.subckt Gm1_v5_Practice_schematic ibias vdd vim vip vom vop vss
Mm8 net08 ntail1 vss vss nmos_hvt L={Gm1_v5_Practice_schematic_Mm8_L} W={Gm1_v5_Practice_schematic_Mm8_W} M={Gm1_v5_Practice_schematic_Mm8_M} Nf={Gm1_v5_Practice_schematic_Mm8_Nf}
Mm2 vdd ibias vdd vdd pmos_lvt L={Gm1_v5_Practice_schematic_Mm2_L} W={Gm1_v5_Practice_schematic_Mm2_W} M={Gm1_v5_Practice_schematic_Mm2_M} Nf={Gm1_v5_Practice_schematic_Mm2_Nf}
Mm4 vdd ibias vdd vdd pmos_lvt L={Gm1_v5_Practice_schematic_Mm4_L} W={Gm1_v5_Practice_schematic_Mm4_W} M={Gm1_v5_Practice_schematic_Mm4_M} Nf={Gm1_v5_Practice_schematic_Mm4_Nf}
Mm12 ibias ibias vdd vdd pmos_lvt L={Gm1_v5_Practice_schematic_Mm12_L} W={Gm1_v5_Practice_schematic_Mm12_W} M={Gm1_v5_Practice_schematic_Mm12_M} Nf={Gm1_v5_Practice_schematic_Mm12_Nf}
Mm11 vom ibias vdd vdd pmos_lvt L={Gm1_v5_Practice_schematic_Mm11_L} W={Gm1_v5_Practice_schematic_Mm11_W} M={Gm1_v5_Practice_schematic_Mm11_M} Nf={Gm1_v5_Practice_schematic_Mm11_Nf}
Mm15 ibias ibias vdd vdd pmos_lvt L={Gm1_v5_Practice_schematic_Mm15_L} W={Gm1_v5_Practice_schematic_Mm15_W} M={Gm1_v5_Practice_schematic_Mm15_M} Nf={Gm1_v5_Practice_schematic_Mm15_Nf}
Mm14 vop ibias vdd vdd pmos_lvt L={Gm1_v5_Practice_schematic_Mm14_L} W={Gm1_v5_Practice_schematic_Mm14_W} M={Gm1_v5_Practice_schematic_Mm14_M} Nf={Gm1_v5_Practice_schematic_Mm14_Nf}
**Series configuration of R12
xr12 ntail1 vop vss rppolywo_m lr=6.6e-6 wr=400e-9 multi=1 m=1 series=9 segspace=250e-9
**End of R12

**Series configuration of R11
xr11 vom ntail1 vss rppolywo_m lr=6.6e-6 wr=400e-9 multi=1 m=1 series=9 segspace=250e-9
**End of R11

Mm3 vss ntail1 vss vss nmos_lvt L={Gm1_v5_Practice_schematic_Mm3_L} W={Gm1_v5_Practice_schematic_Mm3_W} M={Gm1_v5_Practice_schematic_Mm3_M} Nf={Gm1_v5_Practice_schematic_Mm3_Nf}
Mm0 vss ntail1 vss vss nmos_lvt L={Gm1_v5_Practice_schematic_Mm0_L} W={Gm1_v5_Practice_schematic_Mm0_W} M={Gm1_v5_Practice_schematic_Mm0_M} Nf={Gm1_v5_Practice_schematic_Mm0_Nf}
Mm26 vop vim net08 vss nmos_lvt L={Gm1_v5_Practice_schematic_Mm26_L} W={Gm1_v5_Practice_schematic_Mm26_W} M={Gm1_v5_Practice_schematic_Mm26_M} Nf={Gm1_v5_Practice_schematic_Mm26_Nf}
Mm27 vom vip net08 vss nmos_lvt L={Gm1_v5_Practice_schematic_Mm27_L} W={Gm1_v5_Practice_schematic_Mm27_W} M={Gm1_v5_Practice_schematic_Mm27_M} Nf={Gm1_v5_Practice_schematic_Mm27_Nf}
xc1 ntail1 vop cfmom_2t nr=46 lr=1e-6 w=70e-9 s=70e-9 stm=2 spm=6 multi=1 ftip=140e-9
xc0 ntail1 vom cfmom_2t nr=46 lr=1e-6 w=70e-9 s=70e-9 stm=2 spm=6 multi=1 ftip=140e-9
.ends Gm1_v5_Practice_schematic
** End of subcircuit definition.
** Library name: 2019_CTDSM_MAGICAL
** Cell name: DFCNQD2BWP_LVT
** View name: schematic
.subckt DFCNQD2BWP_LVT d cp cdn q vdd vss
M0 net63 cp vss vss nmos_lvt L={DFCNQD2BWP_LVT_M0_L} W={DFCNQD2BWP_LVT_M0_W} M={DFCNQD2BWP_LVT_M0_M} Nf={DFCNQD2BWP_LVT_M0_Nf}
Mmi4 net61 net63 vss vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi4_L} W={DFCNQD2BWP_LVT_Mmi4_W} M={DFCNQD2BWP_LVT_Mmi4_M} Nf={DFCNQD2BWP_LVT_Mmi4_Nf}
M1 net97 cdn net60 vss nmos_lvt L={DFCNQD2BWP_LVT_M1_L} W={DFCNQD2BWP_LVT_M1_W} M={DFCNQD2BWP_LVT_M1_M} Nf={DFCNQD2BWP_LVT_M1_Nf}
M2 net123 net95 vss vss nmos_lvt L={DFCNQD2BWP_LVT_M2_L} W={DFCNQD2BWP_LVT_M2_W} M={DFCNQD2BWP_LVT_M2_M} Nf={DFCNQD2BWP_LVT_M2_Nf}
Mmi29 net49 net63 net17 vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi29_L} W={DFCNQD2BWP_LVT_Mmi29_W} M={DFCNQD2BWP_LVT_Mmi29_M} Nf={DFCNQD2BWP_LVT_Mmi29_Nf}
Mmi15 net123 net81 net49 vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi15_L} W={DFCNQD2BWP_LVT_Mmi15_W} M={DFCNQD2BWP_LVT_Mmi15_M} Nf={DFCNQD2BWP_LVT_Mmi15_Nf}
M3 net60 net49 vss vss nmos_lvt L={DFCNQD2BWP_LVT_M3_L} W={DFCNQD2BWP_LVT_M3_W} M={DFCNQD2BWP_LVT_M3_M} Nf={DFCNQD2BWP_LVT_M3_Nf}
M4 net97 cdn net21 vss nmos_lvt L={DFCNQD2BWP_LVT_M4_L} W={DFCNQD2BWP_LVT_M4_W} M={DFCNQD2BWP_LVT_M4_M} Nf={DFCNQD2BWP_LVT_M4_Nf}
M5 net81 net63 vss vss nmos_lvt L={DFCNQD2BWP_LVT_M5_L} W={DFCNQD2BWP_LVT_M5_W} M={DFCNQD2BWP_LVT_M5_M} Nf={DFCNQD2BWP_LVT_M5_Nf}
Mmi5 net95 d net61 vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi5_L} W={DFCNQD2BWP_LVT_Mmi5_W} M={DFCNQD2BWP_LVT_Mmi5_M} Nf={DFCNQD2BWP_LVT_Mmi5_Nf}
Mmi49 net25 cdn vss vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi49_L} W={DFCNQD2BWP_LVT_Mmi49_W} M={DFCNQD2BWP_LVT_Mmi49_M} Nf={DFCNQD2BWP_LVT_Mmi49_Nf}
M6 net21 net49 vss vss nmos_lvt L={DFCNQD2BWP_LVT_M6_L} W={DFCNQD2BWP_LVT_M6_W} M={DFCNQD2BWP_LVT_M6_M} Nf={DFCNQD2BWP_LVT_M6_Nf}
Mmi26 net17 net97 vss vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi26_L} W={DFCNQD2BWP_LVT_Mmi26_W} M={DFCNQD2BWP_LVT_Mmi26_M} Nf={DFCNQD2BWP_LVT_Mmi26_Nf}
Mmi48 net13 net123 net25 vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi48_L} W={DFCNQD2BWP_LVT_Mmi48_W} M={DFCNQD2BWP_LVT_Mmi48_M} Nf={DFCNQD2BWP_LVT_Mmi48_Nf}
M7 q net97 vss vss nmos_lvt L={DFCNQD2BWP_LVT_M7_L} W={DFCNQD2BWP_LVT_M7_W} M={DFCNQD2BWP_LVT_M7_M} Nf={DFCNQD2BWP_LVT_M7_Nf}
M8 q net97 vss vss nmos_lvt L={DFCNQD2BWP_LVT_M8_L} W={DFCNQD2BWP_LVT_M8_W} M={DFCNQD2BWP_LVT_M8_M} Nf={DFCNQD2BWP_LVT_M8_Nf}
Mmi47 net95 net81 net13 vss nmos_lvt L={DFCNQD2BWP_LVT_Mmi47_L} W={DFCNQD2BWP_LVT_Mmi47_W} M={DFCNQD2BWP_LVT_Mmi47_M} Nf={DFCNQD2BWP_LVT_Mmi47_Nf}
Mmi33 net80 net97 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi33_L} W={DFCNQD2BWP_LVT_Mmi33_W} M={DFCNQD2BWP_LVT_Mmi33_M} Nf={DFCNQD2BWP_LVT_Mmi33_Nf}
M9 q net97 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M9_L} W={DFCNQD2BWP_LVT_M9_W} M={DFCNQD2BWP_LVT_M9_M} Nf={DFCNQD2BWP_LVT_M9_Nf}
M10 net97 net49 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M10_L} W={DFCNQD2BWP_LVT_M10_W} M={DFCNQD2BWP_LVT_M10_M} Nf={DFCNQD2BWP_LVT_M10_Nf}
Mmi43 net101 net123 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi43_L} W={DFCNQD2BWP_LVT_Mmi43_W} M={DFCNQD2BWP_LVT_Mmi43_M} Nf={DFCNQD2BWP_LVT_Mmi43_Nf}
Mmi6 net95 d net120 vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi6_L} W={DFCNQD2BWP_LVT_Mmi6_W} M={DFCNQD2BWP_LVT_Mmi6_M} Nf={DFCNQD2BWP_LVT_Mmi6_Nf}
M11 q net97 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M11_L} W={DFCNQD2BWP_LVT_M11_W} M={DFCNQD2BWP_LVT_M11_M} Nf={DFCNQD2BWP_LVT_M11_Nf}
M12 net97 net49 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M12_L} W={DFCNQD2BWP_LVT_M12_W} M={DFCNQD2BWP_LVT_M12_M} Nf={DFCNQD2BWP_LVT_M12_Nf}
M13 net97 cdn vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M13_L} W={DFCNQD2BWP_LVT_M13_W} M={DFCNQD2BWP_LVT_M13_M} Nf={DFCNQD2BWP_LVT_M13_Nf}
Mmi44 net101 cdn vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi44_L} W={DFCNQD2BWP_LVT_Mmi44_W} M={DFCNQD2BWP_LVT_Mmi44_M} Nf={DFCNQD2BWP_LVT_Mmi44_Nf}
M14 net97 cdn vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M14_L} W={DFCNQD2BWP_LVT_M14_W} M={DFCNQD2BWP_LVT_M14_M} Nf={DFCNQD2BWP_LVT_M14_Nf}
M15 net123 net95 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M15_L} W={DFCNQD2BWP_LVT_M15_W} M={DFCNQD2BWP_LVT_M15_M} Nf={DFCNQD2BWP_LVT_M15_Nf}
M16 net63 cp vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M16_L} W={DFCNQD2BWP_LVT_M16_W} M={DFCNQD2BWP_LVT_M16_M} Nf={DFCNQD2BWP_LVT_M16_Nf}
Mmi16 net123 net63 net49 vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi16_L} W={DFCNQD2BWP_LVT_Mmi16_W} M={DFCNQD2BWP_LVT_Mmi16_M} Nf={DFCNQD2BWP_LVT_Mmi16_Nf}
M17 net81 net63 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_M17_L} W={DFCNQD2BWP_LVT_M17_W} M={DFCNQD2BWP_LVT_M17_M} Nf={DFCNQD2BWP_LVT_M17_Nf}
Mmi32 net49 net81 net80 vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi32_L} W={DFCNQD2BWP_LVT_Mmi32_W} M={DFCNQD2BWP_LVT_Mmi32_M} Nf={DFCNQD2BWP_LVT_Mmi32_Nf}
Mmi45 net95 net63 net101 vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi45_L} W={DFCNQD2BWP_LVT_Mmi45_W} M={DFCNQD2BWP_LVT_Mmi45_M} Nf={DFCNQD2BWP_LVT_Mmi45_Nf}
Mmi7 net120 net81 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_Mmi7_L} W={DFCNQD2BWP_LVT_Mmi7_W} M={DFCNQD2BWP_LVT_Mmi7_M} Nf={DFCNQD2BWP_LVT_Mmi7_Nf}
.ends DFCNQD2BWP_LVT
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: C_DAC_CTDSM_DEC2016
** View name: schematic
.subckt C_DAC_CTDSM_DEC2016_schematic clkb in r3 r4 rstb vdd vss
**Series configuration of R27
xr27 r3 net10 vss rppolywo_m lr=19.92e-6 wr=1.2e-6 multi=1 m=1 series=18 segspace=250e-9
**End of R27

**Series configuration of R64
xr64 r4 in vss rppolywo_m lr=18.67e-6 wr=1.2e-6 multi=1 m=1 series=4 segspace=250e-9
**End of R64

xi94 in clkb rstb net10 vdd vss DFCNQD2BWP_LVT
.ends C_DAC_CTDSM_DEC2016_schematic
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: DFCNQD2BWP_LVT
** View name: schematic
.subckt DFCNQD2BWP_LVT_schematic d cp cdn q vdd vss
M0 net63 cp vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M0_L} W={DFCNQD2BWP_LVT_schematic_M0_W} M={DFCNQD2BWP_LVT_schematic_M0_M} Nf={DFCNQD2BWP_LVT_schematic_M0_Nf}
Mmi4 net61 net63 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi4_L} W={DFCNQD2BWP_LVT_schematic_Mmi4_W} M={DFCNQD2BWP_LVT_schematic_Mmi4_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi4_Nf}
M1 net97 cdn net60 vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M1_L} W={DFCNQD2BWP_LVT_schematic_M1_W} M={DFCNQD2BWP_LVT_schematic_M1_M} Nf={DFCNQD2BWP_LVT_schematic_M1_Nf}
M2 net123 net95 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M2_L} W={DFCNQD2BWP_LVT_schematic_M2_W} M={DFCNQD2BWP_LVT_schematic_M2_M} Nf={DFCNQD2BWP_LVT_schematic_M2_Nf}
Mmi29 net49 net63 net17 vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi29_L} W={DFCNQD2BWP_LVT_schematic_Mmi29_W} M={DFCNQD2BWP_LVT_schematic_Mmi29_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi29_Nf}
Mmi15 net123 net81 net49 vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi15_L} W={DFCNQD2BWP_LVT_schematic_Mmi15_W} M={DFCNQD2BWP_LVT_schematic_Mmi15_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi15_Nf}
M3 net60 net49 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M3_L} W={DFCNQD2BWP_LVT_schematic_M3_W} M={DFCNQD2BWP_LVT_schematic_M3_M} Nf={DFCNQD2BWP_LVT_schematic_M3_Nf}
M4 net97 cdn net21 vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M4_L} W={DFCNQD2BWP_LVT_schematic_M4_W} M={DFCNQD2BWP_LVT_schematic_M4_M} Nf={DFCNQD2BWP_LVT_schematic_M4_Nf}
M5 net81 net63 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M5_L} W={DFCNQD2BWP_LVT_schematic_M5_W} M={DFCNQD2BWP_LVT_schematic_M5_M} Nf={DFCNQD2BWP_LVT_schematic_M5_Nf}
Mmi5 net95 d net61 vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi5_L} W={DFCNQD2BWP_LVT_schematic_Mmi5_W} M={DFCNQD2BWP_LVT_schematic_Mmi5_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi5_Nf}
Mmi49 net25 cdn vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi49_L} W={DFCNQD2BWP_LVT_schematic_Mmi49_W} M={DFCNQD2BWP_LVT_schematic_Mmi49_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi49_Nf}
M6 net21 net49 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M6_L} W={DFCNQD2BWP_LVT_schematic_M6_W} M={DFCNQD2BWP_LVT_schematic_M6_M} Nf={DFCNQD2BWP_LVT_schematic_M6_Nf}
Mmi26 net17 net97 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi26_L} W={DFCNQD2BWP_LVT_schematic_Mmi26_W} M={DFCNQD2BWP_LVT_schematic_Mmi26_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi26_Nf}
Mmi48 net13 net123 net25 vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi48_L} W={DFCNQD2BWP_LVT_schematic_Mmi48_W} M={DFCNQD2BWP_LVT_schematic_Mmi48_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi48_Nf}
M7 q net97 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M7_L} W={DFCNQD2BWP_LVT_schematic_M7_W} M={DFCNQD2BWP_LVT_schematic_M7_M} Nf={DFCNQD2BWP_LVT_schematic_M7_Nf}
M8 q net97 vss vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_M8_L} W={DFCNQD2BWP_LVT_schematic_M8_W} M={DFCNQD2BWP_LVT_schematic_M8_M} Nf={DFCNQD2BWP_LVT_schematic_M8_Nf}
Mmi47 net95 net81 net13 vss nmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi47_L} W={DFCNQD2BWP_LVT_schematic_Mmi47_W} M={DFCNQD2BWP_LVT_schematic_Mmi47_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi47_Nf}
Mmi33 net80 net97 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi33_L} W={DFCNQD2BWP_LVT_schematic_Mmi33_W} M={DFCNQD2BWP_LVT_schematic_Mmi33_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi33_Nf}
M9 q net97 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M9_L} W={DFCNQD2BWP_LVT_schematic_M9_W} M={DFCNQD2BWP_LVT_schematic_M9_M} Nf={DFCNQD2BWP_LVT_schematic_M9_Nf}
M10 net97 net49 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M10_L} W={DFCNQD2BWP_LVT_schematic_M10_W} M={DFCNQD2BWP_LVT_schematic_M10_M} Nf={DFCNQD2BWP_LVT_schematic_M10_Nf}
Mmi43 net101 net123 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi43_L} W={DFCNQD2BWP_LVT_schematic_Mmi43_W} M={DFCNQD2BWP_LVT_schematic_Mmi43_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi43_Nf}
Mmi6 net95 d net120 vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi6_L} W={DFCNQD2BWP_LVT_schematic_Mmi6_W} M={DFCNQD2BWP_LVT_schematic_Mmi6_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi6_Nf}
M11 q net97 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M11_L} W={DFCNQD2BWP_LVT_schematic_M11_W} M={DFCNQD2BWP_LVT_schematic_M11_M} Nf={DFCNQD2BWP_LVT_schematic_M11_Nf}
M12 net97 net49 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M12_L} W={DFCNQD2BWP_LVT_schematic_M12_W} M={DFCNQD2BWP_LVT_schematic_M12_M} Nf={DFCNQD2BWP_LVT_schematic_M12_Nf}
M13 net97 cdn vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M13_L} W={DFCNQD2BWP_LVT_schematic_M13_W} M={DFCNQD2BWP_LVT_schematic_M13_M} Nf={DFCNQD2BWP_LVT_schematic_M13_Nf}
Mmi44 net101 cdn vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi44_L} W={DFCNQD2BWP_LVT_schematic_Mmi44_W} M={DFCNQD2BWP_LVT_schematic_Mmi44_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi44_Nf}
M14 net97 cdn vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M14_L} W={DFCNQD2BWP_LVT_schematic_M14_W} M={DFCNQD2BWP_LVT_schematic_M14_M} Nf={DFCNQD2BWP_LVT_schematic_M14_Nf}
M15 net123 net95 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M15_L} W={DFCNQD2BWP_LVT_schematic_M15_W} M={DFCNQD2BWP_LVT_schematic_M15_M} Nf={DFCNQD2BWP_LVT_schematic_M15_Nf}
M16 net63 cp vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M16_L} W={DFCNQD2BWP_LVT_schematic_M16_W} M={DFCNQD2BWP_LVT_schematic_M16_M} Nf={DFCNQD2BWP_LVT_schematic_M16_Nf}
Mmi16 net123 net63 net49 vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi16_L} W={DFCNQD2BWP_LVT_schematic_Mmi16_W} M={DFCNQD2BWP_LVT_schematic_Mmi16_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi16_Nf}
M17 net81 net63 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_M17_L} W={DFCNQD2BWP_LVT_schematic_M17_W} M={DFCNQD2BWP_LVT_schematic_M17_M} Nf={DFCNQD2BWP_LVT_schematic_M17_Nf}
Mmi32 net49 net81 net80 vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi32_L} W={DFCNQD2BWP_LVT_schematic_Mmi32_W} M={DFCNQD2BWP_LVT_schematic_Mmi32_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi32_Nf}
Mmi45 net95 net63 net101 vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi45_L} W={DFCNQD2BWP_LVT_schematic_Mmi45_W} M={DFCNQD2BWP_LVT_schematic_Mmi45_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi45_Nf}
Mmi7 net120 net81 vdd vdd pmos_lvt L={DFCNQD2BWP_LVT_schematic_Mmi7_L} W={DFCNQD2BWP_LVT_schematic_Mmi7_W} M={DFCNQD2BWP_LVT_schematic_Mmi7_M} Nf={DFCNQD2BWP_LVT_schematic_Mmi7_Nf}
.ends DFCNQD2BWP_LVT_schematic
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: myComparator_v3_CTDSM_DEC2016
** View name: schematic
.subckt myComparator_v3_CTDSM_DEC2016_schematic clk gnd outm outp vdd _net0 _net1
Mm0 gnd intern gnd gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm0_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm0_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm0_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm0_Nf}
Mm22 gnd interp gnd gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm22_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm22_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm22_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm22_Nf}
Mm16 outm crossp gnd gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm16_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm16_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm16_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm16_Nf}
Mm17 outp crossn gnd gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm17_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm17_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm17_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm17_Nf}
Mm4 crossn crossp intern gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm4_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm4_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm4_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm4_Nf}
Mm3 crossp crossn interp gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm3_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm3_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm3_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm3_Nf}
Mm7 net069 clk gnd gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm7_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm7_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm7_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm7_Nf}
Mm5 intern _net0 net069 gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm5_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm5_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm5_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm5_Nf}
Mm6 interp _net1 net069 gnd nmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm6_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm6_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm6_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm6_Nf}
Mm8 outm crossp vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm8_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm8_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm8_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm8_Nf}
Mm18 intern clk vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm18_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm18_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm18_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm18_Nf}
Mm15 outp crossn vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm15_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm15_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm15_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm15_Nf}
Mm2 interp clk vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm2_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm2_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm2_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm2_Nf}
Mm1 crossn clk vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm1_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm1_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm1_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm1_Nf}
Mm12 crossp clk vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm12_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm12_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm12_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm12_Nf}
Mm14 crossn crossp vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm14_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm14_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm14_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm14_Nf}
Mm13 crossp crossn vdd vdd pmos_lvt L={myComparator_v3_CTDSM_DEC2016_schematic_Mm13_L} W={myComparator_v3_CTDSM_DEC2016_schematic_Mm13_W} M={myComparator_v3_CTDSM_DEC2016_schematic_Mm13_M} Nf={myComparator_v3_CTDSM_DEC2016_schematic_Mm13_Nf}
.ends myComparator_v3_CTDSM_DEC2016_schematic
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL
** Cell name: NR2D8BWP_LVT_RESIZE
** View name: schematic
.subckt NR2D8BWP_LVT a1 a2 zn vdd vss
M0 zn a2 vss vss nmos_lvt L={NR2D8BWP_LVT_M0_L} W={NR2D8BWP_LVT_M0_W} M={NR2D8BWP_LVT_M0_M} Nf={NR2D8BWP_LVT_M0_Nf}
M1 zn a1 vss vss nmos_lvt L={NR2D8BWP_LVT_M1_L} W={NR2D8BWP_LVT_M1_W} M={NR2D8BWP_LVT_M1_M} Nf={NR2D8BWP_LVT_M1_Nf}
M2 net13 a2 vdd vdd pmos_lvt L={NR2D8BWP_LVT_M2_L} W={NR2D8BWP_LVT_M2_W} M={NR2D8BWP_LVT_M2_M} Nf={NR2D8BWP_LVT_M2_Nf}
M3 zn a1 net13 vdd pmos_lvt L={NR2D8BWP_LVT_M3_L} W={NR2D8BWP_LVT_M3_W} M={NR2D8BWP_LVT_M3_M} Nf={NR2D8BWP_LVT_M3_Nf}
.ends NR2D8BWP_LVT
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: SR_Latch_CTDSM_DEC2016
** View name: schematic
.subckt SR_Latch_LVT q qb r s vdd vss
xi1 r qb q vdd vss NR2D8BWP_LVT
xi0 s q qb vdd vss NR2D8BWP_LVT
.ends SR_Latch_LVT
** End of subcircuit definition.

.subckt SR_Latch_LVT_wrapper q qb r s vdd vss
x q qb r s vdd vss SR_Latch_LVT
.ends SR_Latch_LVT_wrapper

** Library name: tcbn40lpbwp
** Cell name: INVD2BWP
** View name: schematic
.subckt INVD4BWP_LVT i zn vdd vss
m0 zn i vss vss nmos_rvt L={INVD4BWP_LVT_m0_L} W={INVD4BWP_LVT_m0_W} M={INVD4BWP_LVT_m0_M} Nf={INVD4BWP_LVT_m0_Nf}
m1 zn i vss vss nmos_rvt L={INVD4BWP_LVT_m1_L} W={INVD4BWP_LVT_m1_W} M={INVD4BWP_LVT_m1_M} Nf={INVD4BWP_LVT_m1_Nf}
m2 zn i vdd vdd pmos_rvt L={INVD4BWP_LVT_m2_L} W={INVD4BWP_LVT_m2_W} M={INVD4BWP_LVT_m2_M} Nf={INVD4BWP_LVT_m2_Nf}
m3 zn i vdd vdd pmos_rvt L={INVD4BWP_LVT_m3_L} W={INVD4BWP_LVT_m3_W} M={INVD4BWP_LVT_m3_M} Nf={INVD4BWP_LVT_m3_Nf}
.ends INVD4BWP_LVT
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: C2_BANK
** View name: schematic
.subckt C2_BANK a b vss d_4_ d_3_ d_2_ d_1_ vdd
Mm17 a d_3_ net027 vss nmos_lvt L={C2_BANK_Mm17_L} W={C2_BANK_Mm17_W} M={C2_BANK_Mm17_M} Nf={C2_BANK_Mm17_Nf}
Mm15 net062 db_3_ vss vss nmos_lvt L={C2_BANK_Mm15_L} W={C2_BANK_Mm15_W} M={C2_BANK_Mm15_M} Nf={C2_BANK_Mm15_Nf}
Mm13 b d_3_ net062 vss nmos_lvt L={C2_BANK_Mm13_L} W={C2_BANK_Mm13_W} M={C2_BANK_Mm13_M} Nf={C2_BANK_Mm13_Nf}
Mm12 net027 db_3_ vss vss nmos_lvt L={C2_BANK_Mm12_L} W={C2_BANK_Mm12_W} M={C2_BANK_Mm12_M} Nf={C2_BANK_Mm12_Nf}
Mm10 b d_2_ net063 vss nmos_lvt L={C2_BANK_Mm10_L} W={C2_BANK_Mm10_W} M={C2_BANK_Mm10_M} Nf={C2_BANK_Mm10_Nf}
Mm8 net063 db_2_ vss vss nmos_lvt L={C2_BANK_Mm8_L} W={C2_BANK_Mm8_W} M={C2_BANK_Mm8_M} Nf={C2_BANK_Mm8_Nf}
Mm20 net061 db_4_ vss vss nmos_lvt L={C2_BANK_Mm20_L} W={C2_BANK_Mm20_W} M={C2_BANK_Mm20_M} Nf={C2_BANK_Mm20_Nf}
Mm18 a d_4_ net026 vss nmos_lvt L={C2_BANK_Mm18_L} W={C2_BANK_Mm18_W} M={C2_BANK_Mm18_M} Nf={C2_BANK_Mm18_Nf}
Mm23 net026 db_4_ vss vss nmos_lvt L={C2_BANK_Mm23_L} W={C2_BANK_Mm23_W} M={C2_BANK_Mm23_M} Nf={C2_BANK_Mm23_Nf}
Mm11 net028 db_2_ vss vss nmos_lvt L={C2_BANK_Mm11_L} W={C2_BANK_Mm11_W} M={C2_BANK_Mm11_M} Nf={C2_BANK_Mm11_Nf}
Mm6 a d_2_ net028 vss nmos_lvt L={C2_BANK_Mm6_L} W={C2_BANK_Mm6_W} M={C2_BANK_Mm6_M} Nf={C2_BANK_Mm6_Nf}
Mm2 b d_1_ net041 vss nmos_lvt L={C2_BANK_Mm2_L} W={C2_BANK_Mm2_W} M={C2_BANK_Mm2_M} Nf={C2_BANK_Mm2_Nf}
Mm4 net029 db_1_ vss vss nmos_lvt L={C2_BANK_Mm4_L} W={C2_BANK_Mm4_W} M={C2_BANK_Mm4_M} Nf={C2_BANK_Mm4_Nf}
Mm5 net041 db_1_ vss vss nmos_lvt L={C2_BANK_Mm5_L} W={C2_BANK_Mm5_W} M={C2_BANK_Mm5_M} Nf={C2_BANK_Mm5_Nf}
Mm0 a d_1_ net029 vss nmos_lvt L={C2_BANK_Mm0_L} W={C2_BANK_Mm0_W} M={C2_BANK_Mm0_M} Nf={C2_BANK_Mm0_Nf}
Mm22 b d_4_ net061 vss nmos_lvt L={C2_BANK_Mm22_L} W={C2_BANK_Mm22_W} M={C2_BANK_Mm22_M} Nf={C2_BANK_Mm22_Nf}
xc14 net029 net041 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc11 a b cfmom_2t nr=270 lr=21.02e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_3_ net027 net062 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_2_ net027 net062 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_1_ net027 net062 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_0_ net027 net062 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc15_1_ net028 net063 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc15_0_ net028 net063 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_7_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_6_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_5_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_4_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_3_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_2_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_1_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc17_0_ net026 net061 cfmom_2t nr=14 lr=13.6e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
Mm16 net027 db_3_ a vdd pmos_lvt L={C2_BANK_Mm16_L} W={C2_BANK_Mm16_W} M={C2_BANK_Mm16_M} Nf={C2_BANK_Mm16_Nf}
Mm14 net062 db_3_ b vdd pmos_lvt L={C2_BANK_Mm14_L} W={C2_BANK_Mm14_W} M={C2_BANK_Mm14_M} Nf={C2_BANK_Mm14_Nf}
Mm9 net063 db_2_ b vdd pmos_lvt L={C2_BANK_Mm9_L} W={C2_BANK_Mm9_W} M={C2_BANK_Mm9_M} Nf={C2_BANK_Mm9_Nf}
Mm7 net028 db_2_ a vdd pmos_lvt L={C2_BANK_Mm7_L} W={C2_BANK_Mm7_W} M={C2_BANK_Mm7_M} Nf={C2_BANK_Mm7_Nf}
Mm19 net026 db_4_ a vdd pmos_lvt L={C2_BANK_Mm19_L} W={C2_BANK_Mm19_W} M={C2_BANK_Mm19_M} Nf={C2_BANK_Mm19_Nf}
Mm1 net029 db_1_ a vdd pmos_lvt L={C2_BANK_Mm1_L} W={C2_BANK_Mm1_W} M={C2_BANK_Mm1_M} Nf={C2_BANK_Mm1_Nf}
Mm21 net061 db_4_ b vdd pmos_lvt L={C2_BANK_Mm21_L} W={C2_BANK_Mm21_W} M={C2_BANK_Mm21_M} Nf={C2_BANK_Mm21_Nf}
Mm3 net041 db_1_ b vdd pmos_lvt L={C2_BANK_Mm3_L} W={C2_BANK_Mm3_W} M={C2_BANK_Mm3_M} Nf={C2_BANK_Mm3_Nf}
xi0_4_ d_4_ db_4_ vdd vss INVD4BWP_LVT
xi0_3_ d_3_ db_3_ vdd vss INVD4BWP_LVT
xi0_2_ d_2_ db_2_ vdd vss INVD4BWP_LVT
xi0_1_ d_1_ db_1_ vdd vss INVD4BWP_LVT
.ends C2_BANK
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: C1_BANK
** View name: schematic
.subckt C1_BANK a b vss d_4_ d_3_ d_2_ d_1_ vdd
Mm17 a d_3_ net027 vss nmos_lvt L={C1_BANK_Mm17_L} W={C1_BANK_Mm17_W} M={C1_BANK_Mm17_M} Nf={C1_BANK_Mm17_Nf}
Mm15 net062 db_3_ vss vss nmos_lvt L={C1_BANK_Mm15_L} W={C1_BANK_Mm15_W} M={C1_BANK_Mm15_M} Nf={C1_BANK_Mm15_Nf}
Mm13 b d_3_ net062 vss nmos_lvt L={C1_BANK_Mm13_L} W={C1_BANK_Mm13_W} M={C1_BANK_Mm13_M} Nf={C1_BANK_Mm13_Nf}
Mm12 net027 db_3_ vss vss nmos_lvt L={C1_BANK_Mm12_L} W={C1_BANK_Mm12_W} M={C1_BANK_Mm12_M} Nf={C1_BANK_Mm12_Nf}
Mm10 b d_2_ net063 vss nmos_lvt L={C1_BANK_Mm10_L} W={C1_BANK_Mm10_W} M={C1_BANK_Mm10_M} Nf={C1_BANK_Mm10_Nf}
Mm8 net063 db_2_ vss vss nmos_lvt L={C1_BANK_Mm8_L} W={C1_BANK_Mm8_W} M={C1_BANK_Mm8_M} Nf={C1_BANK_Mm8_Nf}
Mm20 net061 db_4_ vss vss nmos_lvt L={C1_BANK_Mm20_L} W={C1_BANK_Mm20_W} M={C1_BANK_Mm20_M} Nf={C1_BANK_Mm20_Nf}
Mm18 a d_4_ net026 vss nmos_lvt L={C1_BANK_Mm18_L} W={C1_BANK_Mm18_W} M={C1_BANK_Mm18_M} Nf={C1_BANK_Mm18_Nf}
Mm23 net026 db_4_ vss vss nmos_lvt L={C1_BANK_Mm23_L} W={C1_BANK_Mm23_W} M={C1_BANK_Mm23_M} Nf={C1_BANK_Mm23_Nf}
Mm11 net028 db_2_ vss vss nmos_lvt L={C1_BANK_Mm11_L} W={C1_BANK_Mm11_W} M={C1_BANK_Mm11_M} Nf={C1_BANK_Mm11_Nf}
Mm6 a d_2_ net028 vss nmos_lvt L={C1_BANK_Mm6_L} W={C1_BANK_Mm6_W} M={C1_BANK_Mm6_M} Nf={C1_BANK_Mm6_Nf}
Mm2 b d_1_ net041 vss nmos_lvt L={C1_BANK_Mm2_L} W={C1_BANK_Mm2_W} M={C1_BANK_Mm2_M} Nf={C1_BANK_Mm2_Nf}
Mm4 net029 db_1_ vss vss nmos_lvt L={C1_BANK_Mm4_L} W={C1_BANK_Mm4_W} M={C1_BANK_Mm4_M} Nf={C1_BANK_Mm4_Nf}
Mm5 net041 db_1_ vss vss nmos_lvt L={C1_BANK_Mm5_L} W={C1_BANK_Mm5_W} M={C1_BANK_Mm5_M} Nf={C1_BANK_Mm5_Nf}
Mm0 a d_1_ net029 vss nmos_lvt L={C1_BANK_Mm0_L} W={C1_BANK_Mm0_W} M={C1_BANK_Mm0_M} Nf={C1_BANK_Mm0_Nf}
Mm22 b d_4_ net061 vss nmos_lvt L={C1_BANK_Mm22_L} W={C1_BANK_Mm22_W} M={C1_BANK_Mm22_M} Nf={C1_BANK_Mm22_Nf}
xc16_7_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_6_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_5_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_4_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_3_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_2_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_1_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc16_0_ net026 net061 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc15_3_ net027 net062 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc15_2_ net027 net062 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc15_1_ net027 net062 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc15_0_ net027 net062 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc14_1_ net028 net063 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc14_0_ net028 net063 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc13 net029 net041 cfmom_2t nr=94 lr=10e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc1_3_ a b cfmom_2t nr=210 lr=35.7e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc1_2_ a b cfmom_2t nr=210 lr=35.7e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc1_1_ a b cfmom_2t nr=210 lr=35.7e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc1_0_ a b cfmom_2t nr=210 lr=35.7e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
Mm16 net027 db_3_ a vdd pmos_lvt L={C1_BANK_Mm16_L} W={C1_BANK_Mm16_W} M={C1_BANK_Mm16_M} Nf={C1_BANK_Mm16_Nf}
Mm14 net062 db_3_ b vdd pmos_lvt L={C1_BANK_Mm14_L} W={C1_BANK_Mm14_W} M={C1_BANK_Mm14_M} Nf={C1_BANK_Mm14_Nf}
Mm9 net063 db_2_ b vdd pmos_lvt L={C1_BANK_Mm9_L} W={C1_BANK_Mm9_W} M={C1_BANK_Mm9_M} Nf={C1_BANK_Mm9_Nf}
Mm7 net028 db_2_ a vdd pmos_lvt L={C1_BANK_Mm7_L} W={C1_BANK_Mm7_W} M={C1_BANK_Mm7_M} Nf={C1_BANK_Mm7_Nf}
Mm19 net026 db_4_ a vdd pmos_lvt L={C1_BANK_Mm19_L} W={C1_BANK_Mm19_W} M={C1_BANK_Mm19_M} Nf={C1_BANK_Mm19_Nf}
Mm1 net029 db_1_ a vdd pmos_lvt L={C1_BANK_Mm1_L} W={C1_BANK_Mm1_W} M={C1_BANK_Mm1_M} Nf={C1_BANK_Mm1_Nf}
Mm21 net061 db_4_ b vdd pmos_lvt L={C1_BANK_Mm21_L} W={C1_BANK_Mm21_W} M={C1_BANK_Mm21_M} Nf={C1_BANK_Mm21_Nf}
Mm3 net041 db_1_ b vdd pmos_lvt L={C1_BANK_Mm3_L} W={C1_BANK_Mm3_W} M={C1_BANK_Mm3_M} Nf={C1_BANK_Mm3_Nf}
xi0_4_ d_4_ db_4_ vdd vss INVD4BWP_LVT
xi0_3_ d_3_ db_3_ vdd vss INVD4BWP_LVT
xi0_2_ d_2_ db_2_ vdd vss INVD4BWP_LVT
xi0_1_ d_1_ db_1_ vdd vss INVD4BWP_LVT
.ends C1_BANK
** End of subcircuit definition.

** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: FIR_DAC_CTDSM_DEC2016
** View name: schematic
** End of subcircuit definition.

.subckt DIGITAL_TOP clk vssd vddd vo3p vo3m outm outp
xi146 clk vss net072 net071 vddd vo3p vo3m myComparator_v3_CTDSM_DEC2016_schematic
xi128 outm outp net072 net071 vddd vssd SR_Latch_LVT
.ends DIGITAL_TOP


.subckt DIGITAL_TOP_flat clk vssd vddd vo3p vo3m outm outp
xi128 outm outp net072 net071 vddd vssd SR_Latch_LVT
Mm0 vssd intern vssd vssd nmos_lvt L={DIGITAL_TOP_flat_Mm0_L} W={DIGITAL_TOP_flat_Mm0_W} M={DIGITAL_TOP_flat_Mm0_M} Nf={DIGITAL_TOP_flat_Mm0_Nf}
Mm22 vssd interp vssd vssd nmos_lvt L={DIGITAL_TOP_flat_Mm22_L} W={DIGITAL_TOP_flat_Mm22_W} M={DIGITAL_TOP_flat_Mm22_M} Nf={DIGITAL_TOP_flat_Mm22_Nf}
Mm16 net072 crossp vssd vssd nmos_lvt L={DIGITAL_TOP_flat_Mm16_L} W={DIGITAL_TOP_flat_Mm16_W} M={DIGITAL_TOP_flat_Mm16_M} Nf={DIGITAL_TOP_flat_Mm16_Nf}
Mm17 net071 crossn vssd vssd nmos_lvt L={DIGITAL_TOP_flat_Mm17_L} W={DIGITAL_TOP_flat_Mm17_W} M={DIGITAL_TOP_flat_Mm17_M} Nf={DIGITAL_TOP_flat_Mm17_Nf}
Mm4 crossn crossp intern vssd nmos_lvt L={DIGITAL_TOP_flat_Mm4_L} W={DIGITAL_TOP_flat_Mm4_W} M={DIGITAL_TOP_flat_Mm4_M} Nf={DIGITAL_TOP_flat_Mm4_Nf}
Mm3 crossp crossn interp vssd nmos_lvt L={DIGITAL_TOP_flat_Mm3_L} W={DIGITAL_TOP_flat_Mm3_W} M={DIGITAL_TOP_flat_Mm3_M} Nf={DIGITAL_TOP_flat_Mm3_Nf}
Mm7 net069 clk vssd vssd nmos_lvt L={DIGITAL_TOP_flat_Mm7_L} W={DIGITAL_TOP_flat_Mm7_W} M={DIGITAL_TOP_flat_Mm7_M} Nf={DIGITAL_TOP_flat_Mm7_Nf}
Mm5 intern vo3p net069 vssd nmos_lvt L={DIGITAL_TOP_flat_Mm5_L} W={DIGITAL_TOP_flat_Mm5_W} M={DIGITAL_TOP_flat_Mm5_M} Nf={DIGITAL_TOP_flat_Mm5_Nf}
Mm6 interp vo3m net069 vssd nmos_lvt L={DIGITAL_TOP_flat_Mm6_L} W={DIGITAL_TOP_flat_Mm6_W} M={DIGITAL_TOP_flat_Mm6_M} Nf={DIGITAL_TOP_flat_Mm6_Nf}
Mm8 net072 crossp vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm8_L} W={DIGITAL_TOP_flat_Mm8_W} M={DIGITAL_TOP_flat_Mm8_M} Nf={DIGITAL_TOP_flat_Mm8_Nf}
Mm18 intern clk vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm18_L} W={DIGITAL_TOP_flat_Mm18_W} M={DIGITAL_TOP_flat_Mm18_M} Nf={DIGITAL_TOP_flat_Mm18_Nf}
Mm15 net071 crossn vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm15_L} W={DIGITAL_TOP_flat_Mm15_W} M={DIGITAL_TOP_flat_Mm15_M} Nf={DIGITAL_TOP_flat_Mm15_Nf}
Mm2 interp clk vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm2_L} W={DIGITAL_TOP_flat_Mm2_W} M={DIGITAL_TOP_flat_Mm2_M} Nf={DIGITAL_TOP_flat_Mm2_Nf}
Mm1 crossn clk vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm1_L} W={DIGITAL_TOP_flat_Mm1_W} M={DIGITAL_TOP_flat_Mm1_M} Nf={DIGITAL_TOP_flat_Mm1_Nf}
Mm12 crossp clk vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm12_L} W={DIGITAL_TOP_flat_Mm12_W} M={DIGITAL_TOP_flat_Mm12_M} Nf={DIGITAL_TOP_flat_Mm12_Nf}
Mm14 crossn crossp vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm14_L} W={DIGITAL_TOP_flat_Mm14_W} M={DIGITAL_TOP_flat_Mm14_M} Nf={DIGITAL_TOP_flat_Mm14_Nf}
Mm13 crossp crossn vddd vddd pmos_lvt L={DIGITAL_TOP_flat_Mm13_L} W={DIGITAL_TOP_flat_Mm13_W} M={DIGITAL_TOP_flat_Mm13_M} Nf={DIGITAL_TOP_flat_Mm13_Nf}
.ends DIGITAL_TOP_flat


.subckt INPUT_RES vss vi vo
xr16 vi vo vss rppolywo_m lr=19.92e-6 wr=1.2e-6 multi=1 m=1 para=2 segspace=250e-9
.ends INPUT_RES

.subckt wrapper vss clkb1 clkb2
m1 vss clkb2 vss vss nmos_rvt L={wrapper_m1_L} W={wrapper_m1_W} M={wrapper_m1_M} Nf={wrapper_m1_Nf}
m0 vss clkb1 vss vss nmos_rvt L={wrapper_m0_L} W={wrapper_m0_W} M={wrapper_m0_M} Nf={wrapper_m0_Nf}
.ends wrapper

.subckt DAC3 clkb in r3 r4 rstb vdd vss out
xr27 r3 net10 vss rppolywo_m lr=19.92e-6 wr=1.2e-6 multi=1 m=1 series=18 segspace=250e-9
xr64 r4 in vss rppolywo_m lr=18.67e-6 wr=1.2e-6 multi=1 m=1 series=4 segspace=250e-9
xi94 in clkb rstb net10 vdd vss DFCNQD2BWP_LVT
xi97 out clkb rstb in vdd vss DFCNQD2BWP_LVT
.ends DAC3

.subckt DAC1 clk in r1 r2 rstb vdd vss out
xr19 net3 r1 vss rppolywo_m lr=19.92e-6 wr=1.2e-6 multi=1 m=1 series=1 segspace=250e-9
xr48 in r2 vss rppolywo_m lr=19.92e-6 wr=1.2e-6 multi=1 m=1 series=1 segspace=250e-9
xi86 in clk rstb net3 vdd vss DFCNQD2BWP_LVT
xi88 out clk rstb in vdd vss DFCNQD2BWP_LVT
.ends DAC1

.subckt CAP2_RES2 vo2m vo2p vss
xc0 net074 net073 cfmom_2t nr=210 lr=34e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xr51 vo2m net073 vss rppolywo_m lr=19.92e-6 wr=1.2e-6 multi=1 m=1 para=5 segspace=250e-9
xr25 vo2p net074 vss rppolywo_m lr=19.92e-6 wr=1.2e-6 multi=1 m=1 para=5 segspace=250e-9
.ends CAP2_RES2

.subckt CAP1 vo1p vo1m
xc1_3_ vo1p vo1m cfmom_2t nr=260 lr=36e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc1_2_ vo1p vo1m cfmom_2t nr=260 lr=36e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc1_1_ vo1p vo1m cfmom_2t nr=260 lr=36e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
xc1_0_ vo1p vo1m cfmom_2t nr=260 lr=36e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
.ends CAP1

** End of subcircuit definition.
** Library name: 2019_CTDSM_MAGICAL_TAPEOUT
** Cell name: CTDSM_CORE_NEW
** View name: schematic
.subckt CTDSM_CORE_NEW_schematic clk clkb1 clkb2 ibias1 ibias2 outm outp rstb vdda vim vip vssa vddd vssd vo1m vo1p vo2m vo2p vo3m vo3p
ota2 ibias2 vdda vo2m vo2p vo3p vo3m vssa Gm2_v5_Practice_schematic
ota1 ibias1 vdda vo1m vo1p vo2p vo2m vssa Gm1_v5_Practice_schematic
dac3b clkb2 net063 vo3p vo3m rstb vdda vssa outm DAC3
dac3a clkb1 net062 vo3m vo3p rstb vdda vssa outp DAC3
digital0 clk vssd vddd vo3p vo3m outm outp DIGITAL_TOP_flat
** xi168 vo3p vo3m vss d3_4_ d3_3_ d3_2_ d3_1_ vdda C2_BANK
** xi167 net074 net073 vss d2_4_ d2_3_ d2_2_ d2_1_ vdda C2_BANK
** xi166 vo1p vo1m vss d1_4_ d1_3_ d1_2_ d1_1_ vdda C1_BANK
cap1 vo1p vo1m CAP1
cap2_res2 vo2m vo2p vssa CAP2_RES2
cap3 vo3p vo3m cfmom_2t nr=220 lr=34e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9
dac1b clk net051 vo1m vo1m rstb vdda vssa net063 DAC1
dac1a clk net052 vo1p vo1p rstb vdda vssa net062 DAC1
w1 vssa clkb1 clkb2 wrapper
input_resp vssa vip vo1p INPUT_RES
input_resm vssa vim vo1m INPUT_RES
.ends CTDSM_CORE_NEW_schematic
** End of subcircuit definition.
** .END
