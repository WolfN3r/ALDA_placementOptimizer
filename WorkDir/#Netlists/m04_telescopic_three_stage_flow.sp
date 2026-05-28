* ============================================================
* Circuit : telescopic_three_stage_flow
* Source  : MAGICAL analog layout examples
* File    : MAGICALexamples/Telescopic_Three_stage_flow.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 32
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 6 resistors, 4 capacitors
* Note: Converted from Spectre/HSPICE format to ALIGN SPICE format.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param M60_L=200n M60_W=8.8u M60_M=1 M60_Nf=4
.param M105_L=400n M105_W=88.0u M105_M=1 M105_Nf=8
.param M93_L=200n M93_W=8.8u M93_M=1 M93_Nf=4
.param M110_L=400n M110_W=20u M110_M=1 M110_Nf=8
.param M75_L=400n M75_W=20u M75_M=1 M75_Nf=8
.param M97_L=400n M97_W=44.0u M97_M=1 M97_Nf=4
.param M24_L=1u M24_W=60u M24_M=1 M24_Nf=10
.param M96_L=400n M96_W=44.0u M96_M=1 M96_Nf=4
.param M21_L=400n M21_W=44.0u M21_M=1 M21_Nf=4
.param M113_L=400n M113_W=40u M113_M=1 M113_Nf=16
.param M13_L=400n M13_W=40u M13_M=1 M13_Nf=16
.param M102_L=400n M102_W=44.0u M102_M=1 M102_Nf=4
.param M18_L=400n M18_W=44.0u M18_M=1 M18_Nf=4
.param M106_L=200n M106_W=60u M106_M=1 M106_Nf=10
.param M4_L=400n M4_W=308.000000u M4_M=1 M4_Nf=28
.param M3_L=200n M3_W=60u M3_M=1 M3_Nf=10
.param M63_L=200n M63_W=10u M63_M=1 M63_Nf=4
.param M112_L=800n M112_W=400.0000u M112_M=1 M112_Nf=40
.param M73_L=800n M73_W=400.0000u M73_M=1 M73_Nf=40
.param M114_L=200n M114_W=10u M114_M=1 M114_Nf=4
.param M26_L=1.6u M26_W=50u M26_M=1 M26_Nf=10
.param M90_L=800n M90_W=40u M90_M=1 M90_Nf=4
.param M111_L=800n M111_W=400.0000u M111_M=1 M111_Nf=40
.param M14_L=800n M14_W=400.0000u M14_M=1 M14_Nf=40
.param M109_L=400n M109_W=800.0000u M109_M=1 M109_Nf=80
.param M9_L=400n M9_W=800.0000u M9_M=1 M9_Nf=80
.param M7_L=800n M7_W=40u M7_M=1 M7_Nf=4
.param M6_L=200n M6_W=50u M6_M=1 M6_Nf=10
.param M107_L=200n M107_W=50u M107_M=1 M107_Nf=10
.param M108_L=800n M108_W=40u M108_M=1 M108_Nf=4
.param M12_L=800n M12_W=90u M12_M=1 M12_Nf=10
.param M2_L=800n M2_W=90u M2_M=1 M2_Nf=10


* --- CIRCUIT DEFINITION ---
* Generated for: spectre
* Generated on: May  3 15:01:57 2019
* Design library name: 2019_Synthesizing_OTA_copy
* Design cell name: Telescopic_Three_stage_flow
* Design view name: schematic
* simulator lang=spectre
* global 0
* include "/usr/local/packages/tsmc_40/pdk/tsmcN40/../models/spectre/toplevel.scs" section=top_tt

* Library name: 2019_Synthesizing_OTA_copy
* Cell name: Telescopic_Three_stage_flow
* View name: schematic
* terminal mapping: INM	= INM
* INP	= INP
* OUTM	= OUTM
* OUTP	= OUTP
* VBN1	= VBN1
* VDD	= VDD
* VREF	= VREF
* VSS	= VSS
.subckt Telescopic_Three_stage_flow INM INP OUTM OUTP VBN1 VDDA VREF VSSA

