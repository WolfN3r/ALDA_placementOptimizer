* ============================================================
* Circuit : mimo_bulk
* Source  : ALIGN analog layout examples
* File    : mimo_bulk\mimo_bulk.sp
* ============================================================
* Stats:
*   Subcircuits  : 21
*   Devices (M)  : 88
*   Device types : nmos_lvt nmos_rvt pmos_rvt
*   Passives     : 12 resistors, 20 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param TIA_1_m1_L=400e-9 TIA_1_m1_W=64e-6 TIA_1_m1_M=1 TIA_1_m1_Nf=8
.param TIA_1_m0_L=400e-9 TIA_1_m0_W=64e-6 TIA_1_m0_M=1 TIA_1_m0_Nf=8
.param TIA_1_m5_L=200e-9 TIA_1_m5_W=32e-6 TIA_1_m5_M=1 TIA_1_m5_Nf=8
.param TIA_1_m4_L=200e-9 TIA_1_m4_W=32e-6 TIA_1_m4_M=1 TIA_1_m4_Nf=8
.param TIA_1_m3_L=200e-9 TIA_1_m3_W=192e-6 TIA_1_m3_M=1 TIA_1_m3_Nf=32
.param TIA_1_m2_L=200e-9 TIA_1_m2_W=192e-6 TIA_1_m2_M=1 TIA_1_m2_Nf=32
.param bottom_plate_4path_beamforming_m15_L=60e-9 bottom_plate_4path_beamforming_m15_W=2e-6 bottom_plate_4path_beamforming_m15_Nf=16
.param bottom_plate_4path_beamforming_m14_L=60e-9 bottom_plate_4path_beamforming_m14_W=2e-6 bottom_plate_4path_beamforming_m14_Nf=16
.param bottom_plate_4path_beamforming_m13_L=60e-9 bottom_plate_4path_beamforming_m13_W=2e-6 bottom_plate_4path_beamforming_m13_Nf=16
.param bottom_plate_4path_beamforming_m12_L=60e-9 bottom_plate_4path_beamforming_m12_W=2e-6 bottom_plate_4path_beamforming_m12_Nf=16
.param bottom_plate_4path_beamforming_m11_L=60e-9 bottom_plate_4path_beamforming_m11_W=2e-6 bottom_plate_4path_beamforming_m11_Nf=16
.param bottom_plate_4path_beamforming_m10_L=60e-9 bottom_plate_4path_beamforming_m10_W=2e-6 bottom_plate_4path_beamforming_m10_Nf=16
.param bottom_plate_4path_beamforming_m9_L=60e-9 bottom_plate_4path_beamforming_m9_W=2e-6 bottom_plate_4path_beamforming_m9_Nf=16
.param bottom_plate_4path_beamforming_m8_L=60e-9 bottom_plate_4path_beamforming_m8_W=2e-6 bottom_plate_4path_beamforming_m8_Nf=16
.param bottom_plate_4path_beamforming_m7_L=60e-9 bottom_plate_4path_beamforming_m7_W=2e-6 bottom_plate_4path_beamforming_m7_Nf=16
.param bottom_plate_4path_beamforming_m6_L=60e-9 bottom_plate_4path_beamforming_m6_W=2e-6 bottom_plate_4path_beamforming_m6_Nf=16
.param bottom_plate_4path_beamforming_m5_L=60e-9 bottom_plate_4path_beamforming_m5_W=2e-6 bottom_plate_4path_beamforming_m5_Nf=16
.param bottom_plate_4path_beamforming_m4_L=60e-9 bottom_plate_4path_beamforming_m4_W=2e-6 bottom_plate_4path_beamforming_m4_Nf=16
.param bottom_plate_4path_beamforming_m3_L=60e-9 bottom_plate_4path_beamforming_m3_W=2e-6 bottom_plate_4path_beamforming_m3_Nf=16
.param bottom_plate_4path_beamforming_m2_L=60e-9 bottom_plate_4path_beamforming_m2_W=2e-6 bottom_plate_4path_beamforming_m2_Nf=16
.param bottom_plate_4path_beamforming_m1_L=60e-9 bottom_plate_4path_beamforming_m1_W=2e-6 bottom_plate_4path_beamforming_m1_Nf=16
.param bottom_plate_4path_beamforming_m0_L=60e-9 bottom_plate_4path_beamforming_m0_W=2e-6 bottom_plate_4path_beamforming_m0_Nf=16
.param INVx1_8Phase_m1_L=60e-9 INVx1_8Phase_m1_W=1.2e-6 INVx1_8Phase_m1_Nf=4
.param INVx1_8Phase_m0_L=60e-9 INVx1_8Phase_m0_W=600e-9 INVx1_8Phase_m0_Nf=4
.param CLK_IO_m6_L=60e-9 CLK_IO_m6_W=300e-9 CLK_IO_m6_Nf=2
.param CLK_IO_m4_L=60e-9 CLK_IO_m4_W=300e-9 CLK_IO_m4_Nf=2
.param CLK_IO_m0_L=60e-9 CLK_IO_m0_W=300e-9 CLK_IO_m0_Nf=2
.param CLK_IO_m2_L=60e-9 CLK_IO_m2_W=300e-9 CLK_IO_m2_Nf=2
.param CLK_IO_m7_L=60e-9 CLK_IO_m7_W=300e-9 CLK_IO_m7_Nf=2
.param CLK_IO_m5_L=60e-9 CLK_IO_m5_W=300e-9 CLK_IO_m5_Nf=2
.param CLK_IO_m3_L=60e-9 CLK_IO_m3_W=7.5e-7 CLK_IO_m3_Nf=2
.param CLK_IO_m1_L=60e-9 CLK_IO_m1_W=7.5e-7 CLK_IO_m1_Nf=2
.param INVx1_8Phase_schematic_m1_L=60e-9 INVx1_8Phase_schematic_m1_W=1.2e-6 INVx1_8Phase_schematic_m1_Nf=4
.param INVx1_8Phase_schematic_m0_L=60e-9 INVx1_8Phase_schematic_m0_W=600e-9 INVx1_8Phase_schematic_m0_Nf=4
.param INVx4_8Phase_m1_L=60e-9 INVx4_8Phase_m1_W=1.2e-6 INVx4_8Phase_m1_Nf=16
.param INVx4_8Phase_m0_L=60e-9 INVx4_8Phase_m0_W=600e-9 INVx4_8Phase_m0_Nf=16
.param AND2_m4_L=60e-9 AND2_m4_W=600e-9 AND2_m4_Nf=4
.param AND2_m6_L=60e-9 AND2_m6_W=600e-9 AND2_m6_Nf=4
.param AND2_m5_L=60e-9 AND2_m5_W=600e-9 AND2_m5_Nf=4
.param AND2_m13_L=60e-9 AND2_m13_W=1.2e-6 AND2_m13_Nf=4
.param AND2_m14_L=60e-9 AND2_m14_W=1.2e-6 AND2_m14_Nf=4
.param AND2_m1_L=60e-9 AND2_m1_W=1.2e-6 AND2_m1_Nf=4
.param FF_DTG_m1_L=60e-9 FF_DTG_m1_W=600e-9 FF_DTG_m1_Nf=4
.param FF_DTG_m2_L=60e-9 FF_DTG_m2_W=600e-9 FF_DTG_m2_Nf=4
.param FF_DTG_m3_L=60e-9 FF_DTG_m3_W=600e-9 FF_DTG_m3_Nf=4
.param FF_DTG_m5_L=60e-9 FF_DTG_m5_W=600e-9 FF_DTG_m5_Nf=4
.param FF_DTG_m14_L=60e-9 FF_DTG_m14_W=600e-9 FF_DTG_m14_Nf=4
.param FF_DTG_m12_L=60e-9 FF_DTG_m12_W=600e-9 FF_DTG_m12_Nf=4
.param FF_DTG_m11_L=60e-9 FF_DTG_m11_W=600e-9 FF_DTG_m11_Nf=4
.param FF_DTG_m6_L=60e-9 FF_DTG_m6_W=600e-9 FF_DTG_m6_Nf=4
.param FF_DTG_m10_L=60e-9 FF_DTG_m10_W=600e-9 FF_DTG_m10_Nf=4
.param FF_DTG_m20_L=60e-9 FF_DTG_m20_W=1.2e-6 FF_DTG_m20_Nf=4
.param FF_DTG_m0_L=60e-9 FF_DTG_m0_W=1.2e-6 FF_DTG_m0_Nf=4
.param FF_DTG_m4_L=60e-9 FF_DTG_m4_W=1.2e-6 FF_DTG_m4_Nf=4
.param FF_DTG_m8_L=60e-9 FF_DTG_m8_W=1.2e-6 FF_DTG_m8_Nf=4
.param FF_DTG_m7_L=60e-9 FF_DTG_m7_W=1.2e-6 FF_DTG_m7_Nf=4
.param FF_DTG_m17_L=60e-9 FF_DTG_m17_W=1.2e-6 FF_DTG_m17_Nf=4
.param FF_DTG_m13_L=60e-9 FF_DTG_m13_W=1.2e-6 FF_DTG_m13_Nf=4
.param FF_DTG_m16_L=60e-9 FF_DTG_m16_W=1.2e-6 FF_DTG_m16_Nf=4
.param FF_DTG_m9_L=60e-9 FF_DTG_m9_W=1.2e-6 FF_DTG_m9_Nf=4
.param Divider_m3<0>_L=60e-9 Divider_m3<0>_W=600e-9 Divider_m3<0>_Nf=4
.param Divider_m3<1>_L=60e-9 Divider_m3<1>_W=600e-9 Divider_m3<1>_Nf=4
.param Divider_m3<2>_L=60e-9 Divider_m3<2>_W=600e-9 Divider_m3<2>_Nf=4
.param Divider_m3<3>_L=60e-9 Divider_m3<3>_W=600e-9 Divider_m3<3>_Nf=4
.param Divider_m2<0>_L=60e-9 Divider_m2<0>_W=600e-9 Divider_m2<0>_Nf=4
.param Divider_m2<1>_L=60e-9 Divider_m2<1>_W=600e-9 Divider_m2<1>_Nf=4
.param Divider_m2<2>_L=60e-9 Divider_m2<2>_W=600e-9 Divider_m2<2>_Nf=4
.param Divider_m2<3>_L=60e-9 Divider_m2<3>_W=600e-9 Divider_m2<3>_Nf=4
.param Divider_m0<0>_L=60e-9 Divider_m0<0>_W=1.2e-6 Divider_m0<0>_Nf=4
.param Divider_m0<1>_L=60e-9 Divider_m0<1>_W=1.2e-6 Divider_m0<1>_Nf=4
.param Divider_m0<2>_L=60e-9 Divider_m0<2>_W=1.2e-6 Divider_m0<2>_Nf=4
.param Divider_m0<3>_L=60e-9 Divider_m0<3>_W=1.2e-6 Divider_m0<3>_Nf=4
.param Divider_m1<0>_L=60e-9 Divider_m1<0>_W=1.2e-6 Divider_m1<0>_Nf=4
.param Divider_m1<1>_L=60e-9 Divider_m1<1>_W=1.2e-6 Divider_m1<1>_Nf=4
.param Divider_m1<2>_L=60e-9 Divider_m1<2>_W=1.2e-6 Divider_m1<2>_Nf=4
.param Divider_m1<3>_L=60e-9 Divider_m1<3>_W=1.2e-6 Divider_m1<3>_Nf=4
.param bottom_plate_4path_mixer_diff_end_m0_L=60e-9 bottom_plate_4path_mixer_diff_end_m0_W=4e-6 bottom_plate_4path_mixer_diff_end_m0_Nf=16
.param bottom_plate_4path_mixer_diff_end_m1_L=60e-9 bottom_plate_4path_mixer_diff_end_m1_W=4e-6 bottom_plate_4path_mixer_diff_end_m1_Nf=16
.param bottom_plate_4path_mixer_diff_end_m2_L=60e-9 bottom_plate_4path_mixer_diff_end_m2_W=4e-6 bottom_plate_4path_mixer_diff_end_m2_Nf=16
.param bottom_plate_4path_mixer_diff_end_m3_L=60e-9 bottom_plate_4path_mixer_diff_end_m3_W=4e-6 bottom_plate_4path_mixer_diff_end_m3_Nf=16
.param bottom_plate_4path_mixer_diff_end_m4_L=60e-9 bottom_plate_4path_mixer_diff_end_m4_W=4e-6 bottom_plate_4path_mixer_diff_end_m4_Nf=16
.param bottom_plate_4path_mixer_diff_end_m5_L=60e-9 bottom_plate_4path_mixer_diff_end_m5_W=4e-6 bottom_plate_4path_mixer_diff_end_m5_Nf=16
.param bottom_plate_4path_mixer_diff_end_m6_L=60e-9 bottom_plate_4path_mixer_diff_end_m6_W=4e-6 bottom_plate_4path_mixer_diff_end_m6_Nf=16
.param bottom_plate_4path_mixer_diff_end_m7_L=60e-9 bottom_plate_4path_mixer_diff_end_m7_W=4e-6 bottom_plate_4path_mixer_diff_end_m7_Nf=16
.param bottom_plate_4path_mixer_diff_end_m8_L=60e-9 bottom_plate_4path_mixer_diff_end_m8_W=4e-6 bottom_plate_4path_mixer_diff_end_m8_Nf=16
.param bottom_plate_4path_mixer_diff_end_m9_L=60e-9 bottom_plate_4path_mixer_diff_end_m9_W=4e-6 bottom_plate_4path_mixer_diff_end_m9_Nf=16
.param bottom_plate_4path_mixer_diff_end_m10_L=60e-9 bottom_plate_4path_mixer_diff_end_m10_W=4e-6 bottom_plate_4path_mixer_diff_end_m10_Nf=16
.param bottom_plate_4path_mixer_diff_end_m11_L=60e-9 bottom_plate_4path_mixer_diff_end_m11_W=4e-6 bottom_plate_4path_mixer_diff_end_m11_Nf=16


