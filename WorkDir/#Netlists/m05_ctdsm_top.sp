* ============================================================
* Circuit : ctdsm_top
* Source  : MAGICAL analog layout examples
* File    : MAGICALexamples/CTDSM_TOP.sp
* ============================================================
* Stats:
*   Subcircuits  : 12
*   Devices (M)  : 139
*   Device types : nmos_hvt nmos_lvt pmos_hvt pmos_lvt
*   Passives     : 25 resistors, 16 capacitors
* Note: Converted from Spectre/HSPICE format to ALIGN SPICE format.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param INVD4BWP_LVT_M0_L=80e-9 INVD4BWP_LVT_M0_W=620e-9 INVD4BWP_LVT_M0_M=1 INVD4BWP_LVT_M0_Nf=1
.param INVD4BWP_LVT_M1_L=80e-9 INVD4BWP_LVT_M1_W=620e-9 INVD4BWP_LVT_M1_M=1 INVD4BWP_LVT_M1_Nf=1
.param INVD4BWP_LVT_M2_L=80e-9 INVD4BWP_LVT_M2_W=620e-9 INVD4BWP_LVT_M2_M=1 INVD4BWP_LVT_M2_Nf=1
.param INVD4BWP_LVT_M3_L=80e-9 INVD4BWP_LVT_M3_W=620e-9 INVD4BWP_LVT_M3_M=1 INVD4BWP_LVT_M3_Nf=1
.param INVD4BWP_LVT_M4_L=80e-9 INVD4BWP_LVT_M4_W=820e-9 INVD4BWP_LVT_M4_M=1 INVD4BWP_LVT_M4_Nf=1
.param INVD4BWP_LVT_M5_L=80e-9 INVD4BWP_LVT_M5_W=820e-9 INVD4BWP_LVT_M5_M=1 INVD4BWP_LVT_M5_Nf=1
.param INVD4BWP_LVT_M6_L=80e-9 INVD4BWP_LVT_M6_W=820e-9 INVD4BWP_LVT_M6_M=1 INVD4BWP_LVT_M6_Nf=1
.param INVD4BWP_LVT_M7_L=80e-9 INVD4BWP_LVT_M7_W=820e-9 INVD4BWP_LVT_M7_M=1 INVD4BWP_LVT_M7_Nf=1
.param DFCND4BWP_LVT_stupid_M0_L=80e-9 DFCND4BWP_LVT_stupid_M0_W=820e-9 DFCND4BWP_LVT_stupid_M0_M=1 DFCND4BWP_LVT_stupid_M0_Nf=1
.param DFCND4BWP_LVT_stupid_M1_L=80e-9 DFCND4BWP_LVT_stupid_M1_W=820e-9 DFCND4BWP_LVT_stupid_M1_M=1 DFCND4BWP_LVT_stupid_M1_Nf=1
.param DFCND4BWP_LVT_stupid_M2_L=80e-9 DFCND4BWP_LVT_stupid_M2_W=820e-9 DFCND4BWP_LVT_stupid_M2_M=1 DFCND4BWP_LVT_stupid_M2_Nf=1
.param DFCND4BWP_LVT_stupid_M3_L=80e-9 DFCND4BWP_LVT_stupid_M3_W=820e-9 DFCND4BWP_LVT_stupid_M3_M=1 DFCND4BWP_LVT_stupid_M3_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi43_L=80e-9 DFCND4BWP_LVT_stupid_Mmi43_W=240e-9 DFCND4BWP_LVT_stupid_Mmi43_M=1 DFCND4BWP_LVT_stupid_Mmi43_Nf=1
.param DFCND4BWP_LVT_stupid_M4_L=80e-9 DFCND4BWP_LVT_stupid_M4_W=820e-9 DFCND4BWP_LVT_stupid_M4_M=1 DFCND4BWP_LVT_stupid_M4_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi6_L=80e-9 DFCND4BWP_LVT_stupid_Mmi6_W=680e-9 DFCND4BWP_LVT_stupid_Mmi6_M=1 DFCND4BWP_LVT_stupid_Mmi6_Nf=1
.param DFCND4BWP_LVT_stupid_M5_L=80e-9 DFCND4BWP_LVT_stupid_M5_W=820e-9 DFCND4BWP_LVT_stupid_M5_M=1 DFCND4BWP_LVT_stupid_M5_Nf=1
.param DFCND4BWP_LVT_stupid_M6_L=80e-9 DFCND4BWP_LVT_stupid_M6_W=820e-9 DFCND4BWP_LVT_stupid_M6_M=1 DFCND4BWP_LVT_stupid_M6_Nf=1
.param DFCND4BWP_LVT_stupid_M7_L=80e-9 DFCND4BWP_LVT_stupid_M7_W=820e-9 DFCND4BWP_LVT_stupid_M7_M=1 DFCND4BWP_LVT_stupid_M7_Nf=1
.param DFCND4BWP_LVT_stupid_M8_L=80e-9 DFCND4BWP_LVT_stupid_M8_W=820e-9 DFCND4BWP_LVT_stupid_M8_M=1 DFCND4BWP_LVT_stupid_M8_Nf=1
.param DFCND4BWP_LVT_stupid_M9_L=80e-9 DFCND4BWP_LVT_stupid_M9_W=820e-9 DFCND4BWP_LVT_stupid_M9_M=1 DFCND4BWP_LVT_stupid_M9_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi44_L=80e-9 DFCND4BWP_LVT_stupid_Mmi44_W=240e-9 DFCND4BWP_LVT_stupid_Mmi44_M=1 DFCND4BWP_LVT_stupid_Mmi44_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi17_L=80e-9 DFCND4BWP_LVT_stupid_Mmi17_W=240e-9 DFCND4BWP_LVT_stupid_Mmi17_M=1 DFCND4BWP_LVT_stupid_Mmi17_Nf=1
.param DFCND4BWP_LVT_stupid_M10_L=80e-9 DFCND4BWP_LVT_stupid_M10_W=820e-9 DFCND4BWP_LVT_stupid_M10_M=1 DFCND4BWP_LVT_stupid_M10_Nf=1
.param DFCND4BWP_LVT_stupid_M11_L=80e-9 DFCND4BWP_LVT_stupid_M11_W=360e-9 DFCND4BWP_LVT_stupid_M11_M=1 DFCND4BWP_LVT_stupid_M11_Nf=1
.param DFCND4BWP_LVT_stupid_M12_L=80e-9 DFCND4BWP_LVT_stupid_M12_W=820e-9 DFCND4BWP_LVT_stupid_M12_M=1 DFCND4BWP_LVT_stupid_M12_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi16_L=80e-9 DFCND4BWP_LVT_stupid_Mmi16_W=360e-9 DFCND4BWP_LVT_stupid_Mmi16_M=1 DFCND4BWP_LVT_stupid_Mmi16_Nf=1
.param DFCND4BWP_LVT_stupid_M13_L=80e-9 DFCND4BWP_LVT_stupid_M13_W=560e-9 DFCND4BWP_LVT_stupid_M13_M=1 DFCND4BWP_LVT_stupid_M13_Nf=1
.param DFCND4BWP_LVT_stupid_M14_L=80e-9 DFCND4BWP_LVT_stupid_M14_W=560e-9 DFCND4BWP_LVT_stupid_M14_M=1 DFCND4BWP_LVT_stupid_M14_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi45_L=80e-9 DFCND4BWP_LVT_stupid_Mmi45_W=240e-9 DFCND4BWP_LVT_stupid_Mmi45_M=1 DFCND4BWP_LVT_stupid_Mmi45_Nf=1
.param DFCND4BWP_LVT_stupid_M15_L=80e-9 DFCND4BWP_LVT_stupid_M15_W=820e-9 DFCND4BWP_LVT_stupid_M15_M=1 DFCND4BWP_LVT_stupid_M15_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi7_L=80e-9 DFCND4BWP_LVT_stupid_Mmi7_W=680e-9 DFCND4BWP_LVT_stupid_Mmi7_M=1 DFCND4BWP_LVT_stupid_Mmi7_Nf=1
.param DFCND4BWP_LVT_stupid_M16_L=80e-9 DFCND4BWP_LVT_stupid_M16_W=620e-9 DFCND4BWP_LVT_stupid_M16_M=1 DFCND4BWP_LVT_stupid_M16_Nf=1
.param DFCND4BWP_LVT_stupid_M17_L=80e-9 DFCND4BWP_LVT_stupid_M17_W=620e-9 DFCND4BWP_LVT_stupid_M17_M=1 DFCND4BWP_LVT_stupid_M17_Nf=1
.param DFCND4BWP_LVT_stupid_M18_L=80e-9 DFCND4BWP_LVT_stupid_M18_W=620e-9 DFCND4BWP_LVT_stupid_M18_M=1 DFCND4BWP_LVT_stupid_M18_Nf=1
.param DFCND4BWP_LVT_stupid_M19_L=80e-9 DFCND4BWP_LVT_stupid_M19_W=400e-9 DFCND4BWP_LVT_stupid_M19_M=1 DFCND4BWP_LVT_stupid_M19_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi4_L=80e-9 DFCND4BWP_LVT_stupid_Mmi4_W=620e-9 DFCND4BWP_LVT_stupid_Mmi4_M=1 DFCND4BWP_LVT_stupid_Mmi4_Nf=1
.param DFCND4BWP_LVT_stupid_M20_L=80e-9 DFCND4BWP_LVT_stupid_M20_W=620e-9 DFCND4BWP_LVT_stupid_M20_M=1 DFCND4BWP_LVT_stupid_M20_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi18_L=80e-9 DFCND4BWP_LVT_stupid_Mmi18_W=240e-9 DFCND4BWP_LVT_stupid_Mmi18_M=1 DFCND4BWP_LVT_stupid_Mmi18_Nf=1
.param DFCND4BWP_LVT_stupid_M21_L=80e-9 DFCND4BWP_LVT_stupid_M21_W=300e-9 DFCND4BWP_LVT_stupid_M21_M=1 DFCND4BWP_LVT_stupid_M21_Nf=1
.param DFCND4BWP_LVT_stupid_M22_L=80e-9 DFCND4BWP_LVT_stupid_M22_W=400e-9 DFCND4BWP_LVT_stupid_M22_M=1 DFCND4BWP_LVT_stupid_M22_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi15_L=80e-9 DFCND4BWP_LVT_stupid_Mmi15_W=300e-9 DFCND4BWP_LVT_stupid_Mmi15_M=1 DFCND4BWP_LVT_stupid_Mmi15_Nf=1
.param DFCND4BWP_LVT_stupid_M23_L=80e-9 DFCND4BWP_LVT_stupid_M23_W=380e-9 DFCND4BWP_LVT_stupid_M23_M=1 DFCND4BWP_LVT_stupid_M23_Nf=1
.param DFCND4BWP_LVT_stupid_M24_L=80e-9 DFCND4BWP_LVT_stupid_M24_W=620e-9 DFCND4BWP_LVT_stupid_M24_M=1 DFCND4BWP_LVT_stupid_M24_Nf=1
.param DFCND4BWP_LVT_stupid_M25_L=80e-9 DFCND4BWP_LVT_stupid_M25_W=620e-9 DFCND4BWP_LVT_stupid_M25_M=1 DFCND4BWP_LVT_stupid_M25_Nf=1
.param DFCND4BWP_LVT_stupid_M26_L=80e-9 DFCND4BWP_LVT_stupid_M26_W=400e-9 DFCND4BWP_LVT_stupid_M26_M=1 DFCND4BWP_LVT_stupid_M26_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi5_L=80e-9 DFCND4BWP_LVT_stupid_Mmi5_W=620e-9 DFCND4BWP_LVT_stupid_Mmi5_M=1 DFCND4BWP_LVT_stupid_Mmi5_Nf=1
.param DFCND4BWP_LVT_stupid_M27_L=80e-9 DFCND4BWP_LVT_stupid_M27_W=620e-9 DFCND4BWP_LVT_stupid_M27_M=1 DFCND4BWP_LVT_stupid_M27_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi49_L=80e-9 DFCND4BWP_LVT_stupid_Mmi49_W=240e-9 DFCND4BWP_LVT_stupid_Mmi49_M=1 DFCND4BWP_LVT_stupid_Mmi49_Nf=1
.param DFCND4BWP_LVT_stupid_M28_L=80e-9 DFCND4BWP_LVT_stupid_M28_W=400e-9 DFCND4BWP_LVT_stupid_M28_M=1 DFCND4BWP_LVT_stupid_M28_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi48_L=80e-9 DFCND4BWP_LVT_stupid_Mmi48_W=240e-9 DFCND4BWP_LVT_stupid_Mmi48_M=1 DFCND4BWP_LVT_stupid_Mmi48_Nf=1
.param DFCND4BWP_LVT_stupid_M29_L=80e-9 DFCND4BWP_LVT_stupid_M29_W=620e-9 DFCND4BWP_LVT_stupid_M29_M=1 DFCND4BWP_LVT_stupid_M29_Nf=1
.param DFCND4BWP_LVT_stupid_M30_L=80e-9 DFCND4BWP_LVT_stupid_M30_W=620e-9 DFCND4BWP_LVT_stupid_M30_M=1 DFCND4BWP_LVT_stupid_M30_Nf=1
.param DFCND4BWP_LVT_stupid_M31_L=80e-9 DFCND4BWP_LVT_stupid_M31_W=620e-9 DFCND4BWP_LVT_stupid_M31_M=1 DFCND4BWP_LVT_stupid_M31_Nf=1
.param DFCND4BWP_LVT_stupid_Mmi47_L=80e-9 DFCND4BWP_LVT_stupid_Mmi47_W=240e-9 DFCND4BWP_LVT_stupid_Mmi47_M=1 DFCND4BWP_LVT_stupid_Mmi47_Nf=1
.param OTA_XT_MAGICAL_Mm29_L=120e-9 OTA_XT_MAGICAL_Mm29_W=40.5e-6 OTA_XT_MAGICAL_Mm29_M=1 OTA_XT_MAGICAL_Mm29_Nf=15
.param OTA_XT_MAGICAL_Mm5_L=120e-9 OTA_XT_MAGICAL_Mm5_W=4.8e-6 OTA_XT_MAGICAL_Mm5_M=1 OTA_XT_MAGICAL_Mm5_Nf=5
.param OTA_XT_MAGICAL_Mm30_L=120e-9 OTA_XT_MAGICAL_Mm30_W=20e-6 OTA_XT_MAGICAL_Mm30_M=1 OTA_XT_MAGICAL_Mm30_Nf=25
.param OTA_XT_MAGICAL_Mm53_L=120e-9 OTA_XT_MAGICAL_Mm53_W=7.2e-6 OTA_XT_MAGICAL_Mm53_M=1 OTA_XT_MAGICAL_Mm53_Nf=8
.param OTA_XT_MAGICAL_Mm12_L=120e-9 OTA_XT_MAGICAL_Mm12_W=7.2e-6 OTA_XT_MAGICAL_Mm12_M=1 OTA_XT_MAGICAL_Mm12_Nf=8
.param OTA_XT_MAGICAL_Mm50_L=120e-9 OTA_XT_MAGICAL_Mm50_W=9e-6 OTA_XT_MAGICAL_Mm50_M=1 OTA_XT_MAGICAL_Mm50_Nf=10
.param OTA_XT_MAGICAL_Mm49_L=120e-9 OTA_XT_MAGICAL_Mm49_W=9e-6 OTA_XT_MAGICAL_Mm49_M=1 OTA_XT_MAGICAL_Mm49_Nf=10
.param OTA_XT_MAGICAL_Mm51_L=120e-9 OTA_XT_MAGICAL_Mm51_W=4e-6 OTA_XT_MAGICAL_Mm51_M=1 OTA_XT_MAGICAL_Mm51_Nf=5
.param OTA_XT_MAGICAL_Mm47_L=120e-9 OTA_XT_MAGICAL_Mm47_W=4.8e-6 OTA_XT_MAGICAL_Mm47_M=1 OTA_XT_MAGICAL_Mm47_Nf=5
.param OTA_XT_MAGICAL_Mm38_L=120e-9 OTA_XT_MAGICAL_Mm38_W=4e-6 OTA_XT_MAGICAL_Mm38_M=1 OTA_XT_MAGICAL_Mm38_Nf=5
.param OTA_XT_MAGICAL_Mm7_L=120e-9 OTA_XT_MAGICAL_Mm7_W=36e-6 OTA_XT_MAGICAL_Mm7_M=1 OTA_XT_MAGICAL_Mm7_Nf=15
.param OTA_XT_MAGICAL_Mm43_L=120e-9 OTA_XT_MAGICAL_Mm43_W=13.5e-6 OTA_XT_MAGICAL_Mm43_M=1 OTA_XT_MAGICAL_Mm43_Nf=5
.param OTA_XT_MAGICAL_Mm10_L=120e-9 OTA_XT_MAGICAL_Mm10_W=36e-6 OTA_XT_MAGICAL_Mm10_M=1 OTA_XT_MAGICAL_Mm10_Nf=15
.param OTA_XT_MAGICAL_Mm40_L=120e-9 OTA_XT_MAGICAL_Mm40_W=13.5e-6 OTA_XT_MAGICAL_Mm40_M=1 OTA_XT_MAGICAL_Mm40_Nf=5
.param OTA_XT_MAGICAL_Mm41_L=120e-9 OTA_XT_MAGICAL_Mm41_W=14.4e-6 OTA_XT_MAGICAL_Mm41_M=1 OTA_XT_MAGICAL_Mm41_Nf=10
.param OTA_XT_MAGICAL_Mm31_L=120e-9 OTA_XT_MAGICAL_Mm31_W=4e-6 OTA_XT_MAGICAL_Mm31_M=1 OTA_XT_MAGICAL_Mm31_Nf=5
.param OTA_XT_MAGICAL_Mm57_L=120e-9 OTA_XT_MAGICAL_Mm57_W=18e-6 OTA_XT_MAGICAL_Mm57_M=1 OTA_XT_MAGICAL_Mm57_Nf=10
.param OTA_XT_MAGICAL_Mm64_L=120e-9 OTA_XT_MAGICAL_Mm64_W=9.6e-6 OTA_XT_MAGICAL_Mm64_M=1 OTA_XT_MAGICAL_Mm64_Nf=10
.param OTA_XT_MAGICAL_Mm67_L=120e-9 OTA_XT_MAGICAL_Mm67_W=28.8e-6 OTA_XT_MAGICAL_Mm67_M=1 OTA_XT_MAGICAL_Mm67_Nf=20
.param OTA_XT_MAGICAL_Mm66_L=120e-9 OTA_XT_MAGICAL_Mm66_W=9.6e-6 OTA_XT_MAGICAL_Mm66_M=1 OTA_XT_MAGICAL_Mm66_Nf=10
.param OTA_XT_MAGICAL_Mm8_L=120e-9 OTA_XT_MAGICAL_Mm8_W=12e-6 OTA_XT_MAGICAL_Mm8_M=1 OTA_XT_MAGICAL_Mm8_Nf=10
.param OTA_XT_MAGICAL_Mm61_L=120e-9 OTA_XT_MAGICAL_Mm61_W=12e-6 OTA_XT_MAGICAL_Mm61_M=1 OTA_XT_MAGICAL_Mm61_Nf=10
.param OTA_XT_MAGICAL_Mm56_L=120e-9 OTA_XT_MAGICAL_Mm56_W=18e-6 OTA_XT_MAGICAL_Mm56_M=1 OTA_XT_MAGICAL_Mm56_Nf=10
.param OTA_XT_MAGICAL_Mm9_L=120e-9 OTA_XT_MAGICAL_Mm9_W=28.8e-6 OTA_XT_MAGICAL_Mm9_M=1 OTA_XT_MAGICAL_Mm9_Nf=20
.param OTA_XT_MAGICAL_Mm58_L=120e-9 OTA_XT_MAGICAL_Mm58_W=6.4e-6 OTA_XT_MAGICAL_Mm58_M=1 OTA_XT_MAGICAL_Mm58_Nf=4
.param OTA_XT_MAGICAL_Mm63_L=120e-9 OTA_XT_MAGICAL_Mm63_W=1.07e-6 OTA_XT_MAGICAL_Mm63_M=1 OTA_XT_MAGICAL_Mm63_Nf=1
.param OTA_XT_MAGICAL_2_Mm29_L=120e-9 OTA_XT_MAGICAL_2_Mm29_W=40.5e-6 OTA_XT_MAGICAL_2_Mm29_M=1 OTA_XT_MAGICAL_2_Mm29_Nf=20
.param OTA_XT_MAGICAL_2_Mm5_L=120e-9 OTA_XT_MAGICAL_2_Mm5_W=4.8e-6 OTA_XT_MAGICAL_2_Mm5_M=1 OTA_XT_MAGICAL_2_Mm5_Nf=5
.param OTA_XT_MAGICAL_2_Mm30_L=120e-9 OTA_XT_MAGICAL_2_Mm30_W=20e-6 OTA_XT_MAGICAL_2_Mm30_M=1 OTA_XT_MAGICAL_2_Mm30_Nf=25
.param OTA_XT_MAGICAL_2_Mm53_L=120e-9 OTA_XT_MAGICAL_2_Mm53_W=7.2e-6 OTA_XT_MAGICAL_2_Mm53_M=1 OTA_XT_MAGICAL_2_Mm53_Nf=8
.param OTA_XT_MAGICAL_2_Mm12_L=120e-9 OTA_XT_MAGICAL_2_Mm12_W=7.2e-6 OTA_XT_MAGICAL_2_Mm12_M=1 OTA_XT_MAGICAL_2_Mm12_Nf=8
.param OTA_XT_MAGICAL_2_Mm50_L=120e-9 OTA_XT_MAGICAL_2_Mm50_W=9e-6 OTA_XT_MAGICAL_2_Mm50_M=1 OTA_XT_MAGICAL_2_Mm50_Nf=10
.param OTA_XT_MAGICAL_2_Mm49_L=120e-9 OTA_XT_MAGICAL_2_Mm49_W=9e-6 OTA_XT_MAGICAL_2_Mm49_M=1 OTA_XT_MAGICAL_2_Mm49_Nf=10
.param OTA_XT_MAGICAL_2_Mm51_L=120e-9 OTA_XT_MAGICAL_2_Mm51_W=4e-6 OTA_XT_MAGICAL_2_Mm51_M=1 OTA_XT_MAGICAL_2_Mm51_Nf=5
.param OTA_XT_MAGICAL_2_Mm47_L=120e-9 OTA_XT_MAGICAL_2_Mm47_W=4.8e-6 OTA_XT_MAGICAL_2_Mm47_M=1 OTA_XT_MAGICAL_2_Mm47_Nf=5
.param OTA_XT_MAGICAL_2_Mm38_L=120e-9 OTA_XT_MAGICAL_2_Mm38_W=4e-6 OTA_XT_MAGICAL_2_Mm38_M=1 OTA_XT_MAGICAL_2_Mm38_Nf=5
.param OTA_XT_MAGICAL_2_Mm7_L=120e-9 OTA_XT_MAGICAL_2_Mm7_W=36e-6 OTA_XT_MAGICAL_2_Mm7_M=1 OTA_XT_MAGICAL_2_Mm7_Nf=15
.param OTA_XT_MAGICAL_2_Mm43_L=120e-9 OTA_XT_MAGICAL_2_Mm43_W=13.5e-6 OTA_XT_MAGICAL_2_Mm43_M=1 OTA_XT_MAGICAL_2_Mm43_Nf=5
.param OTA_XT_MAGICAL_2_Mm10_L=120e-9 OTA_XT_MAGICAL_2_Mm10_W=36e-6 OTA_XT_MAGICAL_2_Mm10_M=1 OTA_XT_MAGICAL_2_Mm10_Nf=15
.param OTA_XT_MAGICAL_2_Mm40_L=120e-9 OTA_XT_MAGICAL_2_Mm40_W=13.5e-6 OTA_XT_MAGICAL_2_Mm40_M=1 OTA_XT_MAGICAL_2_Mm40_Nf=5
.param OTA_XT_MAGICAL_2_Mm41_L=120e-9 OTA_XT_MAGICAL_2_Mm41_W=14.4e-6 OTA_XT_MAGICAL_2_Mm41_M=1 OTA_XT_MAGICAL_2_Mm41_Nf=10
.param OTA_XT_MAGICAL_2_Mm31_L=120e-9 OTA_XT_MAGICAL_2_Mm31_W=4e-6 OTA_XT_MAGICAL_2_Mm31_M=1 OTA_XT_MAGICAL_2_Mm31_Nf=5
.param OTA_XT_MAGICAL_2_Mm57_L=120e-9 OTA_XT_MAGICAL_2_Mm57_W=18e-6 OTA_XT_MAGICAL_2_Mm57_M=1 OTA_XT_MAGICAL_2_Mm57_Nf=10
.param OTA_XT_MAGICAL_2_Mm64_L=120e-9 OTA_XT_MAGICAL_2_Mm64_W=9.6e-6 OTA_XT_MAGICAL_2_Mm64_M=1 OTA_XT_MAGICAL_2_Mm64_Nf=10
.param OTA_XT_MAGICAL_2_Mm67_L=120e-9 OTA_XT_MAGICAL_2_Mm67_W=28.8e-6 OTA_XT_MAGICAL_2_Mm67_M=1 OTA_XT_MAGICAL_2_Mm67_Nf=20
.param OTA_XT_MAGICAL_2_Mm66_L=120e-9 OTA_XT_MAGICAL_2_Mm66_W=9.6e-6 OTA_XT_MAGICAL_2_Mm66_M=1 OTA_XT_MAGICAL_2_Mm66_Nf=10
.param OTA_XT_MAGICAL_2_Mm8_L=120e-9 OTA_XT_MAGICAL_2_Mm8_W=12e-6 OTA_XT_MAGICAL_2_Mm8_M=1 OTA_XT_MAGICAL_2_Mm8_Nf=10
.param OTA_XT_MAGICAL_2_Mm61_L=120e-9 OTA_XT_MAGICAL_2_Mm61_W=12e-6 OTA_XT_MAGICAL_2_Mm61_M=1 OTA_XT_MAGICAL_2_Mm61_Nf=10
.param OTA_XT_MAGICAL_2_Mm56_L=120e-9 OTA_XT_MAGICAL_2_Mm56_W=18e-6 OTA_XT_MAGICAL_2_Mm56_M=1 OTA_XT_MAGICAL_2_Mm56_Nf=10
.param OTA_XT_MAGICAL_2_Mm9_L=120e-9 OTA_XT_MAGICAL_2_Mm9_W=28.8e-6 OTA_XT_MAGICAL_2_Mm9_M=1 OTA_XT_MAGICAL_2_Mm9_Nf=20
.param OTA_XT_MAGICAL_2_Mm58_L=120e-9 OTA_XT_MAGICAL_2_Mm58_W=6.4e-6 OTA_XT_MAGICAL_2_Mm58_M=1 OTA_XT_MAGICAL_2_Mm58_Nf=4
.param OTA_XT_MAGICAL_2_Mm63_L=120e-9 OTA_XT_MAGICAL_2_Mm63_W=1.07e-6 OTA_XT_MAGICAL_2_Mm63_M=1 OTA_XT_MAGICAL_2_Mm63_Nf=1
.param BUFFD4BWP_LVT_M0_L=80e-9 BUFFD4BWP_LVT_M0_W=820e-9 BUFFD4BWP_LVT_M0_M=1 BUFFD4BWP_LVT_M0_Nf=1
.param BUFFD4BWP_LVT_M1_L=80e-9 BUFFD4BWP_LVT_M1_W=820e-9 BUFFD4BWP_LVT_M1_M=1 BUFFD4BWP_LVT_M1_Nf=1
.param BUFFD4BWP_LVT_M2_L=80e-9 BUFFD4BWP_LVT_M2_W=820e-9 BUFFD4BWP_LVT_M2_M=1 BUFFD4BWP_LVT_M2_Nf=1
.param BUFFD4BWP_LVT_M3_L=80e-9 BUFFD4BWP_LVT_M3_W=820e-9 BUFFD4BWP_LVT_M3_M=1 BUFFD4BWP_LVT_M3_Nf=1
.param BUFFD4BWP_LVT_M4_L=80e-9 BUFFD4BWP_LVT_M4_W=820e-9 BUFFD4BWP_LVT_M4_M=1 BUFFD4BWP_LVT_M4_Nf=1
.param BUFFD4BWP_LVT_M5_L=80e-9 BUFFD4BWP_LVT_M5_W=820e-9 BUFFD4BWP_LVT_M5_M=1 BUFFD4BWP_LVT_M5_Nf=1
.param BUFFD4BWP_LVT_M6_L=80e-9 BUFFD4BWP_LVT_M6_W=620e-9 BUFFD4BWP_LVT_M6_M=1 BUFFD4BWP_LVT_M6_Nf=1
.param BUFFD4BWP_LVT_M7_L=80e-9 BUFFD4BWP_LVT_M7_W=620e-9 BUFFD4BWP_LVT_M7_M=1 BUFFD4BWP_LVT_M7_Nf=1
.param BUFFD4BWP_LVT_M8_L=80e-9 BUFFD4BWP_LVT_M8_W=620e-9 BUFFD4BWP_LVT_M8_M=1 BUFFD4BWP_LVT_M8_Nf=1
.param BUFFD4BWP_LVT_M9_L=80e-9 BUFFD4BWP_LVT_M9_W=620e-9 BUFFD4BWP_LVT_M9_M=1 BUFFD4BWP_LVT_M9_Nf=1
.param BUFFD4BWP_LVT_M10_L=80e-9 BUFFD4BWP_LVT_M10_W=620e-9 BUFFD4BWP_LVT_M10_M=1 BUFFD4BWP_LVT_M10_Nf=1
.param BUFFD4BWP_LVT_M11_L=80e-9 BUFFD4BWP_LVT_M11_W=620e-9 BUFFD4BWP_LVT_M11_M=1 BUFFD4BWP_LVT_M11_Nf=1
.param NR2D8BWP_LVT_M0_L=80e-9 NR2D8BWP_LVT_M0_W=6.56e-6 NR2D8BWP_LVT_M0_M=1 NR2D8BWP_LVT_M0_Nf=1
.param NR2D8BWP_LVT_M1_L=80e-9 NR2D8BWP_LVT_M1_W=6.56e-6 NR2D8BWP_LVT_M1_M=1 NR2D8BWP_LVT_M1_Nf=1
.param NR2D8BWP_LVT_M2_L=80e-9 NR2D8BWP_LVT_M2_W=4.96e-6 NR2D8BWP_LVT_M2_M=1 NR2D8BWP_LVT_M2_Nf=1
.param NR2D8BWP_LVT_M3_L=80e-9 NR2D8BWP_LVT_M3_W=4.96e-6 NR2D8BWP_LVT_M3_M=1 NR2D8BWP_LVT_M3_Nf=1
.param COMPARATOR_schematic_Mm0_L=1e-6 COMPARATOR_schematic_Mm0_W=1.05e-6 COMPARATOR_schematic_Mm0_M=1 COMPARATOR_schematic_Mm0_Nf=1
.param COMPARATOR_schematic_Mm22_L=1e-6 COMPARATOR_schematic_Mm22_W=1.05e-6 COMPARATOR_schematic_Mm22_M=1 COMPARATOR_schematic_Mm22_Nf=1
.param COMPARATOR_schematic_Mm16_L=40e-9 COMPARATOR_schematic_Mm16_W=1.44e-6 COMPARATOR_schematic_Mm16_M=1 COMPARATOR_schematic_Mm16_Nf=4
.param COMPARATOR_schematic_Mm17_L=40e-9 COMPARATOR_schematic_Mm17_W=1.44e-6 COMPARATOR_schematic_Mm17_M=1 COMPARATOR_schematic_Mm17_Nf=4
.param COMPARATOR_schematic_Mm4_L=40e-9 COMPARATOR_schematic_Mm4_W=1.92e-6 COMPARATOR_schematic_Mm4_M=1 COMPARATOR_schematic_Mm4_Nf=4
.param COMPARATOR_schematic_Mm3_L=40e-9 COMPARATOR_schematic_Mm3_W=1.92e-6 COMPARATOR_schematic_Mm3_M=1 COMPARATOR_schematic_Mm3_Nf=4
.param COMPARATOR_schematic_Mm7_L=40e-9 COMPARATOR_schematic_Mm7_W=3.68e-6 COMPARATOR_schematic_Mm7_M=1 COMPARATOR_schematic_Mm7_Nf=8
.param COMPARATOR_schematic_Mm5_L=40e-9 COMPARATOR_schematic_Mm5_W=7.68e-6 COMPARATOR_schematic_Mm5_M=1 COMPARATOR_schematic_Mm5_Nf=8
.param COMPARATOR_schematic_Mm6_L=40e-9 COMPARATOR_schematic_Mm6_W=7.68e-6 COMPARATOR_schematic_Mm6_M=1 COMPARATOR_schematic_Mm6_Nf=8
.param COMPARATOR_schematic_Mm8_L=40e-9 COMPARATOR_schematic_Mm8_W=1.92e-6 COMPARATOR_schematic_Mm8_M=1 COMPARATOR_schematic_Mm8_Nf=4
.param COMPARATOR_schematic_Mm18_L=40e-9 COMPARATOR_schematic_Mm18_W=960e-9 COMPARATOR_schematic_Mm18_M=1 COMPARATOR_schematic_Mm18_Nf=2
.param COMPARATOR_schematic_Mm15_L=40e-9 COMPARATOR_schematic_Mm15_W=1.92e-6 COMPARATOR_schematic_Mm15_M=1 COMPARATOR_schematic_Mm15_Nf=4
.param COMPARATOR_schematic_Mm2_L=40e-9 COMPARATOR_schematic_Mm2_W=960e-9 COMPARATOR_schematic_Mm2_M=1 COMPARATOR_schematic_Mm2_Nf=2
.param COMPARATOR_schematic_Mm1_L=40e-9 COMPARATOR_schematic_Mm1_W=960e-9 COMPARATOR_schematic_Mm1_M=1 COMPARATOR_schematic_Mm1_Nf=2
.param COMPARATOR_schematic_Mm12_L=40e-9 COMPARATOR_schematic_Mm12_W=960e-9 COMPARATOR_schematic_Mm12_M=1 COMPARATOR_schematic_Mm12_Nf=2
.param COMPARATOR_schematic_Mm14_L=40e-9 COMPARATOR_schematic_Mm14_W=3.84e-6 COMPARATOR_schematic_Mm14_M=1 COMPARATOR_schematic_Mm14_Nf=8
.param COMPARATOR_schematic_Mm13_L=40e-9 COMPARATOR_schematic_Mm13_W=3.84e-6 COMPARATOR_schematic_Mm13_M=1 COMPARATOR_schematic_Mm13_Nf=8


