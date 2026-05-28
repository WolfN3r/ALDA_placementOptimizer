* ============================================================
* Circuit : ota2
* Source  : MAGICAL analog layout examples
* File    : MAGICALexamples/ota2.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 35
*   Device types : nmos_hvt nmos_lvt pmos_hvt pmos_lvt pmos_rvt
*   Passives     : 6 resistors, 8 capacitors
* Note: Converted from Spectre/HSPICE format to ALIGN SPICE format.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param M36_L=120.0n M36_W=2.4u M36_M=1 M36_Nf=2
.param M33_L=120.0n M33_W=4.8u M33_M=1 M33_Nf=4
.param M32_L=120.0n M32_W=7.2u M32_M=1 M32_Nf=6
.param M21_L=120.0n M21_W=5.4u M21_M=1 M21_Nf=6
.param M20_L=120.0n M20_W=5.4u M20_M=1 M20_Nf=6
.param M18_L=240.0n M18_W=118.8u M18_M=1 M18_Nf=33
.param M17_L=240.0n M17_W=118.8u M17_M=1 M17_Nf=33
.param M7_L=120.0n M7_W=11.7u M7_M=1 M7_Nf=13
.param M8_L=240.0n M8_W=115.2u M8_M=1 M8_Nf=32
.param M9_L=120.0n M9_W=108.000000u M9_M=1 M9_Nf=30
.param M10_L=240.0n M10_W=115.2u M10_M=1 M10_Nf=32
.param M12_L=120.0n M12_W=108.000000u M12_M=1 M12_Nf=30
.param M1_L=120.0n M1_W=93.6u M1_M=1 M1_Nf=104
.param M19_L=120.0n M19_W=9.9u M19_M=1 M19_Nf=11
.param M16_L=120.0n M16_W=11.7u M16_M=1 M16_Nf=13
.param M15_L=120.0n M15_W=11.7u M15_M=1 M15_Nf=13
.param M14_L=240.0n M14_W=1.2u M14_M=1 M14_Nf=2
.param M13_L=120.0n M13_W=4.5u M13_M=1 M13_Nf=5
.param M3_L=120.0n M3_W=4.5u M3_M=1 M3_Nf=5
.param M4_L=120.0n M4_W=11.7u M4_M=1 M4_Nf=13
.param M2_L=120.0n M2_W=11.7u M2_M=1 M2_Nf=13
.param M74_L=120.0n M74_W=48.0u M74_M=1 M74_Nf=40
.param M71_L=120.0n M71_W=48.0u M71_M=1 M71_Nf=20
.param M70_L=120.0n M70_W=48.0u M70_M=1 M70_Nf=20
.param M69_L=120.0n M69_W=7.2u M69_M=1 M69_Nf=6
.param M68_L=120.0n M68_W=7.2u M68_M=1 M68_Nf=6
.param M35_L=240.0n M35_W=86.4u M35_M=1 M35_Nf=24
.param M34_L=240.0n M34_W=86.4u M34_M=1 M34_Nf=24
.param M27_L=240.0n M27_W=124.8u M27_M=1 M27_Nf=26
.param M26_L=240.0n M26_W=124.8u M26_M=1 M26_Nf=26
.param M28_L=120.0n M28_W=1.2u M28_M=1 M28_Nf=1
.param M25_L=120.0n M25_W=4.8u M25_M=1 M25_Nf=4
.param M24_L=120.0n M24_W=7.2u M24_M=1 M24_Nf=6
.param M50_L=120.0n M50_W=144.000000u M50_M=1 M50_Nf=40
.param M6_L=240.0n M6_W=1.2u M6_M=1 M6_Nf=2


