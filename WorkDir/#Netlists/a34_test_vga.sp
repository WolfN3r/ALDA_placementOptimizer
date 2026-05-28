* ============================================================
* Circuit : test_vga
* Source  : ALIGN analog layout examples
* File    : test_vga\test_vga.sp
* ============================================================
* Stats:
*   Subcircuits  : 7
*   Devices (M)  : 36
*   Device types : nmos_lvt pmos_lvt
*   Passives     : 0 resistors, 0 capacitors
* Note: Converted from FinFET-style to CMOS-style netlist.
*       Device sizes are placeholders — optimizer generates new sizes.
* ============================================================

* --- DEVICE PARAMETERS ---
.param nlvt_s_pcell_0_mi1_W=180e-9 nlvt_s_pcell_0_mi1_L=40e-9 nlvt_s_pcell_0_mi1_M=1 nlvt_s_pcell_0_mi1_Nf=2
.param nlvt_s_pcell_0_mi2_W=180e-9 nlvt_s_pcell_0_mi2_L=40e-9 nlvt_s_pcell_0_mi2_M=1 nlvt_s_pcell_0_mi2_Nf=2
.param nlvt_s_pcell_0_mi3_W=180e-9 nlvt_s_pcell_0_mi3_L=40e-9 nlvt_s_pcell_0_mi3_M=1 nlvt_s_pcell_0_mi3_Nf=2
.param nlvt_s_pcell_0_mi4_W=180e-9 nlvt_s_pcell_0_mi4_L=40e-9 nlvt_s_pcell_0_mi4_M=1 nlvt_s_pcell_0_mi4_Nf=2
.param nlvt_s_pcell_0_mi5_W=180e-9 nlvt_s_pcell_0_mi5_L=40e-9 nlvt_s_pcell_0_mi5_M=1 nlvt_s_pcell_0_mi5_Nf=2
.param nlvt_s_pcell_0_mi6_W=180e-9 nlvt_s_pcell_0_mi6_L=40e-9 nlvt_s_pcell_0_mi6_M=1 nlvt_s_pcell_0_mi6_Nf=2
.param plvt_s_pcell_1_mi8_W=360e-9 plvt_s_pcell_1_mi8_L=40e-9 plvt_s_pcell_1_mi8_M=1 plvt_s_pcell_1_mi8_Nf=2
.param plvt_s_pcell_1_mi7_W=360e-9 plvt_s_pcell_1_mi7_L=40e-9 plvt_s_pcell_1_mi7_M=1 plvt_s_pcell_1_mi7_Nf=2
.param plvt_s_pcell_1_mi6_W=360e-9 plvt_s_pcell_1_mi6_L=40e-9 plvt_s_pcell_1_mi6_M=1 plvt_s_pcell_1_mi6_Nf=2
.param plvt_s_pcell_1_mi5_W=360e-9 plvt_s_pcell_1_mi5_L=40e-9 plvt_s_pcell_1_mi5_M=1 plvt_s_pcell_1_mi5_Nf=2
.param plvt_s_pcell_1_mi4_W=360e-9 plvt_s_pcell_1_mi4_L=40e-9 plvt_s_pcell_1_mi4_M=1 plvt_s_pcell_1_mi4_Nf=2
.param plvt_s_pcell_1_mi3_W=360e-9 plvt_s_pcell_1_mi3_L=40e-9 plvt_s_pcell_1_mi3_M=1 plvt_s_pcell_1_mi3_Nf=2
.param plvt_s_pcell_1_mi2_W=360e-9 plvt_s_pcell_1_mi2_L=40e-9 plvt_s_pcell_1_mi2_M=1 plvt_s_pcell_1_mi2_Nf=2
.param plvt_s_pcell_1_mi1_W=360e-9 plvt_s_pcell_1_mi1_L=40e-9 plvt_s_pcell_1_mi1_M=1 plvt_s_pcell_1_mi1_Nf=2
.param plvt_s_pcell_2_mi4_W=360e-9 plvt_s_pcell_2_mi4_L=40e-9 plvt_s_pcell_2_mi4_M=1 plvt_s_pcell_2_mi4_Nf=2
.param plvt_s_pcell_2_mi3_W=360e-9 plvt_s_pcell_2_mi3_L=40e-9 plvt_s_pcell_2_mi3_M=1 plvt_s_pcell_2_mi3_Nf=2
.param plvt_s_pcell_2_mi2_W=360e-9 plvt_s_pcell_2_mi2_L=40e-9 plvt_s_pcell_2_mi2_M=1 plvt_s_pcell_2_mi2_Nf=2
.param plvt_s_pcell_2_mi1_W=360e-9 plvt_s_pcell_2_mi1_L=40e-9 plvt_s_pcell_2_mi1_M=1 plvt_s_pcell_2_mi1_Nf=2
.param plvt_s_pcell_3_mi4_W=360e-9 plvt_s_pcell_3_mi4_L=40e-9 plvt_s_pcell_3_mi4_M=1 plvt_s_pcell_3_mi4_Nf=2
.param plvt_s_pcell_3_mi3_W=360e-9 plvt_s_pcell_3_mi3_L=40e-9 plvt_s_pcell_3_mi3_M=1 plvt_s_pcell_3_mi3_Nf=2
.param plvt_s_pcell_3_mi2_W=360e-9 plvt_s_pcell_3_mi2_L=40e-9 plvt_s_pcell_3_mi2_M=1 plvt_s_pcell_3_mi2_Nf=2
.param plvt_s_pcell_3_mi1_W=360e-9 plvt_s_pcell_3_mi1_L=40e-9 plvt_s_pcell_3_mi1_M=1 plvt_s_pcell_3_mi1_Nf=2
.param test_vga_inv_als_mqn1_W=180e-9 test_vga_inv_als_mqn1_L=40e-9 test_vga_inv_als_mqn1_M=1 test_vga_inv_als_mqn1_Nf=2
.param test_vga_inv_als_mqp1_W=180e-9 test_vga_inv_als_mqp1_L=40e-9 test_vga_inv_als_mqp1_M=1 test_vga_inv_als_mqp1_Nf=2
.param test_vga_mmn16_W=1.62e-6 test_vga_mmn16_L=40e-9 test_vga_mmn16_M=1 test_vga_mmn16_Nf=6
.param test_vga_mmn211_W=1.62e-6 test_vga_mmn211_L=40e-9 test_vga_mmn211_M=1 test_vga_mmn211_Nf=6
.param test_vga_mmn221_W=1.62e-6 test_vga_mmn221_L=40e-9 test_vga_mmn221_M=1 test_vga_mmn221_Nf=6
.param test_vga_mmn23_W=1.62e-6 test_vga_mmn23_L=40e-9 test_vga_mmn23_M=1 test_vga_mmn23_Nf=6
.param test_vga_mmn14_W=1.62e-6 test_vga_mmn14_L=40e-9 test_vga_mmn14_M=1 test_vga_mmn14_Nf=6
.param test_vga_mmn19_W=1.62e-6 test_vga_mmn19_L=40e-9 test_vga_mmn19_M=1 test_vga_mmn19_Nf=6
.param test_vga_mmn20_W=1.62e-6 test_vga_mmn20_L=40e-9 test_vga_mmn20_M=1 test_vga_mmn20_Nf=6
.param test_vga_mmn24_W=1.62e-6 test_vga_mmn24_L=40e-9 test_vga_mmn24_M=1 test_vga_mmn24_Nf=6
.param test_vga_mmp10_W=1.44e-6 test_vga_mmp10_L=40e-9 test_vga_mmp10_M=1 test_vga_mmp10_Nf=4
.param test_vga_mmp91_W=1.44e-6 test_vga_mmp91_L=40e-9 test_vga_mmp91_M=1 test_vga_mmp91_Nf=4
.param test_vga_mmp6_W=1.44e-6 test_vga_mmp6_L=40e-9 test_vga_mmp6_M=1 test_vga_mmp6_Nf=4
.param test_vga_mmp2_W=1.44e-6 test_vga_mmp2_L=40e-9 test_vga_mmp2_M=1 test_vga_mmp2_Nf=4