* --- CIRCUIT DEFINITION ---
** Generated for: hspiceD
** Generated on: Nov 12 20:24:11 2019
** Design library name: CTDSM_TOP
** Design cell name: CTDSM_TOP
** Design view name: schematic

.subckt INPUT_RES VINP VINN OTA1_INP OTA1_INN VSSA
xr13 OTA1_INP VINP VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=5 segspace=250e-9
xr14 VINN OTA1_INN VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=5 segspace=250e-9
.ends INPUT_RES


** .TEMP 25.0
** .OPTION
** +    ARTIST=2
** +    INGOLD=2
** +    PARHIER=LOCAL
** +    PSF=2
** .LIB "/usr/local/packages/tsmc_40/pdk/models/hspice/toplevel.l" top_tt

** Library name: STDLIB
** Cell name: INVD4BWP_LVT
** View name: schematic
** terminal mapping: I	= i
**                   ZN	= zn
**                   VDD	= vdd
**                   VSS	= vss
.subckt INVD4BWP_LVT i zn VDDA VSSA

** nch_lvt_mac Instance MU1_0-M_u2 = hspiceD device x0
M0 zn i VSSA VSSA nmos_lvt L={INVD4BWP_LVT_M0_L} W={INVD4BWP_LVT_M0_W} M={INVD4BWP_LVT_M0_M} Nf={INVD4BWP_LVT_M0_Nf}

