# -*- coding: utf-8 -*-
"""
Created on Fri Jan 23 12:15:35 2026

@author: Diego NOvoa Vazquez

Gama interactive platform
"""
import json
import os
import sys
from swmm_api.input_file import read_inp_file, section_labels as sections
from swmm_api.input_file.sections import RainGage, LIDControl, LIDUsage
from swmm_api import read_rpt_file, SwmmOutput
from pyswmm import Simulation
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path



def main():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        # 1. Open and load the JSON data
        with open('json_python.json', 'r') as file:
            data = json.load(file)

        name_gama = 'from gama.inp'
        dur = data["event_duration"]
        RP = data["RP"]
        hash_name = data["hash"]
        tanks = data["tanks"]
        GR_list = data["GR"]
        PP_list = data["PP"]
        
        return_period =  int(''.join(filter(str.isdigit, RP)))
        duration =  int(''.join(filter(str.isdigit, dur)))
        
        rain_file = 'Euler_II_'+str(return_period)+'T_'+str(duration)+'D.dat'
        
        log_path = Path("simulation_log.csv")

               
        # --- 1. Prepare the row to append ---
        # Use the JSON fields directly. If you want, you can flatten nested lists/dicts
        row = {
            "run_id": hash_name,
            "event_duration": data.get("event_duration"),
            "RP": data.get("RP"),
            "tanks": json.dumps(data.get("tanks")),  # lists/dicts → string for CSV
            "GR_list": json.dumps(data.get("GR")),
            "PP_list": json.dumps(data.get("PP")),
            
        }
        
        # --- 2. Append to CSV ---
        df_row = pd.DataFrame([row])
        
        if log_path.exists():
            df_row.to_csv(log_path, mode="a", header=False, index=False)
        else:
            df_row.to_csv(log_path, index=False)
        
        
        event_datetime = datetime(2018,7,20,12,00)