* --- CIRCUIT DEFINITION ---

.subckt nlvt_s_pcell_0 d g s b
.param m=1
mi1 d g inet1 b nmos_lvt W={nlvt_s_pcell_0_mi1_W} L={nlvt_s_pcell_0_mi1_L} M={nlvt_s_pcell_0_mi1_M} Nf={nlvt_s_pcell_0_mi1_Nf}
mi2 inet1 g inet2 b nmos_lvt W={nlvt_s_pcell_0_mi2_W} L={nlvt_s_pcell_0_mi2_L} M={nlvt_s_pcell_0_mi2_M} Nf={nlvt_s_pcell_0_mi2_Nf}
mi3 inet2 g inet3 b nmos_lvt W={nlvt_s_pcell_0_mi3_W} L={nlvt_s_pcell_0_mi3_L} M={nlvt_s_pcell_0_mi3_M} Nf={nlvt_s_pcell_0_mi3_Nf}
mi4 inet3 g inet4 b nmos_lvt W={nlvt_s_pcell_0_mi4_W} L={nlvt_s_pcell_0_mi4_L} M={nlvt_s_pcell_0_mi4_M} Nf={nlvt_s_pcell_0_mi4_Nf}
mi5 inet4 g inet5 b nmos_lvt W={nlvt_s_pcell_0_mi5_W} L={nlvt_s_pcell_0_mi5_L} M={nlvt_s_pcell_0_mi5_M} Nf={nlvt_s_pcell_0_mi5_Nf}
mi6 inet5 g s b nmos_lvt W={nlvt_s_pcell_0_mi6_W} L={nlvt_s_pcell_0_mi6_L} M={nlvt_s_pcell_0_mi6_M} Nf={nlvt_s_pcell_0_mi6_Nf}
.ends nlvt_s_pcell_0