** nch_lvt_mac Instance MU1_3-M_u2 = hspiceD device x1
M1 zn i VSSA VSSA nmos_lvt L={INVD4BWP_LVT_M1_L} W={INVD4BWP_LVT_M1_W} M={INVD4BWP_LVT_M1_M} Nf={INVD4BWP_LVT_M1_Nf}

** nch_lvt_mac Instance MU1_1-M_u2 = hspiceD device x2
M2 zn i VSSA VSSA nmos_lvt L={INVD4BWP_LVT_M2_L} W={INVD4BWP_LVT_M2_W} M={INVD4BWP_LVT_M2_M} Nf={INVD4BWP_LVT_M2_Nf}

** nch_lvt_mac Instance MU1_2-M_u2 = hspiceD device x3
M3 zn i VSSA VSSA nmos_lvt L={INVD4BWP_LVT_M3_L} W={INVD4BWP_LVT_M3_W} M={INVD4BWP_LVT_M3_M} Nf={INVD4BWP_LVT_M3_Nf}

** pch_lvt_mac Instance MU1_0-M_u3 = hspiceD device x4
M4 zn i VDDA VDDA pmos_lvt L={INVD4BWP_LVT_M4_L} W={INVD4BWP_LVT_M4_W} M={INVD4BWP_LVT_M4_M} Nf={INVD4BWP_LVT_M4_Nf}