# current_dir = os.path.dirname(os.path.abspath(__file__))
# os.chdir(current_dir)

        
        def create_inp_file(swmname, dt):
            
            if isinstance(swmname,str):
                
                swmmod = read_inp_file(swmname)
            else:
                swmmod=swmname
            
            rep = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            
            start = rep - timedelta(days=1) 
            
            end = rep.replace(hour=23, minute=55)
              
            
                   
            swmmod.OPTIONS['START_DATE']=start.date()
            swmmod.OPTIONS['START_TIME']=start.time()
        
            swmmod.OPTIONS['REPORT_START_DATE']=rep.date()
            swmmod.OPTIONS['REPORT_START_TIME']=rep.time()
        
            swmmod.OPTIONS['END_DATE']=end.date()
            swmmod.OPTIONS['END_TIME']=end.time()
            
            return swmmod
        
        def change_RainGage (inp,  file_name):
            if isinstance(inp,str):
                
                inp2 = read_inp_file(inp)
            else:
                inp2 = inp
            
            
            inp2[sections.RAINGAGES].add_obj(RainGage('LO',form='VOLUME', 
                                                      interval='0:05', SCF=1.0, 
                                                      source='FILE',
                                                      filename=file_name,
                                                      units='MM',
                                                      station = 'LO'
                                                      ))
            
        
            
            return inp2
        
        def get_flooded_manholes (rpt):
            if isinstance(rpt,str):
                
                rpt = read_rpt_file(rpt)
              
            flooded_manholes = rpt.node_flooding_summary  
            
            if flooded_manholes is None:
                manholes_list = list()
            else:
                manholes_list =  flooded_manholes.index.tolist()
            
            return manholes_list
        
        """Function to extract the flood volume as a time series for the flooded 
        manholes"""
        def get_manhole_floodseries (list_nodes, out_file):
            if list_nodes:
                    
                if isinstance(out_file,str):
                    out2 = SwmmOutput(out_file)
                    out2 = out2.to_frame()
                else:
                    out2 = out_file
                   
                manholes_series = out2.loc[:,('node',list_nodes,'flooding')]
                manholes_series = manholes_series.droplevel(level=[0,2],axis=1)
            else:
                manholes_series = pd.DataFrame()
            
            return manholes_series
        
        def export_timeseries (df):
            non_zero = (df != 0).any(axis=1)
        
            first_nz = non_zero.idxmax()
            last_nz = non_zero[::-1].idxmax()
            
            start_pos = max(df.index.get_loc(first_nz) - 1, 0)
            end_pos = df.index.get_loc(last_nz)
            
            df_trimmed = df.iloc[start_pos:end_pos + 2]
            df_trimmed.index.name = "datetime"
            return df_trimmed
        
        def add_GR (inp,subc_list):
            if isinstance(inp,str):
                
                inp2 = read_inp_file(inp)
            else:
                inp2 = inp
            
            lid = LIDControl('GreenRoof', lid_kind=LIDControl.LID_TYPES.GREEN_ROOF)
            lid.add_layer(LIDControl.LAYER_TYPES.Surface(StorHt=70.0, 
                                                        VegFrac=0.1, 
                                                        Rough=0.15, 
                                                        Slope=1.0, 
                                                        Xslope=5.0))
            lid.add_layer(LIDControl.LAYER_TYPES.Soil(Thick=75.0,
                                                        Por=0.5, 
                                                        FC=0.4, 
                                                        WP=0.1, 
                                                        Ksat=300, 
                                                        Kcoeff=10.0,
                                                        Suct=65.0))
            lid.add_layer(LIDControl.LAYER_TYPES.Drainmat(Thick=20.0, 
                                                          Vratio=0.7, 
                                                          Rough=0.03))
            
            
            inp2.add_obj(lid)
            catch = inp2.SUBCATCHMENTS.frame
            
            for sub in subc_list:
                Wid = catch.at[sub,'width']
                AREA = catch.at[sub,'area']
                inp2.add_obj(LIDUsage(subcatchment=sub, lid='GreenRoof', 
                         n_replicate=1, area=AREA*10000, 
                         width=Wid, saturation_init=0.0, 
                         impervious_portion=100.0, route_to_pervious=0, fn_lid_report='*', drain_to='*', from_pervious=0.0))
                
            
            return inp2
        
        def add_PP (inp,subc_list):
            if isinstance(inp,str):
                
                inp2 = read_inp_file(inp)
            else:
                inp2 = inp
            
            lid = LIDControl('PervPav', lid_kind=LIDControl.LID_TYPES.PERMEABLE_PAVEMENT)
            
            lid.add_layer(LIDControl.LAYER_TYPES.Surface(StorHt=0.0, 
                                                         VegFrac=0.0, 
                                                         Rough=0.02, 
                                                         Slope=1.0, 
                                                         Xslope=5.0))
            lid.add_layer(LIDControl.LAYER_TYPES.Pavement(Thick=150.0, 
                                                          Vratio=0.25, 
                                                          FracImp=0.8, 
                                                          Perm=745.33, 
                                                          Vclog='0', 
                                                          regeneration_interval=0.0, 
                                                          regeneration_fraction=0.0))
            lid.add_layer(LIDControl.LAYER_TYPES.Storage(Height=150.0, 
                                                         Vratio=0.4, 
                                                         Seepage=172.0, 
                                                         Vclog=0, 
                                                         Covrd=False)) 
            lid.add_layer(LIDControl.LAYER_TYPES.Drain(Coeff=2.0, 
                                                       Expon=0.5, 
                                                       Offset=0.0, 
                                                       Delay='6', 
                                                       open_level='0', 
                                                       close_level='0', 
                                                       Qcurve=np.nan))
            
            
        
            inp2.add_obj(lid)
            catch = inp2.SUBCATCHMENTS.frame
            for sub in subc_list:
                Wid = catch.at[sub,'width']
                AREA = catch.at[sub,'area']
                inp2.add_obj(LIDUsage(subcatchment=sub, lid='PervPav', 
                                      n_replicate=1, area=AREA*10000, width=Wid, 
                                      saturation_init=0.0, 
                                      impervious_portion=100.0, route_to_pervious=0, 
                                      fn_lid_report='*', drain_to='*',
                                      from_pervious=0.0))
            
            return inp2
        
                
        swmm_dir = os.path.join(script_dir, '..', 'SWMM')
        os.chdir(swmm_dir)
        swmm_file = 'swmm_model.inp'
  
        swmm_mod = create_inp_file(swmm_file, event_datetime)
        swmm_mod = change_RainGage (swmm_mod,  rain_file)
        swmm_mod =add_GR(swmm_mod, GR_list)
        swmm_mod =add_PP(swmm_mod, PP_list)
        
        
        name_gama = 'swmm_modified.inp'
        swmm_mod.write_file(name_gama)
        name_rp = name_gama[0:-4]+('.rpt')
        name_out = name_gama[0:-4]+('.out')  
        # print(rain_file)
        with Simulation(name_gama) as sim:
            for step in sim:
                pass
        
        
        flood_nodes = get_flooded_manholes (name_rp)
        flood_series = get_manhole_floodseries(flood_nodes, name_out)
        for_export = export_timeseries (flood_series) 
        save_dir = os.path.join(script_dir, '..', 'flood_series')

        # Make sure the folder exists
        os.makedirs(save_dir, exist_ok=True)
        os.chdir(save_dir)
        for_export.to_csv("flood_series_"+hash_name+".csv")
        print("End of SWMM simulations ans succesful export")
          
    except Exception as e:
            print(f"Python Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    main()