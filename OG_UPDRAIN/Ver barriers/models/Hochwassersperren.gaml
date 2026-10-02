/**
* Name: Hochwassersperren
* Based on the internal empty template. 
* Author: Diego
* Tags: 
*/


model Hochwassersperren

/* Insert your model definition here */

global  {
	
	float step <- 5 #mn;
	int DEMsize <- 10;
	file DEM<- grid_file("../includes/files/DGM.tif");
	file shp_build <- shape_file("../includes/files/Connected_Buildings.shp");
	file shp_street <- shape_file("../includes/files/Connected_Street_Areas.shp");
	file shp_network <- shape_file("../includes/files/Designed_Sewer_Network.shp");
	file shp_manholes <- shape_file("../includes/files/Base_Sewer_Nodes.shp");
	file shp_outfalls <- shape_file("../includes/files/Outfall.shp");
	//file shp_raingauge <- shape_file("../includes/files/MS5_SWMM_raingages.shp");
	file shp_LandUse <- shape_file("../includes/files/LandBedeckung.shp");
	file satellite_image <- image_file("../includes/files/backdrop.png");

	// all inside the statement//

    
	string floodmatrix<- "floodseries_T50_D60.csv"; //This file is used BY gama
	string savename<- "floodseries_T50_D60";             //simple string that is added at the end of the export
	
	int nb_pairs<-8;
	float tubewall_height<-0.5;
	int lead_time<-120;
	
	// ADDTIONAL STRING TO BE INSERTED AND SAVED
	file floodsurcharge <- csv_file("../includes/"+floodmatrix,false); // TO BE READ WITHIN THE NEW ACTION
	matrix floodvol <- matrix(floodsurcharge);
	date inicial <- date(floodvol[0, 1]);
	date starting_date <- inicial-lead_time#mn;
	
	date endflood<-date( floodvol[0, (length(firstcol)-1)]);
	
	
	list<string> toprow <- floodvol row_at (0);
	list<string> firstcol <- floodvol column_at (0);
	list<manholes> mansource;
	list<cell> sourcecells;
	
	int j;
	date real <- #now;	
	list time_series;
	
	// until here
	kml exportkml;


	bool fprot<-true;
	float xx;
	float yy;
	float length_fb;
	list<point> endpair;
	list<point> vertex;
	

    /* Visualization */

    rgb Roof <- rgb(#firebrick);         // Cumin red

    rgb Street <- 	rgb(#grey); // Indigo color
    rgb LID <- rgb(#darkgreen);   // Amazon green
    rgb perm <-rgb(#yellowgreen);
	
    /*Visualization */
	rgb agriculture<- rgb(220,255,0);
	rgb commercial<-  rgb(255, 51, 0);
	rgb industry <- rgb(255, 255, 102);
	rgb infrastructure <-rgb(255, 0, 255);
	rgb no_damage<- rgb(55, 86, 35);
	rgb mixed<-  rgb(255, 204, 0);
	rgb residential<-  rgb(191, 143, 0);
	rgb water_bodies<-  rgb(0, 176, 240);
	rgb total<- #grey;
	string RP <-"";
	map<string,rgb> legend<-['Agriculture'::agriculture,'Commercial'::commercial,'Industry'::industry,
		'Infrastrcuture'::infrastructure, 'No damage'::no_damage,"Mixed Area"::mixed,'Residential'::residential
	];
	
	rgb build<- rgb(#darkgray);
	rgb sewer<- rgb(#orange);
	rgb manh<-  rgb(#lightgray);
	rgb manh_source <- rgb(#blue);
	
	rgb lowpoint<-  rgb(0, 0, 0);
	rgb highpoint <- rgb(255, 255, 255);
	
	rgb waterdepthhigh<-  rgb(107, 174, 214);
	rgb waterdepthmid<- rgb(49, 130, 189);
	rgb waterdepthlow <- rgb(8, 81, 156);
	
	map<string,rgb> legend2<-['Buildings'::build,'Network'::sewer,'Manhole'::manh,'Source manhole'::manh_source];
	map<string,rgb> legend3<-['175 m'::highpoint,'111.63 m'::lowpoint];
	map<string,rgb> legend4<-['<0.05m'::waterdepthhigh,'>0.05m'::waterdepthmid,'>0.50m'::waterdepthlow];
	
	map<string,rgb> superl<- legend2+legend3+legend4;
	int pausa <- length(floodvol column_at (0)) - 2; //defines number of steps of the simulation
	geometry shape <- envelope(DEM);
	
	//maps where damage and floods are updated every cycle
	map<int, float> damagesums;
	map<int, float> floodsums;

	float max_value;
	float min_value;
	
	point first_click <- nil;
    bool waiting_for_second_click <- false;
	// Boolean variables for buttons




    
//Part 2: Initialization======================================================================================================================
	init {
		write(floodmatrix);
		write(savename);
	
		// Trigger the export CSV action on initialization
  

  
  


		list<date> time_series2<- (floodvol column_at (0))[1::length(floodvol column_at (0))];
		loop label over:time_series2{
			time_series<+ string(label,"HH:mm"); 
		}
		
		max_value <- cell max_of (each.grid_value);
		min_value <- cell min_of (each.grid_value);
		ask cell {
			
	/*Original code to use DEM to color
			 if (source = true) {
				color <- #blue;
		} 	else	{
				int val <- int(255 * ( 1  - (grid_value - min_value) /(max_value - min_value)));
				color <- rgb(val,val,val);*/
			if (source = true) {
				color <- #blue;					 
		}
		}
		
		list<string> findsource <- floodvol row_at (0); //creates list of flooded nodes as strings
	
		//creation of the building agents from the shapefile: the height and type attributes of the building agents are initialized according to the HEIGHT and NATURE attributes of the shapefile
		create building from: shp_build with:[height::float(5),name:: string(read("Name"))];
		create manholes from: shp_manholes  with: [name:: string(read("NODE_ID")),Name:: string(read("Name"))];
		create streets from: shp_street  with: [name:: string(read("Name"))];
		ask manholes{
			if self.name in findsource{
				self.source<-true;
			}
		}
		
		mansource <- manholes where (each.source = true);
		mansource <- mansource sort_by (each.name);
		
		ask mansource{
			cell targetf <- (cell at_distance (5)) closest_to self;
			targetf.source <- true;
		}
		
		create network from: shp_network;

		create outfall from: shp_outfalls;
		create landU from: shp_LandUse with: [code::int(read("LUCode"))];

		
		
			
		loop i over: findsource {
			manholes target <- manholes first_with (each.name = i);
			cell targetf <- (cell at_distance (10)) closest_to target;
			
			targetf.source <- true;
			targetf.node_name <-i;
			
		}
		sourcecells <- cell where (each.source = true);
		sourcecells <- sourcecells sort_by (each.name);
		xx<-shape.width;	
		yy<-shape.height;	
		write('Load Succesful');
		
		
		// POSSIBLE END OF INIT
		
       // Correctly create source_cell agents from grid cells marked as source
       /*  ask cell where (each.source) {
            create source_cell number: 1 {
                location <- self.location;
                height <- self.height;
                node_name <- self.node_name;
                waterdepth <- self.waterdepth;
                shape <- self.shape;
            }
            write ("source_cell created at " + location + " - Height: " + height + ", Water Depth: " + waterdepth);*/
        }
        
    
    // DECLARE NEW ACTION: SEND THE LIST TO R > 
     // SIMPLE OPTION: WRITE REFLEX THAT HAS A CONDITIONAL THAT ONLY RUN ON CYCLE 0/1 9CHECK THE FIRST)
     // OPTION 2: run the action declared when we click on the button
     
   
   //Part 3: Reflex and Actions ==========================================================================================================
		
		
		reflex flow when:  (current_date>=inicial) and (current_date<=endflood) {
			j <- firstcol index_of (string(current_date));
			write (current_date);
			ask sourcecells {
				do flow;
				
				if (experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0"or experiment.name= "Schutzsperren0"or experiment.name= "Schutzsperren_mitgraph0"){		
					do calc_damage;	
				
				}
				ask flowcells{
					if waterdepth > 0.00 {
						do update_color;
					}	
				}
				
			}
		}
		
		action draw_barrier {
        point location_clicked <- #user_location;
        
        if (!waiting_for_second_click) {
            // This is the first click of a pair
            first_click <- location_clicked;
            waiting_for_second_click <- true;
            write "First point selected at: " + first_click + ". Click again to create line.";
        } else {
            // This is the second click - create the line
            point second_click <- location_clicked;
            
            // Create a new limits agent as a line between the two points
            create floodbarriers {
                shape <- line([first_click, second_click]);
                location <- (first_click + second_click) / 2; // Center of the line
            }
            
            write "Line created from " + first_click + " to " + second_click;
            
            // Reset for next pair
            first_click <- nil;
            waiting_for_second_click <- false;
        }
    }


		reflex exportfinal {
		//first saves the headers
			if (current_date = endflood and (experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0"or experiment.name= "Schutzsperren0"or experiment.name= "Schutzsperren_mitgraph0")) {
				save ("Raster,Node,Inundated Area,Final Depth,Agriculture,Commercial,Industry,Infrastructure,Mixed Area,Residential,Total Damage") to:
					"../results/Manhole_Damage_" + savename + ".csv" format: "csv" header: false rewrite: true;
				save ("Raster,Node,Final Depth,Agriculture,Commercial,Industry,Infrastructure,No Damage,Mixed Area,Residential,Water Bodies,Total Area") to:
					"../results/Manhole_Flood_" + savename + ".csv" format: "csv" header: false rewrite: true;
				ask sourcecells {
					
						do exportf;
					 
				}
			}
		}
		
		
	
	reflex create_barrierpeople when: cycle = 0 {
			if (fprot = true) {
			//extracting vertices of barriers and dividing segments into 30 meters of length
			ask floodbarriers{
				list<geometry>segments<-to_segments(self.shape);
				loop i over:segments{
					list<point>endvertex<-i.points;
					self.vertices<<+ i points_on 30;
					self.vertices<+ last(endvertex);
					
				}
				self.vertices<-remove_duplicates(self.vertices);
				vertex<<+self.vertices;
				endpair<+last(self.shape.points);
				
				}
			
			//designating start points for the people			
			point start<-point(xx/2,yy/2);		
			create people number:nb_pairs*2{
				speed <- 0.5  #km / #h ;
				location<-start;
			}
			//agents install barriers in pairs, so they find a working pair
			list<people>pairing<-people collect(each);
			loop k from:0 to: length(pairing)-1{
				if (!empty(vertex)){
				if (even(k)){
					pairing[k].partner<-pairing[k+1];
					pairing[k].the_target<-vertex[0];
					vertex>>-vertex[0];
						}
				else{
					pairing[k].the_target<-vertex[0];
					if(endpair contains (vertex[0])){
						vertex>>-vertex[0];
								}
							}
						}
					}
	}}
	
	
		reflex export_grid{
			if (current_date = endflood) {				
				ask cell {
					do export_grid1;
				}
			save cell to: "../results/waterdepth " + savename + ".asc" format: "asc";
			
			ask cell  {
				do export_grid2;
			}

			if ((experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0"or experiment.name= "Schutzsperren0"or experiment.name= "Schutzsperren_mitgraph0")){	
				save cell to: "../results/totaldamage " + savename + ".asc" format: "asc";
				}
			
			
		}

	}
		
		reflex export {
		//writes header into file and erases previous file with same name
			if (current_date = endflood and (experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0"or experiment.name= "Schutzsperren0"or experiment.name= "Schutzsperren_mitgraph0")) {
				save
				("Time,Agriculture,Commercial,Industry,Infrastructure,Mixed Area,Residential,Total Damage,Flood_Agriculture,Flood_Commercial,Flood_Industry,Flood_Infrastructure,Flood_Green Areas,Flood_Mixed Area,Flood_Residential,Flood_Water Bodies,Total Flood Area")
				to: "../results/lu_series_"+savename +".csv" format: "csv" header: false rewrite: true;
				}
	
			//updated values for floodmap
			floodsums <+ 0::(cell sum_of (each.lc[0]));
			floodsums <+ 1::(cell sum_of (each.lc[1]));
			floodsums <+ 2::(cell sum_of (each.lc[2]));
			floodsums <+ 3::(cell sum_of (each.lc[3]));
			floodsums <+ 4::(cell sum_of (each.lc[4]));
			floodsums <+ 5::(cell sum_of (each.lc[5]));
			floodsums <+ 6::(cell sum_of (each.lc[6]));
			floodsums <+ 7::(cell sum_of (each.lc[7]));
			
			float totalflood <- floodsums sum_of (each);
			list<cell> damagecell <- cell where (each.waterdepth > 0.00);
			
			
			
			
			
			//updates values for damagemap
			damagesums <+ 0::damagecell sum_of ((each.lc[0] / 1000000) * 96711 * (each.waterdepth) ^ 0.4623);
			damagesums <+ 1::damagecell sum_of (each.lc[1] * 112.17 * (each.waterdepth) ^ 0.7756);
			damagesums <+ 2::damagecell sum_of (each.lc[2] * 85.333 * (each.waterdepth) ^ 0.7907);
			damagesums <+ 3::damagecell sum_of (each.lc[3] * 11.78 * (each.waterdepth) ^ 0.5617);
			damagesums <+ 4::0;
			damagesums <+ 5::damagecell sum_of ((each.lc[5] * 71.533 * (each.waterdepth) ^ 0.5589 + each.lc[5] * 112.17 * (each.waterdepth) ^ 0.7756) / 2);
			damagesums <+ 6::damagecell sum_of (each.lc[6] * 71.533 * (each.waterdepth) ^ 0.5589);
			damagesums <+ 7::0;

			
			float totaldam <- damagesums sum_of (each);
			
			//saves value vor flood and damage each cycle
			save
			((string(current_date, "HH:mm:ss") + "," + damagesums[0] + "," + damagesums[1] + "," + damagesums[2] + "," + damagesums[3] + "," + damagesums[5] + "," + damagesums[6] + "," + totaldam + "," + floodsums[0] + "," + floodsums[1] + "," + floodsums[2] + "," + floodsums[3] + "," + floodsums[4] + "," + floodsums[5] + "," + floodsums[6] + "," + floodsums[7] + "," + totalflood))
			to: "../results/lu_series_"+savename +'.csv' format: "csv" header: false rewrite: false;
	}
		reflex pause {
				
				//Why is this inside the other reflex??
			if (current_date = endflood) {
				write('End of Simulation and exports');
				
			}

		}
		}


//Part 4: Species Definition===============================================================================================================
species building {
	float height;
	string Name;
	string type;
	rgb color <-  Roof;
	bool Green_Roof<-false;
	
	
	/*file texture <- image_file("../includes/root_top1.jpg")*/ // Define the texture file
	
	aspect base {
		draw shape  color:color border:#black; /*texture: texture;*/ // Use the texture for the building
		if (Green_Roof) {
        // Make sure the image is clearly visible and positioned correctly
        
        draw shape color:LID border:#black; 
	}
}

}
	


species manholes  {
	string Name;
	bool source;
	bool Det_Tank <- false;
	
   
	aspect base {
		draw circle(3) color: source ? manh_source: manh border:#black;
		// Draw the detention tank image if Det_Tank is true

    }
}

		
species network {
	
	geometry shp <- shape+1;

	aspect pipe {
		draw shp color: sewer /*border:#black*/;
	}

}

species high_subcatchment {
    rgb color <- #yellow;

	aspect base {
		draw square(5) color: color border:#black;
	}

}

species streets {
    string Name;
    bool Perm_Pav <- false;
    

	aspect base {
		draw shape color:Street border:#black; 
	
	if (Perm_Pav) {
       draw shape color:perm border:#black; 
		}
	

}}


species people skills:[moving]{
	//definition of attributes
	point the_target <- nil ;
	int counter<-0;
	geometry fbarrier;
	people partner;
	float timeinstall<-6.0 max:6.0;
	rgb color<-rnd_color(255);
	file my_icon <- file("../includes/data/worker.png") ;
	
	//reflex to move whenever the target location changes
	reflex move when: the_target != nil {
		path path_followed <- goto(target:the_target);
	}
	
	//creates link when self and partner are in position, calculates time needed to install according to length and counts time in position
	reflex barrierline when:partner != nil{
		if (the_target = location)  {	
			ask partner{		
				if (self.the_target = self.location){	
					myself.fbarrier<-link(self,myself);
					myself.timeinstall<-ceil(myself.fbarrier.perimeter*12/60);
					myself.counter<-myself.counter+1;
				}
			}
		}
		else{
			fbarrier<-nil;
		}
	}
	
	//when time needed to install is reached the barrier is created in the raster and as the Tubewall for the 3d display
	reflex fbarrier when:(partner != nil){
		if(counter=timeinstall){	
			geometry edge<-fbarrier;
			list<cell> barriers<-(cell at_distance(distance_to(self.location,partner.location)*10)) overlapping (edge);
			ask barriers{
				
				if (waterdepth=0){
					self.height<-self.height+tubewall_height;
					self.barrier<-true;
					do update_color;
					}
				}
			
			create Tubewall {
			
			location<-{(myself.location.x+myself.partner.location.x)/2,(myself.location.y+myself.partner.location.y)/2};
			length<-distance_to(myself,myself.partner);
			rotation<-atan2((myself.location.y-myself.partner.location.y),(myself.location.x-myself.partner.location.x));
		
			}
			
			//when barrier is created new target locations is designated for wach pair, if still needed	
			if (!empty(vertex)){
				the_target<-vertex[0];
				partner.the_target<-vertex[1];
				vertex>>-vertex[0];
				if(endpair contains (vertex[0])){
					vertex>>-vertex[0];
					}
				counter<-0;
			}
			
			}
		}
	
		//regular display
		aspect base {
			//draw my_icon size:{8,15,0} at:location+{0,5,0};
			draw circle(4) color:#green border:#black;			
		}
		
		//3d display
		aspect geom3D {	
			draw obj_file("../includes/data/people.obj", 90::{-1,0,0}) size: 5
			at: location + {0,0,7} rotate: heading - 90 color: color;
	}
}

//flood barrier species where the locations for the barriers are extracted from
species floodbarriers frequency:0 {
	string node;
	list<point> vertices;
	map<people,point> floodbar;

	aspect base {
		draw shape+2.0 color:#black width: 16;
		
	}
	
}



species limits {
    // Line visualization
    aspect default {
        draw shape color: #red width: 2;
        // Optional: draw endpoints as small circles
        draw circle(1) at: shape.points[0] color: #blue;
        draw circle(1) at: shape.points[1] color: #blue;
    }
}

//barrier species created for 3d display
species Tubewall {
	rgb color<-#green;
	float length;
	float rotation;
	geometry tubew;
	
	aspect tube{
		draw box(length,3,5) at: location +{0,0,2.5}  rotate:rotation color:#green;
	}
}
    

species outfall{
	string name;
	rgb color <- #red;

	aspect base {
		draw triangle(10) color: color border:#black;
	}

}

//species raingauge {
//	rgb color <- #blue;

//	aspect base {
//		draw circle(5) color: color;
	//}

//}

species landU frequency: 1000 {
	int code;
	rgb color;

	init {
		if (code = 0) {
			color <- agriculture;
		} else if (code = 1) {
			color <- commercial;
		} else if (code = 2) {
			color <- industry;
		} else if (code = 3) {
			color <-infrastructure;
		} else if (code = 4) {
			color <- no_damage;
		} else if (code = 5) {
			color <- mixed;
		} else if (code = 6) {
			color <- residential;
		} else if (code = 7) {
			color <- water_bodies;
		} }

	aspect base {
		draw shape color: color border:#black;
	} }

grid cell file: DEM neighbors: 8 {
	bool source;
	float height;
	string node_name;
	float waterdepth min: 0.0;
	float waterflowing;
	list<cell> flowcells;
	bool bflow <- false;
	map<int, float> lc;
	bool barrier <- false;
	
	/*additional part  */
	aspect default {
        if (bflow) { // Modified to check only if bflow is true
            draw shape size: 1 color: #royalblue border: #dodgerblue; // Cyan for flooded cells
        }
        // Cells where bflow is false are not drawn
    }
	
	init {
		height <- grid_value;//assigns the DEM values as attribute height
	}

/*species source_cell {
    float height;
    string node_name;
    float waterdepth;
    geometry shape;

    aspect default {
        draw shape color: #red size: 30; // Use the desired color for water extent
    }
}*/

//---------------------------------------------------------------------------------------------------------------------------------------------//	

//Chen's algorithm
	action flow {
		int i <- toprow index_of (node_name);//looks for value i in the flood matrix

		if ((float(floodvol[i, j])) > 0) {//if the value is greater than zero, asigns the value to the variable waterflowing divided by the area of the cell
			waterflowing <- waterflowing + ((float(floodvol[i, j])*300/1000) / DEMsize ^ 2); //conversion for lps to m3/5 minutes, divided by area 
			
			
			
			//when waterflowing is higher than 0.05 water is allowed to flow to neighbors,
			if (waterflowing > 0.05) {
				int n <- 1;
				
				//for first time it flows if it has an aempty floowcells list
				if(empty(flowcells)){
					bflow <- true;
					waterdepth <- (waterflowing);
				}
				else {
					//if not empty, it recalculates the depth it should have with updated volume
					waterdepth <- (waterflowing/length(flowcells));
				}
				
				//assign waterdepth to all cells already flooded in the list
				
	
				loop m over: flowcells {
						m.waterdepth <- waterdepth;
					}
				if (waterdepth>0.05){
					
				//loop while the border conditions of the algorithm are true	
				loop while: (waterdepth > 0.05 and n < 50) {
					list<cell> bcell <- flowcells where (each.bflow = true);
					
					//inside loop looks for neighbor cells that have lower elevation and asigns them to list 	

					loop m over: bcell {
						list<cell> flowneigh;
						flowneigh <- (m.neighbors + m) where (each.height <= m.height);
						add all: flowneigh to: flowcells;
					}
					
	
					//remove repeated cells and divide the water in number of cells in the list
					flowcells <- reverse(remove_duplicates((flowcells + self) sort_by (each.height)));
					waterdepth <- waterflowing / length(flowcells);		
					
					//assign the value of depth to all cells in the list	
					loop m over: flowcells {
						m.waterdepth <- waterdepth;
						m.bflow <- true;
					}

					n <- n + 1;
				}
				
				}

			}

		}

	}
	
	action calc_damage {
		int i <- toprow index_of (node_name);
		if (float(floodvol[i, j]) > 0) {
		//checks for intesecting and overlapping Land use shapes
		
			ask flowcells{
				if empty(self.lc){
					list<landU> inters <- (landU at_distance (10)) overlapping self;
					loop k over: inters {
						add k.code::((self inter k).area) to: self.lc;				
					}			
				}				
			}
		}
	}

	action update_color {
	//values depending of waterdepth
		if (waterdepth > 0.0 and waterdepth <= 0.25) {
			color <- rgb(107, 174, 214);
		} else if (waterdepth > 0.25 and waterdepth <= 0.50) {
			color <- rgb(49, 130, 189);
		} else if (waterdepth > 0.50) {
			color <- rgb(8, 81, 156);
			//value if there is a flood barrier
		} else if (barrier = true) {
			color <- #green;
		} else {
			//if there is no flood barrier or water DSM set to grayscale
			int val <- int(255 * (1 - (height - min_value) / (max_value - min_value)));
			color <- rgb(val, val, val);
		} 
	}
	
	action export_grid1 {		
		if(waterdepth=0){
			grid_value <- nil;
		}
		else {
			grid_value <- waterdepth;
		}
	}

	//assigns damage values to grid value to export as raster
	action export_grid2 {
		if(waterdepth=0){
			grid_value <- nil;
		}
		else {

		map<int, float> damage <- [0::(lc[0] / 1000000) * 109722 * waterdepth ^ 0.4623, 
			1::lc[1] * 127.272 * waterdepth ^ 0.7756, 
			2::lc[2] * 96.813 * waterdepth ^0.7907, 
			3::lc[3] * 13.365 * waterdepth ^ 0.5617, 
			4::0, 
			5::(lc[5] * 81.157 * waterdepth ^ 0.5589) * 0.5 + (lc[5] * 127.27 * waterdepth ^0.7756) * 0.5, 
			6::(lc[6] * 81.157 * waterdepth ^ 0.5589), 
			7::0];
		float totaldamage <- damage sum_of (each);
		grid_value <- totaldamage;
		}
	}
	
	action exportf {
		map<int, float> damagesumsf;
		map<int, float> floodarea;
		float inundatedarea <- length(flowcells) * DEMsize ^ 2;
		damagesumsf <+ 0::(flowcells sum_of ((each.lc[0] / 1000000) * 96711 * (each.waterdepth) ^ 0.4623));
        damagesumsf <+ 1::flowcells sum_of (each.lc[1] * 112.17 * (each.waterdepth) ^ 0.7756);
        damagesumsf <+ 2::flowcells sum_of (each.lc[2] * 85.333 * (each.waterdepth) ^ 0.7907);
        damagesumsf <+ 3::flowcells sum_of (each.lc[3] * 11.78 * (each.waterdepth) ^ 0.5617);
        damagesumsf <+ 4::0;
        damagesumsf <+ 5::flowcells sum_of ((each.lc[5] * 71.533 * (each.waterdepth) ^ 0.5589 + each.lc[5] * 112.17 * (each.waterdepth) ^ 0.7756) / 2);
        damagesumsf <+ 6::flowcells sum_of (each.lc[6] * 71.533 * (each.waterdepth) ^ 0.5589);
        damagesumsf <+ 7::0;

		float totaldam <- damagesumsf sum_of (each);
        floodarea <+ 0::flowcells sum_of (each.lc[0]);
        floodarea <+ 1::flowcells sum_of (each.lc[1]);
        floodarea <+ 2::flowcells sum_of (each.lc[2]);
        floodarea <+ 3::flowcells sum_of (each.lc[3]);
        floodarea <+ 4::flowcells sum_of (each.lc[4]);
        floodarea <+ 5::flowcells sum_of (each.lc[5]);
        floodarea <+ 6::flowcells sum_of (each.lc[6]);
        floodarea <+ 7::flowcells sum_of (each.lc[7]);
		float totalf <- floodarea sum_of (each);
		
		//exports csv with damagevalues
		save
		(name + "," + node_name + "," + inundatedarea + "," + waterdepth + "," + damagesumsf[0] + "," + damagesumsf[1] + "," + damagesumsf[2] + "," + damagesumsf[3] + "," + damagesumsf[5] + "," + damagesumsf[6] + "," + totaldam)
		to: "../results/Manhole_Damage_"+savename+ ".csv" format: "csv" header: false rewrite: false;
		
		//exports csv with floodvalues
		save
		(name + "," + node_name + "," + waterdepth + "," + floodarea[0] + "," + floodarea[1] + "," + floodarea[2] + "," + floodarea[3] + "," + floodarea[4] + "," + floodarea[5] + "," + floodarea[6] + "," + floodarea[7] + "," + totalf)
		to: "../results/Manhole_Flood_"+savename +".csv" format: "csv" header: false rewrite: false;
	} 
	
}

//PART 5: Experiments ============================================================================================================

experiment Flood_Propagation type: gui {
		
	category "Explanation" expanded: false color: #green; 	
	text "Welcome! You can modify the model in this control panel. Remember to check the constraints before applying any modification. The model can be reverted to its original state trough the Reset Button. Enjoy!" category: "Explanation" color: #lightgreen background: #black font: font("Helvetica",8,#bold); 
    // Category for file choosers
  category "Rain Event Selection" expanded: false color: #orange;
    // In the following, when a_boolean_to_enable_parameters is true, it enables the input chooser for multiple_choice.
	

   
    output synchronized:true
 
     {
     
	layout horizontal([0.7::70, 0.3::30]) tabs:true; // Adjust the ratio according to your needs
		
		display Map_display type: 2d axes:false fullscreen: false {
		
            overlay position: {0, 0} size: { 120 #px, 300 #px } background: #black transparency: 0.5 border: #black rounded: true
            {
                //for each possible type, we draw a square with the corresponding color and we write the name of the type
                float y <- 15#px;
                loop type over: legend2.keys
                {
                    draw square(5#px) at: { 10#px, y } color: legend2[type] border: #white;
                    draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                    y <- y + 20#px; // Reduced spacing
                }
                draw "" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                y <- y + 20#px; // Reduced spacing
                draw "Subcatchment" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                y <- y + 20#px; // Reduced spacing
                    
                    
                map<string, rgb> subcatchment_legend <- [
                   
                    "Roof"::Roof,
                   
                    "Street"::Street,
                    "LID Implementation"::LID
                ];

                loop type over: subcatchment_legend.keys
                {
                    draw square(5#px) at: { 10#px, y } color: subcatchment_legend[type] border: #white;
                    draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                    y <- y + 20#px; // Reduced spacing
                }

                draw "" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                y <- y + 20#px; // Reduced spacing
                draw "Flooded Area" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                y <- y + 20#px; // Reduced spacing
                draw square(5#px) at: { 10#px, y } color: rgb(0, 0, 255) border: #white; // Assuming flooded area is blue
                draw "Flooded" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                y <- y + 20#px; // Reduced spacing
            }
            
			
			
			
			/*grid cell border: #lightgrey elevation: grid_value * 5 transparency: 0.5;*/
			image satellite_image transparency: 0;
			species cell;
			species building aspect: base;
			species streets aspect: base;
			species outfall aspect: base;
			species network aspect: pipe;
			species manholes aspect: base;
			
			/*species high_subcatchment aspect: base;*/
		
		
		
		
		}
		 
   
	}

}

experiment Flood_Damages type: gui {
	
		
    output synchronized:true {
     
	layout horizontal([0.7::70, 0.3::30]) tabs:true; // Adjust the ratio according to your needs
		
	display Map_display type: 2d axes:false fullscreen: false {
		
        overlay position: {0, 0} size: { 120 #px, 300 #px } background: #black transparency: 0.5 border: #black rounded: true {
            //for each possible type, we draw a square with the corresponding color and we write the name of the type
            float y <- 15#px;
            loop type over: legend2.keys {
                draw square(5#px) at: { 10#px, y } color: legend2[type] border: #white;
                draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                y <- y + 20#px; // Reduced spacing
            }
            draw "" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
            y <- y + 20#px; // Reduced spacing
            draw "Subcatchment" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
            y <- y + 20#px; // Reduced spacing
                
            map<string, rgb> subcatchment_legend <- [
             
                "Roof"::Roof,
                
                "Street"::Street,
                "LID implementation"::LID
            ];

            loop type over: subcatchment_legend.keys {
                draw square(5#px) at: { 10#px, y } color: subcatchment_legend[type] border: #white;
                draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
                y <- y + 20#px; // Reduced spacing
            }

            draw "" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
            y <- y + 20#px; // Reduced spacing
            draw "Flooded Area" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
            y <- y + 20#px; // Reduced spacing
            draw square(5#px) at: { 10#px, y } color: rgb(0, 0, 255) border: #white; // Assuming flooded area is blue
            draw "Flooded" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 10, #bold); // Reduced font size
            y <- y + 20#px; // Reduced spacing
        }
        image satellite_image transparency: 0;
			
		species landU aspect: base transparency: (cycle <3) ? (cycle/3) : 0.6;
		/*grid cell border: #lightgrey elevation: grid_value * 5 transparency: 0.5;*/
		species cell;
		species building aspect: base;
		species streets aspect: base;
		species outfall aspect: base;
		species network aspect: pipe;
		
		
		species manholes aspect: base;
		/*species high_subcatchment aspect: base;*/
	}
    
	display damage type:2d  {
		chart "Damage Propagation" type: series size: {1, 0.5} position: {0, 0.5} x_label:'Time'+string(current_date,"dd.MM.yyyy") x_serie_labels:time_series y_label:'Damages [$]' {
			data "Agriculture" value: ((damagesums[0])) color: agriculture;
			data "Commercial" value: ((damagesums[1])) color: commercial;
			data "Industry" value: ((damagesums[2])) color: industry;
			data "Infrastructure" value: ((damagesums[3])) color: infrastructure;
			data "Mixed Area" value: ((damagesums[5])) color: mixed;
			data "Residential" value: ((damagesums[6])) color: residential;
			data "Total" value: (damagesums sum_of (each)) color: total;
		}
		chart "Flood Propagation" type: series size: {1, 0.5} position: {0, 0} x_label:'Time '+string(current_date,"dd.MM.yyyy") x_serie_labels:time_series y_label:'Inundated Area [m^2]'{
			data "Agriculture" value: (floodsums[0]) color: agriculture;
			data "Commercial" value: (floodsums[1]) color: commercial;
			data "Industry" value: (floodsums[2]) color: rgb(255, 255, 102);
			data "Infrastructure" value: (floodsums[3]) color:infrastructure;
			data "No Damage Area" value: (floodsums[4]) color: no_damage;
			data "Mixed Area" value: (floodsums[5]) color: mixed;
			data "Residential" value: (floodsums[6]) color: residential;
			data "Water Bodies" value: (floodsums[7]) color: water_bodies;
			data "Total" value: (floodsums sum_of (each)) color: total;
		}
	}
}
}


experiment Schutzsperren type: gui {
	parameter "Number of Pairs" var: nb_pairs min:1 max:10 category: "Load Param";
	parameter "Lead Time" var: lead_time min:30 max:300 step:15 category: "Load Param";
	parameter "Tubewall Height" var: tubewall_height among:[0.5,0.75,1.0] category: "Load Param";
	
	output {
		display city_display type: 2d axes:false {
			
						overlay position: {0, 0} size: { 390 #px, 140 #px } background: # black transparency: 0.5 border: #black rounded: true
            {
            	//for each possible type, we draw a square with the corresponding color and we write the name of the type
                float y <- 15#px;
                loop type over: legend2.keys
                {
                	draw square(5#px) at: { 10#px, y } color: legend2[type] border: #white;
                	draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y <- y + 15#px;
                }
                draw "" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y <- y + 15#px;
                draw "DEM" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y <- y + 15#px;
                    
                    
                loop type over: legend3.keys
                {
                    draw square(5#px) at: { 10#px, y } color: legend3[type] border: #white;
                    draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y <- y + 15#px;
                }
                
                
                float y2 <- 15#px;
                draw "Land cover" at: { 130#px, y2 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y2 <- y2 + 15#px;
                    
                    
                loop type over: legend.keys
                {
                    draw square(5#px) at: { 130#px, y2 } color: legend[type] border: #white;
                    draw type at: { 150#px, y2 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y2 <- y2 + 15#px;
                }
                float y3 <- 15#px;
                
                draw "Water depth" at: { 260#px, y3 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y3 <- y3 + 15#px;
                loop type over: legend4.keys
                {
                    draw square(5#px) at: { 260#px, y3 } color: legend4[type] border: #white;
                    draw type at: { 280#px, y3 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y3 <- y3 + 15#px;
                }

            }
			
			
			grid cell border:#lightgray;
			species landU aspect: base transparency: (cycle <3) ? (cycle/3) : 1;
			species building ;
			species outfall aspect:base;
			//species raingauge aspect: base;
			species network aspect: pipe;
			//species street aspect: pipe;
			species manholes aspect: base;
			species floodbarriers aspect:base ;	
			species people aspect: base;
			event #mouse_down {ask simulation {do draw_barrier;}}
			
		}
		

	}
}

experiment Schutzsperren_mitgraph type: gui {
	output {
		display city_display type: 2d axes:false {
			
						overlay position: {0, 0} size: { 390 #px, 140 #px } background: # black transparency: 0.5 border: #black rounded: true
            {
            	//for each possible type, we draw a square with the corresponding color and we write the name of the type
                float y <- 15#px;
                loop type over: legend2.keys
                {
                	draw square(5#px) at: { 10#px, y } color: legend2[type] border: #white;
                	draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y <- y + 15#px;
                }
                draw "" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y <- y + 15#px;
                draw "DEM" at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y <- y + 15#px;
                    
                    
                loop type over: legend3.keys
                {
                    draw square(5#px) at: { 10#px, y } color: legend3[type] border: #white;
                    draw type at: { 20#px, y + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y <- y + 15#px;
                }
                
                
                float y2 <- 15#px;
                draw "Land cover" at: { 130#px, y2 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y2 <- y2 + 15#px;
                    
                    
                loop type over: legend.keys
                {
                    draw square(5#px) at: { 130#px, y2 } color: legend[type] border: #white;
                    draw type at: { 150#px, y2 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y2 <- y2 + 15#px;
                }
                float y3 <- 15#px;
                
                draw "Water depth" at: { 260#px, y3 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                y3 <- y3 + 15#px;
                loop type over: legend4.keys
                {
                    draw square(5#px) at: { 260#px, y3 } color: legend4[type] border: #white;
                    draw type at: { 280#px, y3 + 4#px } color: # white font: font("Helvetica", 12, #bold);
                    y3 <- y3 + 15#px;
                }

            }
			
			
			grid cell border:#lightgray;
			species landU aspect: base transparency: (cycle <3) ? (cycle/3) : 1;
			species building ;
			species outfall aspect:base;
			//species raingauge aspect: base;
			species network aspect: pipe;
			//species street aspect: pipe;
			species manholes aspect: base;
			species floodbarriers aspect:base ;	
			species people aspect: base;
			event #mouse_down {ask simulation {do draw_barrier;}}
			
		}
		
display damage type:2d refresh: every(1#cycle){
    chart "Damage Propagation" type: series size: {1, 0.5} position: {0, 0.5} 
    x_label:'Time'+string(current_date,"dd.MM.yyyy") x_serie_labels:time_series y_label:'Damages [$]' {
    	ask simulation {
            
    	
         
            data "Agriculture" value: ((damagesums[0])) color: agriculture;
            data "Commercial" value: ((damagesums[1])) color: commercial;
            data "Industry" value: ((damagesums[2])) color: industry;
            data "Infrastructure" value: ((damagesums[3])) color: infrastructure;
            data "Mixed Area" value: ((damagesums[5])) color: mixed;
            data "Residential" value: ((damagesums[6])) color: residential;
            data "Total" value: (damagesums sum_of (each)) color: total;
        }
    }
    chart "Flood Propagation" type: series size: {1, 0.5} position: {0, 0} 
    x_label:'Time '+string(current_date,"dd.MM.yyyy") x_serie_labels:time_series y_label:'Inundated Area [m^2]'{
        
            data "Agriculture" value: (floodsums[0]) color: agriculture;
            data "Commercial" value: (floodsums[1]) color: commercial;
            data "Industry" value: (floodsums[2]) color: rgb(255, 255, 102);
            data "Infrastructure" value: (floodsums[3]) color:infrastructure;
            data "No Damage Area" value: (floodsums[4]) color: no_damage;
            data "Mixed Area" value: (floodsums[5]) color: mixed;
            data "Residential" value: (floodsums[6]) color: residential;
            data "Water Bodies" value: (floodsums[7]) color: water_bodies;
            data "Total" value: (floodsums sum_of (each)) color: total;
        
    }
}
	}
}

experiment 3d type: gui {

	output {
		
		display urbanflood type:opengl {
			grid cell border: #black;
			species network aspect: pipe;
			species manholes aspect: base;
			species landU aspect: base  transparency: 1;
			species people aspect: geom3D;
			species floodbarriers aspect:base transparency: (cycle <1) ? 0 : 1;
			species Tubewall aspect:tube;	
			event #mouse_down {ask simulation {do draw_barrier;}}		
			}
}
}