** pch_lvt_mac Instance MU1_1-M_u3 = hspiceD device x5
M5 zn i VDDA VDDA pmos_lvt L={INVD4BWP_LVT_M5_L} W={INVD4BWP_LVT_M5_W} M={INVD4BWP_LVT_M5_M} Nf={INVD4BWP_LVT_M5_Nf}

** pch_lvt_mac Instance MU1_3-M_u3 = hspiceD device x6
M6 zn i VDDA VDDA pmos_lvt L={INVD4BWP_LVT_M6_L} W={INVD4BWP_LVT_M6_W} M={INVD4BWP_LVT_M6_M} Nf={INVD4BWP_LVT_M6_Nf}

** pch_lvt_mac Instance MU1_2-M_u3 = hspiceD device x7
M7 zn i VDDA VDDA pmos_lvt L={INVD4BWP_LVT_M7_L} W={INVD4BWP_LVT_M7_W} M={INVD4BWP_LVT_M7_M} Nf={INVD4BWP_LVT_M7_Nf}
.ends INVD4BWP_LVT
** End of subcircuit definition.

** Library name: STDLIB
** Cell name: DFCND4BWP_LVT
** View name: schematic
** terminal mapping: D	= d
**                   CP	= cp
**                   CDN	= cdn
**                   Q	= q
**                   QN	= qn
**                   VDD	= vdd
**                   VSS	= vss
.subckt DFCND4BWP_LVT_stupid d cp q qn VDDA VSSA

** pch_lvt_mac Instance MI14-M_u3 = hspiceD device x0
M0 net175 net149 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M0_L} W={DFCND4BWP_LVT_stupid_M0_W} M={DFCND4BWP_LVT_stupid_M0_M} Nf={DFCND4BWP_LVT_stupid_M0_Nf}

** pch_lvt_mac Instance MI22-M_u3 = hspiceD device x1
M1 q net149 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M1_L} W={DFCND4BWP_LVT_stupid_M1_W} M={DFCND4BWP_LVT_stupid_M1_M} Nf={DFCND4BWP_LVT_stupid_M1_Nf}

** pch_lvt_mac Instance MI28-M_u3 = hspiceD device x2
M2 qn net175 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M2_L} W={DFCND4BWP_LVT_stupid_M2_W} M={DFCND4BWP_LVT_stupid_M2_M} Nf={DFCND4BWP_LVT_stupid_M2_Nf}

** pch_lvt_mac Instance MI23-M_u3 = hspiceD device x3
M3 qn net175 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M3_L} W={DFCND4BWP_LVT_stupid_M3_W} M={DFCND4BWP_LVT_stupid_M3_M} Nf={DFCND4BWP_LVT_stupid_M3_Nf}

** pch_lvt_mac Instance MI43 = hspiceD device xmi43
Mmi43 net12 net145 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_Mmi43_L} W={DFCND4BWP_LVT_stupid_Mmi43_W} M={DFCND4BWP_LVT_stupid_Mmi43_M} Nf={DFCND4BWP_LVT_stupid_Mmi43_Nf}

** pch_lvt_mac Instance MI39-M_u3 = hspiceD device x4
M4 net95 net11 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M4_L} W={DFCND4BWP_LVT_stupid_M4_W} M={DFCND4BWP_LVT_stupid_M4_M} Nf={DFCND4BWP_LVT_stupid_M4_Nf}

** pch_lvt_mac Instance MI6 = hspiceD device xmi6
Mmi6 net9 d net1 VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_Mmi6_L} W={DFCND4BWP_LVT_stupid_Mmi6_W} M={DFCND4BWP_LVT_stupid_Mmi6_M} Nf={DFCND4BWP_LVT_stupid_Mmi6_Nf}

** pch_lvt_mac Instance MI26-M_u3 = hspiceD device x5
M5 qn net175 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M5_L} W={DFCND4BWP_LVT_stupid_M5_W} M={DFCND4BWP_LVT_stupid_M5_M} Nf={DFCND4BWP_LVT_stupid_M5_Nf}

** pch_lvt_mac Instance MI29-M_u3 = hspiceD device x6
M6 qn net175 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M6_L} W={DFCND4BWP_LVT_stupid_M6_W} M={DFCND4BWP_LVT_stupid_M6_M} Nf={DFCND4BWP_LVT_stupid_M6_Nf}

** pch_lvt_mac Instance MI31-M_u3 = hspiceD device x7
M7 net11 cp VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M7_L} W={DFCND4BWP_LVT_stupid_M7_W} M={DFCND4BWP_LVT_stupid_M7_M} Nf={DFCND4BWP_LVT_stupid_M7_Nf}

** pch_lvt_mac Instance MI27-M_u3 = hspiceD device x8
M8 q net149 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M8_L} W={DFCND4BWP_LVT_stupid_M8_W} M={DFCND4BWP_LVT_stupid_M8_M} Nf={DFCND4BWP_LVT_stupid_M8_Nf}

** pch_lvt_mac Instance MI36-M_u2 = hspiceD device x9
M9 net149 cdn VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M9_L} W={DFCND4BWP_LVT_stupid_M9_W} M={DFCND4BWP_LVT_stupid_M9_M} Nf={DFCND4BWP_LVT_stupid_M9_Nf}

** pch_lvt_mac Instance MI44 = hspiceD device xmi44
Mmi44 net12 cdn VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_Mmi44_L} W={DFCND4BWP_LVT_stupid_Mmi44_W} M={DFCND4BWP_LVT_stupid_Mmi44_M} Nf={DFCND4BWP_LVT_stupid_Mmi44_Nf}

** pch_lvt_mac Instance MI17 = hspiceD device xmi17
Mmi17 net175 net95 net24 VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_Mmi17_L} W={DFCND4BWP_LVT_stupid_Mmi17_W} M={DFCND4BWP_LVT_stupid_Mmi17_M} Nf={DFCND4BWP_LVT_stupid_Mmi17_Nf}

** pch_lvt_mac Instance MI36-M_u1 = hspiceD device x10
M10 net149 net24 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M10_L} W={DFCND4BWP_LVT_stupid_M10_W} M={DFCND4BWP_LVT_stupid_M10_M} Nf={DFCND4BWP_LVT_stupid_M10_Nf}

** pch_lvt_mac Instance MI13-M_u3 = hspiceD device x11
M11 net145 net9 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M11_L} W={DFCND4BWP_LVT_stupid_M11_W} M={DFCND4BWP_LVT_stupid_M11_M} Nf={DFCND4BWP_LVT_stupid_M11_Nf}

** pch_lvt_mac Instance MI24-M_u3 = hspiceD device x12
M12 q net149 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M12_L} W={DFCND4BWP_LVT_stupid_M12_W} M={DFCND4BWP_LVT_stupid_M12_M} Nf={DFCND4BWP_LVT_stupid_M12_Nf}

** pch_lvt_mac Instance MI16 = hspiceD device xmi16
Mmi16 net145 net11 net24 VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_Mmi16_L} W={DFCND4BWP_LVT_stupid_Mmi16_W} M={DFCND4BWP_LVT_stupid_Mmi16_M} Nf={DFCND4BWP_LVT_stupid_Mmi16_Nf}

** pch_lvt_mac Instance MI30-M_u1 = hspiceD device x13
M13 net149 net24 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M13_L} W={DFCND4BWP_LVT_stupid_M13_W} M={DFCND4BWP_LVT_stupid_M13_M} Nf={DFCND4BWP_LVT_stupid_M13_Nf}

** pch_lvt_mac Instance MI30-M_u2 = hspiceD device x14
M14 net149 cdn VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M14_L} W={DFCND4BWP_LVT_stupid_M14_W} M={DFCND4BWP_LVT_stupid_M14_M} Nf={DFCND4BWP_LVT_stupid_M14_Nf}

** pch_lvt_mac Instance MI45 = hspiceD device xmi45
Mmi45 net9 net11 net12 VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_Mmi45_L} W={DFCND4BWP_LVT_stupid_Mmi45_W} M={DFCND4BWP_LVT_stupid_Mmi45_M} Nf={DFCND4BWP_LVT_stupid_Mmi45_Nf}

** pch_lvt_mac Instance MI25-M_u3 = hspiceD device x15
M15 q net149 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_M15_L} W={DFCND4BWP_LVT_stupid_M15_W} M={DFCND4BWP_LVT_stupid_M15_M} Nf={DFCND4BWP_LVT_stupid_M15_Nf}

** pch_lvt_mac Instance MI7 = hspiceD device xmi7
Mmi7 net1 net95 VDDA VDDA pmos_lvt L={DFCND4BWP_LVT_stupid_Mmi7_L} W={DFCND4BWP_LVT_stupid_Mmi7_W} M={DFCND4BWP_LVT_stupid_Mmi7_M} Nf={DFCND4BWP_LVT_stupid_Mmi7_Nf}

** nch_lvt_mac Instance MI26-M_u2 = hspiceD device x16
M16 qn net175 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M16_L} W={DFCND4BWP_LVT_stupid_M16_W} M={DFCND4BWP_LVT_stupid_M16_M} Nf={DFCND4BWP_LVT_stupid_M16_Nf}

** nch_lvt_mac Instance MI24-M_u2 = hspiceD device x17
M17 q net149 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M17_L} W={DFCND4BWP_LVT_stupid_M17_W} M={DFCND4BWP_LVT_stupid_M17_M} Nf={DFCND4BWP_LVT_stupid_M17_Nf}

** nch_lvt_mac Instance MI29-M_u2 = hspiceD device x18
M18 qn net175 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M18_L} W={DFCND4BWP_LVT_stupid_M18_W} M={DFCND4BWP_LVT_stupid_M18_M} Nf={DFCND4BWP_LVT_stupid_M18_Nf}

** nch_lvt_mac Instance MI30-M_u4 = hspiceD device x19
M19 net169 cdn VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M19_L} W={DFCND4BWP_LVT_stupid_M19_W} M={DFCND4BWP_LVT_stupid_M19_M} Nf={DFCND4BWP_LVT_stupid_M19_Nf}

** nch_lvt_mac Instance MI4 = hspiceD device xmi4
Mmi4 net128 net11 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_Mmi4_L} W={DFCND4BWP_LVT_stupid_Mmi4_W} M={DFCND4BWP_LVT_stupid_Mmi4_M} Nf={DFCND4BWP_LVT_stupid_Mmi4_Nf}

** nch_lvt_mac Instance MI23-M_u2 = hspiceD device x20
M20 qn net175 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M20_L} W={DFCND4BWP_LVT_stupid_M20_W} M={DFCND4BWP_LVT_stupid_M20_M} Nf={DFCND4BWP_LVT_stupid_M20_Nf}

** nch_lvt_mac Instance MI18 = hspiceD device xmi18
Mmi18 net175 net11 net24 VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_Mmi18_L} W={DFCND4BWP_LVT_stupid_Mmi18_W} M={DFCND4BWP_LVT_stupid_Mmi18_M} Nf={DFCND4BWP_LVT_stupid_Mmi18_Nf}