.subckt plvt_s_pcell_1 d g s b
.param m=1
mi8 inet7 g s b pmos_lvt W={plvt_s_pcell_1_mi8_W} L={plvt_s_pcell_1_mi8_L} M={plvt_s_pcell_1_mi8_M} Nf={plvt_s_pcell_1_mi8_Nf}
mi7 inet6 g inet7 b pmos_lvt W={plvt_s_pcell_1_mi7_W} L={plvt_s_pcell_1_mi7_L} M={plvt_s_pcell_1_mi7_M} Nf={plvt_s_pcell_1_mi7_Nf}
mi6 inet5 g inet6 b pmos_lvt W={plvt_s_pcell_1_mi6_W} L={plvt_s_pcell_1_mi6_L} M={plvt_s_pcell_1_mi6_M} Nf={plvt_s_pcell_1_mi6_Nf}
mi5 inet4 g inet5 b pmos_lvt W={plvt_s_pcell_1_mi5_W} L={plvt_s_pcell_1_mi5_L} M={plvt_s_pcell_1_mi5_M} Nf={plvt_s_pcell_1_mi5_Nf}
mi4 inet3 g inet4 b pmos_lvt W={plvt_s_pcell_1_mi4_W} L={plvt_s_pcell_1_mi4_L} M={plvt_s_pcell_1_mi4_M} Nf={plvt_s_pcell_1_mi4_Nf}
mi3 inet2 g inet3 b pmos_lvt W={plvt_s_pcell_1_mi3_W} L={plvt_s_pcell_1_mi3_L} M={plvt_s_pcell_1_mi3_M} Nf={plvt_s_pcell_1_mi3_Nf}
mi2 inet1 g inet2 b pmos_lvt W={plvt_s_pcell_1_mi2_W} L={plvt_s_pcell_1_mi2_L} M={plvt_s_pcell_1_mi2_M} Nf={plvt_s_pcell_1_mi2_Nf}
mi1 d g inet1 b pmos_lvt W={plvt_s_pcell_1_mi1_W} L={plvt_s_pcell_1_mi1_L} M={plvt_s_pcell_1_mi1_M} Nf={plvt_s_pcell_1_mi1_Nf}
.ends plvt_s_pcell_1

