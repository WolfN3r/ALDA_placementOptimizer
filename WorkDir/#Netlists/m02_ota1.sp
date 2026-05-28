* ============================================================
* Circuit : ota1
* Source  : MAGICAL analog layout examples
* File    : MAGICALexamples/ota1.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 23
*   Device types : nmos_lvt nmos_rvt pmos_lvt pmos_rvt
*   Passives     : 0 resistors, 2 capacitors
* Note: Converted from Spectre/HSPICE format to ALIGN SPICE format.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param MP1c_L=120.0n MP1c_W=16.0u MP1c_M=1 MP1c_Nf=8
.param M20_L=120.0n M20_W=16.0u M20_M=1 M20_Nf=8
.param M7_L=120.0n M7_W=16.0u M7_M=1 M7_Nf=8
.param M5_L=120.0n M5_W=16.0u M5_M=1 M5_Nf=8
.param MP1a_L=120.0n MP1a_W=40u MP1a_M=1 MP1a_Nf=20
.param MP1b_L=120.0n MP1b_W=40u MP1b_M=1 MP1b_Nf=20
.param M10_L=120.0n M10_W=32.0u M10_M=1 M10_Nf=16
.param M9_L=120.0n M9_W=12.0u M9_M=1 M9_Nf=6
.param M6_L=120.0n M6_W=12.0u M6_M=1 M6_Nf=6
.param M13_L=120.0n M13_W=4u M13_M=1 M13_Nf=2
.param M12_L=120.0n M12_W=4u M12_M=1 M12_Nf=2
.param M11_L=120.0n M11_W=8u M11_M=1 M11_Nf=4
.param M4_L=120.0n M4_W=8u M4_M=1 M4_Nf=4
.param M19_L=120.0n M19_W=16.0u M19_M=1 M19_Nf=8
.param M17_L=120.0n M17_W=16.0u M17_M=1 M17_Nf=8
.param M15_L=120.0n M15_W=16.0u M15_M=1 M15_Nf=8
.param M25_L=120.0n M25_W=24.0u M25_M=1 M25_Nf=12
.param M23_L=120.0n M23_W=24.0u M23_M=1 M23_Nf=12
.param M3_L=120.0n M3_W=24.0u M3_M=1 M3_Nf=12
.param M1_L=120.0n M1_W=24.0u M1_M=1 M1_Nf=12
.param M18_L=120.0n M18_W=16.0u M18_M=1 M18_Nf=8
.param M0_L=500n M0_W=60u M0_M=1 M0_Nf=12
.param M2_L=500n M2_W=60u M2_M=1 M2_Nf=12


* --- CIRCUIT DEFINITION ---
* Generated for: spectre
* Generated on: Dec  9 17:25:45 2018
* Design library name: Two_stage_miller
* Design cell name: Core
* Design view name: schematic
* simulator lang=spectre
* global 0
* include "/usr/local/packages/tsmc_40/pdk/tsmcN40/../models/spectre/toplevel.scs" section=top_tt

* Library name: Two_stage_miller
* Cell name: Core
* View name: schematic
* terminal mapping: INM	= INM
* INP	= INP
* OUTM	= OUTM
* OUTP	= OUTP
* VBIAS_P	= VBIAS_P
* VDD	= VDD
* VREF	= VREF
* VSS	= VSS
.subckt Core_test_flow INM INP OUTM OUTP VBIAS_P VDDA VREF VSSA
* pch Instance MP1c = spectre device MP1c
MP1c net020 VBIAS_P VDDA VDDA pmos_rvt L={MP1c_L} W={MP1c_W} M={MP1c_M} Nf={MP1c_Nf}

* pch Instance M20 = spectre device M20
M20 net028 VBIAS_P VDDA VDDA pmos_rvt L={M20_L} W={M20_W} M={M20_M} Nf={M20_Nf}

* pch Instance M7 = spectre device M7
M7 vbias_n VBIAS_P VDDA VDDA pmos_rvt L={M7_L} W={M7_W} M={M7_M} Nf={M7_Nf}

* pch Instance M5 = spectre device M5
M5 VBIAS_P VBIAS_P VDDA VDDA pmos_rvt L={M5_L} W={M5_W} M={M5_M} Nf={M5_Nf}

* pch Instance MP1a = spectre device MP1a
MP1a intm VBIAS_P VDDA VDDA pmos_rvt L={MP1a_L} W={MP1a_W} M={MP1a_M} Nf={MP1a_Nf}

* pch Instance MP1b = spectre device MP1b
MP1b intp VBIAS_P VDDA VDDA pmos_rvt L={MP1b_L} W={MP1b_W} M={MP1b_M} Nf={MP1b_Nf}