** nch_lvt_mac Instance MI13-M_u2 = hspiceD device x21
M21 net145 net9 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M21_L} W={DFCND4BWP_LVT_stupid_M21_W} M={DFCND4BWP_LVT_stupid_M21_M} Nf={DFCND4BWP_LVT_stupid_M21_Nf}

** nch_lvt_mac Instance MI30-M_u3 = hspiceD device x22
M22 net149 net24 net169 VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M22_L} W={DFCND4BWP_LVT_stupid_M22_W} M={DFCND4BWP_LVT_stupid_M22_M} Nf={DFCND4BWP_LVT_stupid_M22_Nf}

** nch_lvt_mac Instance MI15 = hspiceD device xmi15
Mmi15 net145 net95 net24 VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_Mmi15_L} W={DFCND4BWP_LVT_stupid_Mmi15_W} M={DFCND4BWP_LVT_stupid_Mmi15_M} Nf={DFCND4BWP_LVT_stupid_Mmi15_Nf}

** nch_lvt_mac Instance MI14-M_u2 = hspiceD device x23
M23 net175 net149 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M23_L} W={DFCND4BWP_LVT_stupid_M23_W} M={DFCND4BWP_LVT_stupid_M23_M} Nf={DFCND4BWP_LVT_stupid_M23_Nf}

** nch_lvt_mac Instance MI25-M_u2 = hspiceD device x24
M24 q net149 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M24_L} W={DFCND4BWP_LVT_stupid_M24_W} M={DFCND4BWP_LVT_stupid_M24_M} Nf={DFCND4BWP_LVT_stupid_M24_Nf}

** nch_lvt_mac Instance MI39-M_u2 = hspiceD device x25
M25 net95 net11 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M25_L} W={DFCND4BWP_LVT_stupid_M25_W} M={DFCND4BWP_LVT_stupid_M25_M} Nf={DFCND4BWP_LVT_stupid_M25_Nf}

** nch_lvt_mac Instance MI36-M_u3 = hspiceD device x26
M26 net149 net24 net132 VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M26_L} W={DFCND4BWP_LVT_stupid_M26_W} M={DFCND4BWP_LVT_stupid_M26_M} Nf={DFCND4BWP_LVT_stupid_M26_Nf}

** nch_lvt_mac Instance MI5 = hspiceD device xmi5
Mmi5 net9 d net128 VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_Mmi5_L} W={DFCND4BWP_LVT_stupid_Mmi5_W} M={DFCND4BWP_LVT_stupid_Mmi5_M} Nf={DFCND4BWP_LVT_stupid_Mmi5_Nf}

** nch_lvt_mac Instance MI31-M_u2 = hspiceD device x27
M27 net11 cp VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M27_L} W={DFCND4BWP_LVT_stupid_M27_W} M={DFCND4BWP_LVT_stupid_M27_M} Nf={DFCND4BWP_LVT_stupid_M27_Nf}

** nch_lvt_mac Instance MI49 = hspiceD device xmi49
Mmi49 net112 cdn VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_Mmi49_L} W={DFCND4BWP_LVT_stupid_Mmi49_W} M={DFCND4BWP_LVT_stupid_Mmi49_M} Nf={DFCND4BWP_LVT_stupid_Mmi49_Nf}

** nch_lvt_mac Instance MI36-M_u4 = hspiceD device x28
M28 net132 cdn VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M28_L} W={DFCND4BWP_LVT_stupid_M28_W} M={DFCND4BWP_LVT_stupid_M28_M} Nf={DFCND4BWP_LVT_stupid_M28_Nf}

** nch_lvt_mac Instance MI48 = hspiceD device xmi48
Mmi48 net96 net145 net112 VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_Mmi48_L} W={DFCND4BWP_LVT_stupid_Mmi48_W} M={DFCND4BWP_LVT_stupid_Mmi48_M} Nf={DFCND4BWP_LVT_stupid_Mmi48_Nf}

** nch_lvt_mac Instance MI27-M_u2 = hspiceD device x29
M29 q net149 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M29_L} W={DFCND4BWP_LVT_stupid_M29_W} M={DFCND4BWP_LVT_stupid_M29_M} Nf={DFCND4BWP_LVT_stupid_M29_Nf}

** nch_lvt_mac Instance MI28-M_u2 = hspiceD device x30
M30 qn net175 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M30_L} W={DFCND4BWP_LVT_stupid_M30_W} M={DFCND4BWP_LVT_stupid_M30_M} Nf={DFCND4BWP_LVT_stupid_M30_Nf}

** nch_lvt_mac Instance MI22-M_u2 = hspiceD device x31
M31 q net149 VSSA VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_M31_L} W={DFCND4BWP_LVT_stupid_M31_W} M={DFCND4BWP_LVT_stupid_M31_M} Nf={DFCND4BWP_LVT_stupid_M31_Nf}

** nch_lvt_mac Instance MI47 = hspiceD device xmi47
Mmi47 net9 net95 net96 VSSA nmos_lvt L={DFCND4BWP_LVT_stupid_Mmi47_L} W={DFCND4BWP_LVT_stupid_Mmi47_W} M={DFCND4BWP_LVT_stupid_Mmi47_M} Nf={DFCND4BWP_LVT_stupid_Mmi47_Nf}
.ends DFCND4BWP_LVT_stupid
** End of subcircuit definition.

** Library name: CTDSM_TOP
** Cell name: OTA_XT_MAGICAL
** View name: schematic
** terminal mapping: GND	= gnd
**                   NCAS	= ncas
**                   VCM	= vcm
**                   VDD	= vdd
**                   VIM	= vim
**                   VIP	= vip
**                   VOM	= vom
**                   VOP	= vop
.subckt OTA_XT_MAGICAL VSSA ncas vcm VDDA vim vip vom vop

** nch_hvt_mac Instance M29 = hspiceD device xm29
Mm29 vs vcmon VSSA VSSA nmos_hvt L={OTA_XT_MAGICAL_Mm29_L} W={OTA_XT_MAGICAL_Mm29_W} M={OTA_XT_MAGICAL_Mm29_M} Nf={OTA_XT_MAGICAL_Mm29_Nf}

** nch_lvt_mac Instance M5 = hspiceD device xm5
Mm5 pcas vcm bias2 VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm5_L} W={OTA_XT_MAGICAL_Mm5_W} M={OTA_XT_MAGICAL_Mm5_M} Nf={OTA_XT_MAGICAL_Mm5_Nf}

** nch_lvt_mac Instance M30 = hspiceD device xm30
Mm30 tail1 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm30_L} W={OTA_XT_MAGICAL_Mm30_W} M={OTA_XT_MAGICAL_Mm30_M} Nf={OTA_XT_MAGICAL_Mm30_Nf}

** nch_lvt_mac Instance M53 = hspiceD device xm53
Mm53 vcmop net0108 vs2 VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm53_L} W={OTA_XT_MAGICAL_Mm53_W} M={OTA_XT_MAGICAL_Mm53_M} Nf={OTA_XT_MAGICAL_Mm53_Nf}

** nch_lvt_mac Instance M12 = hspiceD device xm12
Mm12 vcmon vcm vs2 VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm12_L} W={OTA_XT_MAGICAL_Mm12_W} M={OTA_XT_MAGICAL_Mm12_M} Nf={OTA_XT_MAGICAL_Mm12_Nf}

** nch_lvt_mac Instance M50 = hspiceD device xm50
Mm50 vo1p ncas casn VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm50_L} W={OTA_XT_MAGICAL_Mm50_W} M={OTA_XT_MAGICAL_Mm50_M} Nf={OTA_XT_MAGICAL_Mm50_Nf}

** nch_lvt_mac Instance M49 = hspiceD device xm49
Mm49 vo1m ncas casp VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm49_L} W={OTA_XT_MAGICAL_Mm49_W} M={OTA_XT_MAGICAL_Mm49_M} Nf={OTA_XT_MAGICAL_Mm49_Nf}

** nch_lvt_mac Instance M51 = hspiceD device xm51
Mm51 ncas ncas nbias_tail VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm51_L} W={OTA_XT_MAGICAL_Mm51_W} M={OTA_XT_MAGICAL_Mm51_M} Nf={OTA_XT_MAGICAL_Mm51_Nf}

** nch_lvt_mac Instance M47 = hspiceD device xm47
Mm47 nbias_tail vcm bias1 VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm47_L} W={OTA_XT_MAGICAL_Mm47_W} M={OTA_XT_MAGICAL_Mm47_M} Nf={OTA_XT_MAGICAL_Mm47_Nf}

** nch_lvt_mac Instance M38 = hspiceD device xm38
Mm38 bias1 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm38_L} W={OTA_XT_MAGICAL_Mm38_W} M={OTA_XT_MAGICAL_Mm38_M} Nf={OTA_XT_MAGICAL_Mm38_Nf}

** nch_lvt_mac Instance M7 = hspiceD device xm7
Mm7 vop vim vs VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm7_L} W={OTA_XT_MAGICAL_Mm7_W} M={OTA_XT_MAGICAL_Mm7_M} Nf={OTA_XT_MAGICAL_Mm7_Nf}

** nch_lvt_mac Instance M43 = hspiceD device xm43
Mm43 casn vim tail1 VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm43_L} W={OTA_XT_MAGICAL_Mm43_W} M={OTA_XT_MAGICAL_Mm43_M} Nf={OTA_XT_MAGICAL_Mm43_Nf}

** nch_lvt_mac Instance M10 = hspiceD device xm10
Mm10 vom vip vs VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm10_L} W={OTA_XT_MAGICAL_Mm10_W} M={OTA_XT_MAGICAL_Mm10_M} Nf={OTA_XT_MAGICAL_Mm10_Nf}

** nch_lvt_mac Instance M40 = hspiceD device xm40
Mm40 casp vip tail1 VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm40_L} W={OTA_XT_MAGICAL_Mm40_W} M={OTA_XT_MAGICAL_Mm40_M} Nf={OTA_XT_MAGICAL_Mm40_Nf}

** nch_lvt_mac Instance M41 = hspiceD device xm41
Mm41 vs2 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm41_L} W={OTA_XT_MAGICAL_Mm41_W} M={OTA_XT_MAGICAL_Mm41_M} Nf={OTA_XT_MAGICAL_Mm41_Nf}

** nch_lvt_mac Instance M31 = hspiceD device xm31
Mm31 bias2 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_Mm31_L} W={OTA_XT_MAGICAL_Mm31_W} M={OTA_XT_MAGICAL_Mm31_M} Nf={OTA_XT_MAGICAL_Mm31_Nf}

** cfmom_2t Instance C0 = hspiceD device xc0
xc0 vo1p net096 cfmom_2t nr=26 lr=1.9e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C1 = hspiceD device xc1
xc1 vo1m net096 cfmom_2t nr=26 lr=1.9e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C4 = hspiceD device xc4
xc4 vcmon vop cfmom_2t nr=36 lr=4.17e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C7 = hspiceD device xc7
xc7 net0108 vop cfmom_2t nr=18 lr=1.91e-6 w=70e-9 s=70e-9 stm=2 spm=4 multi=1 ftip=140e-9

** cfmom_2t Instance C3 = hspiceD device xc3
xc3 vcmon vom cfmom_2t nr=36 lr=4.17e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C6 = hspiceD device xc6
xc6 net0108 vom cfmom_2t nr=18 lr=1.91e-6 w=70e-9 s=70e-9 stm=2 spm=4 multi=1 ftip=140e-9
**Series configuration of R10
xr10 net0108 vom VSSA rppolywo_m lr=3.6e-6 wr=400e-9 multi=1 m=1 series=6 segspace=250e-9
**End of R10

**Series configuration of R1
xr1 vop net0108 VSSA rppolywo_m lr=3.6e-6 wr=400e-9 multi=1 m=1 series=6 segspace=250e-9
**End of R1

**Series configuration of R8
xr8 vo1m net096 VSSA rppolywo_m lr=7.86e-6 wr=400e-9 multi=1 m=1 series=10 segspace=250e-9
**End of R8

