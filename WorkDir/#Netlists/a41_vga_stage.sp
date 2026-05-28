* ============================================================
* Circuit : vga_stage
* Source  : ALIGN analog layout examples
* File    : vga_stage\vga_stage.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 4
*   Device types : nmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param M02_M=1 M02_Nf=6
.param M01_M=1 M01_Nf=4
.param M00_Nf=4
.param Msw0_L=0.014u Msw0_Nf=6


* --- CIRCUIT DEFINITION ---
.subckt vga_stage vmirror_vga s0 vin1 vin2 vout_vga1 vout_vga2 VSSA
.param nfpf_sw=12 nfpf_cm=12 nfpf_dp=12 rl=400
	M02 net3p vmirror_vga VSSA VSSA nmos_rvt W=nfpf_cm M={M02_M} Nf={M02_Nf}
	M01 vout_vga2 vin2 net3 VSSA nmos_rvt W=nfpf_dp M={M01_M} Nf={M01_Nf}
	M00 vout_vga1 vin1 net3 VSSA nmos_rvt W=nfpf_dp Nf={M00_Nf}
	Msw0 net3 s0 net3p VSSA nmos_rvt L={Msw0_L} W=nfpf_sw Nf={Msw0_Nf}
.ends vga_stage

