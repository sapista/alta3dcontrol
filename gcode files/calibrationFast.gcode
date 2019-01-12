G28
G90

G1 Z3 F2500
G1 X-43.3 Y-25 F1000		//A  Point Coordinates (Front Left)
G1 Z0 F1000					
G4 S10


G1 Z3 F2500
G1 X43.3 Y-25 F1000			//B  Point Coordinates (Front right)
G1 Z0 F1000
G4 S10

G1 Z3 F2500
G1 X0 Y50 F1000				//C  Point Coordinates (Back mid)
G1 Z0 F1000
G4 S10

G28
M114