* --- HELPER SUBCKTS (split-resistor wrappers) ---
.subckt res8 n1 n2
.param seg_r=100
r1 n1 x1 {seg_r}
r2 x1 x2 {seg_r}
r3 x2 x3 {seg_r}
r4 x3 x4 {seg_r}
r5 x4 x5 {seg_r}
r6 x5 x6 {seg_r}
r7 x6 x7 {seg_r}
r8 x7 n2 {seg_r}
.ends res8

.subckt res18 n1 n2
.param seg_r=200
r1 n1 x1 {seg_r}
r2 x1 x2 {seg_r}
r3 x2 x3 {seg_r}
r4 x3 x4 {seg_r}
r5 x4 x5 {seg_r}
r6 x5 x6 {seg_r}
r7 x6 x7 {seg_r}
r8 x7 x8 {seg_r}
r9 x8 x9 {seg_r}
r10 x9 x10 {seg_r}
r11 x10 x11 {seg_r}
r12 x11 x12 {seg_r}
r13 x12 x13 {seg_r}
r14 x13 x14 {seg_r}
r15 x14 x15 {seg_r}
r16 x15 x16 {seg_r}
r17 x16 x17 {seg_r}
r18 x17 n2 {seg_r}
.ends res18


* --- CIRCUIT DEFINITION ---
** Generated for: hspiceD
** Generated on: Mar  6 10:41:14 2021
** Design library name: TO65_20200429
** Design cell name: mimo_bulk
** Design view name: schematic