.subckt plvt_s_pcell_2 d g s b
.param m=1
mi4 inet3 g s b pmos_lvt W={plvt_s_pcell_2_mi4_W} L={plvt_s_pcell_2_mi4_L} M={plvt_s_pcell_2_mi4_M} Nf={plvt_s_pcell_2_mi4_Nf}
mi3 inet2 g inet3 b pmos_lvt W={plvt_s_pcell_2_mi3_W} L={plvt_s_pcell_2_mi3_L} M={plvt_s_pcell_2_mi3_M} Nf={plvt_s_pcell_2_mi3_Nf}
mi2 inet1 g inet2 b pmos_lvt W={plvt_s_pcell_2_mi2_W} L={plvt_s_pcell_2_mi2_L} M={plvt_s_pcell_2_mi2_M} Nf={plvt_s_pcell_2_mi2_Nf}
mi1 d g inet1 b pmos_lvt W={plvt_s_pcell_2_mi1_W} L={plvt_s_pcell_2_mi1_L} M={plvt_s_pcell_2_mi1_M} Nf={plvt_s_pcell_2_mi1_Nf}
.ends plvt_s_pcell_2

.subckt plvt_s_pcell_3 d g s b
.param m=1
mi4 inet3 g s b pmos_lvt W={plvt_s_pcell_3_mi4_W} L={plvt_s_pcell_3_mi4_L} M={plvt_s_pcell_3_mi4_M} Nf={plvt_s_pcell_3_mi4_Nf}
mi3 inet2 g inet3 b pmos_lvt W={plvt_s_pcell_3_mi3_W} L={plvt_s_pcell_3_mi3_L} M={plvt_s_pcell_3_mi3_M} Nf={plvt_s_pcell_3_mi3_Nf}
mi2 inet1 g inet2 b pmos_lvt W={plvt_s_pcell_3_mi2_W} L={plvt_s_pcell_3_mi2_L} M={plvt_s_pcell_3_mi2_M} Nf={plvt_s_pcell_3_mi2_Nf}
mi1 d g inet1 b pmos_lvt W={plvt_s_pcell_3_mi1_W} L={plvt_s_pcell_3_mi1_L} M={plvt_s_pcell_3_mi1_M} Nf={plvt_s_pcell_3_mi1_Nf}
.ends plvt_s_pcell_3

.subckt test_vga_inv_als in in_b VDDA VSSA
mqn1 in_b in VSSA VSSA nmos_lvt W={test_vga_inv_als_mqn1_W} L={test_vga_inv_als_mqn1_L} M={test_vga_inv_als_mqn1_M} Nf={test_vga_inv_als_mqn1_Nf}
mqp1 in_b in VDDA VDDA pmos_lvt W={test_vga_inv_als_mqp1_W} L={test_vga_inv_als_mqp1_L} M={test_vga_inv_als_mqp1_M} Nf={test_vga_inv_als_mqp1_Nf}
.ends test_vga_inv_als

.subckt test_vga_buf_als in out VDDA VSSA
xi1 net7 out VDDA VSSA test_vga_inv_als
xi0 in net7 VDDA VSSA test_vga_inv_als
.ends test_vga_buf_als