**Series configuration of R2
xr2 net096 vo1p VSSA rppolywo_m lr=7.86e-6 wr=400e-9 multi=1 m=1 series=10 segspace=250e-9
**End of R2


** pch_lvt_mac Instance M57 = hspiceD device xm57
Mm57 vo1p pcas cas2n VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm57_L} W={OTA_XT_MAGICAL_Mm57_W} M={OTA_XT_MAGICAL_Mm57_M} Nf={OTA_XT_MAGICAL_Mm57_Nf}

** pch_lvt_mac Instance M64 = hspiceD device xm64
Mm64 vcmon vcmop VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm64_L} W={OTA_XT_MAGICAL_Mm64_W} M={OTA_XT_MAGICAL_Mm64_M} Nf={OTA_XT_MAGICAL_Mm64_Nf}

** pch_lvt_mac Instance M67 = hspiceD device xm67
Mm67 vom vo1p VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm67_L} W={OTA_XT_MAGICAL_Mm67_W} M={OTA_XT_MAGICAL_Mm67_M} Nf={OTA_XT_MAGICAL_Mm67_Nf}

** pch_lvt_mac Instance M66 = hspiceD device xm66
Mm66 vcmop vcmop VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm66_L} W={OTA_XT_MAGICAL_Mm66_W} M={OTA_XT_MAGICAL_Mm66_M} Nf={OTA_XT_MAGICAL_Mm66_Nf}

** pch_lvt_mac Instance M8 = hspiceD device xm8
Mm8 cas2n net096 VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm8_L} W={OTA_XT_MAGICAL_Mm8_W} M={OTA_XT_MAGICAL_Mm8_M} Nf={OTA_XT_MAGICAL_Mm8_Nf}

** pch_lvt_mac Instance M61 = hspiceD device xm61
Mm61 cas2p net096 VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm61_L} W={OTA_XT_MAGICAL_Mm61_W} M={OTA_XT_MAGICAL_Mm61_M} Nf={OTA_XT_MAGICAL_Mm61_Nf}

** pch_lvt_mac Instance M56 = hspiceD device xm56
Mm56 vo1m pcas cas2p VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm56_L} W={OTA_XT_MAGICAL_Mm56_W} M={OTA_XT_MAGICAL_Mm56_M} Nf={OTA_XT_MAGICAL_Mm56_Nf}

** pch_lvt_mac Instance M9 = hspiceD device xm9
Mm9 vop vo1m VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm9_L} W={OTA_XT_MAGICAL_Mm9_W} M={OTA_XT_MAGICAL_Mm9_M} Nf={OTA_XT_MAGICAL_Mm9_Nf}

** pch_lvt_mac Instance M58 = hspiceD device xm58
Mm58 pcas pcas net088 VDDA pmos_lvt L={OTA_XT_MAGICAL_Mm58_L} W={OTA_XT_MAGICAL_Mm58_W} M={OTA_XT_MAGICAL_Mm58_M} Nf={OTA_XT_MAGICAL_Mm58_Nf}

** pch_hvt_mac Instance M63 = hspiceD device xm63
Mm63 net088 pcas VDDA VDDA pmos_hvt L={OTA_XT_MAGICAL_Mm63_L} W={OTA_XT_MAGICAL_Mm63_W} M={OTA_XT_MAGICAL_Mm63_M} Nf={OTA_XT_MAGICAL_Mm63_Nf}
.ends OTA_XT_MAGICAL
** End of subcircuit definition.

.subckt OTA_XT_MAGICAL_2 VSSA ncas vcm VDDA vim vip vom vop

** nch_hvt_mac Instance M29 = hspiceD device xm29
Mm29 vs vcmon VSSA VSSA nmos_hvt L={OTA_XT_MAGICAL_2_Mm29_L} W={OTA_XT_MAGICAL_2_Mm29_W} M={OTA_XT_MAGICAL_2_Mm29_M} Nf={OTA_XT_MAGICAL_2_Mm29_Nf}

** nch_lvt_mac Instance M5 = hspiceD device xm5
Mm5 pcas vcm bias2 VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm5_L} W={OTA_XT_MAGICAL_2_Mm5_W} M={OTA_XT_MAGICAL_2_Mm5_M} Nf={OTA_XT_MAGICAL_2_Mm5_Nf}

** nch_lvt_mac Instance M30 = hspiceD device xm30
Mm30 tail1 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm30_L} W={OTA_XT_MAGICAL_2_Mm30_W} M={OTA_XT_MAGICAL_2_Mm30_M} Nf={OTA_XT_MAGICAL_2_Mm30_Nf}

** nch_lvt_mac Instance M53 = hspiceD device xm53
Mm53 vcmop net0108 vs2 VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm53_L} W={OTA_XT_MAGICAL_2_Mm53_W} M={OTA_XT_MAGICAL_2_Mm53_M} Nf={OTA_XT_MAGICAL_2_Mm53_Nf}

** nch_lvt_mac Instance M12 = hspiceD device xm12
Mm12 vcmon vcm vs2 VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm12_L} W={OTA_XT_MAGICAL_2_Mm12_W} M={OTA_XT_MAGICAL_2_Mm12_M} Nf={OTA_XT_MAGICAL_2_Mm12_Nf}

** nch_lvt_mac Instance M50 = hspiceD device xm50
Mm50 vo1p ncas casn VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm50_L} W={OTA_XT_MAGICAL_2_Mm50_W} M={OTA_XT_MAGICAL_2_Mm50_M} Nf={OTA_XT_MAGICAL_2_Mm50_Nf}

** nch_lvt_mac Instance M49 = hspiceD device xm49
Mm49 vo1m ncas casp VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm49_L} W={OTA_XT_MAGICAL_2_Mm49_W} M={OTA_XT_MAGICAL_2_Mm49_M} Nf={OTA_XT_MAGICAL_2_Mm49_Nf}

** nch_lvt_mac Instance M51 = hspiceD device xm51
Mm51 ncas ncas nbias_tail VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm51_L} W={OTA_XT_MAGICAL_2_Mm51_W} M={OTA_XT_MAGICAL_2_Mm51_M} Nf={OTA_XT_MAGICAL_2_Mm51_Nf}

** nch_lvt_mac Instance M47 = hspiceD device xm47
Mm47 nbias_tail vcm bias1 VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm47_L} W={OTA_XT_MAGICAL_2_Mm47_W} M={OTA_XT_MAGICAL_2_Mm47_M} Nf={OTA_XT_MAGICAL_2_Mm47_Nf}

** nch_lvt_mac Instance M38 = hspiceD device xm38
Mm38 bias1 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm38_L} W={OTA_XT_MAGICAL_2_Mm38_W} M={OTA_XT_MAGICAL_2_Mm38_M} Nf={OTA_XT_MAGICAL_2_Mm38_Nf}

** nch_lvt_mac Instance M7 = hspiceD device xm7
Mm7 vop vim vs VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm7_L} W={OTA_XT_MAGICAL_2_Mm7_W} M={OTA_XT_MAGICAL_2_Mm7_M} Nf={OTA_XT_MAGICAL_2_Mm7_Nf}

** nch_lvt_mac Instance M43 = hspiceD device xm43
Mm43 casn vim tail1 VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm43_L} W={OTA_XT_MAGICAL_2_Mm43_W} M={OTA_XT_MAGICAL_2_Mm43_M} Nf={OTA_XT_MAGICAL_2_Mm43_Nf}

** nch_lvt_mac Instance M10 = hspiceD device xm10
Mm10 vom vip vs VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm10_L} W={OTA_XT_MAGICAL_2_Mm10_W} M={OTA_XT_MAGICAL_2_Mm10_M} Nf={OTA_XT_MAGICAL_2_Mm10_Nf}

** nch_lvt_mac Instance M40 = hspiceD device xm40
Mm40 casp vip tail1 VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm40_L} W={OTA_XT_MAGICAL_2_Mm40_W} M={OTA_XT_MAGICAL_2_Mm40_M} Nf={OTA_XT_MAGICAL_2_Mm40_Nf}

** nch_lvt_mac Instance M41 = hspiceD device xm41
Mm41 vs2 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm41_L} W={OTA_XT_MAGICAL_2_Mm41_W} M={OTA_XT_MAGICAL_2_Mm41_M} Nf={OTA_XT_MAGICAL_2_Mm41_Nf}

** nch_lvt_mac Instance M31 = hspiceD device xm31
Mm31 bias2 nbias_tail VSSA VSSA nmos_lvt L={OTA_XT_MAGICAL_2_Mm31_L} W={OTA_XT_MAGICAL_2_Mm31_W} M={OTA_XT_MAGICAL_2_Mm31_M} Nf={OTA_XT_MAGICAL_2_Mm31_Nf}

** cfmom_2t Instance C0 = hspiceD device xc0
xc0 vo1p net096 cfmom_2t nr=26 lr=1.9e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C1 = hspiceD device xc1
xc1 vo1m net096 cfmom_2t nr=26 lr=1.9e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C4 = hspiceD device xc4
xc4 vcmon vop cfmom_2t nr=36 lr=4.17e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C7 = hspiceD device xc7
xc7 net0108 vop cfmom_2t nr=18 lr=1.91e-6 w=70e-9 s=70e-9 stm=2 spm=4 multi=1 ftip=140e-9

** cfmom_2t Instance C3 = hspiceD device xc3
xc3 vcmon vom cfmom_2t nr=36 lr=4.17e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C6 = hspiceD device xc6
xc6 net0108 vom cfmom_2t nr=18 lr=1.91e-6 w=70e-9 s=70e-9 stm=2 spm=4 multi=1 ftip=140e-9
**Series configuration of R10
xr10 net0108 vom VSSA rppolywo_m lr=3.6e-6 wr=400e-9 multi=1 m=1 series=6 segspace=250e-9
**End of R10

**Series configuration of R1
xr1 vop net0108 VSSA rppolywo_m lr=3.6e-6 wr=400e-9 multi=1 m=1 series=6 segspace=250e-9
**End of R1

**Series configuration of R8
xr8 vo1m net096 VSSA rppolywo_m lr=7.86e-6 wr=400e-9 multi=1 m=1 series=10 segspace=250e-9
**End of R8

**Series configuration of R2
xr2 net096 vo1p VSSA rppolywo_m lr=7.86e-6 wr=400e-9 multi=1 m=1 series=10 segspace=250e-9
**End of R2


** pch_lvt_mac Instance M57 = hspiceD device xm57
Mm57 vo1p pcas cas2n VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm57_L} W={OTA_XT_MAGICAL_2_Mm57_W} M={OTA_XT_MAGICAL_2_Mm57_M} Nf={OTA_XT_MAGICAL_2_Mm57_Nf}

** pch_lvt_mac Instance M64 = hspiceD device xm64
Mm64 vcmon vcmop VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm64_L} W={OTA_XT_MAGICAL_2_Mm64_W} M={OTA_XT_MAGICAL_2_Mm64_M} Nf={OTA_XT_MAGICAL_2_Mm64_Nf}

** pch_lvt_mac Instance M67 = hspiceD device xm67
Mm67 vom vo1p VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm67_L} W={OTA_XT_MAGICAL_2_Mm67_W} M={OTA_XT_MAGICAL_2_Mm67_M} Nf={OTA_XT_MAGICAL_2_Mm67_Nf}

** pch_lvt_mac Instance M66 = hspiceD device xm66
Mm66 vcmop vcmop VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm66_L} W={OTA_XT_MAGICAL_2_Mm66_W} M={OTA_XT_MAGICAL_2_Mm66_M} Nf={OTA_XT_MAGICAL_2_Mm66_Nf}

** pch_lvt_mac Instance M8 = hspiceD device xm8
Mm8 cas2n net096 VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm8_L} W={OTA_XT_MAGICAL_2_Mm8_W} M={OTA_XT_MAGICAL_2_Mm8_M} Nf={OTA_XT_MAGICAL_2_Mm8_Nf}

** pch_lvt_mac Instance M61 = hspiceD device xm61
Mm61 cas2p net096 VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm61_L} W={OTA_XT_MAGICAL_2_Mm61_W} M={OTA_XT_MAGICAL_2_Mm61_M} Nf={OTA_XT_MAGICAL_2_Mm61_Nf}