.TEMP 25.0
.OPTION ARTIST=2 INGOLD=2 PARHIER=LOCAL PSF=2

** Library name: TO65_20200429
** Cell name: TIA_1
** View name: schematic
.subckt TIA_1 _net3 _net1 _net0 _net2 VDDA VSSA
m1 _net0 _net1 VSSA VSSA nmos_lvt L={TIA_1_m1_L} W={TIA_1_m1_W} M={TIA_1_m1_M} Nf={TIA_1_m1_Nf}
m0 _net2 _net3 VSSA VSSA nmos_lvt L={TIA_1_m0_L} W={TIA_1_m0_W} M={TIA_1_m0_M} Nf={TIA_1_m0_Nf}
m5 net13 _net0 VDDA VDDA pmos_rvt L={TIA_1_m5_L} W={TIA_1_m5_W} M={TIA_1_m5_M} Nf={TIA_1_m5_Nf}
m4 net13 _net2 VDDA VDDA pmos_rvt L={TIA_1_m4_L} W={TIA_1_m4_W} M={TIA_1_m4_M} Nf={TIA_1_m4_Nf}
m3 _net0 _net1 net13 net13 pmos_rvt L={TIA_1_m3_L} W={TIA_1_m3_W} M={TIA_1_m3_M} Nf={TIA_1_m3_Nf}
m2 _net2 _net3 net13 net13 pmos_rvt L={TIA_1_m2_L} W={TIA_1_m2_W} M={TIA_1_m2_M} Nf={TIA_1_m2_Nf}
.ends TIA_1
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: bottom_plate_4path_beamforming
** View name: schematic
.subckt bottom_plate_4path_beamforming clk_x1 clk_x1_b clk_x2 clk_x2_b clk_x3 clk_x3_b clk_x4 clk_x4_b _net19 _net17 vcmbias VDDA VSSA _net11 _net6 _net10 _net4 _net9 _net2 _net8 _net0
m15 _net0 clk_x4 _net1 _net1 nmos_rvt L={bottom_plate_4path_beamforming_m15_L} W={bottom_plate_4path_beamforming_m15_W} Nf={bottom_plate_4path_beamforming_m15_Nf}
m14 _net2 clk_x3 _net3 _net3 nmos_rvt L={bottom_plate_4path_beamforming_m14_L} W={bottom_plate_4path_beamforming_m14_W} Nf={bottom_plate_4path_beamforming_m14_Nf}
m13 _net4 clk_x2 _net5 _net5 nmos_rvt L={bottom_plate_4path_beamforming_m13_L} W={bottom_plate_4path_beamforming_m13_W} Nf={bottom_plate_4path_beamforming_m13_Nf}
m12 _net6 clk_x1 _net7 _net7 nmos_rvt L={bottom_plate_4path_beamforming_m12_L} W={bottom_plate_4path_beamforming_m12_W} Nf={bottom_plate_4path_beamforming_m12_Nf}
m11 _net8 clk_x4_b _net1 _net1 nmos_rvt L={bottom_plate_4path_beamforming_m11_L} W={bottom_plate_4path_beamforming_m11_W} Nf={bottom_plate_4path_beamforming_m11_Nf}
m10 _net9 clk_x3_b _net3 _net3 nmos_rvt L={bottom_plate_4path_beamforming_m10_L} W={bottom_plate_4path_beamforming_m10_W} Nf={bottom_plate_4path_beamforming_m10_Nf}
m9 _net10 clk_x2_b _net5 _net5 nmos_rvt L={bottom_plate_4path_beamforming_m9_L} W={bottom_plate_4path_beamforming_m9_W} Nf={bottom_plate_4path_beamforming_m9_Nf}
m8 _net11 clk_x1_b _net7 _net7 nmos_rvt L={bottom_plate_4path_beamforming_m8_L} W={bottom_plate_4path_beamforming_m8_W} Nf={bottom_plate_4path_beamforming_m8_Nf}
m7 _net0 clk_x4_b _net12 _net12 nmos_rvt L={bottom_plate_4path_beamforming_m7_L} W={bottom_plate_4path_beamforming_m7_W} Nf={bottom_plate_4path_beamforming_m7_Nf}
m6 _net2 clk_x3_b _net13 _net13 nmos_rvt L={bottom_plate_4path_beamforming_m6_L} W={bottom_plate_4path_beamforming_m6_W} Nf={bottom_plate_4path_beamforming_m6_Nf}
m5 _net4 clk_x2_b _net14 _net14 nmos_rvt L={bottom_plate_4path_beamforming_m5_L} W={bottom_plate_4path_beamforming_m5_W} Nf={bottom_plate_4path_beamforming_m5_Nf}
m4 _net6 clk_x1_b _net15 _net15 nmos_rvt L={bottom_plate_4path_beamforming_m4_L} W={bottom_plate_4path_beamforming_m4_W} Nf={bottom_plate_4path_beamforming_m4_Nf}
m3 _net8 clk_x4 _net12 _net12 nmos_rvt L={bottom_plate_4path_beamforming_m3_L} W={bottom_plate_4path_beamforming_m3_W} Nf={bottom_plate_4path_beamforming_m3_Nf}
m2 _net9 clk_x3 _net13 _net13 nmos_rvt L={bottom_plate_4path_beamforming_m2_L} W={bottom_plate_4path_beamforming_m2_W} Nf={bottom_plate_4path_beamforming_m2_Nf}
m1 _net10 clk_x2 _net14 _net14 nmos_rvt L={bottom_plate_4path_beamforming_m1_L} W={bottom_plate_4path_beamforming_m1_W} Nf={bottom_plate_4path_beamforming_m1_Nf}
m0 _net11 clk_x1 _net15 _net15 nmos_rvt L={bottom_plate_4path_beamforming_m0_L} W={bottom_plate_4path_beamforming_m0_W} Nf={bottom_plate_4path_beamforming_m0_Nf}
xR18 _net16 _net17 res8