.subckt test_vga cmfb_p1 gain_ctrl[1] gain_ctrl[0] iref VDDA vinn vinp voutn voutp VSSA
xmn29 net093 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
xmn13 net0102 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
xmn30 net092 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
xmn27 net0101 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
xmn31 net091 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
xmn32 net090 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
xmn15 net0103 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
xmn28 net0100 cmfb_p1 VSSA VSSA nlvt_s_pcell_0 m=1
mmn16 voutp VDDA net0103 VSSA nmos_lvt W={test_vga_mmn16_W} L={test_vga_mmn16_L} M={test_vga_mmn16_M} Nf={test_vga_mmn16_Nf}
mmn211 voutn gain_ctrl_bf[1] net093 VSSA nmos_lvt W={test_vga_mmn211_W} L={test_vga_mmn211_L} M={test_vga_mmn211_M} Nf={test_vga_mmn211_Nf}
mmn221 voutn gain_ctrl_bf[1] net092 VSSA nmos_lvt W={test_vga_mmn221_W} L={test_vga_mmn221_L} M={test_vga_mmn221_M} Nf={test_vga_mmn221_Nf}
mmn23 voutn gain_ctrl_bf[0] net091 VSSA nmos_lvt W={test_vga_mmn23_W} L={test_vga_mmn23_L} M={test_vga_mmn23_M} Nf={test_vga_mmn23_Nf}
mmn14 voutp gain_ctrl_bf[0] net0102 VSSA nmos_lvt W={test_vga_mmn14_W} L={test_vga_mmn14_L} M={test_vga_mmn14_M} Nf={test_vga_mmn14_Nf}
mmn19 voutp gain_ctrl_bf[1] net0101 VSSA nmos_lvt W={test_vga_mmn19_W} L={test_vga_mmn19_L} M={test_vga_mmn19_M} Nf={test_vga_mmn19_Nf}
mmn20 voutp gain_ctrl_bf[1] net0100 VSSA nmos_lvt W={test_vga_mmn20_W} L={test_vga_mmn20_L} M={test_vga_mmn20_M} Nf={test_vga_mmn20_Nf}
mmn24 voutn VDDA net090 VSSA nmos_lvt W={test_vga_mmn24_W} L={test_vga_mmn24_L} M={test_vga_mmn24_M} Nf={test_vga_mmn24_Nf}
xmp21 voutp vinn net078 VDDA plvt_s_pcell_1 m=4
xmp20 voutn vinp net078 VDDA plvt_s_pcell_1 m=4
xmp19 voutp vinn net076 VDDA plvt_s_pcell_1 m=4
xmp18 voutn vinp net076 VDDA plvt_s_pcell_1 m=4
xmp5 voutp vinn net88 VDDA plvt_s_pcell_1 m=4
xmp4 voutn vinp net88 VDDA plvt_s_pcell_1 m=4
xmp12 voutp vinn net86 VDDA plvt_s_pcell_1 m=4
xmn0 voutn vinp net86 VDDA plvt_s_pcell_1 m=4
xmn6 iref iref VDDA VDDA plvt_s_pcell_2 m=2
xmp14 net0104 iref VDDA VDDA plvt_s_pcell_3 m=3
xmp01 net0105 iref VDDA VDDA plvt_s_pcell_3 m=3
xmp3 net99 iref VDDA VDDA plvt_s_pcell_3 m=3
xmp0 net100 iref VDDA VDDA plvt_s_pcell_3 m=3
xinv1[1] gain_ctrl_bf[1] gain_ctrlb_bf[1] VDDA VSSA test_vga_inv_als
xinv1[0] gain_ctrl_bf[0] gain_ctrlb_bf[0] VDDA VSSA test_vga_inv_als
xbuf1[1] gain_ctrl[1] gain_ctrl_bf[1] VDDA VSSA test_vga_buf_als
xbuf1[0] gain_ctrl[0] gain_ctrl_bf[0] VDDA VSSA test_vga_buf_als
mmp10 net078 gain_ctrlb_bf[1] net0104 VDDA pmos_lvt W={test_vga_mmp10_W} L={test_vga_mmp10_L} M={test_vga_mmp10_M} Nf={test_vga_mmp10_Nf}
mmp91 net076 gain_ctrlb_bf[1] net0105 VDDA pmos_lvt W={test_vga_mmp91_W} L={test_vga_mmp91_L} M={test_vga_mmp91_M} Nf={test_vga_mmp91_Nf}
mmp6 net88 gain_ctrlb_bf[0] net99 VDDA pmos_lvt W={test_vga_mmp6_W} L={test_vga_mmp6_L} M={test_vga_mmp6_M} Nf={test_vga_mmp6_Nf}
mmp2 net86 VSSA net100 VDDA pmos_lvt W={test_vga_mmp2_W} L={test_vga_mmp2_L} M={test_vga_mmp2_M} Nf={test_vga_mmp2_Nf}
.ends test_vga
