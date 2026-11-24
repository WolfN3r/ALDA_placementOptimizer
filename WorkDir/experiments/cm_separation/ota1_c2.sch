v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
B 4 -800 -760 800 140 {fill=false dash=5}
T {Gain path} -790 -810 0 0 0.6 0.6 {}
B 4 -1200 -760 -840 140 {fill=false dash=5}
T {Bias} -1190 -810 0 0 0.6 0.6 {}
B 4 880 -760 1760 140 {fill=false dash=5}
T {Common-mode feedback} 890 -810 0 0 0.6 0.6 {}
T {input pair} -1060 420 0 0 0.3 0.3 {}
T {NMOS mirror rows} -740 420 0 0 0.3 0.3 {}
T {PMOS mirror rows} -420 420 0 0 0.3 0.3 {}
T {2nd stage} -100 420 0 0 0.3 0.3 {}
T {CMFB pairs} 220 420 0 0 0.3 0.3 {}
T {Rz (R23/R25)} 620 420 0 0 0.3 0.3 {}
B 4 -1200 250 1000 470 {fill=false dash=5}
T {Dummies (layout only, all terminals on the rails)} -1190 200 0 0 0.6 0.6 {}
T {Ports} -1500 -810 0 0 0.6 0.6 {}
T {OTA1 case c2: NMOS mirror row separated from the OTA core (equal line lengths)} -1500 -960 0 0 0.8 0.8 {}
T {Tail line dt -> tail (M10 + M11) and output lines d6 -> OUTP, d9 -> OUTM, all of length L_W.} -1500 -900 0 0 0.4 0.4 {}
N -260 -580 -300 -580 {lab=VBIAS_P}
N -260 -270 -300 -270 {lab=INM}
N -220 -550 -220 -420 {lab=intp}
N -220 -420 -220 -300 {lab=intp}
N -640 -40 -600 -40 {lab=vbias_n}
N -420 -340 -460 -340 {lab=VSS}
N -640 -580 -560 -580 {lab=intp}
N -560 -580 -560 -420 {lab=intp}
N -560 -420 -400 -420 {lab=intp}
N -400 -420 -220 -420 {lab=intp}
N -400 -420 -400 -370 {lab=intp}
N -400 -310 -400 -270 {lab=net037}
N -400 -270 -400 -220 {lab=net037}
N -680 -550 -680 -300 {lab=OUTM}
N -680 -300 -680 -110 {lab=OUTM}
N -400 -160 -400 -110 {lab=OUTM}
N -400 -110 -680 -110 {lab=OUTM}
N -680 -300 -740 -300 {lab=OUTM}
N 260 -580 300 -580 {lab=VBIAS_P}
N 260 -270 300 -270 {lab=INP}
N 220 -550 220 -420 {lab=intm}
N 220 -420 220 -300 {lab=intm}
N 640 -40 600 -40 {lab=vbias_n}
N 420 -340 460 -340 {lab=VSS}
N 640 -580 560 -580 {lab=intm}
N 560 -580 560 -420 {lab=intm}
N 560 -420 400 -420 {lab=intm}
N 400 -420 220 -420 {lab=intm}
N 400 -420 400 -370 {lab=intm}
N 400 -310 400 -270 {lab=net047}
N 400 -270 400 -220 {lab=net047}
N 680 -550 680 -300 {lab=OUTP}
N 680 -300 680 -110 {lab=OUTP}
N 400 -160 400 -110 {lab=OUTP}
N 400 -110 680 -110 {lab=OUTP}
N 680 -300 740 -300 {lab=OUTP}
N -140 -40 -180 -40 {lab=vbias_n}
N 140 -40 180 -40 {lab=vcmfb}
N -220 -240 -220 -150 {lab=tail}
N -220 -150 -100 -150 {lab=tail}
N -100 -150 0 -150 {lab=tail}
N 0 -150 100 -150 {lab=tail}
N 100 -150 220 -150 {lab=tail}
N 220 -150 220 -240 {lab=tail}
N -1040 -580 -990 -580 {lab=VBIAS_P}
N -990 -580 -940 -580 {lab=VBIAS_P}
N -1080 -550 -1080 -480 {lab=VBIAS_P}
N -1080 -480 -990 -480 {lab=VBIAS_P}
N -990 -480 -990 -580 {lab=VBIAS_P}
N -1080 -480 -1080 -420 {lab=VBIAS_P}
N -900 -550 -900 -150 {lab=vbias_n}
N -900 -150 -900 -70 {lab=vbias_n}
N -940 -40 -990 -40 {lab=vbias_n}
N -990 -40 -990 -150 {lab=vbias_n}
N -990 -150 -900 -150 {lab=vbias_n}
N 980 -270 940 -270 {lab=OUTP}
N 1660 -270 1700 -270 {lab=OUTM}
N 1240 -270 1320 -270 {lab=VREF}
N 1320 -270 1400 -270 {lab=VREF}
N 1070 -540 1030 -540 {lab=VBIAS_P}
N 1490 -540 1450 -540 {lab=VBIAS_P}
N 1020 -300 1020 -400 {lab=net020}
N 1020 -400 1110 -400 {lab=net020}
N 1110 -400 1200 -400 {lab=net020}
N 1200 -400 1200 -300 {lab=net020}
N 1110 -400 1110 -510 {lab=net020}
N 1440 -300 1440 -400 {lab=net028}
N 1440 -400 1530 -400 {lab=net028}
N 1530 -400 1620 -400 {lab=net028}
N 1620 -400 1620 -300 {lab=net028}
N 1530 -400 1530 -510 {lab=net028}
N 1200 -240 1200 -150 {lab=net025}
N 1200 -150 1290 -150 {lab=net025}
N 1290 -150 1330 -150 {lab=net025}
N 1330 -150 1440 -150 {lab=net025}
N 1440 -150 1440 -240 {lab=net025}
N 1330 -150 1330 -70 {lab=net025}
N 1290 -40 1290 -150 {lab=net025}
N 1020 -240 1020 -150 {lab=vcmfb}
N 1020 -150 1020 -70 {lab=vcmfb}
N 980 -40 940 -40 {lab=vcmfb}
N 940 -40 940 -150 {lab=vcmfb}
N 940 -150 1020 -150 {lab=vcmfb}
N 1620 -240 1620 -150 {lab=vcmfb}
N -1020 360 -1060 360 {lab=VSS}
N -980 330 -940 330 {lab=VSS}
N -980 390 -940 390 {lab=VSS}
N -700 360 -740 360 {lab=VSS}
N -660 330 -620 330 {lab=VSS}
N -660 390 -620 390 {lab=VSS}
N -380 360 -420 360 {lab=VDD}
N -340 390 -300 390 {lab=VDD}
N -340 330 -300 330 {lab=VDD}
N -60 360 -100 360 {lab=VDD}
N -20 390 20 390 {lab=VDD}
N -20 330 20 330 {lab=VDD}
N 260 360 220 360 {lab=VDD}
N 300 390 340 390 {lab=VDD}
N 300 330 340 330 {lab=VDD}
N 640 330 680 330 {lab=VSS}
N 640 390 680 390 {lab=VSS}
N 620 360 580 360 {lab=VSS}
N 840 330 880 330 {lab=VSS}
N 840 390 880 390 {lab=VSS}
N 820 360 780 360 {lab=VSS}
N -220 -610 -220 -700 {lab=VDD}
N -680 -610 -680 -700 {lab=VDD}
N 220 -610 220 -700 {lab=VDD}
N 680 -610 680 -700 {lab=VDD}
N -680 -700 -220 -700 {lab=VDD}
N -220 -700 220 -700 {lab=VDD}
N 220 -700 680 -700 {lab=VDD}
N -680 -10 -680 80 {lab=VSS}
N 680 -10 680 80 {lab=VSS}
N -100 -10 -100 80 {lab=VSS}
N 100 -10 100 80 {lab=VSS}
N -680 80 -100 80 {lab=VSS}
N -100 80 100 80 {lab=VSS}
N 100 80 680 80 {lab=VSS}
N -1080 -610 -1080 -700 {lab=VDD}
N -900 -610 -900 -700 {lab=VDD}
N -1080 -700 -900 -700 {lab=VDD}
N -900 -10 -900 80 {lab=VSS}
N 1110 -570 1110 -700 {lab=VDD}
N 1530 -570 1530 -700 {lab=VDD}
N 1110 -700 1530 -700 {lab=VDD}
N 1020 -10 1020 80 {lab=VSS}
N 1330 -10 1330 80 {lab=VSS}
N 1020 80 1330 80 {lab=VSS}
C {sky130_fd_pr/pfet3_01v8.sym} -240 -580 0 0 {name=MP1b
W=\{WPU\}
L=\{LPU\}
body=VDD
nf=\{NFPU\}
mult=\{nint(MP1_M)\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet3_01v8.sym} -240 -270 0 0 {name=M0
W=\{W1/W1_M\}
L=\{L1\}
body=VSS
nf=\{NF1\}
mult=\{W1_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {lab_pin.sym} -300 -580 0 0 {name=l1 sig_type=std_logic lab=VBIAS_P}
C {lab_pin.sym} -300 -270 0 0 {name=l2 sig_type=std_logic lab=INM}
C {lab_pin.sym} -220 -420 0 1 {name=l3 sig_type=std_logic lab=intp}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} -660 -580 0 1 {name=M1
W=\{W2/W2_M\}
L=\{L2\}
body=VDD
nf=\{NF2\}
mult=\{W2_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} -660 -40 0 1 {name=M9
W=\{WNU\}
L=\{LNU\}
body=VSS
nf=\{NFNU\}
mult=\{2*nint(M6_M/2)\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} -600 -40 0 1 {name=l4 sig_type=std_logic lab=vbias_n}
C {sky130_fd_pr/res_high_po_0p69.sym} -400 -340 0 0 {name=R25
L=\{RZ_L\}
model=res_high_po_0p69
spiceprefix=X
mult=1}
C {lab_pin.sym} -460 -340 0 0 {name=l5 sig_type=std_logic lab=VSS}
C {sky130_fd_pr/cap_mim_m3_1.sym} -400 -190 0 0 {name=C1 model=cap_mim_m3_1 W=\{CC_W\} L=\{CC_W\} MF=1 spiceprefix=X}
C {lab_pin.sym} -400 -270 0 0 {name=l6 sig_type=std_logic lab=net037}
C {lab_pin.sym} -740 -300 0 0 {name=l7 sig_type=std_logic lab=OUTM}
C {sky130_fd_pr/pfet3_01v8.sym} 240 -580 0 1 {name=MP1a
W=\{WPU\}
L=\{LPU\}
body=VDD
nf=\{NFPU\}
mult=\{nint(MP1_M)\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet3_01v8.sym} 240 -270 0 1 {name=M2
W=\{W1/W1_M\}
L=\{L1\}
body=VSS
nf=\{NF1\}
mult=\{W1_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {lab_pin.sym} 300 -580 0 1 {name=l8 sig_type=std_logic lab=VBIAS_P}
C {lab_pin.sym} 300 -270 0 1 {name=l9 sig_type=std_logic lab=INP}
C {lab_pin.sym} 220 -420 0 0 {name=l10 sig_type=std_logic lab=intm}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} 660 -580 0 0 {name=M3
W=\{W2/W2_M\}
L=\{L2\}
body=VDD
nf=\{NF2\}
mult=\{W2_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} 660 -40 0 0 {name=M6
W=\{WNU\}
L=\{LNU\}
body=VSS
nf=\{NFNU\}
mult=\{2*nint(M6_M/2)\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} 600 -40 0 0 {name=l11 sig_type=std_logic lab=vbias_n}
C {sky130_fd_pr/res_high_po_0p69.sym} 400 -340 0 1 {name=R23
L=\{RZ_L\}
model=res_high_po_0p69
spiceprefix=X
mult=1}
C {lab_pin.sym} 460 -340 0 1 {name=l12 sig_type=std_logic lab=VSS}
C {sky130_fd_pr/cap_mim_m3_1.sym} 400 -190 0 0 {name=C0 model=cap_mim_m3_1 W=\{CC_W\} L=\{CC_W\} MF=1 spiceprefix=X}
C {lab_pin.sym} 400 -270 0 1 {name=l13 sig_type=std_logic lab=net047}
C {lab_pin.sym} 740 -300 0 1 {name=l14 sig_type=std_logic lab=OUTP}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} -120 -40 0 0 {name=M10
W=\{WNU\}
L=\{LNU\}
body=VSS
nf=\{NFNU\}
mult=\{2*nint(MP1_M)-4\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} 120 -40 0 1 {name=M11
W=\{WNU\}
L=\{LNU\}
body=VSS
nf=\{NFNU\}
mult=4
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} -180 -40 0 0 {name=l15 sig_type=std_logic lab=vbias_n}
C {lab_pin.sym} 180 -40 0 1 {name=l16 sig_type=std_logic lab=vcmfb}
C {lab_pin.sym} 0 -150 0 1 {name=l17 sig_type=std_logic lab=tail}
C {sky130_fd_pr/pfet3_01v8.sym} -1060 -580 0 1 {name=M5
W=\{WPU\}
L=\{LPU\}
body=VDD
nf=\{NFPU\}
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet3_01v8.sym} -920 -580 0 0 {name=M7
W=\{WPU\}
L=\{LPU\}
body=VDD
nf=\{NFPU\}
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} -920 -40 0 0 {name=M4
W=\{WNU\}
L=\{LNU\}
body=VSS
nf=\{NFNU\}
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} -1080 -420 0 0 {name=l18 sig_type=std_logic lab=VBIAS_P}
C {lab_pin.sym} -990 -150 0 0 {name=l19 sig_type=std_logic lab=vbias_n}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} 1000 -270 0 0 {name=M15
W=\{WCM/WCM_M\}
L=\{LCM\}
body=VDD
nf=\{NFCM\}
mult=\{WCM_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} 1220 -270 0 1 {name=M17
W=\{WCM/WCM_M\}
L=\{LCM\}
body=VDD
nf=\{NFCM\}
mult=\{WCM_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} 1420 -270 0 0 {name=M19
W=\{WCM/WCM_M\}
L=\{LCM\}
body=VDD
nf=\{NFCM\}
mult=\{WCM_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} 1640 -270 0 1 {name=M18
W=\{WCM/WCM_M\}
L=\{LCM\}
body=VDD
nf=\{NFCM\}
mult=\{WCM_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} 940 -270 0 0 {name=l20 sig_type=std_logic lab=OUTP}
C {lab_pin.sym} 1700 -270 0 1 {name=l21 sig_type=std_logic lab=OUTM}
C {lab_pin.sym} 1320 -270 0 1 {name=l22 sig_type=std_logic lab=VREF}
C {sky130_fd_pr/pfet3_01v8.sym} 1090 -540 0 0 {name=MP1c
W=\{WPU\}
L=\{LPU\}
body=VDD
nf=\{NFPU\}
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {sky130_fd_pr/pfet3_01v8.sym} 1510 -540 0 0 {name=M20
W=\{WPU\}
L=\{LPU\}
body=VDD
nf=\{NFPU\}
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {lab_pin.sym} 1030 -540 0 0 {name=l23 sig_type=std_logic lab=VBIAS_P}
C {lab_pin.sym} 1450 -540 0 0 {name=l24 sig_type=std_logic lab=VBIAS_P}
C {lab_pin.sym} 1110 -400 0 1 {name=l25 sig_type=std_logic lab=net020}
C {lab_pin.sym} 1530 -400 0 1 {name=l26 sig_type=std_logic lab=net028}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} 1000 -40 0 0 {name=M13
W=\{WNU\}
L=\{LNU\}
body=VSS
nf=\{NFNU\}
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} 1310 -40 0 0 {name=M12
W=\{WNU\}
L=\{LNU\}
body=VSS
nf=\{NFNU\}
mult=2
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} 1330 -150 0 1 {name=l27 sig_type=std_logic lab=net025}
C {lab_pin.sym} 940 -150 0 0 {name=l28 sig_type=std_logic lab=vcmfb}
C {lab_pin.sym} 1620 -150 0 1 {name=l29 sig_type=std_logic lab=vcmfb}
C {sky130_fd_pr/nfet3_01v8.sym} -1000 360 0 0 {name=MD0
W=\{W1/(W1_M*NF1)\}
L=\{L1\}
body=VSS
nf=1
mult=\{MD0_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8
spiceprefix=X
}
C {lab_pin.sym} -1060 360 0 0 {name=l30 sig_type=std_logic lab=VSS}
C {lab_pin.sym} -940 330 0 1 {name=l31 sig_type=std_logic lab=VSS}
C {lab_pin.sym} -940 390 0 1 {name=l32 sig_type=std_logic lab=VSS}
C {sky130_fd_pr/nfet3_01v8_lvt.sym} -680 360 0 0 {name=MDN
W=\{WNU/NFNU\}
L=\{LNU\}
body=VSS
nf=1
mult=\{MDN_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=nfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} -740 360 0 0 {name=l33 sig_type=std_logic lab=VSS}
C {lab_pin.sym} -620 330 0 1 {name=l34 sig_type=std_logic lab=VSS}
C {lab_pin.sym} -620 390 0 1 {name=l35 sig_type=std_logic lab=VSS}
C {sky130_fd_pr/pfet3_01v8.sym} -360 360 0 0 {name=MDP
W=\{WPU/NFPU\}
L=\{LPU\}
body=VDD
nf=1
mult=\{MDP_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8
spiceprefix=X
}
C {lab_pin.sym} -420 360 0 0 {name=l36 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -300 390 0 1 {name=l37 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -300 330 0 1 {name=l38 sig_type=std_logic lab=VDD}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} -40 360 0 0 {name=MD1
W=\{W2/(W2_M*NF2)\}
L=\{L2\}
body=VDD
nf=1
mult=\{MD1_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} -100 360 0 0 {name=l39 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 20 390 0 1 {name=l40 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 20 330 0 1 {name=l41 sig_type=std_logic lab=VDD}
C {sky130_fd_pr/pfet3_01v8_lvt.sym} 280 360 0 0 {name=MDCM
W=\{WCM/(WCM_M*NFCM)\}
L=\{LCM\}
body=VDD
nf=1
mult=\{MDCM_M\}
ad="expr('int((@nf + 1)/2) * @W / @nf * 0.29')"
pd="expr('2*int((@nf + 1)/2) * (@W / @nf + 0.29)')"
as="expr('int((@nf + 2)/2) * @W / @nf * 0.29')"
ps="expr('2*int((@nf + 2)/2) * (@W / @nf + 0.29)')"
nrd="expr('0.29 / @W ')" nrs="expr('0.29 / @W ')"
sa=0 sb=0 sd=0
model=pfet_01v8_lvt
spiceprefix=X
}
C {lab_pin.sym} 220 360 0 0 {name=l42 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 340 390 0 1 {name=l43 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 340 330 0 1 {name=l44 sig_type=std_logic lab=VDD}
C {sky130_fd_pr/res_high_po_0p69.sym} 640 360 0 0 {name=RD1
L=\{RZ_L\}
model=res_high_po_0p69
spiceprefix=X
mult=1}
C {lab_pin.sym} 680 330 0 1 {name=l45 sig_type=std_logic lab=VSS}
C {lab_pin.sym} 680 390 0 1 {name=l46 sig_type=std_logic lab=VSS}
C {lab_pin.sym} 580 360 0 0 {name=l47 sig_type=std_logic lab=VSS}
C {sky130_fd_pr/res_high_po_0p69.sym} 840 360 0 0 {name=RD2
L=\{RZ_L\}
model=res_high_po_0p69
spiceprefix=X
mult=1}
C {lab_pin.sym} 880 330 0 1 {name=l48 sig_type=std_logic lab=VSS}
C {lab_pin.sym} 880 390 0 1 {name=l49 sig_type=std_logic lab=VSS}
C {lab_pin.sym} 780 360 0 0 {name=l50 sig_type=std_logic lab=VSS}
C {lab_pin.sym} -680 -700 0 0 {name=l51 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -680 80 0 0 {name=l52 sig_type=std_logic lab=VSS}
C {lab_pin.sym} -1080 -700 0 0 {name=l53 sig_type=std_logic lab=VDD}
C {lab_pin.sym} -900 80 0 0 {name=l54 sig_type=std_logic lab=VSS}
C {lab_pin.sym} 1530 -700 0 1 {name=l55 sig_type=std_logic lab=VDD}
C {lab_pin.sym} 1330 80 0 1 {name=l56 sig_type=std_logic lab=VSS}
C {ipin.sym} -1420 -680 0 0 {name=p1 lab=INM}
C {ipin.sym} -1420 -630 0 0 {name=p2 lab=INP}
C {opin.sym} -1420 -580 0 0 {name=p3 lab=OUTM}
C {opin.sym} -1420 -530 0 0 {name=p4 lab=OUTP}
C {ipin.sym} -1420 -480 0 0 {name=p5 lab=VBIAS_P}
C {iopin.sym} -1420 -430 0 0 {name=p6 lab=VDD}
C {ipin.sym} -1420 -380 0 0 {name=p7 lab=VREF}
C {iopin.sym} -1420 -330 0 0 {name=p8 lab=VSS}
C {lab_pin.sym} -100 -70 0 0 {name=lwd10 sig_type=std_logic lab=dt}
C {lab_pin.sym} 100 -70 0 1 {name=lwd11 sig_type=std_logic lab=dt}
C {lab_pin.sym} -680 -70 0 1 {name=lwd9 sig_type=std_logic lab=d9}
C {lab_pin.sym} 680 -70 0 0 {name=lwd6 sig_type=std_logic lab=d6}
B 4 -1200 560 1760 900 {fill=false dash=5}
T {Wire model (pi: R = RW*L, C = CW*L/2 at each end)} -1190 510 0 0 0.6 0.6 {}
T {Wire per um at min. width: met1 RW = 0.89 Ohm, CW = 92 aF; li1 RW = 75 Ohm, CW = 57 aF (sky130A.tech). Swept L = 1 ... 100 um.} -1190 920 0 0 0.4 0.4 {}
T {tail line (M10 + M11, 74 uA)} -1140 570 0 0 0.3 0.3 {}
N -1100 640 -940 640 {lab=dt}
N -1100 760 -940 760 {lab=tail}
N -1040 640 -1040 670 {lab=dt}
N -1040 730 -1040 760 {lab=tail}
C {lab_pin.sym} -1100 640 0 0 {name=lw0a sig_type=std_logic lab=dt}
C {lab_pin.sym} -1100 760 0 0 {name=lw0b sig_type=std_logic lab=tail}
C {res.sym} -1040 700 0 0 {name=Rwt value=\{RW*L_W\} footprint=1206 device=resistor m=1}
C {capa.sym} -940 670 0 0 {name=Cwta m=1 value=\{CW*L_W/2\} footprint=1206 device="ceramic capacitor"}
C {capa.sym} -940 790 0 0 {name=Cwtb m=1 value=\{CW*L_W/2\} footprint=1206 device="ceramic capacitor"}
C {lab_pin.sym} -940 700 0 1 {name=lw0c sig_type=std_logic lab=VSS}
C {lab_pin.sym} -940 820 0 1 {name=lw0d sig_type=std_logic lab=VSS}
T {output line M6 (301 uA)} -620 570 0 0 0.3 0.3 {}
N -580 640 -420 640 {lab=d6}
N -580 760 -420 760 {lab=OUTP}
N -520 640 -520 670 {lab=d6}
N -520 730 -520 760 {lab=OUTP}
C {lab_pin.sym} -580 640 0 0 {name=lw1a sig_type=std_logic lab=d6}
C {lab_pin.sym} -580 760 0 0 {name=lw1b sig_type=std_logic lab=OUTP}
C {res.sym} -520 700 0 0 {name=Rwo6 value=\{RW*L_W\} footprint=1206 device=resistor m=1}
C {capa.sym} -420 670 0 0 {name=Cwo6a m=1 value=\{CW*L_W/2\} footprint=1206 device="ceramic capacitor"}
C {capa.sym} -420 790 0 0 {name=Cwo6b m=1 value=\{CW*L_W/2\} footprint=1206 device="ceramic capacitor"}
C {lab_pin.sym} -420 700 0 1 {name=lw1c sig_type=std_logic lab=VSS}
C {lab_pin.sym} -420 820 0 1 {name=lw1d sig_type=std_logic lab=VSS}
T {output line M9 (301 uA)} -100 570 0 0 0.3 0.3 {}
N -60 640 100 640 {lab=d9}
N -60 760 100 760 {lab=OUTM}
N 0 640 0 670 {lab=d9}
N 0 730 0 760 {lab=OUTM}
C {lab_pin.sym} -60 640 0 0 {name=lw2a sig_type=std_logic lab=d9}
C {lab_pin.sym} -60 760 0 0 {name=lw2b sig_type=std_logic lab=OUTM}
C {res.sym} 0 700 0 0 {name=Rwo9 value=\{RW*L_W\} footprint=1206 device=resistor m=1}
C {capa.sym} 100 670 0 0 {name=Cwo9a m=1 value=\{CW*L_W/2\} footprint=1206 device="ceramic capacitor"}
C {capa.sym} 100 790 0 0 {name=Cwo9b m=1 value=\{CW*L_W/2\} footprint=1206 device="ceramic capacitor"}
C {lab_pin.sym} 100 700 0 1 {name=lw2c sig_type=std_logic lab=VSS}
C {lab_pin.sym} 100 820 0 1 {name=lw2d sig_type=std_logic lab=VSS}
