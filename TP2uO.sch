<QucsStudio Schematic 5.9>
<Properties>
View=0,0,1498,800,1,83,0
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
Pac P1 1 270 230 -74 -26 0 "1"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
Pac P2 1 480 230 18 -26 0 "2"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
Pac P3 1 450 320 18 -26 0 "3"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
Pac P4 1 310 320 -74 -26 0 "4"1"50"1"0 dBm"0"1 GHz"0"26.85"0"con_2"0
GND * 1 270 260 0 0 0
GND * 1 310 350 0 0 0
GND * 1 480 260 0 0 0
GND * 1 450 350 0 0 0
MCOUPLED MSTC1 1 360 230 -26 37 0 "Subst1"1"3.13717mm"1"15mm"1"3.81157mm"1"26.85"0
SUBST Subst1 1 740 240 -30 24 0 "4.15"1"1.6mm"1"20µm"1"0.02"1"1.72e-08"1"0µm"1"Metal"0"Hammerstad"0"Kirschning"0
.SP SP1 1 870 240 0 9 0 "log"1"0.2 GHz"1"20 GHz"1"201"1"no"0"1"0"2"0"none"0
</Components>
<Wires>
270 200 330 200
310 260 310 290
310 260 330 260
390 200 480 200
450 260 450 290
390 260 450 260
</Wires>
<Diagrams>
<Rect 1098 240 360 220 31 #c0c0c0 1 00 1 0 1 1 1 0 1 1 1 0 1 1 -1 -1 -1 "" "" "">
	<Legend 10 -100 0>
	<"dB(S[1,1])" "" #0000ff 2 3 0 0 0 0 "">
	<"dB(S[2,1])" "" #ff0000 2 3 0 0 0 0 "">
</Rect>
<Smith 1098 540 220 220 31 #c0c0c0 1 00 1 0 1 1 1 0 1 1 1 0 1 1 -1 -1 -1 "" "" "">
	<Legend 10 -100 0>
	<"S[1,1]" "" #0000ff 2 3 0 0 0 0 "">
	<"S[2,2]" "" #ff0000 2 3 0 0 0 0 "">
	<"S[3,3]" "" #00dc00 2 3 0 0 0 0 "">
	<"S[4,4]" "" #ff00ff 2 3 0 0 0 0 "">
</Smith>
</Diagrams>
<Paintings>
</Paintings>
