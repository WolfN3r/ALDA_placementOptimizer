* ============================================================
* Circuit : vco_dtype_12_hierarchical
* Source  : ALIGN analog layout examples
* File    : vco_dtype_12_hierarchical\vco_dtype_12_hierarchical.sp
* ============================================================
* Stats:
*   Subcircuits  : 4
*   Devices (M)  : 14
*   Device types : nmos_lvt pmos_lvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param diff2sing_v1_MP2_M=1 diff2sing_v1_MP2_L=14n
.param diff2sing_v1_MP5_M=1 diff2sing_v1_MP5_L=14n
.param diff2sing_v1_MP1_M=1 diff2sing_v1_MP1_L=14n
.param diff2sing_v1_MP4_M=1 diff2sing_v1_MP4_L=14n
.param diff2sing_v1_MP0_M=1 diff2sing_v1_MP0_L=14n
.param diff2sing_v1_MP3_M=1 diff2sing_v1_MP3_L=14n
.param diff2sing_v1_MN1_M=1 diff2sing_v1_MN1_L=14n
.param diff2sing_v1_MN3_M=1 diff2sing_v1_MN3_L=14n
.param diff2sing_v1_MN0_M=1 diff2sing_v1_MN0_L=14n
.param diff2sing_v1_MN2_M=1 diff2sing_v1_MN2_L=14n
.param three_terminal_inv_MN34_M=1 three_terminal_inv_MN34_L=14n
.param three_terminal_inv_MN33_M=1 three_terminal_inv_MN33_L=14n
.param three_terminal_inv_MP34_M=1 three_terminal_inv_MP34_L=14n
.param three_terminal_inv_MP33_M=1 three_terminal_inv_MP33_L=14n


* --- CIRCUIT DEFINITION ---
* 
.param nfin=14 rres=2k lastt=60n fin_n_diff2sing=4 fin_p_diff2sing=6     width_n_diff2sing=10 width_p_diff2sing=16 fin_n_vco_type_2=4     fin_p_vco_type_2=6 fnnn=24 fppp=4 VDD=0.8 VBIAS=0.7 wpppn=1 wnnn=1

* Library name: CAD_modules
* Cell name: diff2sing_v1
* View name: schematic
.subckt diff2sing_v1 B VDDA VSSA in1 in2 o
.param _ar0=1 _ar1=1 _ar2=1 _ar3=1
    MP2 net3 B net1 VDDA pmos_lvt M={diff2sing_v1_MP2_M} L={diff2sing_v1_MP2_L} W=_ar0 Nf=_ar1
    MP5 net1 B VDDA VDDA pmos_lvt M={diff2sing_v1_MP5_M} L={diff2sing_v1_MP5_L} W=_ar0 Nf=_ar1
    MP1 o in2 net2 VDDA pmos_lvt M={diff2sing_v1_MP1_M} L={diff2sing_v1_MP1_L} W=_ar0 Nf=_ar1
    MP4 net2 in2 net3 VDDA pmos_lvt M={diff2sing_v1_MP4_M} L={diff2sing_v1_MP4_L} W=_ar0 Nf=_ar1
    MP0 net8 in1 net4 VDDA pmos_lvt M={diff2sing_v1_MP0_M} L={diff2sing_v1_MP0_L} W=_ar0 Nf=_ar1
    MP3 net4 in1 net3 VDDA pmos_lvt M={diff2sing_v1_MP3_M} L={diff2sing_v1_MP3_L} W=_ar0 Nf=_ar1
    MN1 net8 net8 net5 VSSA nmos_lvt M={diff2sing_v1_MN1_M} L={diff2sing_v1_MN1_L} W=_ar2 Nf=_ar3
    MN3 net5 net8 VSSA VSSA nmos_lvt M={diff2sing_v1_MN3_M} L={diff2sing_v1_MN3_L} W=_ar2 Nf=_ar3
    MN0 o net8 net6 VSSA nmos_lvt M={diff2sing_v1_MN0_M} L={diff2sing_v1_MN0_L} W=_ar2 Nf=_ar3
    MN2 net6 net8 VSSA VSSA nmos_lvt M={diff2sing_v1_MN2_M} L={diff2sing_v1_MN2_L} W=_ar2 Nf=_ar3