** pch_lvt_mac Instance M56 = hspiceD device xm56
Mm56 vo1m pcas cas2p VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm56_L} W={OTA_XT_MAGICAL_2_Mm56_W} M={OTA_XT_MAGICAL_2_Mm56_M} Nf={OTA_XT_MAGICAL_2_Mm56_Nf}

** pch_lvt_mac Instance M9 = hspiceD device xm9
Mm9 vop vo1m VDDA VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm9_L} W={OTA_XT_MAGICAL_2_Mm9_W} M={OTA_XT_MAGICAL_2_Mm9_M} Nf={OTA_XT_MAGICAL_2_Mm9_Nf}

** pch_lvt_mac Instance M58 = hspiceD device xm58
Mm58 pcas pcas net088 VDDA pmos_lvt L={OTA_XT_MAGICAL_2_Mm58_L} W={OTA_XT_MAGICAL_2_Mm58_W} M={OTA_XT_MAGICAL_2_Mm58_M} Nf={OTA_XT_MAGICAL_2_Mm58_Nf}

** pch_hvt_mac Instance M63 = hspiceD device xm63
Mm63 net088 pcas VDDA VDDA pmos_hvt L={OTA_XT_MAGICAL_2_Mm63_L} W={OTA_XT_MAGICAL_2_Mm63_W} M={OTA_XT_MAGICAL_2_Mm63_M} Nf={OTA_XT_MAGICAL_2_Mm63_Nf}
.ends OTA_XT_MAGICAL_2

** End of subcircuit definition.


** Library name: STDLIB
** Cell name: BUFFD4BWP_LVT
** View name: schematic
** terminal mapping: I	= i
**                   Z	= z
**                   VDD	= vdd
**                   VSS	= vss
.subckt BUFFD4BWP_LVT i z VDDA VSSA

** pch_lvt_mac Instance M_u3_0-M_u3 = hspiceD device x0
M0 z net11 VDDA VDDA pmos_lvt L={BUFFD4BWP_LVT_M0_L} W={BUFFD4BWP_LVT_M0_W} M={BUFFD4BWP_LVT_M0_M} Nf={BUFFD4BWP_LVT_M0_Nf}

** pch_lvt_mac Instance M_u2_1-M_u3 = hspiceD device x1
M1 net11 i VDDA VDDA pmos_lvt L={BUFFD4BWP_LVT_M1_L} W={BUFFD4BWP_LVT_M1_W} M={BUFFD4BWP_LVT_M1_M} Nf={BUFFD4BWP_LVT_M1_Nf}

** pch_lvt_mac Instance M_u2_0-M_u3 = hspiceD device x2
M2 net11 i VDDA VDDA pmos_lvt L={BUFFD4BWP_LVT_M2_L} W={BUFFD4BWP_LVT_M2_W} M={BUFFD4BWP_LVT_M2_M} Nf={BUFFD4BWP_LVT_M2_Nf}

** pch_lvt_mac Instance M_u3_2-M_u3 = hspiceD device x3
M3 z net11 VDDA VDDA pmos_lvt L={BUFFD4BWP_LVT_M3_L} W={BUFFD4BWP_LVT_M3_W} M={BUFFD4BWP_LVT_M3_M} Nf={BUFFD4BWP_LVT_M3_Nf}

** pch_lvt_mac Instance M_u3_1-M_u3 = hspiceD device x4
M4 z net11 VDDA VDDA pmos_lvt L={BUFFD4BWP_LVT_M4_L} W={BUFFD4BWP_LVT_M4_W} M={BUFFD4BWP_LVT_M4_M} Nf={BUFFD4BWP_LVT_M4_Nf}

** pch_lvt_mac Instance M_u3_3-M_u3 = hspiceD device x5
M5 z net11 VDDA VDDA pmos_lvt L={BUFFD4BWP_LVT_M5_L} W={BUFFD4BWP_LVT_M5_W} M={BUFFD4BWP_LVT_M5_M} Nf={BUFFD4BWP_LVT_M5_Nf}

** nch_lvt_mac Instance M_u3_1-M_u2 = hspiceD device x6
M6 z net11 VSSA VSSA nmos_lvt L={BUFFD4BWP_LVT_M6_L} W={BUFFD4BWP_LVT_M6_W} M={BUFFD4BWP_LVT_M6_M} Nf={BUFFD4BWP_LVT_M6_Nf}

** nch_lvt_mac Instance M_u3_2-M_u2 = hspiceD device x7
M7 z net11 VSSA VSSA nmos_lvt L={BUFFD4BWP_LVT_M7_L} W={BUFFD4BWP_LVT_M7_W} M={BUFFD4BWP_LVT_M7_M} Nf={BUFFD4BWP_LVT_M7_Nf}

** nch_lvt_mac Instance M_u3_3-M_u2 = hspiceD device x8
M8 z net11 VSSA VSSA nmos_lvt L={BUFFD4BWP_LVT_M8_L} W={BUFFD4BWP_LVT_M8_W} M={BUFFD4BWP_LVT_M8_M} Nf={BUFFD4BWP_LVT_M8_Nf}

** nch_lvt_mac Instance M_u2_1-M_u2 = hspiceD device x9
M9 net11 i VSSA VSSA nmos_lvt L={BUFFD4BWP_LVT_M9_L} W={BUFFD4BWP_LVT_M9_W} M={BUFFD4BWP_LVT_M9_M} Nf={BUFFD4BWP_LVT_M9_Nf}

** nch_lvt_mac Instance M_u3_0-M_u2 = hspiceD device x10
M10 z net11 VSSA VSSA nmos_lvt L={BUFFD4BWP_LVT_M10_L} W={BUFFD4BWP_LVT_M10_W} M={BUFFD4BWP_LVT_M10_M} Nf={BUFFD4BWP_LVT_M10_Nf}

** nch_lvt_mac Instance M_u2_0-M_u2 = hspiceD device x11
M11 net11 i VSSA VSSA nmos_lvt L={BUFFD4BWP_LVT_M11_L} W={BUFFD4BWP_LVT_M11_W} M={BUFFD4BWP_LVT_M11_M} Nf={BUFFD4BWP_LVT_M11_Nf}
.ends BUFFD4BWP_LVT
** End of subcircuit definition.

** Library name: STDLIB
** Cell name: NR2D8BWP_LVT
** View name: schematic
** terminal mapping: A1	= a1
**                   A2	= a2
**                   ZN	= zn
**                   VDD	= vdd
**                   VSS	= vss
.subckt NR2D8BWP_LVT a1 a2 zn VDDA VSSA

** pch_lvt_mac Instance MI1-M_u1 = hspiceD device x0
M0 net13 a2 VDDA VDDA pmos_lvt L={NR2D8BWP_LVT_M0_L} W={NR2D8BWP_LVT_M0_W} M={NR2D8BWP_LVT_M0_M} Nf={NR2D8BWP_LVT_M0_Nf}

** pch_lvt_mac Instance MI1-M_u2 = hspiceD device x1
M1 zn a1 net13 VDDA pmos_lvt L={NR2D8BWP_LVT_M1_L} W={NR2D8BWP_LVT_M1_W} M={NR2D8BWP_LVT_M1_M} Nf={NR2D8BWP_LVT_M1_Nf}

** nch_lvt_mac Instance MI1-M_u3 = hspiceD device x2
M2 zn a2 VSSA VSSA nmos_lvt L={NR2D8BWP_LVT_M2_L} W={NR2D8BWP_LVT_M2_W} M={NR2D8BWP_LVT_M2_M} Nf={NR2D8BWP_LVT_M2_Nf}

** nch_lvt_mac Instance MI1-M_u4 = hspiceD device x3
M3 zn a1 VSSA VSSA nmos_lvt L={NR2D8BWP_LVT_M3_L} W={NR2D8BWP_LVT_M3_W} M={NR2D8BWP_LVT_M3_M} Nf={NR2D8BWP_LVT_M3_Nf}
.ends NR2D8BWP_LVT
** End of subcircuit definition.

** Library name: 2019_CTDSM_Mingjie
** Cell name: SR_Latch_LVT
** View name: schematic
** terminal mapping: Q	= q
**                   QB	= qb
**                   R	= r
**                   S	= s
**                   VDD	= vdd
**                   VSS	= vss
.subckt SR_Latch_LVT q qb r s VDDA VSSA

** NR2D8BWP_LVT Instance I1 = hspiceD device xi1
** Instance of Lib: STDLIB,  Cell: NR2D8BWP_LVT, View: schematic

** Port Connection: Instance  I1 of NR2D8BWP_LVT
** a1(r) a2(qb) zn(q) vdd(vdd) vss(vss)
xi1 r qb q VDDA VSSA NR2D8BWP_LVT

** NR2D8BWP_LVT Instance I0 = hspiceD device xi0
** Instance of Lib: STDLIB,  Cell: NR2D8BWP_LVT, View: schematic

** Port Connection: Instance  I0 of NR2D8BWP_LVT
** a1(s) a2(q) zn(qb) vdd(vdd) vss(vss)
xi0 s q qb VDDA VSSA NR2D8BWP_LVT
.ends SR_Latch_LVT
** End of subcircuit definition.

** Library name: CTDSM_TOP
** Cell name: COMPARATOR
** View name: schematic
** terminal mapping: CLK	= clk
**                   GND	= gnd
**                   OUTM	= outm
**                   OUTP	= outp
**                   VDD	= vdd
**                   VIP	= _net0
**                   VIM	= _net1
.subckt COMPARATOR_schematic clk VSSA outm outp VDDA _net0 _net1

** nch_lvt_mac Instance M0 = hspiceD device xm0
Mm0 VSSA intern VSSA VSSA nmos_lvt L={COMPARATOR_schematic_Mm0_L} W={COMPARATOR_schematic_Mm0_W} M={COMPARATOR_schematic_Mm0_M} Nf={COMPARATOR_schematic_Mm0_Nf}

** nch_lvt_mac Instance M22 = hspiceD device xm22
Mm22 VSSA interp VSSA VSSA nmos_lvt L={COMPARATOR_schematic_Mm22_L} W={COMPARATOR_schematic_Mm22_W} M={COMPARATOR_schematic_Mm22_M} Nf={COMPARATOR_schematic_Mm22_Nf}

** nch_lvt_mac Instance M16 = hspiceD device xm16
Mm16 outm crossp VSSA VSSA nmos_lvt L={COMPARATOR_schematic_Mm16_L} W={COMPARATOR_schematic_Mm16_W} M={COMPARATOR_schematic_Mm16_M} Nf={COMPARATOR_schematic_Mm16_Nf}

** nch_lvt_mac Instance M17 = hspiceD device xm17
Mm17 outp crossn VSSA VSSA nmos_lvt L={COMPARATOR_schematic_Mm17_L} W={COMPARATOR_schematic_Mm17_W} M={COMPARATOR_schematic_Mm17_M} Nf={COMPARATOR_schematic_Mm17_Nf}

** nch_lvt_mac Instance M4 = hspiceD device xm4
Mm4 crossn crossp intern VSSA nmos_lvt L={COMPARATOR_schematic_Mm4_L} W={COMPARATOR_schematic_Mm4_W} M={COMPARATOR_schematic_Mm4_M} Nf={COMPARATOR_schematic_Mm4_Nf}

** nch_lvt_mac Instance M3 = hspiceD device xm3
Mm3 crossp crossn interp VSSA nmos_lvt L={COMPARATOR_schematic_Mm3_L} W={COMPARATOR_schematic_Mm3_W} M={COMPARATOR_schematic_Mm3_M} Nf={COMPARATOR_schematic_Mm3_Nf}

** nch_lvt_mac Instance M7 = hspiceD device xm7
Mm7 net069 clk VSSA VSSA nmos_lvt L={COMPARATOR_schematic_Mm7_L} W={COMPARATOR_schematic_Mm7_W} M={COMPARATOR_schematic_Mm7_M} Nf={COMPARATOR_schematic_Mm7_Nf}

** nch_lvt_mac Instance M5 = hspiceD device xm5
Mm5 intern _net0 net069 VSSA nmos_lvt L={COMPARATOR_schematic_Mm5_L} W={COMPARATOR_schematic_Mm5_W} M={COMPARATOR_schematic_Mm5_M} Nf={COMPARATOR_schematic_Mm5_Nf}