xR16 _net18 _net19 res8
r11 _net1 _net18 140
r10 _net3 _net18 140
r9 _net5 _net18 140
r8 _net7 _net18 140
r3 _net12 _net16 140
r2 _net13 _net16 140
r1 _net14 _net16 140
r0 _net15 _net16 140

c8 _net16 _net17 2e-12
c9 _net18 _net19 2e-12
c4 _net7 vcmbias 2e-12
c5 _net5 vcmbias 2e-12
c7 _net1 vcmbias 2e-12
c6 _net3 vcmbias 2e-12
c2 _net13 vcmbias 2e-12
c3 _net12 vcmbias 2e-12
c1 _net15 vcmbias 2e-12
c0 _net14 vcmbias 2e-12
xi0 _net16 _net18 _net19 _net17 VDDA VSSA TIA_1
.ends bottom_plate_4path_beamforming
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: bottom_plate_4path_BB_beamformer
** View name: schematic
.subckt bottom_plate_4path_BB_beamformer _net18 _net19 _net0 _net1 _net20 _net21 _net2 _net3 _net22 _net23 _net4 _net5 _net24 _net25 _net6 _net7 _net27 _net26 _net9 _net8 vcmbias _net10 _net11 _net12 _net13 _net14 _net15 _net16 _net17 vdda_bb vssa_bb
xi1 _net0 _net1 _net2 _net3 _net4 _net5 _net6 _net7 _net8 _net9 vcmbias vdda_bb vssa_bb _net10 _net11 _net12 _net13 _net14 _net15 _net16 _net17 bottom_plate_4path_beamforming
xi0 _net18 _net19 _net20 _net21 _net22 _net23 _net24 _net25 _net26 _net27 vcmbias vdda_bb vssa_bb _net10 _net11 _net12 _net13 _net14 _net15 _net16 _net17 bottom_plate_4path_beamforming
.ends bottom_plate_4path_BB_beamformer
** End of subcircuit definition.

** Library name: Tape_Jan20
** Cell name: INVx1_8Phase
** View name: schematic
.subckt INVx1_8Phase in out VDDD VSSD
m1 out in VDDD VDDD pmos_rvt L={INVx1_8Phase_m1_L} W={INVx1_8Phase_m1_W} Nf={INVx1_8Phase_m1_Nf}
m0 out in VSSD VSSD nmos_rvt L={INVx1_8Phase_m0_L} W={INVx1_8Phase_m0_W} Nf={INVx1_8Phase_m0_Nf}
.ends INVx1_8Phase
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: CLK_IO
** View name: schematic
** Digital
.subckt CLK_IO inn inp outn outp VDDD VSSD
c0 net3 inp 2e-13
c1 net2 inn 2e-13
xR2 bias net3 res18

