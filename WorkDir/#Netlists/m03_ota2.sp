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
* SIZES CONVERTED 2026-07-10 scale=2.5 source_L_ref=0.04um
*       Device/passive sizes are scaled from the real source-netlist values
*       (see marker above) -- not random placeholders.
* ============================================================

* --- DEVICE PARAMETERS ---
.param cap_xC7_L=3.478 cap_xC7_W=3.478
.param cap_xC6_L=3.478 cap_xC6_W=3.478
.param cap_xC5_L=2.592 cap_xC5_W=2.592
.param cap_xC4_L=2.592 cap_xC4_W=2.592
.param cap_xC3_L=17.39 cap_xC3_W=17.39
.param cap_xC2_L=17.39 cap_xC2_W=17.39
.param cap_xC1_L=8.299 cap_xC1_W=8.299
.param cap_xC0_L=8.299 cap_xC0_W=8.299
.param res_xR11_L=9 res_xR11_W=1
.param res_xR14_L=9 res_xR14_W=1
.param res_xR5_L=20.46 res_xR5_W=1
.param res_xR12_L=20.46 res_xR12_W=1
.param res_xR13_L=7.5 res_xR13_W=1
.param res_xR0_L=7.5 res_xR0_W=1
.param M36_L=0.4 M36_W=8 M36_M=1 M36_Nf=2
.param M33_L=0.3 M33_W=12 M33_M=1 M33_Nf=4
.param M32_L=0.3 M32_W=18 M32_M=1 M32_Nf=6
.param M21_L=0.3 M21_W=13.5 M21_M=1 M21_Nf=6
.param M20_L=0.3 M20_W=13.5 M20_M=1 M20_Nf=6
.param M18_L=0.6 M18_W=74.25 M18_M=4 M18_Nf=33
.param M17_L=0.6 M17_W=74.25 M17_M=4 M17_Nf=33
.param M7_L=0.3 M7_W=29.25 M7_M=1 M7_Nf=13
.param M8_L=0.6 M8_W=72 M8_M=4 M8_Nf=32
.param M9_L=0.3 M9_W=67.5 M9_M=4 M9_Nf=30
.param M10_L=0.6 M10_W=72 M10_M=4 M10_Nf=32
.param M12_L=0.3 M12_W=67.5 M12_M=4 M12_Nf=30
.param M1_L=0.3 M1_W=58.5 M1_M=4 M1_Nf=104
.param M19_L=0.3 M19_W=24.75 M19_M=1 M19_Nf=11
.param M16_L=0.3 M16_W=29.25 M16_M=1 M16_Nf=13
.param M15_L=0.3 M15_W=29.25 M15_M=1 M15_Nf=13
.param M14_L=0.6 M14_W=3 M14_M=1 M14_Nf=2
.param M13_L=0.3 M13_W=11.25 M13_M=1 M13_Nf=5
.param M3_L=0.3 M3_W=11.25 M3_M=1 M3_Nf=5
.param M4_L=0.3 M4_W=29.25 M4_M=1 M4_Nf=13
.param M2_L=0.3 M2_W=29.25 M2_M=1 M2_Nf=13
.param M74_L=0.3 M74_W=60 M74_M=2 M74_Nf=40
.param M71_L=0.3 M71_W=60 M71_M=2 M71_Nf=20
.param M70_L=0.3 M70_W=60 M70_M=2 M70_Nf=20
.param M69_L=0.3 M69_W=18 M69_M=1 M69_Nf=6
.param M68_L=0.3 M68_W=18 M68_M=1 M68_Nf=6
.param M35_L=0.6 M35_W=54 M35_M=4 M35_Nf=24
.param M34_L=0.6 M34_W=54 M34_M=4 M34_Nf=24
.param M27_L=0.6 M27_W=78 M27_M=4 M27_Nf=26
.param M26_L=0.6 M26_W=78 M26_M=4 M26_Nf=26
.param M28_L=0.3 M28_W=3 M28_M=1 M28_Nf=1
.param M25_L=0.3 M25_W=12 M25_M=1 M25_Nf=4
.param M24_L=0.3 M24_W=18 M24_M=1 M24_Nf=6
.param M50_L=0.4 M50_W=100 M50_M=4 M50_Nf=40
.param M6_L=0.6 M6_W=3 M6_M=1 M6_Nf=2


* --- CIRCUIT DEFINITION ---
.subckt OTA_2 VSSA IBIAS VCM VDDA VIM VIP VOM VOP
    M36 net0134 PCAS VDDA VDDA pmos_hvt L={M36_L} W={M36_W} M={M36_M} Nf={M36_Nf}
    xC7 vtail VOP VSSA cfmom nr=32 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC7_L} W={cap_xC7_W}
    xC6 VOM vtail VSSA cfmom nr=32 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC6_L} W={cap_xC6_W}
    xC5 VOM net0101 VSSA cfmom nr=32 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC5_L} W={cap_xC5_W}
    xC4 net0101 VOP VSSA cfmom nr=32 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC4_L} W={cap_xC4_W}
    xC3 VIM net096 VSSA cfmom nr=120 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC3_L} W={cap_xC3_W}
    xC2 VIP net092 VSSA cfmom nr=120 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC2_L} W={cap_xC2_W}
    xC1 VO1P net0118 VSSA cfmom nr=60 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC1_L} W={cap_xC1_W}
    xC0 net0118 VO1M VSSA cfmom nr=60 stm=1 spm=6 multi=1 ftip=140.0n dmflag=0 L={cap_xC0_L} W={cap_xC0_W}
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

xR11 net0101 VOM VSSA rppolywo lr={res_xR11_L} wr={res_xR11_W} series=6 segspace=250n

xR14 VOP net0101 VSSA rppolywo lr={res_xR14_L} wr={res_xR14_W} series=6 segspace=250n

xR5 VO1M net0118 VSSA rppolywo lr={res_xR5_L} wr={res_xR5_W} series=17 segspace=250n

xR12 net0118 VO1P VSSA rppolywo lr={res_xR12_L} wr={res_xR12_W} series=17 segspace=250n

xR13 net096 INCM2 VSSA rppolywo lr={res_xR13_L} wr={res_xR13_W} series=12 segspace=250n

xR0 net092 INCM2 VSSA rppolywo lr={res_xR0_L} wr={res_xR0_W} series=12 segspace=250n


.ends OTA_2

