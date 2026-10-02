/**
* Name: LIDtool
* Based on the internal empty template. 
* Author: Diego
* Tags: 
*/


model LIDtool

/* Insert your model definition here */


global  {
	
	float step <- 1 #mn;
	int DEMsize <- 10;

	file DEM<- grid_file("../includes/files/DSM10.tif");
	
	
	file shp_build <- shape_file("../includes/files/Connected_Buildings.shp");
	file shp_street <- shape_file("../includes/files/Connected_Street_Areas.shp");
	file shp_network <- shape_file("../includes/files/Designed_Sewer_Network.shp");
	file shp_manholes <- shape_file("../includes/files/Base_Sewer_Nodes.shp");
	file shp_outfalls <- shape_file("../includes/files/Outfall.shp");
	//file shp_raingauge <- shape_file("../includes/files/MS5_SWMM_raingages.shp");
	file shp_LandUse <- shape_file("../includes/files/Land Use.shp");

	
	file satellite_image <- image_file("../includes/images/backnew.png");

	file det_tank_icon <- image_file("../includes/images/det_tank2.png"); 
	string python_path <- "C:/Users/Diego/micromamba/envs/swmm/python.exe";
    string script_path <- "../includes/code/GAMA_swmm.py";
	
	
	list<string> green_roof_subcatchments <- [];

    list<string> detention_tank_junctions <- [];
    list<string> permeable_pavements_subcatchments <- [];

	// all inside the statement//
	
	string event_duration;
	list <string> event_dur_list <-["30 minutes","60 minutes", "90 minutes", "120 minutes"];

	list<string> RP_list<-["5 Year","10 Year","20 Year","50 Year"];
    
	string floodmatrix; //This file is used BY gama
	string savename;             //simple string that is added at the end of the export
	
	// ADDTIONAL STRING TO BE INSERTED AND SAVED
	
	
	list<string> toprow ;
	list<string> firstcol ;
	list<manholes> mansource;
	list<cell> sourcecells;
	
	int j;
	
	
	
	// until here
	kml exportkml;

	
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
	rgb manh_source <- rgb(#darkred);
	
	
	rgb lowpoint<-  rgb(0, 0, 0);
	rgb highpoint <- rgb(255, 255, 255);
	
	rgb waterdepthhigh<-  rgb(107, 174, 214);
	rgb waterdepthmid<- rgb(49, 130, 189);
	rgb waterdepthlow <- rgb(8, 81, 156);
	
	map<string,rgb> legend2<-['Buildings'::build,'Network'::sewer,'Manhole'::manh,'Source manhole'::manh_source];
	map<string,rgb> legend3<-['175 m'::highpoint,'111.63 m'::lowpoint];
	map<string,rgb> legend4<-['<0.05m'::waterdepthhigh,'>0.05m'::waterdepthmid,'>0.50m'::waterdepthlow];
	
	map<string,rgb> superl<- legend2+legend3+legend4;
	
	geometry shape <- envelope(DEM);
	
	//maps where damage and floods are updated every cycle
	map<int, float> damagesums;
	map<int, float> floodsums;

	float max_value;
	float min_value;
	
	// Boolean variables for buttons
    bool trigger_changes <- false;
    bool trigger_reset <- false;
    // Boolean variables for button triggers
    bool trigger_traditional <- false;
    bool show_lids <- false;
	int pausa;
	file floodsurcharge;
	matrix floodvol;
	



 
        
    
//Part 2: Initialization======================================================================================================================
	init {
		


		
		max_value <- cell max_of (each.grid_value);
		min_value <- cell min_of (each.grid_value);
	
		
		
	
		//creation of the building agents from the shapefile: the height and type attributes of the building agents are initialized according to the HEIGHT and NATURE attributes of the shapefile
		create building from: shp_build with:[Name:: string(read("sub_id"))];
		create manholes from: shp_manholes  with: [Name:: string(read("NODE_ID"))];
		create streets from: shp_street  with: [Name:: string(read("sub_id"))];
		
		
		create network from: shp_network;
		//create street from: shp_street;
		//create raingauge from: shp_raingauge;
		create outfall from: shp_outfalls;
		create landU from: shp_LandUse with: [code::int(read("LUCode"))];
	    //create subcatchment from: shp_subcatchment with: [code::int(read("ID"))];
		//create subcatchment from: shp_subcatchment with: [name::string(read("Name"))];
		//create high_subcatchment from: shp_high_subcatchment;
		
		
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
		
action SWMM {
	savename<-string(date('now'), "yyyy-MM-dd_HHmm");
    

    write "Connecting to SWMM";

	
	write "Subcatchments with Green Roof: " + green_roof_subcatchments;
    write "Subcatchments with Permeable Pavement: " + permeable_pavements_subcatchments;
    write "Subcatchments with Detention Tank: " + detention_tank_junctions;
    map<string, unknown> json_python <- [
    	"hash"::savename,
        "event_duration" :: event_duration,
        "RP" :: RP,
        "GR" :: green_roof_subcatchments,
        "PP"::permeable_pavements_subcatchments,
        "tanks"::detention_tank_junctions ];
    save json_python to: "../includes/code/json_python.json" format: "json" rewrite: true;
        
    write "Starting Python execution...";
        
        // Option 1: Direct Python executable path
        string cmd <- python_path + " " + script_path;
        
        
        // Option 2: Using micromamba (alternative)
        // string cmd <- "cmd /c cd /d C:/Users/Diego/micromamba/envs/swmm && micromamba run -n swmm python " + script_path;
        
        write "Executing command: " + cmd;
        string output <- command(cmd);
        
        write "Python Output: " + output;
        
        floodmatrix<-"flood_series_"+savename+'.csv';
        
        
        // Check for success and read results
        if (file_exists("../includes/flood_series/"+floodmatrix)) {
            floodsurcharge <- csv_file("../includes/flood_series/"+floodmatrix,false); 
            
            write "Data read back into GAMA" ;
        } else {
            error "Python script did not produce output file or failed.";
        }
        
  
 
        
    // TO BE READ WITHIN THE NEW ACTION
	floodvol <- matrix(floodsurcharge);
	date inicial <- date(floodvol[0, 1]);
	starting_date <- inicial;
	
	
	
	toprow <- floodvol row_at (0);
	firstcol <- floodvol column_at (0);
	pausa <- length(floodvol column_at (0)) - 2; //defines number of steps of the simulation
    
    list<string> findsource <- floodvol row_at (0); //creates list of flooded nodes as strings
    
		ask manholes{
			if self.Name in findsource{
				self.source<-true;
				
			}
		}
		
		mansource <- manholes where (each.source = true);
		mansource <- mansource sort_by (each.Name);
		
		ask mansource{
			draw circle(3) color: source ? manh_source: manh border:#black;
			cell targetf <- (cell at_distance (5)) closest_to self;
			targetf.source <- true;
			
		}	
		loop i over: findsource {
			manholes target <- manholes first_with (each.Name = i);
			cell targetf <- (cell at_distance (10)) closest_to target;
			
			targetf.source <- true;
			targetf.node_name <-i;
			
		}
		sourcecells <- cell where (each.source = true);
		
		sourcecells <- sourcecells sort_by (each.name);
		
    
    

}
	
 
		
		reflex flow {
			j <- firstcol index_of (string(current_date));
			
			ask sourcecells {
				do flow;
				
				if (experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0"){		
					do calc_damage;	
				
				}
				ask flowcells{
					if waterdepth > 0.00 {
						do update_color;
					}	
				}
				
			}
		}


		reflex exportfinal {
		//first saves the headers
			if (cycle = pausa and (experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0")) {
				save ("Raster,Node,Inundated Area,Final Depth,Agriculture,Commercial,Industry,Infrastructure,Mixed Area,Residential,Total Damage") to:
					"../results/Manhole_Damage_" + savename + ".csv" format: "csv" header: false rewrite: true;
				save ("Raster,Node,Final Depth,Agriculture,Commercial,Industry,Infrastructure,No Damage,Mixed Area,Residential,Water Bodies,Total Area") to:
					"../results/Manhole_Flood_" + savename + ".csv" format: "csv" header: false rewrite: true;
				ask sourcecells {
					
						do exportf;
					 
				}
			}
		}
		

		
		reflex export_grid{
			if (cycle = pausa) {				
				ask cell {
					do export_grid1;
				}
			save cell to: "../results/waterdepth " + savename + ".asc" format: "asc";
			
			ask cell  {
				do export_grid2;
			}

			if ((experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0")){	
				save cell to: "../results/totaldamage " + savename + ".asc" format: "asc";
				}

		}

	}
		
		reflex export {
		//writes header into file and erases previous file with same name
			if (cycle = 0 and (experiment.name= "Flood_Damages0" or experiment.name= "Exhaustive0")) {
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
			if (cycle = pausa) {
				write('End of Simulation and exports');
				do pause;
				
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
	
	user_command "Convert to Green Roof" action: toggle_roof;
    action toggle_roof {
        Green_Roof <- !Green_Roof;
        if (Green_Roof) {
            
            green_roof_subcatchments <- green_roof_subcatchments + [self.Name];
        } else {
            
            green_roof_subcatchments <- green_roof_subcatchments - [self.Name];
        }
        // Debug output to check list content
        
    }
	
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
	
	
	user_command "conversion to Detention Tank" action: toggle_tank;
    action toggle_tank {
        Det_Tank <- !Det_Tank; // Toggle the boolean state
        if (Det_Tank) {
            
            detention_tank_junctions <- detention_tank_junctions + [self.Name];
        } else {
            
            detention_tank_junctions <- detention_tank_junctions - [self.Name];
        }
        // Debug output to check list content
        
    }

	aspect base {
		draw circle(3) color: source ? manh_source: manh border:#black;
		// Draw the detention tank image if Det_Tank is true
        if (Det_Tank) {
        // Make sure the image is clearly visible and positioned correctly
        draw image_file(det_tank_icon) size: {30, 30} at: location;
    }
}
}
		
species network {
	
	geometry shp <- shape+1;

	aspect pipe {
		draw shp color: sewer /*border:#black*/;
	}

}



species streets {
    string Name;
    bool Perm_Pav <- false;
    
    user_command "Convert to Permeable Pavement" action: toggle_pavement;
    action toggle_pavement {
        Perm_Pav <- !Perm_Pav;
        if (Perm_Pav) {
            
            permeable_pavements_subcatchments <- permeable_pavements_subcatchments + [self.Name];
        } else {
            
            permeable_pavements_subcatchments <- permeable_pavements_subcatchments - [self.Name];
        }
        // Debug output to check list content
        
    }

	aspect base {
		draw shape color:Street border:#black; 
	
	if (Perm_Pav) {
       draw shape color:perm border:#black; 
		}
	

}}
    



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
			waterflowing <- waterflowing + ((float(floodvol[i, j])*60/1000) / DEMsize ^ 2); //conversion for lps to m3/5 minutes, divided by area 
			
			
			
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



experiment Flood_Damages type: gui {
		
	category "Explanation" expanded: true color: #green;
	category "Interactive" expanded:true color: #green;
	text "Welcome! You can modify the model in this control panel by right clicking in objects and selecting options. The clock on apply changes and after the SWMM simulation is ready, start the simulation Enjoy!" 
	category: "Explanation" color: #lightgreen background: #black font: font("Helvetica",8,#bold); 
    // Category for file choosers
    category "Rain Event Selection" expanded: true color: #orange;
    // In the following, when a_boolean_to_enable_parameters is true, it enables the input chooser for multiple_choice.
	 parameter "Event Length" category:"Rain Event Selection" var: event_duration <- "" among: event_dur_list;
	 parameter "Return Period" category:"Rain Event Selection" var: RP <- "" among: RP_list;
	 user_command "Apply changes and Run SWMM" category: "Interactive" color:#darkblue {ask world {do SWMM;}}

   

    output synchronized:true {
     
		
	display Map_display type: 2d   {
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
		
		//species landU aspect: base transparency: (cycle <3) ? (cycle/3) : 0.6;
		/*grid cell border: #lightgrey elevation: grid_value * 5 transparency: 0.5;*/
		
		species building aspect: base;
		species streets aspect: base;
		species outfall aspect: base;
		species network aspect: pipe;
		//species landU aspect:base transparency:100;
		
		
		species manholes aspect: base;
		species cell;
		/*species high_subcatchment aspect: base;*/
	}
	
		display damage type:2d  {
			
		chart "Damage Propagation" type: series size: {1, 0.5} position: {0, 0.5} x_label:'Time'x_serie_labels: string(current_date) y_label:'Damages [$]'  {
			data "Agriculture" value: ((damagesums[0])) color: agriculture;
			data "Commercial" value: ((damagesums[1])) color: commercial;
			data "Industry" value: ((damagesums[2])) color: industry;
			data "Infrastructure" value: ((damagesums[3])) color: infrastructure;
			data "Mixed Area" value: ((damagesums[5])) color: mixed;
			data "Residential" value: ((damagesums[6])) color: residential;
			data "Total" value: (damagesums sum_of (each)) color: total;
		}
		chart "Flood Propagation" type: series size: {1, 0.5} position: {0, 0} x_label:'Time ' x_serie_labels:string(current_date) y_label:'Inundated Area [m^2]' {
			data "Agriculture" value: (floodsums[0]) color: agriculture;
			data "Commercial" value: (floodsums[1]) color: commercial;
			data "Industry" value: (floodsums[2]) color: rgb(255, 255, 102);
			data "Infrastructure" value: (floodsums[3]) color:infrastructure;
			data "No Damage Area" value: (floodsums[4]) color: no_damage;
			data "Mixed Area" value: (floodsums[5]) color: mixed;
			data "Residential" value: (floodsums[6]) color: residential;
			data "Water Bodies" value: (floodsums[7]) color: water_bodies;
			data "Total" value: (floodsums sum_of (each)) color: total;
		
	}}
}}
    