* nch Instance M60 = spectre device M60
M60 net057 net056 net058 VSSA nmos_rvt L={M60_L} W={M60_W} M={M60_M} Nf={M60_Nf}

* nch Instance M105 = spectre device M105
M105 net058 VBN VSSA VSSA nmos_rvt L={M105_L} W={M105_W} M={M105_M} Nf={M105_Nf}

* nch Instance M93 = spectre device M93
M93 VCMFB3 VREF net058 VSSA nmos_rvt L={M93_L} W={M93_W} M={M93_M} Nf={M93_Nf}

* nch Instance M110 = spectre device M110
M110 VOM2 VCMFB2 VSSA VSSA nmos_rvt L={M110_L} W={M110_W} M={M110_M} Nf={M110_Nf}

* nch Instance M75 = spectre device M75
M75 VOP2 VCMFB2 VSSA VSSA nmos_rvt L={M75_L} W={M75_W} M={M75_M} Nf={M75_Nf}

* nch Instance M97 = spectre device M97
M97 VBP VBN VSSA VSSA nmos_rvt L={M97_L} W={M97_W} M={M97_M} Nf={M97_Nf}

* nch Instance M24 = spectre device M24
M24 VBN1 VBN1 VBN VSSA nmos_rvt L={M24_L} W={M24_W} M={M24_M} Nf={M24_Nf}

* nch Instance M96 = spectre device M96
M96 VBP1 VBN VSSA VSSA nmos_rvt L={M96_L} W={M96_W} M={M96_M} Nf={M96_Nf}

* nch Instance M21 = spectre device M21
M21 VBN VBN VSSA VSSA nmos_rvt L={M21_L} W={M21_W} M={M21_M} Nf={M21_Nf}

* nch Instance M113 = spectre device M113
M113 OUTP VOM2 VSSA VSSA nmos_rvt L={M113_L} W={M113_W} M={M113_M} Nf={M113_Nf}

* nch Instance M13 = spectre device M13
M13 OUTM VOP2 VSSA VSSA nmos_rvt L={M13_L} W={M13_W} M={M13_M} Nf={M13_Nf}

* nch Instance M102 = spectre device M102
M102 VOM2 VBN VSSA VSSA nmos_rvt L={M102_L} W={M102_W} M={M102_M} Nf={M102_Nf}

* nch Instance M18 = spectre device M18
M18 VOP2 VBN VSSA VSSA nmos_rvt L={M18_L} W={M18_W} M={M18_M} Nf={M18_Nf}

* nch Instance M106 = spectre device M106
M106 VOP1 VBN1 net2 VSSA nmos_rvt L={M106_L} W={M106_W} M={M106_M} Nf={M106_Nf}

* nch Instance M4 = spectre device M4
M4 net1 VBN VSSA VSSA nmos_rvt L={M4_L} W={M4_W} M={M4_M} Nf={M4_Nf}

* nch Instance M3 = spectre device M3
M3 VOM1 VBN1 net4 VSSA nmos_rvt L={M3_L} W={M3_W} M={M3_M} Nf={M3_Nf}

* pch Instance M63 = spectre device M63
M63 net057 net057 VDDA VDDA pmos_rvt L={M63_L} W={M63_W} M={M63_M} Nf={M63_Nf}

* pch Instance M112 = spectre device M112
M112 OUTP VCMFB3 VDDA VDDA pmos_rvt L={M112_L} W={M112_W} M={M112_M} Nf={M112_Nf}

* pch Instance M73 = spectre device M73
M73 OUTM VCMFB3 VDDA VDDA pmos_rvt L={M73_L} W={M73_W} M={M73_M} Nf={M73_Nf}

* pch Instance M114 = spectre device M114
M114 VCMFB3 net057 VDDA VDDA pmos_rvt L={M114_L} W={M114_W} M={M114_M} Nf={M114_Nf}

* pch Instance M26 = spectre device M26
M26 VBP1 VBP1 VDDA VDDA pmos_rvt L={M26_L} W={M26_W} M={M26_M} Nf={M26_Nf}

* pch Instance M90 = spectre device M90
M90 VBP VBP VDDA VDDA pmos_rvt L={M90_L} W={M90_W} M={M90_M} Nf={M90_Nf}