xR0 net2 bias res18

xi3 net1b outn VDDD VSSD INVx1_8Phase
xi2 net1 outp VDDD VSSD INVx1_8Phase
xi1 net2 net1b VDDD VSSD INVx1_8Phase
xi0 net3 net1 VDDD VSSD INVx1_8Phase
m6 net1 net1b VSSD VSSD nmos_rvt L={CLK_IO_m6_L} W={CLK_IO_m6_W} Nf={CLK_IO_m6_Nf}
m4 net1b net1 VSSD VSSD nmos_rvt L={CLK_IO_m4_L} W={CLK_IO_m4_W} Nf={CLK_IO_m4_Nf}
m0 bias bias net026 VSSD nmos_rvt L={CLK_IO_m0_L} W={CLK_IO_m0_W} Nf={CLK_IO_m0_Nf}
m2 net026 VDDD VSSD VSSD nmos_rvt L={CLK_IO_m2_L} W={CLK_IO_m2_W} Nf={CLK_IO_m2_Nf}
m7 net1 net1b VDDD VDDD pmos_rvt L={CLK_IO_m7_L} W={CLK_IO_m7_W} Nf={CLK_IO_m7_Nf}
m5 net1b net1 VDDD VDDD pmos_rvt L={CLK_IO_m5_L} W={CLK_IO_m5_W} Nf={CLK_IO_m5_Nf}
m3 net011 VSSD VDDD VDDD pmos_rvt L={CLK_IO_m3_L} W={CLK_IO_m3_W} Nf={CLK_IO_m3_Nf}
m1 bias bias net011 VDDD pmos_rvt L={CLK_IO_m1_L} W={CLK_IO_m1_W} Nf={CLK_IO_m1_Nf}
.ends CLK_IO
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: INVx1_8Phase
** View name: schematic
.subckt INVx1_8Phase_schematic in out VDDD VSSD
m1 out in VDDD VDDD pmos_rvt L={INVx1_8Phase_schematic_m1_L} W={INVx1_8Phase_schematic_m1_W} Nf={INVx1_8Phase_schematic_m1_Nf}
m0 out in VSSD VSSD nmos_rvt L={INVx1_8Phase_schematic_m0_L} W={INVx1_8Phase_schematic_m0_W} Nf={INVx1_8Phase_schematic_m0_Nf}
.ends INVx1_8Phase_schematic
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: INVx4_8Phase
** View name: schematic
.subckt INVx4_8Phase in out VDDD VSSD
m1 out in VDDD VDDD pmos_rvt L={INVx4_8Phase_m1_L} W={INVx4_8Phase_m1_W} Nf={INVx4_8Phase_m1_Nf}
m0 out in VSSD VSSD nmos_rvt L={INVx4_8Phase_m0_L} W={INVx4_8Phase_m0_W} Nf={INVx4_8Phase_m0_Nf}
.ends INVx4_8Phase
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: AND2
** View name: schematic
.subckt AND2 a b out VDDD VSSD
m4 net26 b VSSD VSSD nmos_rvt L={AND2_m4_L} W={AND2_m4_W} Nf={AND2_m4_Nf}
m6 out net21 VSSD VSSD nmos_rvt L={AND2_m6_L} W={AND2_m6_W} Nf={AND2_m6_Nf}
m5 net21 a net26 VSSD nmos_rvt L={AND2_m5_L} W={AND2_m5_W} Nf={AND2_m5_Nf}
m13 net21 b VDDD VDDD pmos_rvt L={AND2_m13_L} W={AND2_m13_W} Nf={AND2_m13_Nf}
m14 net21 a VDDD VDDD pmos_rvt L={AND2_m14_L} W={AND2_m14_W} Nf={AND2_m14_Nf}
m1 out net21 VDDD VDDD pmos_rvt L={AND2_m1_L} W={AND2_m1_W} Nf={AND2_m1_Nf}
.ends AND2
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: FF_DTG
** View name: schematic
** Digital
.subckt FF_DTG clk clkb in out0 out90 out180 out270 set setb VDDD VSSD
m1 in setb VSSD VSSD nmos_rvt L={FF_DTG_m1_L} W={FF_DTG_m1_W} Nf={FF_DTG_m1_Nf}
m2 net59 in VSSD VSSD nmos_rvt L={FF_DTG_m2_L} W={FF_DTG_m2_W} Nf={FF_DTG_m2_Nf}
m3 net_l1 out90 VSSD VSSD nmos_rvt L={FF_DTG_m3_L} W={FF_DTG_m3_W} Nf={FF_DTG_m3_Nf}
m5 net023 net_l1 VSSD VSSD nmos_rvt L={FF_DTG_m5_L} W={FF_DTG_m5_W} Nf={FF_DTG_m5_Nf}
m14 net59 clkb out90 VSSD nmos_rvt L={FF_DTG_m14_L} W={FF_DTG_m14_W} Nf={FF_DTG_m14_Nf}
m12 net_l1 clk out0 VSSD nmos_rvt L={FF_DTG_m12_L} W={FF_DTG_m12_W} Nf={FF_DTG_m12_Nf}
m11 net023 clk out180 VSSD nmos_rvt L={FF_DTG_m11_L} W={FF_DTG_m11_W} Nf={FF_DTG_m11_Nf}
m6 net026 net59 VSSD VSSD nmos_rvt L={FF_DTG_m6_L} W={FF_DTG_m6_W} Nf={FF_DTG_m6_Nf}
m10 net026 clkb out270 VSSD nmos_rvt L={FF_DTG_m10_L} W={FF_DTG_m10_W} Nf={FF_DTG_m10_Nf}
m20 out90 clk net59 VDDD pmos_rvt L={FF_DTG_m20_L} W={FF_DTG_m20_W} Nf={FF_DTG_m20_Nf}
m0 in set VDDD VDDD pmos_rvt L={FF_DTG_m0_L} W={FF_DTG_m0_W} Nf={FF_DTG_m0_Nf}
m4 net59 in VDDD VDDD pmos_rvt L={FF_DTG_m4_L} W={FF_DTG_m4_W} Nf={FF_DTG_m4_Nf}
m8 net023 net_l1 VDDD VDDD pmos_rvt L={FF_DTG_m8_L} W={FF_DTG_m8_W} Nf={FF_DTG_m8_Nf}
m7 net_l1 out90 VDDD VDDD pmos_rvt L={FF_DTG_m7_L} W={FF_DTG_m7_W} Nf={FF_DTG_m7_Nf}
m17 out0 clkb net_l1 VDDD pmos_rvt L={FF_DTG_m17_L} W={FF_DTG_m17_W} Nf={FF_DTG_m17_Nf}
m13 out270 clk net026 VDDD pmos_rvt L={FF_DTG_m13_L} W={FF_DTG_m13_W} Nf={FF_DTG_m13_Nf}
m16 out180 clkb net023 VDDD pmos_rvt L={FF_DTG_m16_L} W={FF_DTG_m16_W} Nf={FF_DTG_m16_Nf}
m9 net026 net59 VDDD VDDD pmos_rvt L={FF_DTG_m9_L} W={FF_DTG_m9_W} Nf={FF_DTG_m9_Nf}
.ends FF_DTG
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: Divider
** View name: schematic
** Digital
.subckt Divider clk clkb out<0> out<90> out<180> out<270> set setb VDDD VSSD
xi0 clk clkb d<180> d<0> d<90> d<180> d<270> set setb VDDD VSSD FF_DTG
m3<0> out<0> net012<0> VSSD VSSD nmos_rvt L={Divider_m3<0>_L} W={Divider_m3<0>_W} Nf={Divider_m3<0>_Nf}
m3<1> out<90> net012<1> VSSD VSSD nmos_rvt L={Divider_m3<1>_L} W={Divider_m3<1>_W} Nf={Divider_m3<1>_Nf}
m3<2> out<180> net012<2> VSSD VSSD nmos_rvt L={Divider_m3<2>_L} W={Divider_m3<2>_W} Nf={Divider_m3<2>_Nf}
m3<3> out<270> net012<3> VSSD VSSD nmos_rvt L={Divider_m3<3>_L} W={Divider_m3<3>_W} Nf={Divider_m3<3>_Nf}
m2<0> net012<0> d<0> VSSD VSSD nmos_rvt L={Divider_m2<0>_L} W={Divider_m2<0>_W} Nf={Divider_m2<0>_Nf}
m2<1> net012<1> d<90> VSSD VSSD nmos_rvt L={Divider_m2<1>_L} W={Divider_m2<1>_W} Nf={Divider_m2<1>_Nf}
m2<2> net012<2> d<180> VSSD VSSD nmos_rvt L={Divider_m2<2>_L} W={Divider_m2<2>_W} Nf={Divider_m2<2>_Nf}
m2<3> net012<3> d<270> VSSD VSSD nmos_rvt L={Divider_m2<3>_L} W={Divider_m2<3>_W} Nf={Divider_m2<3>_Nf}
m0<0> net012<0> d<0> VDDD VDDD pmos_rvt L={Divider_m0<0>_L} W={Divider_m0<0>_W} Nf={Divider_m0<0>_Nf}
m0<1> net012<1> d<90> VDDD VDDD pmos_rvt L={Divider_m0<1>_L} W={Divider_m0<1>_W} Nf={Divider_m0<1>_Nf}
m0<2> net012<2> d<180> VDDD VDDD pmos_rvt L={Divider_m0<2>_L} W={Divider_m0<2>_W} Nf={Divider_m0<2>_Nf}
m0<3> net012<3> d<270> VDDD VDDD pmos_rvt L={Divider_m0<3>_L} W={Divider_m0<3>_W} Nf={Divider_m0<3>_Nf}
m1<0> out<0> net012<0> VDDD VDDD pmos_rvt L={Divider_m1<0>_L} W={Divider_m1<0>_W} Nf={Divider_m1<0>_Nf}
m1<1> out<90> net012<1> VDDD VDDD pmos_rvt L={Divider_m1<1>_L} W={Divider_m1<1>_W} Nf={Divider_m1<1>_Nf}
m1<2> out<180> net012<2> VDDD VDDD pmos_rvt L={Divider_m1<2>_L} W={Divider_m1<2>_W} Nf={Divider_m1<2>_Nf}
m1<3> out<270> net012<3> VDDD VDDD pmos_rvt L={Divider_m1<3>_L} W={Divider_m1<3>_W} Nf={Divider_m1<3>_Nf}
.ends Divider
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: 4Phase
** View name: schematic
** Digital
.subckt TO65_20200429_4Phase_schematic clk clkb ph<0> ph<1> ph<2> ph<3> set setb VDDD VSSD
xi27<0> d1<0> clkb ph<0> VDDD VSSD AND2
xi27<1> d1<90> clk ph<1> VDDD VSSD AND2
xi27<2> d1<180> clkb ph<2> VDDD VSSD AND2
xi27<3> d1<270> clk ph<3> VDDD VSSD AND2
xi17 clk clkb d1<0> d1<90> d1<180> d1<270> set setb VDDD VSSD Divider
.ends TO65_20200429_4Phase_schematic
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: CLK_DIST_NW1
** View name: schematic
** Digital
.subckt CLK_DIST_NW1 clk clk0 clk180 clk270 clk90 clkb set setb VDDD VSSD
xi3 ph<3> net11 VDDD VSSD INVx1_8Phase_schematic
xi2 ph<2> net10 VDDD VSSD INVx1_8Phase_schematic
xi1 ph<1> net9 VDDD VSSD INVx1_8Phase_schematic
xi0 ph<0> net8 VDDD VSSD INVx1_8Phase_schematic
xi4 net8 clk0 VDDD VSSD INVx4_8Phase
xi5 net9 clk90 VDDD VSSD INVx4_8Phase
xi6 net10 clk180 VDDD VSSD INVx4_8Phase
xi7 net11 clk270 VDDD VSSD INVx4_8Phase
xi28 clk clkb ph<0> ph<1> ph<2> ph<3> set setb VDDD VSSD TO65_20200429_4Phase_schematic
.ends CLK_DIST_NW1
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: CLK_BUFFER_4X
** View name: schematic
** Digital
.subckt CLK_BUFFER_4X in out VDDD VSSD
xi0<0> in net2 VDDD VSSD INVx4_8Phase
xi0<1> in net2 VDDD VSSD INVx4_8Phase
xi0<2> in net2 VDDD VSSD INVx4_8Phase
xi0<3> in net2 VDDD VSSD INVx4_8Phase
xi1<0> net2 out VDDD VSSD INVx4_8Phase
xi1<1> net2 out VDDD VSSD INVx4_8Phase
xi1<2> net2 out VDDD VSSD INVx4_8Phase
xi1<3> net2 out VDDD VSSD INVx4_8Phase
.ends CLK_BUFFER_4X
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: CLK_DIST_NW2
** View name: schematic
** Digital
.subckt CLK_DIST_NW2 clk clk0 clk180 clk270 clk90 clkb set setb VDDD VSSD
xi0 clk clk1 clk3 clk4 clk2 clkb set setb VDDD VSSD CLK_DIST_NW1
xi5 clk4 clk270 VDDD VSSD CLK_BUFFER_4X
xi4 clk3 clk180 VDDD VSSD CLK_BUFFER_4X
xi3 clk2 clk90 VDDD VSSD CLK_BUFFER_4X
xi1 clk1 clk0 VDDD VSSD CLK_BUFFER_4X
.ends CLK_DIST_NW2
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: CLK_IO_DIST_NW1
** View name: schematic
** Digital
.subckt CLK_IO_DIST_NW1 clk0 clk180 clk270 clk90 _net1 _net0 set VDDD VSSD
xi0 _net0 _net1 net15 net16 VDDD VSSD CLK_IO
xi1 net16 clk0 clk180 clk270 clk90 net15 set net14 VDDD VSSD CLK_DIST_NW2
xi2 set net14 VDDD VSSD INVx1_8Phase_schematic
.ends CLK_IO_DIST_NW1
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: CLK4Phase_BUFFER_4X
** View name: schematic
** Digital
.subckt CLK4Phase_BUFFER_4X clk1 clk1_buf clk2 clk2_buf clk3 clk3_buf clk4 clk4_buf VDDD VSSD
xi4 clk3 clk3_buf VDDD VSSD CLK_BUFFER_4X
xi3 clk4 clk4_buf VDDD VSSD CLK_BUFFER_4X
xi2 clk2 clk2_buf VDDD VSSD CLK_BUFFER_4X
xi0 clk1 clk1_buf VDDD VSSD CLK_BUFFER_4X
.ends CLK4Phase_BUFFER_4X
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: MIMO_Beamformers_CLK_NW2
** View name: schematic
.subckt MIMO_Beamformers_CLK_NW2 clk0 clk180 clk270 clk90 _net12 _net13 _net14 _net15 _net0 _net1 _net2 _net3 _net20 _net21 _net22 _net23 _net16 _net17 _net18 _net19 _net24 _net25 set vcmbias vdda_bb VDDD vssa_bb VSSD _net4 _net5 _net6 _net7 _net8 _net9 _net10 _net11
xi11 clk0_k01 clk180_k01 clk90_k01 clk270_k01 clk90_k01 clk270_k01 clk180_k01 clk0_k01 clk180_k01 clk0_k01 clk270_k01 clk90_k01 clk270_k01 clk90_k01 clk0_k01 clk180_k01 _net0 _net1 _net2 _net3 vcmbias _net4 _net5 _net6 _net7 _net8 _net9 _net10 _net11 vdda_bb vssa_bb bottom_plate_4path_BB_beamformer
xi9 clk0_k01 clk180_k01 clk90_k01 clk270_k01 clk0_k01 clk180_k01 clk90_k01 clk270_k01 clk0_k01 clk180_k01 clk90_k01 clk270_k01 clk0_k01 clk180_k01 clk90_k01 clk270_k01 _net12 _net13 _net14 _net15 vcmbias _net4 _net5 _net6 _net7 _net8 _net9 _net10 _net11 vdda_bb vssa_bb bottom_plate_4path_BB_beamformer
xi12 clk0_k23 clk180_k23 clk90_k23 clk270_k23 clk270_k23 clk90_k23 clk0_k23 clk180_k23 clk180_k23 clk0_k23 clk270_k23 clk90_k23 clk90_k23 clk270_k23 clk180_k23 clk0_k23 _net16 _net17 _net18 _net19 vcmbias _net4 _net5 _net6 _net7 _net8 _net9 _net10 _net11 vdda_bb vssa_bb bottom_plate_4path_BB_beamformer
xi10 clk0_k23 clk180_k23 clk90_k23 clk270_k23 clk180_k23 clk0_k23 clk270_k23 clk90_k23 clk0_k23 clk180_k23 clk90_k23 clk270_k23 clk180_k23 clk0_k23 clk270_k23 clk90_k23 _net20 _net21 _net22 _net23 vcmbias _net4 _net5 _net6 _net7 _net8 _net9 _net10 _net11 vdda_bb vssa_bb bottom_plate_4path_BB_beamformer
xi0 clk0 clk180 clk270 clk90 _net24 _net25 set VDDD VSSD CLK_IO_DIST_NW1
xi3 clk0 clk0_k23 clk90 clk90_k23 clk180 clk180_k23 clk270 clk270_k23 VDDD VSSD CLK4Phase_BUFFER_4X
xi2 clk0 clk0_k01 clk90 clk90_k01 clk180 clk180_k01 clk270 clk270_k01 VDDD VSSD CLK4Phase_BUFFER_4X
.ends MIMO_Beamformers_CLK_NW2
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: bottom_plate_4path_mixer_diff_end
** View name: schematic
.subckt bottom_plate_4path_mixer_diff_end clk0 clk90 clk180 clk270 _net1 _net0 vcmbias vdda_q
c7 n5 _net0 13e-12
c3 n1 _net1 13e-12
c8 n6 _net0 13e-12
c9 n7 _net0 13e-12
c5 n3 _net1 13e-12
c4 n2 _net1 13e-12
c6 n4 _net1 13e-12
c10 n8 _net0 13e-12
m0 n1 clk0 n5 vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m0_L} W={bottom_plate_4path_mixer_diff_end_m0_W} Nf={bottom_plate_4path_mixer_diff_end_m0_Nf}
m1 n2 clk90 n6 vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m1_L} W={bottom_plate_4path_mixer_diff_end_m1_W} Nf={bottom_plate_4path_mixer_diff_end_m1_Nf}
m2 n3 clk180 n7 vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m2_L} W={bottom_plate_4path_mixer_diff_end_m2_W} Nf={bottom_plate_4path_mixer_diff_end_m2_Nf}
m3 n4 clk270 n8 vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m3_L} W={bottom_plate_4path_mixer_diff_end_m3_W} Nf={bottom_plate_4path_mixer_diff_end_m3_Nf}
m4 n1 clk0 vcmbias vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m4_L} W={bottom_plate_4path_mixer_diff_end_m4_W} Nf={bottom_plate_4path_mixer_diff_end_m4_Nf}
m5 n2 clk90 vcmbias vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m5_L} W={bottom_plate_4path_mixer_diff_end_m5_W} Nf={bottom_plate_4path_mixer_diff_end_m5_Nf}
m6 n3 clk180 vcmbias vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m6_L} W={bottom_plate_4path_mixer_diff_end_m6_W} Nf={bottom_plate_4path_mixer_diff_end_m6_Nf}
m7 n4 clk270 vcmbias vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m7_L} W={bottom_plate_4path_mixer_diff_end_m7_W} Nf={bottom_plate_4path_mixer_diff_end_m7_Nf}
m8 n5 clk0 vcmbias vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m8_L} W={bottom_plate_4path_mixer_diff_end_m8_W} Nf={bottom_plate_4path_mixer_diff_end_m8_Nf}
m9 n6 clk90 vcmbias vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m9_L} W={bottom_plate_4path_mixer_diff_end_m9_W} Nf={bottom_plate_4path_mixer_diff_end_m9_Nf}
m10 n7 clk180 vcmbias vcmbias nmos_rvt L={bottom_plate_4path_mixer_diff_end_m10_L} W={bottom_plate_4path_mixer_diff_end_m10_W} Nf={bottom_plate_4path_mixer_diff_end_m10_Nf}
m11 n8 clk270 vcmbias vdda_q nmos_rvt L={bottom_plate_4path_mixer_diff_end_m11_L} W={bottom_plate_4path_mixer_diff_end_m11_W} Nf={bottom_plate_4path_mixer_diff_end_m11_Nf}
** vdda_q was floating add to one port @jitesh to fix it
.ends bottom_plate_4path_mixer_diff_end
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: MIMO_mixers_bottom_plate
** View name: schematic
.subckt MIMO_mixers_bottom_plate clk0 clk180 clk270 clk90 vcmbias vdda_q _net0 _net1 _net2 _net3 _net4 _net5 _net6 _net7
xi0 clk0 clk90 clk180 clk270 _net0 _net1 vcmbias vdda_q bottom_plate_4path_mixer_diff_end
xi1 clk0 clk90 clk180 clk270 _net2 _net3 vcmbias vdda_q bottom_plate_4path_mixer_diff_end
xi2 clk0 clk90 clk180 clk270 _net4 _net5 vcmbias vdda_q bottom_plate_4path_mixer_diff_end
xi3 clk0 clk90 clk180 clk270 _net6 _net7 vcmbias vdda_q bottom_plate_4path_mixer_diff_end
.ends MIMO_mixers_bottom_plate
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: MIMO_MIXER_CLK_BUFFER
** View name: schematic
.subckt MIMO_MIXER_CLK_BUFFER clk1 clk2 clk3 clk4 vcmbias vdda_q VDDD VSSD _net0 _net1 _net2 _net3 _net4 _net5 _net6 _net7
xi0 clk0 clk180 clk270 clk90 vcmbias vdda_q _net0 _net1 _net2 _net3 _net4 _net5 _net6 _net7 MIMO_mixers_bottom_plate
xi3<1> clk3 clk180 VDDD VSSD CLK_BUFFER_4X
xi3<0> clk3 clk180 VDDD VSSD CLK_BUFFER_4X
xi2<1> clk1 clk0 VDDD VSSD CLK_BUFFER_4X
xi2<0> clk1 clk0 VDDD VSSD CLK_BUFFER_4X
xi1<1> clk2 clk90 VDDD VSSD CLK_BUFFER_4X
xi1<0> clk2 clk90 VDDD VSSD CLK_BUFFER_4X
xi4<1> clk4 clk270 VDDD VSSD CLK_BUFFER_4X
xi4<0> clk4 clk270 VDDD VSSD CLK_BUFFER_4X
.ends MIMO_MIXER_CLK_BUFFER
** End of subcircuit definition.

** Library name: TO65_20200429
** Cell name: mimo_bulk
** View name: schematic
.subckt mimo_bulk _net7 _net25 _net11 _net10 _net9 _net14 _net13 _net12 _net6 _net5 _net4 _net3 _net2 _net1 _net0 _net8 _net16 _net15 set vcmbias vdda_bb VDDD vssa_bb VSSD _net17 _net24 _net22 _net23 _net20 _net21 _net18 _net19
xi0 clk0 clk180 clk270 clk90 _net7 _net25 _net11 _net10 _net9 _net14 _net13 _net12 _net6 _net5 _net4 _net3 _net2 _net1 _net0 _net8 _net16 _net15 set vcmbias vdda_bb VDDD vssa_bb VSSD _net17 _net24 _net22 _net23 _net20 _net21 _net18 _net19 MIMO_Beamformers_CLK_NW2
xi1 clk0 clk90 clk180 clk270 vcmbias vdda_bb VDDD VSSD _net17 _net24 _net22 _net23 _net20 _net21 _net18 _net19 MIMO_MIXER_CLK_BUFFER
.ends mimo_bulk
** End of subcircuit definition.
.ends
