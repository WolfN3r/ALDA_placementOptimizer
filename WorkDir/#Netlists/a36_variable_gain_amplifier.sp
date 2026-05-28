* ============================================================
* Circuit : variable_gain_amplifier
* Source  : ALIGN analog layout examples
* File    : variable_gain_amplifier\variable_gain_amplifier.sp
* ============================================================
* Stats:
*   Subcircuits  : 1
*   Devices (M)  : 17
*   Device types : nmos_rvt
*   Passives     : 2 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param M03_M=1 M03_Nf=6
.param M02_M=1 M02_Nf=6
.param M01_M=1 M01_Nf=4
.param M00_Nf=4
.param Msw0_L=0.014u Msw0_Nf=6
.param Msw1_L=0.014u Msw1_Nf=6
.param M12_Nf=6
.param M11_Nf=4
.param M10_Nf=4
.param Msw2_L=0.014u Msw2_Nf=6
.param M22_Nf=6
.param M21_Nf=4
.param M20_Nf=4
.param Msw3_L=0.014u Msw3_Nf=6
.param M32_Nf=6
.param M31_Nf=4
.param M30_Nf=4


* --- CIRCUIT DEFINITION ---
.subckt variable_gain_amplifier vmirror_vga s0 s1 s2 s3 vin1 vin2 vout_vga1 vout_vga2 VDDA VSSA
.param nfpf_sw=12 nfpf_cm=12 nfpf_dp=12 rl=400

        M03 vmirror_vga vmirror_vga VSSA VSSA nmos_rvt W=nfpf_cm M={M03_M} Nf={M03_Nf}
		M02 net3p vmirror_vga VSSA VSSA nmos_rvt W=nfpf_cm M={M02_M} Nf={M02_Nf}
		M01 vout_vga2 vin2 net3 VSSA nmos_rvt W=nfpf_dp M={M01_M} Nf={M01_Nf}
		M00 vout_vga1 vin1 net3 VSSA nmos_rvt W=nfpf_dp Nf={M00_Nf}
		Msw0 net3 s0 net3p VSSA nmos_rvt L={Msw0_L} W=nfpf_sw Nf={Msw0_Nf}
		Msw1 net5 s1 net5p VSSA nmos_rvt L={Msw1_L} W=nfpf_sw Nf={Msw1_Nf}
		M12 net5p vmirror_vga VSSA VSSA nmos_rvt W=nfpf_cm Nf={M12_Nf}
		M11 vout_vga2 vin2 net5 VSSA nmos_rvt W=nfpf_dp Nf={M11_Nf}
		M10 vout_vga1 vin1 net5 VSSA nmos_rvt W=nfpf_dp Nf={M10_Nf}
		Msw2 net4 s2 net4p VSSA nmos_rvt L={Msw2_L} W=nfpf_sw Nf={Msw2_Nf}
		M22 net4p vmirror_vga VSSA VSSA nmos_rvt W=nfpf_cm Nf={M22_Nf}
		M21 vout_vga2 vin2 net4 VSSA nmos_rvt W=nfpf_dp Nf={M21_Nf}
		M20 vout_vga1 vin1 net4 VSSA nmos_rvt W=nfpf_dp Nf={M20_Nf}
		Msw3 net6 s3 net6p VSSA nmos_rvt L={Msw3_L} W=nfpf_sw Nf={Msw3_Nf}
		M32 net6p vmirror_vga VSSA VSSA nmos_rvt W=nfpf_cm Nf={M32_Nf}
		M31 vout_vga2 vin2 net6 VSSA nmos_rvt W=nfpf_dp Nf={M31_Nf}
		M30 vout_vga1 vin1 net6 VSSA nmos_rvt W=nfpf_dp Nf={M30_Nf}
		R5 VDDA vout_vga2 rl
		R6 VDDA vout_vga1 rl
.ends variable_gain_amplifier
