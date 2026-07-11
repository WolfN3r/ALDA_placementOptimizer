* ============================================================
* Circuit : single_to_differential_converter
* Source  : ALIGN analog layout examples
* File    : single_to_differential_converter\single_to_differential_converter.sp
* ============================================================
* Stats:
*   Subcircuits  : 2
*   Devices (M)  : 2
*   Device types : nmos_rvt
*   Passives     : 3 resistors, 3 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
* SIZES CONVERTED 2026-07-10 scale=7.14286 source_L_ref=0.014um
*       Device/passive sizes are scaled from the real source-netlist values
*       (see marker above) -- not random placeholders.
* ============================================================

* --- DEVICE PARAMETERS ---
.param res_single_to_differential_converter_R2_L=200 res_single_to_differential_converter_R2_W=1
.param res_single_to_differential_converter_R1_L=9 res_single_to_differential_converter_R1_W=1
.param res_single_to_differential_converter_R0_L=9 res_single_to_differential_converter_R0_W=1
.param nfet2x_MN0_L=0.1 nfet2x_MN0_Nf=2
.param nfet2x_MN1_L=0.1 nfet2x_MN1_Nf=2


* --- CIRCUIT DEFINITION ---

.param nfpf=30 ngf=1 rbias=20k rload=900 	vbias=600m vps=0.85

.subckt nfet2x d g s b
.param p1=30
    MN0 d g n1 b nmos_rvt L={nfet2x_MN0_L} W=p1 Nf={nfet2x_MN0_Nf}
    MN1 n1 g s b nmos_rvt L={nfet2x_MN1_L} W=p1 Nf={nfet2x_MN1_Nf}
.ends nfet2x

.subckt single_to_differential_converter vb vin vout_sdc1 vout_sdc2 VDDA VSSA
.param fin_count=12 rb=20k rl=900 cc=50 cl=50

	xI0 vd net1 vs VSSA nfet2x p1=fin_count
	R2 vb net1 resistor r=rb L={res_single_to_differential_converter_R2_L} W={res_single_to_differential_converter_R2_W}
	R1 vs VSSA resistor r=rl L={res_single_to_differential_converter_R1_L} W={res_single_to_differential_converter_R1_W}
	R0 VDDA vd resistor r=rl L={res_single_to_differential_converter_R0_L} W={res_single_to_differential_converter_R0_W}
	C2 vs vout_sdc2 capacitor W=cl L=cl
	C1 vd vout_sdc1 capacitor W=cl L=cl
	C0 vin net1 capacitor W=cc L=cc
.ends single_to_differential_converter
