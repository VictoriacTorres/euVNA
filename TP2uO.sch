<QucsStudio Schematic 5.9>
<Properties>
View=-371.587,-190.739,1427.27,770.815,0.777891,176,80
Grid=10,10,1
DataSet=*.dat
DataDisplay=*.dpl
OpenDisplay=3
showFrame=0
FrameText0=Title \n @PATH@@FILE@
FrameText1=Drawn By:
FrameText2=Date: @DATE@
FrameText3=Revision:
</Properties>
<Symbol>
</Symbol>
<Components>
CTLIN TL1 1 380 60 -26 16 0 "50 Ω"1"50 Ω"1"1 mm"1"1"0"1"0"0 dB"0"0 dB"0"26.85"0
Pac P1 1 -30 320 -74 -26 0 "1"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
Pac P2 1 180 320 18 -26 0 "2"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
Pac P3 1 150 410 18 -26 0 "3"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
Pac P4 1 10 410 -74 -26 0 "4"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
GND * 1 -30 350 0 0 0
GND * 1 10 440 0 0 0
GND * 1 180 350 0 0 0
GND * 1 150 440 0 0 0
MCOUPLED MSTC1 1 60 320 -26 37 0 "Subst1"1"3.14mm"1"15mm"1"3.2mm"1"26.85"0
SUBST Subst1 1 320 330 -30 24 0 "4.15"1"1.6mm"1"20µm"1"0.02"1"1.72e-08"1"0µm"1"Metal"0"Hammerstad"0"Kirschning"0
.SP SP1 1 680 240 0 9 0 "log"1"0.1 GHz"1"5 GHz"1"400"1"no"0"1"0"2"0"none"0
</Components>
<Wires>
-30 290 30 290
10 350 10 380
10 350 30 350
90 290 180 290
150 350 150 380
90 350 150 350
</Wires>
<Diagrams>
<Rect 578 670 360 220 31 #c0c0c0 1 00 1 0 2e+09 1e+10 1 -67.0722 20 6.08518 1 -1 0.5 1 -1 -1 -1 "" "" "">
	<Legend 10 -100 0>
	<"dB(S[1,1])" "" #0000ff 2 3 0 0 0 0 "">
	  <Mkr 2.00895e+09 22 -190 3 1 0 0 0 50>
</Rect>
<Rect 1020 670 360 220 31 #c0c0c0 1 00 1 0 2e+09 1e+10 1 -60 20 5.07278 1 -1 0.5 1 -1 -1 -1 "" "" "">
	<Legend 10 -100 0>
	<"dB(S[4,1])" "" #00dcdc 2 3 0 0 0 1 "">
	  <Mkr 2.00895e+09 10 -220 3 1 0 0 0 50>
	<"dB(S[3,1])" "" #ff00ff 2 3 0 0 0 1 "">
	  <Mkr 2.00895e+09 40 -60 3 1 0 0 0 50>
</Rect>
<Rect 1020 370 360 220 31 #c0c0c0 1 00 1 0 1e+09 5e+09 1 -13.0149 5 8.09938 1 -1 0.5 1 -1 -1 -1 "" "" "">
	<Legend 10 -100 0>
	<"dB(S[4,1])-dB(S[3,1])" "" #a00080 2 3 0 0 0 1 "">
	  <Mkr 2.00895e+09 150 -210 3 1 0 0 0 50>
</Rect>
<Smith 578 70 220 220 31 #c0c0c0 1 00 1 0 1 1 1 0 4 1 1 0 4 1 -1 -1 -1 "" "" "">
	<Legend 10 -100 0>
	<"S[1,1]" "" #0000ff 2 3 0 0 0 0 "">
	<"S[2,2]" "" #ff0000 2 3 0 0 0 0 "">
	<"S[3,3]" "" #00dc00 2 3 0 0 0 0 "">
	<"S[4,4]" "" #ff00ff 2 3 0 0 0 0 "">
</Smith>
</Diagrams>
<Paintings>
</Paintings>
