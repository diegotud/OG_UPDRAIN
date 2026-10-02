#Model: Implementation of LIDS and Traditional Stormwater Management Practices in an Agent Based Model
#Author: Mattia Paolini - mattia_paolini@outlook.it
#LIBRARIES AND TOOLS=============================================================================================================================================
import os
import shutil
import re
import json
import math
import asyncio
from datetime import datetime
from collections import defaultdict
from io import StringIO
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import networkx as nx
import plotly.graph_objs as go
from pandas.plotting import table
import pyswmm
from pyswmm import Simulation, Subcatchments, Links, Nodes
from swmm.toolkit import solver
import swmmio
from swmmio import Model, Nodes
import swmmtoolbox.swmmtoolbox as swmmtoolbox
from swmm_api.input_file import read_inp_file, SwmmInput, section_labels as sections
from swmm_api.input_file.sections import RainGage, Outfall
from swmm_api.input_file.section_labels import TIMESERIES, JUNCTIONS
from swmm_api.input_file.macros.plotting_map import plot_map, add_node_labels
from swmm_api.input_file.macros.plotting_longitudinal import plot_longitudinal
from swmm_api import swmm5_run
#===========================SELECTION OF THE SWMM MODEL==========================================================================================================
def read_inp_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return lines
# Paths to the original and backup files
file_path = r"C:\Users\mpa010\Desktop\SWMM\MS5 (Smaller model)\SWMM model\MS6.inp"
rpt_file_path = r"C:\Users\mpa010\Desktop\Thesis\Software\GAMA\Impacts Workshop\results\report.rpt"  #extracted report from SWMM
out_file_path = r"C:\Users\mpa010\Desktop\Thesis\Software\GAMA\Impacts Workshop\results\output.out"  #extracted output from SWMM
csv_output_file_path = r"C:\Users\mpa010\Desktop\Thesis\Software\GAMA\Impacts Workshop\includes\floodseries.csv" #extracted floodseries to be used by GAMA
backup_file_path = r"C:\Users\mpa010\Desktop\SWMM\MS5 (Smaller model)\SWMM model\MS6_backup.inp"
# Function to write to the SWMM input file
def write_inp_file(file_path, lines):
    with open(file_path, 'w') as file:
        file.writelines(lines)
#=======================================MODEL RESET==============================================================================================================
# Function to reset the model to the original configuration
def reset_model_to_original():
    shutil.copyfile(backup_file_path, file_path)
    print("Model has been reset to the original configuration.")

# At the end of your work, call this function to restore the original model
reset_model_to_original()
#MODEL RUN=======================================================================================================================================================
# Create and run the simulation specifying report and output files
with Simulation(file_path, rpt_file_path, out_file_path) as sim:
    sim.execute()

print("Simulation completed. Report and output files are saved.")
#ETRACTION OF INFORMATIONS ======================================================================================================================================
# Get the catalog and filter for flooding data using swmmtoolbox
catalog = swmmtoolbox.catalog(out_file_path)
df_catalog = pd.DataFrame(catalog, columns=['Type', 'Node', 'Variable'])
flooding_variables = df_catalog[df_catalog['Variable'].str.contains('Flow_lost_flooding', case=False, na=False)]

# Prepare to collect flooding data for each node
all_flooding_data = pd.DataFrame()

# Loop through each node and extract flooding data
for index, row in flooding_variables.iterrows():
    node_id = row['Node']
    variable = row['Variable']
    # Extract flooding data for the node
    flooding_data = swmmtoolbox.extract(out_file_path, 'node', node_id, variable)
    # Rename the column for clarity, removing '_Flow_lost_flooding'
    new_column_name = node_id.replace('_Flow_lost_flooding', '')
    flooding_data.columns = [new_column_name]
    all_flooding_data = pd.concat([all_flooding_data, flooding_data], axis=1)

# Remove columns where all values are zero
all_flooding_data = all_flooding_data.loc[:, (all_flooding_data != 0).any(axis=0)]
# Remove rows where all values are zero
all_flooding_data = all_flooding_data[(all_flooding_data != 0).any(axis=1)]
# Assume the index is already a DatetimeIndex and simply reformat
all_flooding_data.index = all_flooding_data.index.strftime('%Y-%m-%d %H:%M:%s')
#================================================================================================================================================================
# Save the DataFrame to an Excel file
#all_flooding_data.to_excel(excel_output_file_path, index_label='Index')
# Save the DataFrame to a CSV file
all_flooding_data.to_csv(csv_output_file_path, index_label='Index')

print("Data saved to csv and excel successfully.")
print(all_flooding_data)
#================================================================================================================================================================