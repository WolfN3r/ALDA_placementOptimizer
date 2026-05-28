* ============================================================
* Circuit : unity_gain_buffers
* Source  : ALIGN analog layout examples
* File    : unity_gain_buffers\unity_gain_buffers.sp
* ============================================================
* Stats:
*   Subcircuits  : 5
*   Devices (M)  : 14
*   Device types : nmos_rvt pmos_rvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param p_stack_4_mi4_L=40n p_stack_4_mi4_W=4 p_stack_4_mi4_Nf=2
.param p_stack_4_mi3_L=40n p_stack_4_mi3_W=4 p_stack_4_mi3_Nf=2
.param p_stack_4_mi2_L=40n p_stack_4_mi2_W=4 p_stack_4_mi2_Nf=2
.param p_stack_4_mi1_L=40n p_stack_4_mi1_W=4 p_stack_4_mi1_Nf=2
.param p_stack_2_mi2_L=40n p_stack_2_mi2_W=4 p_stack_2_mi2_Nf=2
.param p_stack_2_mi1_L=40n p_stack_2_mi1_W=4 p_stack_2_mi1_Nf=2
.param n_stack_4_mi1_L=40n n_stack_4_mi1_W=4 n_stack_4_mi1_Nf=2
.param n_stack_4_mi2_L=40n n_stack_4_mi2_W=4 n_stack_4_mi2_Nf=2
.param n_stack_4_mi3_L=40n n_stack_4_mi3_W=4 n_stack_4_mi3_Nf=2
.param n_stack_4_mi4_L=40n n_stack_4_mi4_W=4 n_stack_4_mi4_Nf=2
.param n_stack_2_mi1_L=40n n_stack_2_mi1_W=4 n_stack_2_mi1_Nf=2
.param n_stack_2_mi2_L=40n n_stack_2_mi2_W=4 n_stack_2_mi2_Nf=2
.param unity_gain_buffers_mmn42_L=40n unity_gain_buffers_mmn42_W=4 unity_gain_buffers_mmn42_Nf=2 unity_gain_buffers_mmn42_M=16
.param unity_gain_buffers_mmp33_L=40n unity_gain_buffers_mmp33_W=4 unity_gain_buffers_mmp33_Nf=2 unity_gain_buffers_mmp33_M=16


* --- CIRCUIT DEFINITION ---
.subckt p_stack_4 d g s b
.param m=1
mi4 inet3 g s b pmos_rvt L={p_stack_4_mi4_L} W={p_stack_4_mi4_W} Nf={p_stack_4_mi4_Nf}
mi3 inet2 g inet3 b pmos_rvt L={p_stack_4_mi3_L} W={p_stack_4_mi3_W} Nf={p_stack_4_mi3_Nf}
mi2 inet1 g inet2 b pmos_rvt L={p_stack_4_mi2_L} W={p_stack_4_mi2_W} Nf={p_stack_4_mi2_Nf}
mi1 d g inet1 b pmos_rvt L={p_stack_4_mi1_L} W={p_stack_4_mi1_W} Nf={p_stack_4_mi1_Nf}
.ends p_stack_4

.subckt p_stack_2 d g s b
.param m=1
mi2 inet1 g s b pmos_rvt L={p_stack_2_mi2_L} W={p_stack_2_mi2_W} Nf={p_stack_2_mi2_Nf}
mi1 d g inet1 b pmos_rvt L={p_stack_2_mi1_L} W={p_stack_2_mi1_W} Nf={p_stack_2_mi1_Nf}
.ends p_stack_2

.subckt n_stack_4 d g s b
.param m=1
mi1 d g inet1 b nmos_rvt L={n_stack_4_mi1_L} W={n_stack_4_mi1_W} Nf={n_stack_4_mi1_Nf}
mi2 inet1 g inet2 b nmos_rvt L={n_stack_4_mi2_L} W={n_stack_4_mi2_W} Nf={n_stack_4_mi2_Nf}
mi3 inet2 g inet3 b nmos_rvt L={n_stack_4_mi3_L} W={n_stack_4_mi3_W} Nf={n_stack_4_mi3_Nf}
mi4 inet3 g s b nmos_rvt L={n_stack_4_mi4_L} W={n_stack_4_mi4_W} Nf={n_stack_4_mi4_Nf}
.ends n_stack_4

.subckt n_stack_2 d g s b
.param m=1
mi1 d g inet1 b nmos_rvt L={n_stack_2_mi1_L} W={n_stack_2_mi1_W} Nf={n_stack_2_mi1_Nf}
mi2 inet1 g s b nmos_rvt L={n_stack_2_mi2_L} W={n_stack_2_mi2_W} Nf={n_stack_2_mi2_Nf}
.ends n_stack_2

.subckt unity_gain_buffers vbias_an VDDA vo_hs vo_ls vref_hs vref_ls VSSA
xmn1 v_p1 v_p2 VSSA VSSA n_stack_4 m=4
xmn0 v_p2 v_p2 VSSA VSSA n_stack_4 m=4
xmn43 vo_ls v_p1 VSSA VSSA n_stack_2 m=2
xmn22 v_n1 vo_hs vcom_n VSSA n_stack_2 m=10
xmn23 v_n2 vref_hs vcom_n VSSA n_stack_2 m=10
xmn41 vbias4 vbias_an VSSA VSSA n_stack_4 m=2
xmn3 VSSA vbias_an VSSA VSSA n_stack_4 m=2
xmn2 vcom_n vbias_an VSSA VSSA n_stack_4 m=4
mmn42 vbias_m vbias_m vbias4 VSSA nmos_rvt L={unity_gain_buffers_mmn42_L} W={unity_gain_buffers_mmn42_W} Nf={unity_gain_buffers_mmn42_Nf} M={unity_gain_buffers_mmn42_M}
mmp33 vbias_m vbias_m vbias_n1 VDDA pmos_rvt L={unity_gain_buffers_mmp33_L} W={unity_gain_buffers_mmp33_W} Nf={unity_gain_buffers_mmp33_Nf} M={unity_gain_buffers_mmp33_M}
xmp10 vcom_p vbias_n1 VDDA VDDA p_stack_4 m=2
xmp8 v_p2 vo_ls vcom_p VDDA p_stack_2 m=10
xmp22 v_n2 v_n1 VDDA VDDA p_stack_4 m=4
xmp28 v_n1 v_n1 VDDA VDDA p_stack_4 m=4
xmp7 vo_hs v_n2 VDDA VDDA p_stack_2 m=2
xmp34 vbias_n1 vbias_n1 VDDA VDDA p_stack_4 m=2
xmp9 v_p1 vref_ls vcom_p VDDA p_stack_2 m=10
.ends unity_gain_buffers