* --- CIRCUIT DEFINITION ---
.subckt OTA_2 VSSA IBIAS VCM VDDA VIM VIP VOM VOP
    M36 net0134 PCAS VDDA VDDA pmos_hvt L={M36_L} W={M36_W} M={M36_M} Nf={M36_Nf}
    xC7 vtail VOP VSSA cfmom nr=32 lr=2.7u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    xC6 VOM vtail VSSA cfmom nr=32 lr=2.7u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    xC5 VOM net0101 VSSA cfmom nr=32 lr=1.5u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    xC4 net0101 VOP VSSA cfmom nr=32 lr=1.5u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    xC3 VIM net096 VSSA cfmom nr=120 lr=18.0u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    xC2 VIP net092 VSSA cfmom nr=120 lr=18.0u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    xC1 VO1P net0118 VSSA cfmom nr=60 lr=8.2u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    xC0 net0118 VO1M VSSA cfmom nr=60 lr=8.2u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
    M33 net0138 net077 VDDA VDDA pmos_rvt L={M33_L} W={M33_W} M={M33_M} Nf={M33_Nf}
    M32 net0136 net077 VDDA VDDA pmos_rvt L={M32_L} W={M32_W} M={M32_M} Nf={M32_Nf}
    M21 net0104 net0101 CMFBTAIL VSSA nmos_lvt L={M21_L} W={M21_W} M={M21_M} Nf={M21_Nf}
    M20 vtail VCM CMFBTAIL VSSA nmos_lvt L={M20_L} W={M20_W} M={M20_M} Nf={M20_Nf}
    M18 VO1P IBIAS net0131 VSSA nmos_lvt L={M18_L} W={M18_W} M={M18_M} Nf={M18_Nf}
    M17 VO1M IBIAS net0133 VSSA nmos_lvt L={M17_L} W={M17_W} M={M17_M} Nf={M17_Nf}
    M7 CMFBTAIL NBIAS_TAIL VSSA VSSA nmos_lvt L={M7_L} W={M7_W} M={M7_M} Nf={M7_Nf}
    M8 net0133 VIP NTAIL VSSA nmos_lvt L={M8_L} W={M8_W} M={M8_M} Nf={M8_Nf}
    M9 VOM net092 vs VSSA nmos_lvt L={M9_L} W={M9_W} M={M9_M} Nf={M9_Nf}
    M10 net0131 VIM NTAIL VSSA nmos_lvt L={M10_L} W={M10_W} M={M10_M} Nf={M10_Nf}
    M12 VOP net096 vs VSSA nmos_lvt L={M12_L} W={M12_W} M={M12_M} Nf={M12_Nf}
    M1 NTAIL NBIAS_TAIL VSSA VSSA nmos_lvt L={M1_L} W={M1_W} M={M1_M} Nf={M1_Nf}
    M19 IBIAS IBIAS NBIAS_TAIL VSSA nmos_lvt L={M19_L} W={M19_W} M={M19_M} Nf={M19_Nf}
    M16 PCAS VCM VN1 VSSA nmos_lvt L={M16_L} W={M16_W} M={M16_M} Nf={M16_Nf}
    M15 NBIAS_TAIL VCM VN2 VSSA nmos_lvt L={M15_L} W={M15_W} M={M15_M} Nf={M15_Nf}
    M14 INCM2 INCM2 net0137 VSSA nmos_lvt L={M14_L} W={M14_W} M={M14_M} Nf={M14_Nf}
    M13 net077 VCM net0135 VSSA nmos_lvt L={M13_L} W={M13_W} M={M13_M} Nf={M13_Nf}
    M3 net0135 NBIAS_TAIL VSSA VSSA nmos_lvt L={M3_L} W={M3_W} M={M3_M} Nf={M3_Nf}
    M4 VN2 NBIAS_TAIL VSSA VSSA nmos_lvt L={M4_L} W={M4_W} M={M4_M} Nf={M4_Nf}
    M2 VN1 NBIAS_TAIL VSSA VSSA nmos_lvt L={M2_L} W={M2_W} M={M2_M} Nf={M2_Nf}
    M74 PTAIL net0118 VDDA VDDA pmos_lvt L={M74_L} W={M74_W} M={M74_M} Nf={M74_Nf}
    M71 VOP VO1M VDDA VDDA pmos_lvt L={M71_L} W={M71_W} M={M71_M} Nf={M71_Nf}
    M70 VOM VO1P VDDA VDDA pmos_lvt L={M70_L} W={M70_W} M={M70_M} Nf={M70_Nf}
    M69 net0104 net0104 VDDA VDDA pmos_lvt L={M69_L} W={M69_W} M={M69_M} Nf={M69_Nf}
    M68 vtail net0104 VDDA VDDA pmos_lvt L={M68_L} W={M68_W} M={M68_M} Nf={M68_Nf}
    M35 net0132 VIP PTAIL VDDA pmos_lvt L={M35_L} W={M35_W} M={M35_M} Nf={M35_Nf}
    M34 net0130 VIM PTAIL VDDA pmos_lvt L={M34_L} W={M34_W} M={M34_M} Nf={M34_Nf}
    M27 VO1P PCAS net0130 VDDA pmos_lvt L={M27_L} W={M27_W} M={M27_M} Nf={M27_Nf}
    M26 VO1M PCAS net0132 VDDA pmos_lvt L={M26_L} W={M26_W} M={M26_M} Nf={M26_Nf}
    M28 PCAS PCAS net0134 VDDA pmos_lvt L={M28_L} W={M28_W} M={M28_M} Nf={M28_Nf}
    M25 INCM2 PCAS net0138 VDDA pmos_lvt L={M25_L} W={M25_W} M={M25_M} Nf={M25_Nf}
    M24 net077 PCAS net0136 VDDA pmos_lvt L={M24_L} W={M24_W} M={M24_M} Nf={M24_Nf}
    M50 vs vtail VSSA VSSA nmos_hvt L={M50_L} W={M50_W} M={M50_M} Nf={M50_Nf}
    M6 net0137 INCM2 VSSA VSSA nmos_hvt L={M6_L} W={M6_W} M={M6_M} Nf={M6_Nf}

xR11 net0101 VOM VSSA rppolywo lr=3.6u wr=400n series=6 segspace=250n

xR14 VOP net0101 VSSA rppolywo lr=3.6u wr=400n series=6 segspace=250n

xR5 VO1M net0118 VSSA rppolywo lr=8.185u wr=400n series=17 segspace=250n

xR12 net0118 VO1P VSSA rppolywo lr=8.185u wr=400n series=17 segspace=250n

xR13 net096 INCM2 VSSA rppolywo lr=3u wr=400n series=12 segspace=250n

xR0 net092 INCM2 VSSA rppolywo lr=3u wr=400n series=12 segspace=250n


.ends OTA_2

