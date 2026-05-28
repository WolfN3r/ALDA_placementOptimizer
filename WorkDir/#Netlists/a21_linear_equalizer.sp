* ============================================================
* Circuit : linear_equalizer
* Source  : ALIGN analog layout examples
* File    : linear_equalizer\linear_equalizer.sp
* ============================================================
* Stats:
*   Subcircuits  : 2
*   Devices (M)  : 4
*   Device types : nmos_rvt
*   Passives     : 4 resistors, 2 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param nfet2x_MN0_L=0.014u nfet2x_MN0_W=12
.param nfet2x_MN1_L=0.014u nfet2x_MN1_W=12
.param linear_equalizer_MN9_L=0.014u linear_equalizer_MN9_W=12
.param linear_equalizer_MN6_L=0.014u linear_equalizer_MN6_W=12


* --- CIRCUIT DEFINITION ---
.subckt nfet2x d g s b
.param p1=2
    MN0 d g n1 b nmos_rvt L={nfet2x_MN0_L} W={nfet2x_MN0_W} Nf=p1
    MN1 n1 g s b nmos_rvt L={nfet2x_MN1_L} W={nfet2x_MN1_W} Nf=p1
.ends nfet2x

.subckt linear_equalizer vmirror_ctle s0_ctle s3_ctle vin1 vin2 vout_ctle1 vout_ctle2 VDDA VSSA
.param nfpf_cm=6 nfpf_dp=4 nfpf_sw=4 Rsw=100 Csw=3464n rl=800

	xI0 vout_ctle2 vin2 net8 VSSA nfet2x p1=nfpf_dp
	xI1 vout_ctle1 vin1 net5 VSSA nfet2x p1=nfpf_dp
	xI4 vmirror_ctle vmirror_ctle VSSA VSSA nfet2x p1=nfpf_cm
	xI3 net5 vmirror_ctle VSSA VSSA nfet2x p1=nfpf_cm
	xI2 net8 vmirror_ctle VSSA VSSA nfet2x p1=nfpf_cm
	R1 VDDA vout_ctle2 resistor r=rl
	R0 VDDA vout_ctle1 resistor r=rl
	C4 net021 net8 capacitor w=Csw l=Csw
	C3 net5 net022 capacitor w=Csw l=Csw
	R4 net5 net016 resistor r=Rsw
	R3 net015 net8 resistor r=Rsw
	MN9 net021 s3_ctle net022 VSSA nmos_rvt L={linear_equalizer_MN9_L} W={linear_equalizer_MN9_W} Nf=nfpf_sw
	MN6 net015 s0_ctle net016 VSSA nmos_rvt L={linear_equalizer_MN6_L} W={linear_equalizer_MN6_W} Nf=nfpf_sw
.ends linear_equalizer