** nch_lvt_mac Instance M6 = hspiceD device xm6
Mm6 interp _net1 net069 VSSA nmos_lvt L={COMPARATOR_schematic_Mm6_L} W={COMPARATOR_schematic_Mm6_W} M={COMPARATOR_schematic_Mm6_M} Nf={COMPARATOR_schematic_Mm6_Nf}

** pch_lvt_mac Instance M8 = hspiceD device xm8
Mm8 outm crossp VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm8_L} W={COMPARATOR_schematic_Mm8_W} M={COMPARATOR_schematic_Mm8_M} Nf={COMPARATOR_schematic_Mm8_Nf}

** pch_lvt_mac Instance M18 = hspiceD device xm18
Mm18 intern clk VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm18_L} W={COMPARATOR_schematic_Mm18_W} M={COMPARATOR_schematic_Mm18_M} Nf={COMPARATOR_schematic_Mm18_Nf}

** pch_lvt_mac Instance M15 = hspiceD device xm15
Mm15 outp crossn VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm15_L} W={COMPARATOR_schematic_Mm15_W} M={COMPARATOR_schematic_Mm15_M} Nf={COMPARATOR_schematic_Mm15_Nf}

** pch_lvt_mac Instance M2 = hspiceD device xm2
Mm2 interp clk VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm2_L} W={COMPARATOR_schematic_Mm2_W} M={COMPARATOR_schematic_Mm2_M} Nf={COMPARATOR_schematic_Mm2_Nf}

** pch_lvt_mac Instance M1 = hspiceD device xm1
Mm1 crossn clk VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm1_L} W={COMPARATOR_schematic_Mm1_W} M={COMPARATOR_schematic_Mm1_M} Nf={COMPARATOR_schematic_Mm1_Nf}

** pch_lvt_mac Instance M12 = hspiceD device xm12
Mm12 crossp clk VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm12_L} W={COMPARATOR_schematic_Mm12_W} M={COMPARATOR_schematic_Mm12_M} Nf={COMPARATOR_schematic_Mm12_Nf}

** pch_lvt_mac Instance M14 = hspiceD device xm14
Mm14 crossn crossp VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm14_L} W={COMPARATOR_schematic_Mm14_W} M={COMPARATOR_schematic_Mm14_M} Nf={COMPARATOR_schematic_Mm14_Nf}

** pch_lvt_mac Instance M13 = hspiceD device xm13
Mm13 crossp crossn VDDA VDDA pmos_lvt L={COMPARATOR_schematic_Mm13_L} W={COMPARATOR_schematic_Mm13_W} M={COMPARATOR_schematic_Mm13_M} Nf={COMPARATOR_schematic_Mm13_Nf}
.ends COMPARATOR_schematic
** End of subcircuit definition.

.subckt RR1 net040 net010 VREF VSSA net025 SYS_CLKB VDDA net035
xi24 net040 net010 VREF VSSA BUFFD4BWP_LVT
xi25 net025 SYS_CLKB net040 net035 VDDA VSSA DFCND4BWP_LVT_stupid
.ends RR1

.subckt RRR1 net046 SYS_CLKB VDDA DO net038 VSSA net025 net028 net020 SYS_CLK
xi12 net046 SYS_CLKB DO net038 VDDA VSSA DFCND4BWP_LVT_stupid
xi6 net046 net025 net028 net020 VDDA VSSA SR_Latch_LVT
xi4 SYS_CLK SYS_CLKB VDDA VSSA INVD4BWP_LVT
.ends RRR1

** Library name: CTDSM_TOP
** Cell name: CTDSM_TOP
** View name: schematic
.subckt CTDSM_TOP DO VSSA IBIAS1 IBIAS2 SYS_CLK VCM VDDA VINN VINP OTA1_INN OTA1_INP OTA2_INN OTA2_INP SUM_N SUM_P VINT1N VINT1P VINT2N VINT2P VREF
** terminal mapping: DO	= do
**                   GND	= gnd
**                   IBIAS1	= ibias1
**                   IBIAS2	= ibias2
**                   SYS_CLK	= sys_clk
**                   VCM	= vcm
**                   VDD	= vdd
**                   VINN	= vinn
**                   VINP	= vinp
**                   OTA1_INN	= ota1_inn
**                   OTA1_INP	= ota1_inp
**                   OTA2_INN	= ota2_inn
**                   OTA2_INP	= ota2_inp
**                   SUM_N	= sum_n
**                   SUM_P	= sum_p
**                   VINT1N	= vint1n
**                   VINT1P	= vint1p
**                   VINT2N	= vint2n
**                   VINT2P	= vint2p
**                   VREF	= vref

input_res VINP VINN OTA1_INP OTA1_INN VSSA INPUT_RES

**Series configuration of R47
xr47 OTA1_INN VINT2P VSSA rppolywo_m lr=34.8e-6 wr=400e-9 multi=1 m=1 series=46 segspace=250e-9
**End of R47

**Series configuration of R28
xr28 OTA1_INP VINT2N VSSA rppolywo_m lr=34.8e-6 wr=400e-9 multi=1 m=1 series=46 segspace=250e-9
**End of R28

**Series configuration of R21
xr21 net010 OTA1_INP VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=5 segspace=250e-9
**End of R21

**Series configuration of R20
xr20 net012 OTA1_INN VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=5 segspace=250e-9
**End of R20

**Series configuration of R23
xr23 net010 OTA2_INP VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=10 segspace=250e-9
**End of R23

**Series configuration of R25
xr25 net012 SUM_N VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=15 segspace=250e-9
**End of R25

**Series configuration of R24
xr24 net010 SUM_P VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=15 segspace=250e-9
**End of R24

**Series configuration of R22
xr22 net012 OTA2_INN VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=10 segspace=250e-9
**End of R22

xr19 VINT2N SUM_N VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=1 segspace=250e-9

**Series configuration of R16
xr16 VINT1N OTA2_INN VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=5 segspace=250e-9
**End of R16

**Series configuration of R17
xr17 VINT1P OTA2_INP VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=5 segspace=250e-9
**End of R17


xr18 VINT2P SUM_P VSSA rppolywo_m lr=10e-6 wr=600e-9 multi=1 m=1 series=1 segspace=250e-9


** INVD4BWP_LVT Instance I4 = hspiceD device xi4
** Instance of Lib: STDLIB,  Cell: INVD4BWP_LVT, View: schematic

** Port Connection: Instance  I4 of INVD4BWP_LVT
** i(sys_clk) zn(sys_clkb) vdd(vdd) vss(gnd)
**xi4 SYS_CLK SYS_CLKB VDD GND INVD4BWP_LVT

** cfmom_2t Instance C4 = hspiceD device xc4
xc4 OTA1_INP VINT1N cfmom_2t nr=96 lr=12.4e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C2 = hspiceD device xc2
xc2 OTA2_INN VINT2P cfmom_2t nr=70 lr=9.85e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C0 = hspiceD device xc0
xc0 OTA1_INN VINT1P cfmom_2t nr=96 lr=12.4e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** cfmom_2t Instance C1 = hspiceD device xc1
xc1 OTA2_INP VINT2N cfmom_2t nr=70 lr=9.85e-6 w=70e-9 s=70e-9 stm=2 spm=5 multi=1 ftip=140e-9

** DFCND4BWP_LVT Instance I12 = hspiceD device xi12
** Instance of Lib: STDLIB,  Cell: DFCND4BWP_LVT, View: schematic

** Port Connection: Instance  I12 of DFCND4BWP_LVT
** d(net046) cp(sys_clkb) cdn(vdd) q(do) qn(net038) vdd(vdd) vss(gnd)
**xi12 net046 SYS_CLKB VDD DO net038 VDD GND DFCND4BWP_LVT

** DFCND4BWP_LVT Instance I25 = hspiceD device xi25
** Instance of Lib: STDLIB,  Cell: DFCND4BWP_LVT, View: schematic

** Port Connection: Instance  I25 of DFCND4BWP_LVT
** d(net025) cp(sys_clkb) cdn(vdd) q(net040) qn(net035) vdd(vdd) vss(gnd)
**xi25 net025 SYS_CLKB VDD net040 net035 VDD GND DFCND4BWP_LVT

** DFCND4BWP_LVT Instance I3 = hspiceD device xi3
** Instance of Lib: STDLIB,  Cell: DFCND4BWP_LVT, View: schematic

** Port Connection: Instance  I3 of DFCND4BWP_LVT
** d(net046) cp(sys_clkb) cdn(vdd) q(net026) qn(net022) vdd(vdd) vss(gnd)
**xi3 net046 SYS_CLKB VDD net026 net022 VDD GND DFCND4BWP_LVT

** OTA_XT_MAGICAL Instance I22 = hspiceD device xi22
** Instance of Lib: CTDSM_TOP,  Cell: OTA_XT_MAGICAL, View: schematic

** Port Connection: Instance  I22 of OTA_XT_MAGICAL
** gnd(gnd) ncas(ibias2) vcm(vcm) vdd(vdd) vim(ota2_inn) vip(ota2_inp) vom(vint2n) vop(vint2p)
xi22 VSSA IBIAS2 VCM VDDA OTA2_INN OTA2_INP VINT2N VINT2P OTA_XT_MAGICAL

** OTA_XT_MAGICAL Instance I20 = hspiceD device xi20
** Instance of Lib: CTDSM_TOP,  Cell: OTA_XT_MAGICAL, View: schematic

** Port Connection: Instance  I20 of OTA_XT_MAGICAL
** gnd(gnd) ncas(ibias1) vcm(vcm) vdd(vdd) vim(ota1_inp) vip(ota1_inn) vom(vint1p) vop(vint1n)
xi20 VSSA IBIAS1 VCM VDDA OTA1_INP OTA1_INN VINT1P VINT1N OTA_XT_MAGICAL

** BUFFD4BWP_LVT Instance I24 = hspiceD device xi24
** Instance of Lib: STDLIB,  Cell: BUFFD4BWP_LVT, View: schematic

** Port Connection: Instance  I24 of BUFFD4BWP_LVT
** i(net040) z(net010) vdd(vref) vss(gnd)
**xi24 net040 net010 VREF GND BUFFD4BWP_LVT

** BUFFD4BWP_LVT Instance I23 = hspiceD device xi23
** Instance of Lib: STDLIB,  Cell: BUFFD4BWP_LVT, View: schematic

** Port Connection: Instance  I23 of BUFFD4BWP_LVT
** i(net026) z(net012) vdd(vref) vss(gnd)
**xi23 net026 net012 VREF GND BUFFD4BWP_LVT

** SR_Latch_LVT Instance I6 = hspiceD device xi6
** Instance of Lib: 2019_CTDSM_Mingjie,  Cell: SR_Latch_LVT, View: schematic

** Port Connection: Instance  I6 of SR_Latch_LVT
** q(net046) qb(net025) r(net028) s(net020) vdd(vdd) vss(gnd)
**xi6 net046 net025 net028 net020 VDD GND SR_Latch_LVT

** COMPARATOR Instance I19 = hspiceD device xi19
** Instance of Lib: CTDSM_TOP,  Cell: COMPARATOR, View: schematic

** Port Connection: Instance  I19 of COMPARATOR
** clk(sys_clk) gnd(gnd) outm(net028) outp(net020) vdd(vdd) _net0(sum_p) _net1(sum_n)
xi19 SYS_CLK VSSA net028 net020 VDDA SUM_P SUM_N COMPARATOR_schematic

rr1 net040 net010 VREF VSSA net025 SYS_CLKB VDDA net035 RR1
rr2 net026 net012 VREF VSSA net046 SYS_CLKB VDDA net022 RR1

**xi24 net040 net010 VREF GND BUFFD4BWP_LVT
**xi25 net025 SYS_CLKB VDD net040 net035 VDD GND DFCND4BWP_LVT
**xi23 net026 net012 VREF GND BUFFD4BWP_LVT
**xi3  net046 SYS_CLKB VDD net026 net022 VDD GND DFCND4BWP_LVT

rrr1 net046 SYS_CLKB VDDA DO net038 VSSA net025 net028 net020 SYS_CLK RRR1

.ends CTDSM_TOP
** End of subcircuit definition.
** .END