* cfmom_2t Instance C1 = spectre device C1
xC1 OUTM net037 cfmom_2t nr=210 lr=13.0u w=70n s=70n stm=3 spm=6 multi=1 ftip=140.0n

* cfmom_2t Instance C0 = spectre device C0
xC0 OUTP net047 cfmom_2t nr=210 lr=13.0u w=70n s=70n stm=3 spm=6 multi=1 ftip=140.0n

* nch_lvt Instance M10 = spectre device M10
M10 net7 vbias_n VSSA VSSA nmos_lvt L={M10_L} W={M10_W} M={M10_M} Nf={M10_Nf}

* nch_lvt Instance M9 = spectre device M9
M9 OUTM vbias_n VSSA VSSA nmos_lvt L={M9_L} W={M9_W} M={M9_M} Nf={M9_Nf}

* nch_lvt Instance M6 = spectre device M6
M6 OUTP vbias_n VSSA VSSA nmos_lvt L={M6_L} W={M6_W} M={M6_M} Nf={M6_Nf}

* nch_lvt Instance M13 = spectre device M13
M13 vcmfb vcmfb VSSA VSSA nmos_lvt L={M13_L} W={M13_W} M={M13_M} Nf={M13_Nf}

* nch_lvt Instance M12 = spectre device M12
M12 net025 net025 VSSA VSSA nmos_lvt L={M12_L} W={M12_W} M={M12_M} Nf={M12_Nf}

* nch_lvt Instance M11 = spectre device M11
M11 net7 vcmfb VSSA VSSA nmos_lvt L={M11_L} W={M11_W} M={M11_M} Nf={M11_Nf}

* nch_lvt Instance M4 = spectre device M4
M4 vbias_n vbias_n VSSA VSSA nmos_lvt L={M4_L} W={M4_W} M={M4_M} Nf={M4_Nf}

* pch_lvt Instance M19 = spectre device M19
M19 net025 VREF net028 VDDA pmos_lvt L={M19_L} W={M19_W} M={M19_M} Nf={M19_Nf}

* pch_lvt Instance M17 = spectre device M17
M17 net025 VREF net020 VDDA pmos_lvt L={M17_L} W={M17_W} M={M17_M} Nf={M17_Nf}

* pch_lvt Instance M15 = spectre device M15
M15 vcmfb OUTP net020 VDDA pmos_lvt L={M15_L} W={M15_W} M={M15_M} Nf={M15_Nf}

* pch_lvt Instance M25 = spectre device M25
M25 net037 VSSA intp VDDA pmos_lvt L={M25_L} W={M25_W} M={M25_M} Nf={M25_Nf}

* pch_lvt Instance M23 = spectre device M23
M23 net047 VSSA intm VDDA pmos_lvt L={M23_L} W={M23_W} M={M23_M} Nf={M23_Nf}

* pch_lvt Instance M3 = spectre device M3
M3 OUTP intm VDDA VDDA pmos_lvt L={M3_L} W={M3_W} M={M3_M} Nf={M3_Nf}

* pch_lvt Instance M1 = spectre device M1
M1 OUTM intp VDDA VDDA pmos_lvt L={M1_L} W={M1_W} M={M1_M} Nf={M1_Nf}

* pch_lvt Instance M18 = spectre device M18
M18 vcmfb OUTM net028 VDDA pmos_lvt L={M18_L} W={M18_W} M={M18_M} Nf={M18_Nf}

* nch_25ud18_mac Instance M0 = spectre device M0
M0 intp INM net7 VSSA nmos_rvt L={M0_L} W={M0_W} M={M0_M} Nf={M0_Nf}

* nch_25ud18_mac Instance M2 = spectre device M2
M2 intm INP net7 VSSA nmos_rvt L={M2_L} W={M2_W} M={M2_M} Nf={M2_Nf}
.ends Core_test_flow

* simulatorOptions options reltol=1e-3 vabstol=1e-6 iabstol=1e-12 temp=27 //     tnom=27 scalem=1.0 scale=1.0 gmin=1e-12 rforce=1 maxnotes=5 maxwarns=5 //     digits=5 cols=80 pivrel=1e-3 sensfile="../psf/sens.output" //     checklimitdest=psf
* modelParameter info what=models where=rawfile
* element info what=inst where=rawfile
* outputParameter info what=output where=rawfile
* designParamVals info what=parameters where=rawfile
* primitives info what=primitives where=rawfile
* subckts info what=subckts where=rawfile
* saveOptions options save=allpub