* pch Instance M111 = spectre device M111
M111 OUTP VBP VDDA VDDA pmos_rvt L={M111_L} W={M111_W} M={M111_M} Nf={M111_Nf}

* pch Instance M14 = spectre device M14
M14 OUTM VBP VDDA VDDA pmos_rvt L={M14_L} W={M14_W} M={M14_M} Nf={M14_Nf}

* pch Instance M109 = spectre device M109
M109 VOM2 VOP1 VDDA VDDA pmos_rvt L={M109_L} W={M109_W} M={M109_M} Nf={M109_Nf}

* pch Instance M9 = spectre device M9
M9 VOP2 VOM1 VDDA VDDA pmos_rvt L={M9_L} W={M9_W} M={M9_M} Nf={M9_Nf}

* pch Instance M7 = spectre device M7
M7 net07 VCMFB1 VDDA VDDA pmos_rvt L={M7_L} W={M7_W} M={M7_M} Nf={M7_Nf}

* pch Instance M6 = spectre device M6
M6 VOM1 VBP1 net07 VDDA pmos_rvt L={M6_L} W={M6_W} M={M6_M} Nf={M6_Nf}

* pch Instance M107 = spectre device M107
M107 VOP1 VBP1 net08 VDDA pmos_rvt L={M107_L} W={M107_W} M={M107_M} Nf={M107_Nf}

* pch Instance M108 = spectre device M108
M108 net08 VCMFB1 VDDA VDDA pmos_rvt L={M108_L} W={M108_W} M={M108_M} Nf={M108_Nf}

* cfmom Instance C7 = spectre device C7
xC7 VOP1 OUTM VSSA cfmom nr=50 lr=6u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0

* cfmom Instance C6 = spectre device C6
xC6 VOM1 OUTP VSSA cfmom nr=50 lr=6u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0

* cfmom Instance C5 = spectre device C5
xC5 VOM2 OUTM VSSA cfmom nr=88 lr=10u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0

* cfmom Instance C1 = spectre device C1
xC1 VOM2 OUTP VSSA cfmom nr=88 lr=10u w=70n s=70n stm=1 spm=6 multi=1 ftip=140.0n dmflag=0
xR8 VCMFB2 VOM2 VSSA rppolywo_m lr=10u wr=400n multi=(1) m=1

* Series configuration of R4
xR4 VOP1 VCMFB1 VSSA rppolywo_m lr=10u wr=400n multi=(1) m=1 series=10 segspace=250n
* End of R4

xR9 OUTP net056 VSSA rppolywo_m lr=8u wr=400n multi=(1) m=1

* Series configuration of R6q
xR6q VCMFB1 VOM1 VSSA rppolywo_m lr=10u wr=400n multi=(1) m=1 series=10 segspace=250n
* End of R6q

xR10 net056 OUTM VSSA rppolywo_m lr=8u wr=400n multi=(1) m=1

xR7 VOP2 VCMFB2 VSSA rppolywo_m lr=10u wr=400n multi=(1) m=1


* nch_25ud18_mac Instance M12 = spectre device M12
M12 net4 INP net1 VSSA nmos_rvt L={M12_L} W={M12_W} M={M12_M} Nf={M12_Nf}

* nch_25ud18_mac Instance M2 = spectre device M2
M2 net2 INM net1 VSSA nmos_rvt L={M2_L} W={M2_W} M={M2_M} Nf={M2_Nf}
.ends Telescopic_Three_stage_flow
* simulatorOptions options reltol=1e-3 vabstol=1e-6 iabstol=1e-12 temp=27 //    tnom=27 scalem=1.0 scale=1.0 gmin=1e-12 rforce=1 maxnotes=5 maxwarns=5 //    digits=5 cols=80 pivrel=1e-3 sensfile="../psf/sens.output" //    checklimitdest=psf
* modelParameter info what=models where=rawfile
* element info what=inst where=rawfile
* outputParameter info what=output where=rawfile
* designParamVals info what=parameters where=rawfile
* primitives info what=primitives where=rawfile
* subckts info what=subckts where=rawfile
* saveOptions options save=allpub