.ends diff2sing_v1

.subckt three_terminal_inv VDDA VSSA VBIAS VIN VOUT
.param _ar0=1 _ar1=1 _ar2=1 _ar3=1 _ar4=1 _ar5=0
    MN34 VOUT VIN net1 VSSA nmos_lvt M={three_terminal_inv_MN34_M} L={three_terminal_inv_MN34_L} W=_ar0 Nf=_ar2
    MN33 net1 VIN VSSA VSSA nmos_lvt M={three_terminal_inv_MN33_M} L={three_terminal_inv_MN33_L} W=_ar0 Nf=_ar2
    MP34 VOUT VBIAS net2 VDDA pmos_lvt M={three_terminal_inv_MP34_M} L={three_terminal_inv_MP34_L} W=_ar3 Nf=_ar4
    MP33 net2 VBIAS VDDA VDDA pmos_lvt M={three_terminal_inv_MP33_M} L={three_terminal_inv_MP33_L} W=_ar3 Nf=_ar4
.ends three_terminal_inv
* End of subcircuit definition.

* Library name: CAD_modules
* Cell name: VCO_type2_12
* View name: schematic
.subckt VCO_type2_65 VDDA VSSA o<1> o<2> o<3> o<4> o<5> o<6> o<7> o<8> op<1> VBIAS
.param _ar0=1 _ar1=1 _ar2=1 _ar3=1 _ar4=1 _ar5=0
    xI1<1> VDDA VSSA VBIAS o<1> o<2> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
    xI1<2> VDDA VSSA VBIAS o<2> o<3> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
    xI1<3> VDDA VSSA VBIAS o<3> o<4> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
    xI1<4> VDDA VSSA VBIAS o<4> o<5> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
    xI1<5> VDDA VSSA VBIAS o<5> o<6> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
    xI1<6> VDDA VSSA VBIAS o<6> o<7> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
    xI1<7> VDDA VSSA VBIAS o<7> o<8> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
    xI1<8> VDDA VSSA VBIAS o<8> op<1> three_terminal_inv _ar0=_ar0 _ar1=_ar1 _ar2=_ar2 _ar3=_ar3 _ar4=_ar4 _ar5=_ar5
.ends VCO_type2_65
* End of subcircuit definition.


* Main body of circuit:
.subckt vco_dtype_12_hierarchical VDDA VSSA vbias oo<1> oo<2> oo<3> oo<4> oo<5> oo<6> oo<7> oo<8> on<1> on<2> on<3> on<4> on<5> on<6> on<7> on<8> op<1> op<2> op<3> op<4> op<5> op<6> op<7> op<8>

xI6<1> VSSA VDDA VSSA on<1> op<1> oo<1> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing
xI6<2> VSSA VDDA VSSA on<2> op<2> oo<2> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing
xI6<3> VSSA VDDA VSSA on<3> op<3> oo<3> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing
xI6<4> VSSA VDDA VSSA on<4> op<4> oo<4> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing
xI6<5> VSSA VDDA VSSA on<5> op<5> oo<5> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing
xI6<6> VSSA VDDA VSSA on<6> op<6> oo<6> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing
xI6<7> VSSA VDDA VSSA on<7> op<7> oo<7> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing
xI6<8> VSSA VDDA VSSA on<8> op<8> oo<8> diff2sing_v1 _ar0=fin_p_diff2sing _ar1=width_p_diff2sing _ar2=fin_n_diff2sing _ar3=width_n_diff2sing

xI1 VDDA VSSA op<1> op<2> op<3> op<4> op<5> op<6> op<7> op<8> on<1> vbias VCO_type2_65 _ar0=fin_n_vco_type_2 _ar1=wnnn _ar2=fnnn _ar3=fin_p_vco_type_2 _ar4=fppp _ar5=wpppn

xI0 VDDA VSSA on<1> on<2> on<3> on<4> on<5> on<6> on<7> on<8> op<1> vbias VCO_type2_65 _ar0=fin_n_vco_type_2 _ar1=wnnn _ar2=fnnn _ar3=fin_p_vco_type_2 _ar4=fppp _ar5=wpppn
.ends vco_dtype_12_hierarchical

