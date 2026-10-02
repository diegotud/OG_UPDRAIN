#LIBRARIES AND TOOLS=#########################################################################################################################################################
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
#%%
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
print('import modules done')
#%%
#MODEL DIRECTORY#########################################################################################################################################################
def read_inp_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return lines
#inputs paths #########################################################################################################################################################
file_path = r"D:\IAHR\SWMM new\SWMM model\MS2_osm_new.inp" #Location of the model run by SWMM
file_path2 = r'C:\Users\Diego\Gama_Workspace\IAHR\results\code_DT_Report.xlsx'  #download all the actions done here
file_path3 = r'C:\Users\Diego\Gama_Workspace\IAHR\results\code_SWA_Report.xlsx'  #download all the actions done here
file_path4 = r'C:\Users\Diego\Gama_Workspace\IAHR\results\code_TRE_Report.xlsx' 
file_path5 = r'C:\Users\Diego\Gama_Workspace\IAHR\results\code_GRER_Report.xlsx'
rainfall_file_path = r"C:\Users\Diego\Gama_Workspace\IAHR\includes\rainfall\5y_1h.dat" #Location of the Rainfall .dat file run by SWMM
timeseries_df = pd.read_excel(r'C:\Users\mpa010\Desktop\design\Precipitation\timeseries.xlsx') #Location of Duraiton timeseries
precipitation_list_file = r"C:\Users\Diego\Gama_Workspace\ IAHR\results\rainfall_list.csv"
#outputs paths #########################################################################################################################################################=
directory = r"C:\Users\Diego\Gama_Workspace\IAHR\results" #location of the populated lists from GAMA
rpt_file_path = r"C:\Users\Diego\Gama_Workspace\IAHR\results\report.rpt"  #extracted report from SWMM
out_file_path = r"C:\Users\Diego\Gama_Workspace\IAHR\results\output.out"  #extracted output from SWMM
csv_output_file_path = r"C:\Users\Diego\Gama_Workspace\IAHR\includes\floodseries.csv" #extracted floodseries to be used by GAMA
#########################################################################################################################################################
print('dir done')
#%%# Function to write to the SWMM input file
def write_inp_file(file_path, lines):
    with open(file_path, 'w') as file:
        file.writelines(lines)
# Read the original file
sections = read_inp_file(file_path)
#MODEL RESET#########################################################################################################################################################
backup_file_path = r"D:\IAHR\SWMM new\SWMM model\MS2_osm_new2.inp"

# Function to reset the model to the original configuration
def reset_model_to_original():
    shutil.copyfile(backup_file_path, file_path)
    print("Model has been reset to the original configuration.")

# At the end of your work, call this function to restore the original model
reset_model_to_original()
#########################################################################################################################################################
# Function to read the SWMM input file
def read_inp_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return lines

# Function to write the SWMM input file
def write_inp_file(file_path, lines):
    with open(file_path, 'w') as file:
        file.writelines(lines)

# Function to update the rainfall file reference in the SWMM input file
def update_rainfall_file(swmm_inp_file, new_rainfall_file):
    # Extract the filename from the full path
    new_rainfall_filename = os.path.basename(new_rainfall_file)
    lines = read_inp_file(file_path)
    
    # Find the [RAINGAGES] section
    raingages_start = None
    raingages_end = None
    current_rainfall_file = None
    for i, line in enumerate(lines):
        if line.strip().startswith('[RAINGAGES]'):
            raingages_start = i
        if raingages_start and line.strip() == '':
            raingages_end = i
            break

    if raingages_start is None:
        raise ValueError("No [RAINGAGES] section found in the input file.")

    # Find and print the current rainfall file reference
    pattern = re.compile(r'FILE\s+"([^"]+)"')
    for i in range(raingages_start, raingages_end):
        match = pattern.search(lines[i])
        if match:
            current_rainfall_file = match.group(1)
            print(f"Current rainfall file: {current_rainfall_file}")
            # Replace the current file path with the new filename, keeping the quotes
            lines[i] = lines[i].replace(current_rainfall_file, new_rainfall_filename)
            break
    
    if current_rainfall_file is None:
        raise ValueError("No rainfall file reference found in the [RAINGAGES] section.")
    
    # Write the updated content back to the file
    write_inp_file(file_path, lines)
    # Print success message
    print(f"Rainfall file updated successfully to: {new_rainfall_filename}")

# Function to read the list of precipitation files from a CSV file
def read_precipitation_list(file_path, directory):
    df = pd.read_csv(file_path)
    # Extract the valid filenames, ignoring NaN values
    precipitation_files = [os.path.join(directory, str(line).strip()) for line in df['rainfall_list'] if pd.notna(line) and str(line).strip()]
    return precipitation_files


# Read the list of precipitation files
precipitation_files = read_precipitation_list(precipitation_list_file, directory)

if not precipitation_files:
    print("The CSV file is empty. No changes will be made to the precipitation.")
else:
    for rainfall_file_path in precipitation_files:
        update_rainfall_file(file_path, rainfall_file_path)
#SECTION OF THE SWMM MODEL#########################################################################################################################################################
#SECTION 1: JUNCTIONS=#########################################################################################################################################################
def extract_section(file_path, section_name):
    section_data = []
    section_active = False
    
    with open(file_path, 'r') as file:
        for line in file:
            if f'[{section_name}]' in line:
                section_active = True
                continue
            if section_active and line.startswith('['):
                break
            if section_active and not line.startswith(';') and line.strip():
                section_data.append(line.strip().split())
    
    return section_data

def create_dataframe(section_data, columns):
    if section_data:
        return pd.DataFrame(section_data, columns=columns)
    return pd.DataFrame(columns=['No Data'])
  # Replace with your file path

# Extract junctions and coordinates
junction_data = extract_section(file_path, 'JUNCTIONS')
coordinates_data = extract_section(file_path, 'COORDINATES')
# Define columns based on standard SWMM .inp format
junction_columns = ['Name', 'Invert El.', 'Max Depth', 'Initial Depth', 'Surcharge Depth', 'Ponded Area']
coordinates_columns = ['Node', 'X-Coord', 'Y-Coord']
# Create DataFrames
junction_frame = create_dataframe(junction_data, junction_columns)
coordinates_frame = create_dataframe(coordinates_data, coordinates_columns)
# Normalize the 'Name' and 'Node' columns
junction_frame['Name'] = junction_frame['Name'].str.strip().str.upper()
coordinates_frame['Node'] = coordinates_frame['Node'].str.strip().str.upper()
# Merge the DataFrames
junction_complete = pd.merge(junction_frame, coordinates_frame, left_on='Name', right_on='Node', how='left').drop(columns='Node')
# Display the first row entirely as a DataFrame
first_row_df = junction_complete.to_string()
print(first_row_df)
#SECTION 2: CONDUITS#########################################################################################################################################################
def extract_section(file_path, section_name):
    """Extracts data from a specified section of the input file."""
    data = []
    section_found = False
    
    with open(file_path, 'r') as file:
        for line in file:
            if f'[{section_name}]' in line:
                section_found = True
                continue
            if section_found and line.startswith('['):
                break
            if section_found and not line.startswith(';') and line.strip():
                data.append(line.strip().split())
                
    return data

def extract_xsections(file_path):
    """Extracts the xsections data from the input file and returns a DataFrame."""
    xsections = extract_section(file_path, 'XSECTIONS')
    
    if xsections:
        columns = ['Link', 'Shape', 'Geom1', 'Geom2', 'Geom3', 'Geom4', 'Barrels']
        df_xsections = pd.DataFrame(xsections, columns=columns)
    else:
        df_xsections = pd.DataFrame(columns=['No XSections Data'])

    return df_xsections

def extract_conduits(file_path):
    """Extracts the conduits data from the input file and returns a DataFrame."""
    conduits = extract_section(file_path, 'CONDUITS')
    
    if conduits:
        columns = ['Conduit', 'From Node', 'To Node', 'Length', 'Roughness', 'InOffset', 'OutOffset', 'InitFlow', 'MaxFlow']
        df_conduits = pd.DataFrame(conduits, columns=columns)
    else:
        df_conduits = pd.DataFrame(columns=['No Conduit Data'])
        
    return df_conduits

def merge_junction_data(conduits_df, junction_df):
    """Merges the junction elevation data with the conduits DataFrame."""
    junction_df = junction_df.copy()
    junction_df['Invert El.'] = pd.to_numeric(junction_df['Invert El.'], errors='coerce')
    junction_df.set_index('Name', inplace=True)

    conduits_df = conduits_df.copy()
    conduits_df = conduits_df.merge(junction_df['Invert El.'], left_on='From Node', right_index=True, suffixes=('', '_drop'))
    conduits_df.rename(columns={'Invert El.': 'Inlet Elevation'}, inplace=True)
    conduits_df.drop(conduits_df.filter(regex='_drop$').columns, axis=1, inplace=True)

    conduits_df = conduits_df.merge(junction_df['Invert El.'], left_on='To Node', right_index=True, suffixes=('', '_drop'))
    conduits_df.rename(columns={'Invert El.': 'Outlet Elevation'}, inplace=True)
    conduits_df.drop(conduits_df.filter(regex='_drop$').columns, axis=1, inplace=True)

    conduits_df['Length'] = pd.to_numeric(conduits_df['Length'], errors='coerce')
    conduits_df['Slope'] = (conduits_df['Inlet Elevation'] - conduits_df['Outlet Elevation']) / conduits_df['Length']
    
    return conduits_df

def merge_xsection_data(conduits_df, xsections_df):
    """Merges the xsections data with the conduits DataFrame."""
    conduits_df = conduits_df.copy()
    xsections_df = xsections_df.copy()

    conduits_df = conduits_df.merge(xsections_df[['Link', 'Shape', 'Geom1']], left_on='Conduit', right_on='Link', suffixes=('', '_drop'))
    conduits_df.drop(['Link'], axis=1, inplace=True)
    
    return conduits_df

def main(file_path, junction_frame):
    """Main function to extract and merge data."""
    xsections_frame = extract_xsections(file_path)
    conduits_frame = extract_conduits(file_path)
    
    # Ensure columns are strings for merging
    xsections_frame['Link'] = xsections_frame['Link'].astype(str)
    conduits_frame['Conduit'] = conduits_frame['Conduit'].astype(str)
    conduits_frame['From Node'] = conduits_frame['From Node'].astype(str)
    conduits_frame['To Node'] = conduits_frame['To Node'].astype(str)
    
    conduits_complete = merge_junction_data(conduits_frame, junction_frame)
    conduits_complete = merge_xsection_data(conduits_complete, xsections_frame)
    
    return conduits_complete
    
conduits_complete = main(file_path, junction_frame)
# Display the first row entirely as a DataFrame
first_row_df = conduits_complete.to_string()
print(first_row_df)
#SECTION 3: SUBCATCHMENTS#########################################################################################################################################################
def extract_subcatchments(file_path):
    subcatchments = []
    subcatchment_section = False
    
    with open(file_path, 'r') as file:
        for line in file:
            if '[SUBCATCHMENTS]' in line:
                subcatchment_section = True
                continue
            if subcatchment_section and line.startswith('['):
                break
            if subcatchment_section and not line.startswith(';') and line.strip():
                subcatchments.append(line.strip().split())

    if subcatchments:
        # Adjust the column names based on your .inp file's SUBCATCHMENTS section
        columns = ['Subcatchment', 'Rain Gage', 'Outlet', 'Area', 'Imperv%', 'Width', 'Slope', 'CurbLen']
        df_subcatchments = pd.DataFrame(subcatchments, columns=columns)
    else:
        df_subcatchments = pd.DataFrame(columns=['No Subcatchment Data'])
        
    return df_subcatchments

def extract_polygons(file_path):
    polygons = []
    polygon_section = False
    
    with open(file_path, 'r') as file:
        for line in file:
            if '[Polygons]' in line:
                polygon_section = True
                continue
            if polygon_section and line.startswith('['):
                break
            if polygon_section and not line.startswith(';') and line.strip():
                parts = line.strip().split()
                polygons.append({'Subcatchment': parts[0], 'X-Coord': float(parts[1]), 'Y-Coord': float(parts[2])})

    if polygons:
        df_polygons = pd.DataFrame(polygons)
    else:
        df_polygons = pd.DataFrame(columns=['No Polygon Data'])
        
    return df_polygons

def merge_subcatchments_and_polygons(subcatchment_frame, polygon_frame):
    # Perform an inner merge on Subcatchment
    merged_df = pd.merge(subcatchment_frame, polygon_frame, on='Subcatchment', how='inner')
    return merged_df

subcatchment_frame = extract_subcatchments(file_path)
polygon_frame = extract_polygons(file_path)

subcatchment_complete = merge_subcatchments_and_polygons(subcatchment_frame, polygon_frame)
first_row_df = subcatchment_complete.to_string()
print(first_row_df)
######################################################################################################################################################
#POPULATE THE LIST WITH THE RESULTS FROM GAMA#########################################################################################################
# Define the directory containing the files
# Lists to hold data
detention_tank_list = []
detention_tank_list = []
green_roof_list = []
infiltration_swale_list = []
permeable_pavement_list = []
infiltration_trench_list = []


# Mapping file names to lists
list_mapping = {
    'detention_tank_junctions.csv': detention_tank_list,
    'green_roof_subcatchments.csv': green_roof_list,
    'infiltration_swale_subcatchments.csv': infiltration_swale_list,
    'permeable_pavements_subcatchments.csv': permeable_pavement_list,
    'infiltration_trench_subcatchments.csv': infiltration_trench_list
}

def process_file(csv_file_path, target_list):
    unique_names = set()
    with open(csv_file_path, 'r') as file:
        # Check if there's at least one line to read (i.e., the header)
        first_line = file.readline()
        if not first_line:
            print(f"No data in file: {csv_file_path}")
            return  # Skip processing if file is empty

        # Process subsequent lines assuming the first line was the header
        for line in file:
            names = line.strip().split(',')
            for name in names:
                cleaned_name = name.strip()
                if cleaned_name and cleaned_name not in unique_names:
                    unique_names.add(cleaned_name)

    target_list.extend(unique_names)

# Process files in the specified directory
for filename in os.listdir(directory):
    csv_file_path = os.path.join(directory, filename)
    if filename in list_mapping:
        process_file(csv_file_path, list_mapping[filename])

# Output the results to verify
print("Detention Tank List:", sorted(detention_tank_list))
print("Green Roof List:", sorted(green_roof_list))
print("Infiltration Swale List:", sorted(infiltration_swale_list))
print("Infiltration Trench List:", sorted(infiltration_trench_list))
print("Permeable Pavement List:", sorted(permeable_pavement_list))
############################################################################################################################################
#DETENTION TANK================================================================================================================================================
#############################################################################################################################################
############################################################################################################################################
#SECTION 1 ====================================================================================================================================================
# Initialize the detention tank DataFrame
detention_tank = pd.DataFrame(columns=["Name", "A (m2)", "% Imp.", "% Perv.", "ψm Imperv..", "ψm perv.", "AE imp.", "AE perv.", "Ared imp.", "Ared perv.", "Ared"])

# Pre-calculate conversion factors
hectares_to_m2 = 10000
imperv_factor = 0.9
perv_factor = 0.3

# Function to process a subcatchment
def process_subcatchment(subcatchment, subcatchment_frame, detention_tank):
    # Retrieve area and impervious percentage for the subcatchment
    area_ha = subcatchment_frame.loc[subcatchment_frame['Subcatchment'] == subcatchment, 'Area'].values[0]
    area_m2 = float(area_ha) * hectares_to_m2  # Convert from hectares to square meters
    imperv = subcatchment_frame.loc[subcatchment_frame['Subcatchment'] == subcatchment, 'Imperv%'].values[0]

    # Impervious percentage (convert to float and then to percentage)
    imperv = float(imperv)
    perv = 100 - imperv

    # Calculate other values based on retrieved data
    ae_imp = area_m2 * (imperv / 100)  # Convert imperv to percentage
    ae_perv = area_m2 * (perv / 100)  # Convert perv to percentage
    ared_imp = imperv_factor * ae_imp
    ared_perv = perv_factor * ae_perv

    # Add the calculated values to the detention tank dataframe
    detention_tank.loc[len(detention_tank)] = [
        subcatchment, area_m2, imperv, perv, imperv_factor, perv_factor, ae_imp, ae_perv, ared_imp, ared_perv, 0
    ]

# Function to process a junction and its connected elements
def process_junction(junction_of_interest, subcatchment_frame, conduits_complete, results_df):
    """Process a given junction and its connected elements."""

    # Retrieve direct subcatchments and conduits connected to the junction
    direct_subcatchments = subcatchment_frame[subcatchment_frame['Outlet'] == junction_of_interest]['Subcatchment'].tolist()
    direct_conduits = conduits_complete[conduits_complete['To Node'] == junction_of_interest]['Conduit'].tolist()

    # Dictionary to map outlets to subcatchments
    outlet_to_subcatchment = defaultdict(list)
    for index, row in subcatchment_frame.iterrows():
        outlet_to_subcatchment[row['Outlet']].append(row['Subcatchment'])

    # List to store nested subcatchments
    subcatchment_results = []

    def find_all_generations(subcatchments):
        """Recursively find all generations of subcatchments."""
        for subcatchment in subcatchments:
            if subcatchment in outlet_to_subcatchment:
                nested_subcatchments = outlet_to_subcatchment[subcatchment]
                subcatchment_results.extend(nested_subcatchments)
                find_all_generations(nested_subcatchments)

    # Find nested subcatchments
    find_all_generations(direct_subcatchments)
    subcatchment_results = list(set(subcatchment_results))
    # Retrieve the from nodes of conduits
    from_nodes = conduits_complete[conduits_complete['Conduit'].isin(direct_conduits)]['From Node'].tolist()
    # Calculate total subcatchments
    total_subcatchments = len(set(direct_subcatchments + subcatchment_results))
    # Append the results to the DataFrame
    results_df.loc[len(results_df)] = [junction_of_interest, direct_subcatchments, direct_conduits, subcatchment_results, from_nodes, total_subcatchments]

    # Process additional junctions connected through conduits
    for from_node in from_nodes:
        if not results_df[results_df['Junction'] == from_node].empty:
            continue  # Skip already processed junctions
        process_junction(from_node, subcatchment_frame, conduits_complete, results_df)
    return results_df

# Create a list to store all subcatchments related to the nodes
all_subcatchments_list = []

# Process each junction in the list separately
for junction_of_interest in detention_tank_list:
    # Initialize an empty DataFrame to store the results for each junction
    nested_subcatchment = pd.DataFrame(columns=["Junction", "Direct Subcatchments", "Conduits", "Nested Subcatchments", "Junction of Origin", "Total Subcatchments"])
    # Process the junction
    nested_subcatchment = process_junction(junction_of_interest, subcatchment_frame, conduits_complete, nested_subcatchment)
    # Calculate the total unique subcatchments connected to the initial junction of interest
    total_unique_subcatchments = nested_subcatchment['Total Subcatchments'].sum()
    # Print the total number of unique subcatchments connected to the initial junction of interest
    

    # Append direct and nested subcatchments to the list
    for index, row in nested_subcatchment.iterrows():
        all_subcatchments_list.extend(row["Direct Subcatchments"])
        all_subcatchments_list.extend(row["Nested Subcatchments"])

# Remove duplicates by converting to a set and back to a list
all_subcatchments_list = list(set(all_subcatchments_list))
# Create a DataFrame from the list of all subcatchments
all_subcatchments_df = pd.DataFrame(all_subcatchments_list, columns=["Subcatchment"])

# Calculate total area for each initial junction of interest
def calculate_total_area_for_junction(junction_of_interest, subcatchment_frame, conduits_complete):
    nested_subcatchment = pd.DataFrame(columns=["Junction", "Direct Subcatchments", "Conduits", "Nested Subcatchments", "Junction of Origin", "Total Subcatchments"])
    nested_subcatchment = process_junction(junction_of_interest, subcatchment_frame, conduits_complete, nested_subcatchment)

    total_area = 0
    for index, row in nested_subcatchment.iterrows():
        for subcatchment in row["Direct Subcatchments"] + row["Nested Subcatchments"]:
            area_ha = subcatchment_frame.loc[subcatchment_frame['Subcatchment'] == subcatchment, 'Area'].values[0]
            total_area += float(area_ha) * hectares_to_m2  # Convert from hectares to square meters

    return total_area

# Calculate total areas for each junction in the list
total_areas = {}
for junction_of_interest in detention_tank_list:
    total_area = calculate_total_area_for_junction(junction_of_interest, subcatchment_frame, conduits_complete)
    total_areas[junction_of_interest] = total_area
    

# Function to process a junction and calculate total Ared
def calculate_ared_for_junction(junction_of_interest, subcatchment_frame, conduits_complete):
    nested_subcatchment = pd.DataFrame(columns=["Junction", "Direct Subcatchments", "Conduits", "Nested Subcatchments", "Junction of Origin", "Total Subcatchments"])
    nested_subcatchment = process_junction(junction_of_interest, subcatchment_frame, conduits_complete, nested_subcatchment)

    detention_tank = pd.DataFrame(columns=["Name", "A (m2)", "% Imp.", "% Perv.", "ψm Imperv..", "ψm perv.", "AE imp.", "AE perv.", "Ared imp.", "Ared perv.", "Ared"])

    # Process each subcatchment and update the detention tank DataFrame
    for index, row in nested_subcatchment.iterrows():
        for subcatchment in row["Direct Subcatchments"] + row["Nested Subcatchments"]:
            process_subcatchment(subcatchment, subcatchment_frame, detention_tank)

    # Calculate total values for the detention tank
    total_area = detention_tank['A (m2)'].sum()
    total_ae_imp = detention_tank['AE imp.'].sum()
    total_ae_perv = detention_tank['AE perv.'].sum()
    total_ared_imp = detention_tank['Ared imp.'].sum()
    total_ared_perv = detention_tank['Ared perv.'].sum()
    total_ared = total_ared_imp + total_ared_perv

    return total_ared
#==============================================================================================================================================================
# Calculate total Ared for each junction in the list
ared_totals = {}
for junction_of_interest in detention_tank_list:
    total_ared = calculate_ared_for_junction(junction_of_interest, subcatchment_frame, conduits_complete)
    ared_totals[junction_of_interest] = total_ared
    

ared_totals
#############################################################################################################################################
############################################################################################################################################
#SECTION 2 ====================================================================================================================================================

# Function to find the longest path in a directed graph for a given junction
def find_longest_path(G, target_node):
    """Find all paths in the graph leading to the target node and return the longest one."""
    all_paths = []
    for node in G.nodes:
        if node != target_node:
            try:
                paths = list(nx.all_simple_paths(G, source=node, target=target_node))
                all_paths.extend(paths)
            except nx.NetworkXNoPath:
                continue
    
    # Find the longest path based on path length (number of edges)
    longest_path = max(all_paths, key=len) if all_paths else []
    return longest_path

# Create a directed graph from conduits data
G = nx.DiGraph()
for idx, row in conduits_complete.iterrows():
    G.add_edge(row['From Node'], row['To Node'], length=row['Length'])

# Calculate the longest path for each junction in the list
longest_paths = {}
for junction_of_interest in detention_tank_list:
    longest_path = find_longest_path(G, junction_of_interest)
    longest_paths[junction_of_interest] = longest_path
    

longest_paths
#############################################################################################################################################
############################################################################################################################################
#SECTION 3 ====================================================================================================================================================

def calculate_velocity(diam, slope):
    try:
        # Ensure the diameter and slope are floats
        diam = float(diam)
        slope = float(slope)
        # Check if the slope is zero or negative and adjust it to a small positive value
        if slope <= 0:
            slope = 0.003  # Set a minimal slope to avoid calculation errors
            print(f"Adjusted slope used for calculation due to non-positive input: slope={slope}")
        # Calculate the velocity using the modified Colebrook-White equation
        term1 = 0.0015 / (3.71 * diam)
        term2 = 2.51 * 1.01e-6 / (diam * np.sqrt(2 * 9.81 * diam * slope))
        velocity = -2 * np.log10(term1 + term2) * np.sqrt(2 * 9.81 * diam * slope)
        return velocity
    except Exception as e:
        print(f"Error calculating velocity: {e}")
        print(f"diam: {diam}, slope: {slope}")
        return np.nan

# Function to calculate travel time using the calculated velocity
def calculate_travel_time(length, velocity):
    try:
        length = float(length)
        velocity = float(velocity)
        return length / velocity
    except Exception as e:
        print(f"Error calculating travel time: {e}")
        print(f"length: {length}, velocity: {velocity}")
        return np.nan

# Calculate total travel time for the longest path for each junction
travel_times = {}
for junction_of_interest, longest_path in longest_paths.items():
    total_travel_time = 0
    for i in range(len(longest_path) - 1):
        from_node = longest_path[i]
        to_node = longest_path[i + 1]
        conduit = conduits_complete[(conduits_complete['From Node'] == from_node) & (conduits_complete['To Node'] == to_node)]
        if not conduit.empty:
            conduit = conduit.iloc[0]  # Get the first matching row
            diam = conduit['Geom1']  # Diameter in meters
            length = conduit['Length']  # Length in meters
            slope = conduit['Slope']  # Slope
            
            # Calculate velocity and travel time
            velocity = calculate_velocity(diam, slope)
            travel_time = calculate_travel_time(length, velocity)
            
            total_travel_time += travel_time

    travel_times[junction_of_interest] = total_travel_time
    

travel_times

#SUMMARY############################################################################################################################################
############################################################################################################################################
# Function to create a summary DataFrame for each junction
def create_summary_df(detention_tank_list, subcatchment_frame, conduits_complete, total_areas, ared_totals, longest_paths, travel_times):
    summary_data = []

    for junction_of_interest in detention_tank_list:
        # Initialize an empty DataFrame to store the results for each junction
        nested_subcatchment = pd.DataFrame(columns=["Junction", "Direct Subcatchments", "Conduits", "Nested Subcatchments", "Junction of Origin", "Total Subcatchments"])
        # Process the junction
        nested_subcatchment = process_junction(junction_of_interest, subcatchment_frame, conduits_complete, nested_subcatchment)

        # Retrieve the direct subcatchments
        direct_subcatchments = []
        nested_subcatchments = []

        for index, row in nested_subcatchment.iterrows():
            direct_subcatchments.extend(row["Direct Subcatchments"])
            nested_subcatchments.extend(row["Nested Subcatchments"])

        direct_subcatchments = list(set(direct_subcatchments))
        nested_subcatchments = list(set(nested_subcatchments))
        total_subcatchments = len(set(direct_subcatchments + nested_subcatchments))

        # Retrieve the names of all connected subcatchments
        connected_subcatchments = list(set(direct_subcatchments + nested_subcatchments))

        # Retrieve the total area and total Ared
        total_area = total_areas[junction_of_interest]
        total_ared = ared_totals[junction_of_interest]

        # Retrieve the longest path and total travel time
        longest_path = longest_paths[junction_of_interest]
        total_travel_time = travel_times[junction_of_interest]

        # Append the results to the summary data
        summary_data.append({
            "Junction": junction_of_interest,
            "Num Direct Subcatchments": len(direct_subcatchments),
            "Num Nested Subcatchments": len(nested_subcatchments),
            "Num Total Subcatchments": total_subcatchments,
            "Total Area (m²)": total_area,
            "A Reduced (m²)": total_ared,
            "Longest Path": longest_path,
            "Total Travel Time (s)": total_travel_time,
            "Connected Subcatchments": ', '.join(connected_subcatchments)
        })

    # Create a DataFrame from the summary data
    summary_df = pd.DataFrame(summary_data)
    return summary_df

# Create the summary DataFrame
summary_df = create_summary_df(detention_tank_list, subcatchment_frame, conduits_complete, total_areas, ared_totals, longest_paths, travel_times)
# Create DataFrame from collected data
summary_df = pd.DataFrame(summary_df)

# Display the DataFrame
# Set Pandas display options
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column
summary_df
# Display the summary DataFrame
print(summary_df)
#############################################################################################################################################
############################################################################################################################################
#SECTION 4 ====================================================================================================================================================
return_period = 3    # Return period in years --> Specified exceedingfrequency 
fz = 1.2
Q_D_R_u = 2  # Specified throttle flow 


def calculate_qThrRimp(Q_D_R_u, total_area, ared_totals):
    QThrmax = Q_D_R_u * total_area
    qThrRimp = QThrmax / ared_totals
    return qThrRimp

# Calculate retention volume based on the timeseries data for each junction
retention_volumes = {}
for junction_of_interest, total_travel_time in travel_times.items():

    # Extract the duration and corresponding rain depth (hN)
    duration = timeseries_df['T [min]'].max()
    hN = timeseries_df.loc[timeseries_df['T [min]'] == duration, 'hN [mm]'].values[0]

    #QThr,max = qThr,s ⋅ AC,s 
    #qThr,R,imp = qThr,imp = QThr,max / Ared = 3.0 l/(s·ha)


    # Calculate f1
    def calculate_f1(total_travel_time, qThrRimp):
        t_jj=total_travel_time / 60 
        t_f_min = np.minimum(10,t_jj)  # Convert seconds to minutes
        q = qThrRimp
        f1 = 1 - ((1 * 10**-10 * t_f_min**3) - (8 * 10**-9 * t_f_min**2) + (1 * 10**-8 * t_f_min)) * q**3
        f1 += ((1.6 * 10**-8 * t_f_min**3) - (9.15 * 10**-7 * t_f_min**2) + (1.14 * 10**-6 * t_f_min)) * q**2
        f1 += ((1.8 * 10**-7 * t_f_min**3) - (1.25 * 10**-5 * t_f_min**2) + (1.56 * 10**-5 * t_f_min)) * q
        return f1

    if total_travel_time == 0:
        f1 = 0
        print(f"Travel time for junction {junction_of_interest} is 0. Setting f1 to 0 and fa to 0.98.")
    else:
        f1 = calculate_f1(total_travel_time, Q_D_R_u)
        

    def calculate_fa(n, f1, total_travel_time):
       if total_travel_time == 0:
           return 0.98
       fa = (0.6134 * n + 0.3866) * f1 - (0.6134 * n - 0.6134)
       return fa

# Calculate fa for each junction and store in a dictionary
fa_dict = {}
n = return_period / 100
for junction_of_interest, total_travel_time in travel_times.items():
    qThrRimp = calculate_qThrRimp(Q_D_R_u, total_areas[junction_of_interest], ared_totals[junction_of_interest])
    f1 = calculate_f1(total_travel_time, qThrRimp)
    if total_travel_time == 0:
        fa = 0.98
    else:
        fa = calculate_fa(n, f1, total_travel_time)
    fa_dict[junction_of_interest] = fa
    print(f"f1 of: {junction_of_interest} is setted to {f1}.")
    print(f"fa of: {junction_of_interest} is setted to {fa}.")

########################################################################################################################################################
# Function to process a junction and calculate total Ared
def calculate_ared_for_junction(junction_of_interest, subcatchment_frame, conduits_complete):
    # Initialize nested subcatchment DataFrame
    nested_subcatchment = pd.DataFrame(columns=["Junction", "Direct Subcatchments", "Conduits", "Nested Subcatchments", "Junction of Origin", "Total Subcatchments"])
    nested_subcatchment = process_junction(junction_of_interest, subcatchment_frame, conduits_complete, nested_subcatchment)
    # Initialize detention tank DataFrame
    detention_tank = pd.DataFrame(columns=["Name", "A (m2)", "% Imp.", "% Perv.", "ψm Imperv..", "ψm perv.", "AE imp.", "AE perv.", "Ared imp.", "Ared perv.", "Ared"])
    # Process each subcatchment and update the detention tank DataFrame
    for index, row in nested_subcatchment.iterrows():
        for subcatchment in row["Direct Subcatchments"] + row["Nested Subcatchments"]:
            process_subcatchment(subcatchment, subcatchment_frame, detention_tank)

    # Calculate total values for the detention tank
    total_ared = detention_tank['Ared imp.'].sum() + detention_tank['Ared perv.'].sum()
    return total_ared

# Function to calculate qThrRimp
def calculate_qThrRimp(Q_D_R_u, total_area, ared_total):
    QThrmax = Q_D_R_u * (total_area / 10000)
    qThrRimp = QThrmax / (ared_total / 10000)
    return qThrRimp

# Function to process the timeseries and calculate maximum retention volume
def process_timeseries(timeseries_df, junction_of_interest, retention_volumes, fz, total_areas_dict, qThrRimp, fa_dict):
    timeseries_detention_df = timeseries_df.copy()
    total_area = total_areas_dict[junction_of_interest]
    fa = fa_dict[junction_of_interest]

    def calculate_values(row):
        rDn = row['Intensity [l/(s ha)]']
        D = row['T [min]']
        Vs_imp = (rDn - qThrRimp) * (D * 60) * fa * fz / 1000
        return Vs_imp

    timeseries_detention_df['Vs,imp'] = timeseries_detention_df.apply(calculate_values, axis=1)
    max_Vs_imp = timeseries_detention_df['Vs,imp'].max()
    max_Vret = max_Vs_imp * (total_area / 10000)
    retention_volumes[junction_of_interest] = max_Vret
    
    return timeseries_detention_df


# Calculate total Ared for each junction in the list
ared_totals = {}
for junction_of_interest in detention_tank_list:
    total_ared = calculate_ared_for_junction(junction_of_interest, subcatchment_frame, conduits_complete)
    ared_totals[junction_of_interest] = total_ared
    

# Process the timeseries data for each junction
retention_volumes = {}
for junction_of_interest in detention_tank_list:
    specific_ared_total = ared_totals[junction_of_interest]
    qThrRimp = calculate_qThrRimp(Q_D_R_u, total_areas[junction_of_interest], specific_ared_total)
    process_timeseries(timeseries_df, junction_of_interest, retention_volumes, fz, total_areas, qThrRimp, fa_dict)

# Display the updated timeseries DataFrame and retention volumes
print(timeseries_df)
print(retention_volumes)

data = []

# Process each junction and collect data for DataFrame
for junction_of_interest in detention_tank_list:
    # Calculate Ared total for the junction
    total_ared = calculate_ared_for_junction(junction_of_interest, subcatchment_frame, conduits_complete)
    
    # Calculate qThrRimp
    specific_total_area = total_areas[junction_of_interest]
    qThrRimp = calculate_qThrRimp(Q_D_R_u, specific_total_area, total_ared)
    
    # Process timeseries data
    timeseries_detention_df = process_timeseries(timeseries_df, junction_of_interest, retention_volumes, fz, total_areas, qThrRimp, fa_dict)
    
    # Get maximum Vs,imp and maximum Vret for the junction
    max_Vs_imp = timeseries_detention_df['Vs,imp'].max()
    max_Vret = retention_volumes[junction_of_interest]
    
    # Collect all necessary data for this junction
    data.append({
        "Junction": junction_of_interest,
        "Total Area": specific_total_area,
        "Ared Total": total_ared,
        "fa": fa_dict[junction_of_interest],
        "fz": fz,
        "qThrRimp": qThrRimp,
        "Max Vs,imp": max_Vs_imp,
        "Max Vret": max_Vret
    })

# Create DataFrame from collected data
StorageNodes = pd.DataFrame(data)

# Display the DataFrame
# Set Pandas display options
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column
print(StorageNodes)
####################################################################################################################################################
####################################################################################################################################################
#SECTION 5==========================================================================================================================
def extract_junction_parameters(inp_lines, junction_name):
    """
    Extracts the elevation and max depth for a given junction from INP file lines.
    """
    elevation, max_depth = None, None
    for line in inp_lines:
        if line.strip().startswith(junction_name):
            parts = line.split()
            elevation = float(parts[1])  # Assuming elevation is the second column
            if len(parts) > 2:
                max_depth = float(parts[2])  # Assuming max depth is the third column
            break
    return elevation, max_depth

# Function to transform a junction to a storage unit in the INP file
def final_transform_junction_to_storage(original_lines, junction_id, storage_parameters):
    modified_lines = []
    storage_added = False
    junction_section = False
    storage_section_found = False
    in_storage_section = False

    # Regular expression to match exact junction ID
    junction_regex = re.compile(rf'^\s*{junction_id}\s+')

    for line in original_lines:
        if "[JUNCTIONS]" in line:
            junction_section = True
            modified_lines.append(line)
            continue

        if junction_section and line.strip() == "":
            junction_section = False

        # Use regex to check for exact match
        if junction_section and junction_regex.match(line):
            continue  # Skip adding this junction line

        if "[STORAGE]" in line:
            storage_section_found = True
            in_storage_section = True
            modified_lines.append(line)
            continue

        if in_storage_section and line.strip() == "":
            in_storage_section = False
            if not storage_added:
                modified_lines.append(f"{junction_id}             {storage_parameters}\n")
                storage_added = True

        if in_storage_section and not storage_added and (line.startswith(';;') or line.startswith('[')):
            modified_lines.append(f"{junction_id}             {storage_parameters}\n")
            storage_added = True

        if not storage_added and not junction_section and not storage_section_found and "[CONDUITS]" in line:
            modified_lines.append("[STORAGE]\n")
            modified_lines.append(";;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Type/Params            SurDepth  Fevap    Psi      Ksat     IMD     \n")
            modified_lines.append(";;-------------- -------- ---------- ----------- ---------- ---------------------------- --------- -------- -------- -------- --------\n")
            modified_lines.append(f"{junction_id}             {storage_parameters}\n\n")  # Add a blank line here
            storage_added = True
            storage_section_found = True

        modified_lines.append(line)

    if not storage_added and not storage_section_found:
        modified_lines.append("[STORAGE]\n")
        modified_lines.append(";;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Type/Params            SurDepth  Fevap    Psi      Ksat     IMD     \n")
        modified_lines.append(";;-------------- -------- ---------- ----------- ---------- ---------------------------- --------- -------- -------- -------- --------\n")
        modified_lines.append(f"{junction_id}             {storage_parameters}\n\n")  # Add a blank line here

    return modified_lines

# Read INP file
  # Replace with actual file path
with open(file_path, 'r') as file:
    original_lines = file.readlines()

# List to store data for final DataFrame
final_data = []

for junction_id in detention_tank_list:
    # Extract junction parameters
    storage_elev, existing_max_depth = extract_junction_parameters(original_lines, junction_id)
    max_depth = existing_max_depth if existing_max_depth is not None else 2.5

   # print(f"Extracted elevation for {junction_id}: {storage_elev}")
   # print(f"Extracted max depth for {junction_id}: {max_depth}")

    # Get the max Vret for the current junction
    max_Vret = retention_volumes[junction_id]

    # Format storage parameters
    storage_parameters = f"{storage_elev:.2f}   {max_depth:.2f}       0          TABULAR    {junction_id}                         0         0"

    # Transform junction to storage unit
    try:
        original_lines = final_transform_junction_to_storage(original_lines, junction_id, storage_parameters)
        conversion_status = "Complete"
    except Exception as e:
       # print(f"Error transforming junction {junction_id}: {e}")
        conversion_status = "Failed"

    #print(f"Transformation completed for junction {junction_id}")

    # Collect data for final DataFrame
    final_data.append({
        "Junction": junction_id,
        "Elevation": storage_elev,
        "Max Depth": max_depth,
        "Conversion Status": conversion_status
    })

# Save the final modified lines to the INP file
with open(file_path, 'w') as file:
    file.writelines(original_lines)

print("All junctions have been transformed to storage units and the file has been saved.")

# Create DataFrame from collected data
final_df = pd.DataFrame(final_data)

# Display the DataFrame
# Set Pandas display options
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column

print(final_df)

###############################################################################################################################################
###############################################################################################################################################
#SECTION 6 ======================================================================================================================
import pandas as pd
import re

# Function to extract junction parameters
def extract_junction_parameters(inp_lines, junction_name):
    elevation, max_depth = None, None
    for line in inp_lines:
        if line.strip().startswith(junction_name):
            parts = line.split()
            elevation = float(parts[1])  # Assuming elevation is the second column
            if len(parts) > 2:
                max_depth = float(parts[2])  # Assuming max depth is the third column
            break
    return elevation, max_depth

# Function to transform a junction to a storage unit in the INP file
def final_transform_junction_to_storage(original_lines, junction_id, storage_parameters):
    modified_lines = []
    storage_added = False
    junction_section = False
    storage_section_found = False
    in_storage_section = False

    # Regular expression to match exact junction ID
    junction_regex = re.compile(rf'^\s*{junction_id}\s+')

    for line in original_lines:
        if "[JUNCTIONS]" in line:
            junction_section = True
            modified_lines.append(line)
            continue

        if junction_section and line.strip() == "":
            junction_section = False

        # Use regex to check for exact match
        if junction_section and junction_regex.match(line):
            continue  # Skip adding this junction line

        if "[STORAGE]" in line:
            storage_section_found = True
            in_storage_section = True
            modified_lines.append(line)
            continue

        if in_storage_section and line.strip() == "":
            in_storage_section = False
            if not storage_added:
                modified_lines.append(f"{junction_id}             {storage_parameters}\n")
                storage_added = True

        if in_storage_section and not storage_added and (line.startswith(';;') or line.startswith('[')):
            modified_lines.append(f"{junction_id}             {storage_parameters}\n")
            storage_added = True

        if not storage_added and not junction_section and not storage_section_found and "[CONDUITS]" in line:
            modified_lines.append("[STORAGE]\n")
            modified_lines.append(";;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Type/Params            SurDepth  Fevap    Psi      Ksat     IMD     \n")
            modified_lines.append(";;-------------- -------- ---------- ----------- ---------- ---------------------------- --------- -------- -------- -------- --------\n")
            modified_lines.append(f"{junction_id}             {storage_parameters}\n\n")  # Add a blank line here
            storage_added = True
            storage_section_found = True

        modified_lines.append(line)

    if not storage_added and not storage_section_found:
        modified_lines.append("[STORAGE]\n")
        modified_lines.append(";;Name           Elev.    MaxDepth   InitDepth  Shape      Curve Type/Params            SurDepth  Fevap    Psi      Ksat     IMD     \n")
        modified_lines.append(";;-------------- -------- ---------- ----------- ---------- ---------------------------- --------- -------- -------- -------- --------\n")
        modified_lines.append(f"{junction_id}             {storage_parameters}\n\n")  # Add a blank line here

    return modified_lines

# Function to generate storage curve data for a rectangular tank
def generate_curve_data_rectangular(max_depth, max_volume, steps=1):
    depth_step = max_depth / steps
    curve_data = [(0, 0)]  # Starting point

    # Calculate the base area (A) from the max volume and max depth
    base_area = max_volume / max_depth  # Since volume = base_area * max_depth

    for i in range(1, steps + 1):
        depth = i * depth_step
        area = base_area  # Area remains constant for a rectangular tank
        curve_data.append((depth, area))

    return curve_data

# Function to ensure the CURVES section exists and is updated with storage units
def ensure_curves_section(lines, storage_units, curve_details):
    curves_exist = any("[CURVES]" in line for line in lines)
    new_lines = []
    in_curves_section = False
    added_curves = set(storage_units.keys())

    for line in lines:
        new_lines.append(line)
        if "[XSECTIONS]" in line:
            continue

        if "[CURVES]" in line:
            in_curves_section = True
            new_lines.append(";;Name           Type       X-Value    Y-Value\n")
            new_lines.append(";;-------------- ---------- ---------- ----------\n")
            for junction_id, (max_volume, max_depth) in storage_units.items():
                curve_data = generate_curve_data_rectangular(max_depth, max_volume, 1)
                curve_details[junction_id] = curve_data
                for i, (depth, area) in enumerate(curve_data):
                    if i == 0:
                        new_lines.append(f"{junction_id}         Storage    {depth:.2f}    {area:.2f}\n")
                    else:
                        new_lines.append(f"{junction_id}                     {depth:.2f}    {area:.2f}\n")
            in_curves_section = False
            added_curves.clear()

    if not curves_exist:
        for i, line in enumerate(new_lines):
            if "[XSECTIONS]" in line:
                for j in range(i + 1, len(new_lines)):
                    if new_lines[j].strip() == "":
                        new_lines.insert(j + 1, "[CURVES]\n")
                        new_lines.insert(j + 2, ";;Name           Type       X-Value    Y-Value\n")
                        new_lines.insert(j + 3, ";;-------------- ---------- ---------- ----------\n")
                        for junction_id, (max_volume, max_depth) in storage_units.items():
                            curve_data = generate_curve_data_rectangular(max_depth, max_volume, 1)
                            curve_details[junction_id] = curve_data
                            for i, (depth, area) in enumerate(curve_data):
                                if i == 0:
                                    new_lines.insert(j + 4, f"{junction_id}         Storage    {depth:.2f}    {area:.2f}\n")
                                else:
                                    new_lines.insert(j + 5, f"{junction_id}                     {depth:.2f}    {area:.2f}\n")
                        break
                break

    return new_lines

# Read INP file
  # Replace with actual file path
with open(file_path, 'r') as file:
    lines = file.readlines()

# Ensure curves section for each junction in the detention_tank_list
storage_units = {junction_id: (retention_volumes[junction_id], extract_junction_parameters(lines, junction_id)[1]) for junction_id in detention_tank_list}
curve_details = {}
new_lines = ensure_curves_section(lines, storage_units, curve_details)

# Save the updated file
with open(file_path, 'w') as file:
    file.writelines(new_lines)

print("Storage curves added to the INP file for all junctions.")

# Create DataFrame with curve details
curve_summary_data = []
for junction_id, curve_data in curve_details.items():
    for depth, area in curve_data:
        curve_summary_data.append({
            "Junction": junction_id,
            "Depth (m)": depth,
            "Area (m²)": area
        })

curve_summary_df = pd.DataFrame(curve_summary_data)

# Display the DataFrame
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column

print(curve_summary_df)
####################################################################################################################################################
####################################################################################################################################################
#SECTION7=======================================================================================================================================
# Function to find the 'To Node' for a given 'From Node' in the conduits section
def find_to_node_in_conduits(file_path, junction_id):
    in_conduits_section = False
    to_node = None
    
    with open(file_path, 'r') as file:
        for line in file:
            if "[CONDUITS]" in line:
                in_conduits_section = True
                continue
            if in_conduits_section and line.strip() == "":
                in_conduits_section = False
                continue
            if in_conduits_section and line.strip() and not line.startswith(";;"):
                parts = line.split()
                if parts[1] == junction_id:
                    to_node = parts[2]
                    break
    
    return to_node


# Torricelli's law
# Function to calculate orifice parameters
def calculate_orifice_parameters(ared_total, detention_tank_volume_m3, throttle_flow_rate_per_hectare):
    discharge_coefficient = 0.65  # dimensionless
    gravity = 9.81  # m/s²
    max_water_height = 1.5  # m
    desired_emptying_time_h = 24  # hours

    throttle_flow_L_s = throttle_flow_rate_per_hectare * (ared_total / 10000)
    throttle_flow_m3_s = throttle_flow_L_s / 1000  # 1 m³ = 1000 L
    orifice_area = throttle_flow_m3_s / (discharge_coefficient * math.sqrt(2 * gravity * max_water_height))
    diameter_m = 2 * math.sqrt(orifice_area / math.pi)
    emptying_time_h = detention_tank_volume_m3 / throttle_flow_m3_s / 3600

    if emptying_time_h > desired_emptying_time_h:
        required_throttle_flow_m3_s = detention_tank_volume_m3 / (desired_emptying_time_h * 3600)
        orifice_area = required_throttle_flow_m3_s / (discharge_coefficient * math.sqrt(2 * gravity * max_water_height))
        diameter_m = 2 * math.sqrt(orifice_area / math.pi)
        throttle_flow_m3_s = required_throttle_flow_m3_s

    return throttle_flow_m3_s, orifice_area, diameter_m

# Function to add orifice details to the INP file
def add_orifice_to_storage_unit(lines, storage_unit_id, orifice_params, xsection_params, file_path):
    orifice_section_exists = any("[ORIFICES]" in line for line in lines)
    new_lines = []
    in_conduits_section = False
    in_xsections_section = False
    orifice_added = False
    xsection_added = False

    to_node = find_to_node_in_conduits(file_path, storage_unit_id)
    if not to_node:
        raise ValueError("To Node not found in CONDUITS section for the given storage unit.")

    for line in lines:
        if "[CONDUITS]" in line:
            in_conduits_section = True
            new_lines.append(line)
            continue

        if in_conduits_section and line.strip() == "":
            if not orifice_section_exists and not orifice_added:
                new_lines.append("[ORIFICES]\n")
                new_lines.append(";;Name           From Node        To Node          Type         Offset     Qcoeff     Gated    CloseTime\n")
                new_lines.append(";;-------------- ---------------- ---------------- ------------ ---------- ---------- -------- ----------\n")
                new_lines.append(f"{storage_unit_id}             {storage_unit_id}             {to_node}             {orifice_params}\n")
                orifice_added = True
            new_lines.append(line)
            in_conduits_section = False
            continue

        if "[XSECTIONS]" in line:
            in_xsections_section = True
            if not orifice_added:
                new_lines.append("[ORIFICES]\n")
                new_lines.append(";;Name           From Node        To Node          Type         Offset     Qcoeff     Gated    CloseTime\n")
                new_lines.append(";;-------------- ---------------- ---------------- ------------ ---------- ---------- -------- ----------\n")
                new_lines.append(f"{storage_unit_id}             {storage_unit_id}             {to_node}             {orifice_params}\n")
                orifice_added = True
            new_lines.append(line)
            continue

        if in_xsections_section and line.strip() == "":
            if not xsection_added:
                new_lines.append(f"{storage_unit_id}             {xsection_params}\n")
                xsection_added = True
            new_lines.append(line)
            in_xsections_section = False
            continue

        new_lines.append(line)

    if not orifice_section_exists and not orifice_added:
        new_lines.append("[ORIFICES]\n")
        new_lines.append(";;Name           From Node        To Node          Type         Offset     Qcoeff     Gated    CloseTime\n")
        new_lines.append(";;-------------- ---------------- ---------------- ------------ ---------- ---------- -------- ----------\n")
        new_lines.append(f"{storage_unit_id}             {storage_unit_id}             {to_node}             {orifice_params}\n")

    if not xsection_added:
        new_lines.append("[XSECTIONS]\n")
        new_lines.append(";;Link           Shape        Geom1            Geom2      Geom3      Geom4      Barrels    Culvert\n")
        new_lines.append(";;-------------- ------------ ---------------- ---------- ---------- ---------- ---------- ----------\n")
        new_lines.append(f"{storage_unit_id}             {xsection_params}\n")

    return new_lines

# Calculate total Ared for each junction in the list
ared_totals = {}
for junction_of_interest in detention_tank_list:
    total_ared = calculate_ared_for_junction(junction_of_interest, subcatchment_frame, conduits_complete)
    ared_totals[junction_of_interest] = total_ared

# Prepare to collect data for the final report
final_report_data = []

# Process each junction to calculate orifice parameters and add them to the INP file
for junction_of_interest in detention_tank_list:
    total_ared = ared_totals[junction_of_interest]
    detention_tank_volume = retention_volumes[junction_of_interest]
    # Calculate orifice parameters
    throttle_flow_m3_s, orifice_area, orifice_diameter_m = calculate_orifice_parameters(total_ared, detention_tank_volume, Q_D_R_u)
    # Prepare orifice and cross-section parameters
    orifice_params = f"SIDE         0          0.65       NO       0"
    xsection_params = f"CIRCULAR     0.5            {orifice_diameter_m:.3f}          0          0           1"
    
    # Read INP file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Modify the lines
    new_lines = add_orifice_to_storage_unit(lines, junction_of_interest, orifice_params, xsection_params, file_path)

    # Write the modified lines back to the file
    with open(file_path, 'w') as file:
        file.writelines(new_lines)
    
    # Collect data for the final report
    final_report_data.append({
        "Junction": junction_of_interest,
        "Throttle Flow (m³/s)": throttle_flow_m3_s,
        "Orifice Area (m²)": orifice_area,
        "Orifice Diameter (m)": orifice_diameter_m
    })

# Create the final report DataFrame
final_report_df = pd.DataFrame(final_report_data)

# Display the final report DataFrame
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column

print(final_report_df)
######################################################################################################################################################
####################################################################################################################################################
#SECTION 8: UPDATE INLET OFFSET CONDUITS DOWNSTREAM====================================================================================================
def update_inlet_offsets(file_path, detention_tank_list):
    updated_lines = []
    conduits_section = False

    # Open and read the SWMM input file
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Process each line in the file
    for line in lines:
        if "[CONDUITS]" in line:
            conduits_section = True
            updated_lines.append(line)
            continue
        
        if conduits_section and line.strip() == "":
            conduits_section = False
        
        if conduits_section and line.strip() and not line.startswith(";;"):
            parts = line.split()
            if len(parts) >= 7:
                from_node = parts[1]
                if from_node in detention_tank_list:
                    # Update the InOffset to 1 (index 5)
                    parts[5] = '1'
                    # Ensure the parts list has the required number of elements
                    while len(parts) < 9:
                        parts.append('0')
                    # Reconstruct the line with proper formatting
                    updated_line = "{:<16} {:<16} {:<16} {:<10} {:<10} {:<10} {:<10} {:<10} {:<10}\n".format(*parts)
                    updated_lines.append(updated_line)
                    continue
        
        updated_lines.append(line)
    # Write the updated lines back to the SWMM input file
    with open(file_path, 'w') as file:
        file.writelines(updated_lines)
    print("Inlet offsets updated successfully for specified conduits.")


update_inlet_offsets(file_path, detention_tank_list)

###########################################################################################################################
# Combine all the dataframes into a single Excel file
with pd.ExcelWriter(file_path2) as writer:
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    StorageNodes.to_excel(writer, sheet_name='Storage Nodes', index=False)
    final_df.to_excel(writer, sheet_name='Final Conversion', index=False)
    curve_summary_df.to_excel(writer, sheet_name='Curve Summary', index=False)
    final_report_df.to_excel(writer, sheet_name='Final Report', index=False)

file_path2
#############################################################################################################################################
############################################################################################################################################
#############################################################################################################################################
############################################################################################################################################
#############################################################################################################################################
############################################################################################################################################
#LIDS ########################################################################################################################################################
####################################################################################################################################
#######################################################################################################################################
# PART 1: VEGETATIVE SWALE ########################################################################################################################################################
results_df = pd.DataFrame(columns=["Initial Subcatchment", "Connected Subcatchments"])

# Define a function to process a given subcatchment and its connected subcatchments
def process_subcatchment(subcatchment_of_interest):
    connected_subcatchments = []

    # Function to recursively find all connected subcatchments
    def find_connected_subcatchments(subcatchments):
        for subcatchment in subcatchments:
            current_connected = subcatchment_frame[subcatchment_frame['Outlet'] == subcatchment]['Subcatchment'].tolist()
            connected_subcatchments.extend(current_connected)
            find_connected_subcatchments(current_connected)

    # Start the recursion with the initial subcatchment
    find_connected_subcatchments([subcatchment_of_interest])
    connected_subcatchments = list(set(connected_subcatchments))  # Remove duplicates
    results_df.loc[len(results_df)] = [subcatchment_of_interest, connected_subcatchments]

# Process each subcatchment in the list
for subcatchment in infiltration_swale_list:
    process_subcatchment(subcatchment)

# Print the results DataFrame
# Display the final report DataFrame
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column

print(results_df)
################################################################################################################################
################################################################################################################################
# Define ψm values for different land uses
psi_m_values = {
    "Vegetation": 0.3,
    "Street": 0.9,  # Assuming Asphalt for Street as well
    "Stone": 0.7,  # Assuming Stone Paver
    "Roof": 0.9
}

# Function to determine ψm value based on subcatchment name
def get_psi_m(subcatchment_name):
    for land_use in psi_m_values:
        if land_use in subcatchment_name:
            return psi_m_values[land_use]
    return None  # Default case if no land use is found

# Function to add subcatchments to infiltration trench dataframe
def add_subcatchment_to_dataframe(subcatchment, dataframe):
    area_row = subcatchment_frame[subcatchment_frame['Subcatchment'] == subcatchment]
    if area_row.empty:
        print(f"Subcatchment {subcatchment} not found in subcatchment_frame")
        return None
    area_ha = area_row['Area'].values[0]
    area_m2 = float(area_ha) * 10000  # Convert from hectares to square meters
    imperv = area_row['Imperv%'].values[0]
    imperv = float(imperv)
    perv = 100 - imperv

    # Determine ψm values based on subcatchment name
    psi_m = get_psi_m(subcatchment)
    if psi_m is None:
        print(f"No ψm value found for subcatchment: {subcatchment}")
        return None

    # Calculate other values based on retrieved data
    ae_imp = area_m2 * (imperv / 100)
    ae_perv = area_m2 * (perv / 100)
    ared_imp = psi_m * ae_imp
    ared_perv = psi_m * ae_perv

    # Add the calculated values to the infiltration trench dataframe
    dataframe.loc[len(dataframe)] = [
        subcatchment, area_m2, imperv, perv, psi_m, psi_m, ae_imp, ae_perv, ared_imp, ared_perv, 0
    ]

# Create a DataFrame to store the totals for each subcatchment of interest
totals_list = []
# Iterate through each row in the results_df
for index, row in results_df.iterrows():
    subcatchment_of_interest = row["Initial Subcatchment"]
    infiltration_swale = pd.DataFrame(columns=["Name", "A (m2)", "% Imp.", "% Perv.", "ψm Imp.", "ψm perv.", "AE imp.", "AE perv.", "Ared imp.", "Ared perv.", "Ared"])
    
    # Combine initial subcatchment and connected subcatchments
    all_subcatchments = [subcatchment_of_interest] + row["Connected Subcatchments"]
    unique_subcatchments = set(all_subcatchments)

    # Iterate through all unique subcatchments
    for subcatchment in unique_subcatchments:
        add_subcatchment_to_dataframe(subcatchment, infiltration_swale)

    # Calculate total values for the current subcatchment of interest
    total_area = infiltration_swale['A (m2)'].sum()
    total_ae_imp = infiltration_swale['AE imp.'].sum()
    total_ae_perv = infiltration_swale['AE perv.'].sum()
    total_ared_imp = infiltration_swale['Ared imp.'].sum()
    total_ared_perv = infiltration_swale['Ared perv.'].sum()
    total_ared = total_ared_imp + total_ared_perv

    # Add the totals to the list
    totals_list.append({
        'Subcatchment': subcatchment_of_interest,
        'A total': total_area,
        'AE imp total': total_ae_imp,
        'AE perv total': total_ae_perv,
        'Ared imp total': total_ared_imp,
        'Ared perv total': total_ared_perv,
        'Ared total': total_ared
    })

# Create a DataFrame from the totals list
totals_df = pd.DataFrame(totals_list)
# Display the final report DataFrame
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column

print(totals_df)
#########################################################################################################################################33
# Define additional parameters
kf = 5 * 10**-5  # m/s
fs = 1.2
Ap = 100  # m², provided value

# Function to calculate the necessary parameters for each subcatchment
def calculate_parameters(totals_df, timeseries_df, results_df):
    results_summary = []

    print("Totals DataFrame Columns:", totals_df.columns)
    print("Results DataFrame Columns:", results_df.columns)

    for index, row in totals_df.iterrows():
        subcatchment_name = row['Subcatchment']
        A_imp = row['A total']

        # Retrieve connected subcatchments
        connected_subcatchments = results_df[results_df['Initial Subcatchment'] == subcatchment_name]['Connected Subcatchments'].values
        connected_subcatchments = connected_subcatchments[0] if len(connected_subcatchments) > 0 else []

        # Make a copy of the original DataFrame for calculations
        infiltration_swale_df = timeseries_df.copy()

        # Calculate V using the corrected formula for each timestep
        infiltration_swale_df['V [m3]'] = (
            (A_imp + Ap) * 10**-7 * infiltration_swale_df['Intensity [l/(s ha)]'] - 
            Ap * (kf / 2)
        ) * infiltration_swale_df['T [min]'] * 60 * fs

        # Determine the duration that gives the maximum storage volume V
        max_V = infiltration_swale_df['V [m3]'].max()
        max_V_index = infiltration_swale_df['V [m3]'].idxmax()
        max_D = infiltration_swale_df.loc[max_V_index, 'T [min]']

        # Calculate the necessary impoundage height zSw
        zSw = max_V / Ap

        # Calculate the emptying time tE
        tE = 2 * zSw / kf

        # Check conditions
        h_condition = 'Respected' if zSw < 0.3 else 'Not Respected'
        t_condition = 'Respected' if tE / 3600 < 24 else 'Not Respected'

        # Collect results for the current subcatchment
        subcatchment_result = {
            'Subcatchment': subcatchment_name,
            'Max_V [m3]': max_V,
            'Impoundage height (zSw) [m]': zSw,
            'Emptying time (tE) [hours]': tE / 3600,
            'Condition h': h_condition,
            'Condition t': t_condition,
            'Connected Subcatchments': connected_subcatchments
        }

        # Append the results to the summary list
        results_summary.append(subcatchment_result)

    # Create a DataFrame from the results summary
    calculations_df = pd.DataFrame(results_summary)

    # Display the final report DataFrame
    pd.set_option('display.max_rows', None)  # None means show all rows
    pd.set_option('display.max_columns', None)  # None means show all columns
    pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
    pd.set_option('display.max_colwidth', None)  # Show full content of each column

    print(calculations_df)

    return calculations_df

# Assuming totals_df, timeseries_df, and results_df are defined elsewhere in your script
calculations_df = calculate_parameters(totals_df, timeseries_df, results_df)
################################################################################################################################3
#################################################################################################################################
# Updated add_lid_usage_to_subcatchment function
def add_lid_usage_to_subcatchment(file_path, subcatchment_names, lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv):
    # Read the .inp file content
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    # Find the LID_USAGE section
    start, end = None, None
    for i, line in enumerate(lines):
        if line.startswith("[LID_USAGE]"):
            start = i + 1
        elif start and line.startswith("["):
            end = i
            break
    
    # Check if the section was found
    if start is None:
        print("LID_USAGE section not found.")
        return
    if end is None:
        end = len(lines)
    
    # Check existing LID usages in the section
    existing_lid_usages = set()
    for line in lines[start:end]:
        if line.strip():
            existing_lid_usages.add(line.split()[0])
    
    # Prepare the new LID_USAGE entries
    new_lid_usages = []
    for subcatchment_name in subcatchment_names:
        # Skip subcatchment if it already has a LID usage
        if subcatchment_name in existing_lid_usages:
            print(f"LID already exists for subcatchment: {subcatchment_name}. Skipping.")
            continue
        
        # Check constraints for applying LID usage
        subcatchment_upper = subcatchment_name.upper()
        if lid_process == 'Green_Roof':
            if 'ROOF' not in subcatchment_upper:
                print(f"Error: Green Roof solutions can only be applied to Roof subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Permeable_Pavement':
            if 'STREET' not in subcatchment_upper and 'STONE' not in subcatchment_upper:
                print(f"Error: Permeable Pavement solutions can only be applied to Street or Stone subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Vegetative_Swale':
            if 'VEGETATION' not in subcatchment_upper:
                print(f"Error: Vegetative Swale solutions can only be applied to Vegetation subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Infiltration_Trench':
            if not any(x in subcatchment_upper for x in ['STREET', 'VEGETATION', 'STONE']):
                print(f"Error: Infiltration Trench solutions can only be applied to Street, Vegetation, or Stone Paver subcatchments. Skipping {subcatchment_name}.")
                continue
        else:
            print(f"Error: Unknown LID process '{lid_process}'. Skipping {subcatchment_name}.")
            continue
        
        # Prepare the new LID_USAGE entry
        new_lid_usage = f"{subcatchment_name}\t{lid_process}\t{number}\t{area}\t{width}\t{init_sat}\t{from_imp}\t{to_perv}\t{rpt_file}\t{drain_to}\t{from_perv}\n"
        new_lid_usages.append(new_lid_usage)
    
    if not new_lid_usages:
        print("No valid LID usages to add. Exiting function.")
        return
    
    # Insert the new LID_USAGE entries at the end of LID_USAGE section
    lines[end:end] = new_lid_usages
    
    # Write the changes back to the file
    with open(file_path, 'w') as file:
        file.writelines(lines)

# Function to determine if a LID process can be applied to a subcatchment
def can_apply_lid(subcatchment, lid_process):
    subcatchment_upper = subcatchment.upper()
    if lid_process == 'Green_Roof':
        return 'ROOF' in subcatchment_upper
    elif lid_process == 'Permeable_Pavement':
        return 'STREET' in subcatchment_upper or 'STONE' in subcatchment_upper
    elif lid_process == 'Vegetative_Swale':
        return 'VEGETATION' in subcatchment_upper
    elif lid_process == 'Infiltration_Trench':
        return any(x in subcatchment_upper for x in ['STREET', 'VEGETATION', 'STONE'])
    else:
        print(f"Warning: Unknown LID process '{lid_process}'. No LID will be applied.")
        return False

# Function to retrieve the width of a subcatchment
def get_subcatchment_width(subcatchment_name):
    return subcatchment_frame.loc[subcatchment_frame['Subcatchment'] == subcatchment_name, 'Width'].values[0]

# Updated function to apply LID to subcatchments if needed
def apply_lid_to_subcatchments_if_needed(file_path, lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, calculations_df, subcatchment_list):
    if calculations_df.empty:
        print("Results DataFrame is empty. No LID applications needed.")
        return pd.DataFrame(columns=["Subcatchment", "Converted", "LID Type", "Width"])
    
    converted_subcatchments = []

    # Always apply LID to subcatchments in the provided list if constraints allow
    for subcatchment in subcatchment_list:
        if can_apply_lid(subcatchment, lid_process):
            width =  get_subcatchment_width(subcatchment)      #was previously used
            add_lid_usage_to_subcatchment(file_path, [subcatchment], lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv)
            converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": True, "LID Type": lid_process, "Width": width })  #now i put 5 previously it was width
            #print(f"Converted subcatchment: {subcatchment} to {lid_process} with width {width}.")
        else:
            #print(f"{lid_process} cannot be applied to subcatchment: {subcatchment} due to constraints.")
            converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": False, "LID Type": lid_process, "Width": None})
    
    # Iterate through each subcatchment in calculations_df to check conditions
    for idx, row in calculations_df.iterrows():
        initial_subcatchment = row['Subcatchment']
        h_condition = row['Condition h']
        t_condition = row['Condition t']
        connected_subcatchments = row['Connected Subcatchments']

        # Check if either condition is not respected
        if h_condition == 'Not Respected' or t_condition == 'Not Respected':
            # Apply LID to all connected subcatchments if constraints allow and LID not already applied
            for subcatchment in connected_subcatchments:
                if can_apply_lid(subcatchment, lid_process):
                    width = get_subcatchment_width(subcatchment)      #was previously used
                    add_lid_usage_to_subcatchment(file_path, [subcatchment], lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv)
                    converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": True, "LID Type": lid_process, "Width": width }) #now i put 5 previously it was width
                    #print(f"Converted connected subcatchment: {subcatchment} to {lid_process} with width {width}.")
                else:
                    #print(f"{lid_process} cannot be applied to connected subcatchment: {subcatchment} due to constraints.")
                    converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": False, "LID Type": lid_process, "Width": None})

    # Create a DataFrame from the list of converted subcatchments
    converted_subcatchments_df = pd.DataFrame(converted_subcatchments, columns=["Subcatchment", "Converted", "LID Type", "Width"])
    return converted_subcatchments_df

# Usage example
lid_process = 'Vegetative_Swale'
number = 1
area = 80
init_sat = 0
from_imp = 0
to_perv = 0
rpt_file = '*'
drain_to = '*'
from_perv = 0

# Call the function and capture the returned DataFrame
converted_vegetative_swale_df = apply_lid_to_subcatchments_if_needed(
    file_path, lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, calculations_df, infiltration_swale_list)

print(converted_vegetative_swale_df)
########################################################################################################################################### Using Pandas ExcelWriter to write each DataFrame to a different sheet in the same Excel file
writer = pd.ExcelWriter(file_path3, engine='xlsxwriter')
try:
    results_df.to_excel(writer, sheet_name='Results', index=False)
    totals_df.to_excel(writer, sheet_name='Totals', index=False)
    calculations_df.to_excel(writer, sheet_name='Calculations', index=False)
    converted_vegetative_swale_df.to_excel(writer, sheet_name='Converted Vegetative Swale', index=False)
finally:
    writer.close()  # Ensure the writer is closed properly and the file is saved
print(f"Data successfully written to {file_path3}")
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
#PART 2: GREEN ROOF ####################################################################################################################################
# Function to retrieve subcatchment widths
def get_subcatchment_widths(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    subcatchment_widths = {}
    start, end = None, None
    for i, line in enumerate(lines):
        if line.startswith("[SUBCATCHMENTS]"):
            start = i + 1
        elif start and line.startswith("["):
            end = i
            break
    
    if start is None:
        print("SUBCATCHMENTS section not found.")
        return subcatchment_widths
    if end is None:
        end = len(lines)
    
    for line in lines[start:end]:
        parts = line.split()
        if len(parts) > 5:
            subcatchment_name = parts[0]
            width = parts[5]
            subcatchment_widths[subcatchment_name] = width
    
    return subcatchment_widths

# Function to add LID usage to subcatchments
def add_lid_usage_to_subcatchment(file_path, subcatchment_names, lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, subcatchment_widths):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    start, end = None, None
    for i, line in enumerate(lines):
        if line.startswith("[LID_USAGE]"):
            start = i + 1
        elif start and line.startswith("["):
            end = i
            break
    
    if start is None:
        print("LID_USAGE section not found.")
        return
    if end is None:
        end = len(lines)
    
    new_lid_usages = []
    for subcatchment_name in subcatchment_names:
        subcatchment_upper = subcatchment_name.upper()
        if lid_process == 'Green_Roof':
            if 'ROOF' not in subcatchment_upper:
                print(f"Error: Green Roof solutions can only be applied to Roof subcatchments. Skipping {subcatchment_name}.")
                continue
        
        width = subcatchment_widths.get(subcatchment_name, '10')
        new_lid_usage = f"{subcatchment_name}\t{lid_process}\t{number}\t{area}\t{width}\t{init_sat}\t{from_imp}\t{to_perv}\t{rpt_file}\t{drain_to}\t{from_perv}\n"
        new_lid_usages.append(new_lid_usage)
    
    if not new_lid_usages:
        print("No valid LID usages to add. Exiting function.")
        return
    
    lines[end:end] = new_lid_usages
    
    with open(file_path, 'w') as file:
        file.writelines(lines)

# Function to determine if LID can be applied
def can_apply_lid(subcatchment, lid_process):
    subcatchment_upper = subcatchment.upper()
    if lid_process == 'Green_Roof':
        return 'ROOF' in subcatchment_upper
    else:
        print(f"Warning: Unknown LID process '{lid_process}'. No LID will be applied.")
        return False

# Function to apply LID to subcatchments if needed
def apply_lid_to_subcatchments_if_needed(file_path, lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, green_roof_list):
    if not green_roof_list:
        print("Green roof list is empty. No LID applications needed.")
        return pd.DataFrame(columns=["Converted Subcatchments", "Width"])
    
    subcatchment_widths = get_subcatchment_widths(file_path)
    converted_subcatchments = []
    
    for subcatchment in green_roof_list:
        if can_apply_lid(subcatchment, lid_process):
            add_lid_usage_to_subcatchment(file_path, [subcatchment], lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, subcatchment_widths)
            converted_subcatchments.append(subcatchment)
            print(f"Converted subcatchment: {subcatchment} to {lid_process}.")
        else:
            print(f"{lid_process} cannot be applied to subcatchment: {subcatchment} due to constraints.")

    converted_subcatchments_df = pd.DataFrame(converted_subcatchments, columns=["Converted Subcatchments"])
    return converted_subcatchments_df

# Usage example
lid_process = 'Green_Roof'
number = 1
area = 80
init_sat = 0
from_imp = 0
to_perv = 0
rpt_file = '*'
drain_to = '*'
from_perv = 0

# Call the function and capture the returned DataFrame
converted_green_roof_df = apply_lid_to_subcatchments_if_needed(
    file_path, lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, green_roof_list
)

print(converted_green_roof_df)
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################### Using Pandas ExcelWriter to write each DataFrame to a different sheet in the same Excel file
writer = pd.ExcelWriter(file_path5, engine='xlsxwriter')
try:
    converted_green_roof_df.to_excel(writer, sheet_name='Converted Green Roof', index=False)
finally:
    writer.close()  # Ensure the writer is closed properly and the file is saved
print(f"Data successfully written to {file_path5}")

########################################################################################################################################################
########################################################################################################################################################
####################################################################################################################################
#######################################################################################################################################
# PART 3: INFILTRATION TRENCH ########################################################################################################################################################
results_df = pd.DataFrame(columns=["Initial Subcatchment", "Connected Subcatchments"])

# Define a function to process a given subcatchment and its connected subcatchments
def process_subcatchment(subcatchment_of_interest):
    connected_subcatchments = []

    # Function to recursively find all connected subcatchments
    def find_connected_subcatchments(subcatchments):
        for subcatchment in subcatchments:
            current_connected = subcatchment_frame[subcatchment_frame['Outlet'] == subcatchment]['Subcatchment'].tolist()
            connected_subcatchments.extend(current_connected)
            find_connected_subcatchments(current_connected)

    # Start the recursion with the initial subcatchment
    find_connected_subcatchments([subcatchment_of_interest])
    connected_subcatchments = list(set(connected_subcatchments))  # Remove duplicates
    results_df.loc[len(results_df)] = [subcatchment_of_interest, connected_subcatchments]

# Process each subcatchment in the list
for subcatchment in infiltration_trench_list:
    process_subcatchment(subcatchment)

# Print the results DataFrame
# Display the final report DataFrame
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column

print(results_df)
################################################################################################################################
################################################################################################################################
# Define ψm values for different land uses
psi_m_values = {
    "Vegetation": 0.3,
    "Street": 0.9,  # Assuming Asphalt for Street as well
    "Stone": 0.7,  # Assuming Stone Paver
    "Roof": 0.9
}

# Function to determine ψm value based on subcatchment name
def get_psi_m(subcatchment_name):
    for land_use in psi_m_values:
        if land_use in subcatchment_name:
            return psi_m_values[land_use]
    return None  # Default case if no land use is found

# Function to add subcatchments to infiltration trench dataframe
def add_subcatchment_to_dataframe(subcatchment, dataframe):
    area_row = subcatchment_frame[subcatchment_frame['Subcatchment'] == subcatchment]
    if area_row.empty:
        print(f"Subcatchment {subcatchment} not found in subcatchment_frame")
        return None
    area_ha = area_row['Area'].values[0]
    area_m2 = float(area_ha) * 10000  # Convert from hectares to square meters
    imperv = area_row['Imperv%'].values[0]
    imperv = float(imperv)
    perv = 100 - imperv

    # Determine ψm values based on subcatchment name
    psi_m = get_psi_m(subcatchment)
    if psi_m is None:
        print(f"No ψm value found for subcatchment: {subcatchment}")
        return None

    # Calculate other values based on retrieved data
    ae_imp = area_m2 * (imperv / 100)
    ae_perv = area_m2 * (perv / 100)
    ared_imp = psi_m * ae_imp
    ared_perv = psi_m * ae_perv

    # Add the calculated values to the infiltration trench dataframe
    dataframe.loc[len(dataframe)] = [
        subcatchment, area_m2, imperv, perv, psi_m, psi_m, ae_imp, ae_perv, ared_imp, ared_perv, 0
    ]

# Create a DataFrame to store the totals for each subcatchment of interest
totals_list = []

# Iterate through each row in the results_df
for index, row in results_df.iterrows():
    subcatchment_of_interest = row["Initial Subcatchment"]
    infiltration_trench = pd.DataFrame(columns=["Name", "A (m2)", "% Imp.", "% Perv.", "ψm Imp.", "ψm perv.", "AE imp.", "AE perv.", "Ared imp.", "Ared perv.", "Ared"])
    
    # Combine initial subcatchment and connected subcatchments
    all_subcatchments = [subcatchment_of_interest] + row["Connected Subcatchments"]
    unique_subcatchments = set(all_subcatchments)

    # Iterate through all unique subcatchments
    for subcatchment in unique_subcatchments:
        add_subcatchment_to_dataframe(subcatchment, infiltration_trench)

    # Calculate total values for the current subcatchment of interest
    total_area = infiltration_trench['A (m2)'].sum()
    total_ae_imp = infiltration_trench['AE imp.'].sum()
    total_ae_perv = infiltration_trench['AE perv.'].sum()
    total_ared_imp = infiltration_trench['Ared imp.'].sum()
    total_ared_perv = infiltration_trench['Ared perv.'].sum()
    total_ared = total_ared_imp + total_ared_perv

    # Add the totals to the list
    totals_list.append({
        'Subcatchment': subcatchment_of_interest,
        'A total': total_area,
        'AE imp total': total_ae_imp,
        'AE perv total': total_ae_perv,
        'Ared imp total': total_ared_imp,
        'Ared perv total': total_ared_perv,
        'Ared total': total_ared
    })

# Create a DataFrame from the totals list
totals_df = pd.DataFrame(totals_list)
# Display the final report DataFrame
pd.set_option('display.max_rows', None)  # None means show all rows
pd.set_option('display.max_columns', None)  # None means show all columns
pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
pd.set_option('display.max_colwidth', None)  # Show full content of each column

print(totals_df)
#########################################################################################################################################33
# Define additional parameters
kf = 5 * 10**-5  # m/s
fs = 1.2
Ap = 100  # m², provided value

# Function to calculate the necessary parameters for each subcatchment
def calculate_parameters(totals_df, timeseries_df, results_df):
    results_summary = []

    print("Totals DataFrame Columns:", totals_df.columns)
    print("Results DataFrame Columns:", results_df.columns)

    for index, row in totals_df.iterrows():
        subcatchment_name = row['Subcatchment']
        A_imp = row['A total']

        # Retrieve connected subcatchments
        connected_subcatchments = results_df[results_df['Initial Subcatchment'] == subcatchment_name]['Connected Subcatchments'].values
        connected_subcatchments = connected_subcatchments[0] if len(connected_subcatchments) > 0 else []

        # Make a copy of the original DataFrame for calculations
        infiltration_trench_df = timeseries_df.copy()

        # Calculate V using the corrected formula for each timestep
        infiltration_trench_df['V [m3]'] = (
            (A_imp + Ap) * 10**-7 * infiltration_trench_df['Intensity [l/(s ha)]'] - 
            Ap * (kf / 2)
        ) * infiltration_trench_df['T [min]'] * 60 * fs

        # Determine the duration that gives the maximum storage volume V
        max_V = infiltration_trench_df['V [m3]'].max()
        max_V_index = infiltration_trench_df['V [m3]'].idxmax()
        max_D = infiltration_trench_df.loc[max_V_index, 'T [min]']

        # Calculate the necessary impoundage height zSw
        zSw = max_V / Ap

        # Calculate the emptying time tE
        tE = 2 * zSw / kf

        # Check conditions
        h_condition = 'Respected' if zSw < 0.3 else 'Not Respected'
        t_condition = 'Respected' if tE / 3600 < 24 else 'Not Respected'

        # Collect results for the current subcatchment
        subcatchment_result = {
            'Subcatchment': subcatchment_name,
            'Max_V [m3]': max_V,
            'Impoundage height (zSw) [m]': zSw,
            'Emptying time (tE) [hours]': tE / 3600,
            'Condition h': h_condition,
            'Condition t': t_condition,
            'Connected Subcatchments': connected_subcatchments
        }

        # Append the results to the summary list
        results_summary.append(subcatchment_result)

    # Create a DataFrame from the results summary
    calculations_df = pd.DataFrame(results_summary)

    # Display the final report DataFrame
    pd.set_option('display.max_rows', None)  # None means show all rows
    pd.set_option('display.max_columns', None)  # None means show all columns
    pd.set_option('display.width', None)  # Adjust the display width to show all data without wrapping
    pd.set_option('display.max_colwidth', None)  # Show full content of each column

    print(calculations_df)

    return calculations_df

# Assuming totals_df, timeseries_df, and results_df are defined elsewhere in your script
calculations_df = calculate_parameters(totals_df, timeseries_df, results_df)
################################################################################################################################3
#################################################################################################################################
# Updated add_lid_usage_to_subcatchment function
def add_lid_usage_to_subcatchment(file_path, subcatchment_names, lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv):
    # Read the .inp file content
    with open(file_path, 'r') as file:
        lines = file.readlines()
    
    # Find the LID_USAGE section
    start, end = None, None
    for i, line in enumerate(lines):
        if line.startswith("[LID_USAGE]"):
            start = i + 1
        elif start and line.startswith("["):
            end = i
            break
    
    # Check if the section was found
    if start is None:
        print("LID_USAGE section not found.")
        return
    if end is None:
        end = len(lines)
    
    # Check existing LID usages in the section
    existing_lid_usages = set()
    for line in lines[start:end]:
        if line.strip():
            existing_lid_usages.add(line.split()[0])
    
    # Prepare the new LID_USAGE entries
    new_lid_usages = []
    for subcatchment_name in subcatchment_names:
        # Skip subcatchment if it already has a LID usage
        if subcatchment_name in existing_lid_usages:
            print(f"LID already exists for subcatchment: {subcatchment_name}. Skipping.")
            continue
        
        # Check constraints for applying LID usage
        subcatchment_upper = subcatchment_name.upper()
        if lid_process == 'Green_Roof':
            if 'ROOF' not in subcatchment_upper:
                print(f"Error: Green Roof solutions can only be applied to Roof subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Permeable_Pavement':
            if 'STREET' not in subcatchment_upper and 'STONE' not in subcatchment_upper:
                print(f"Error: Permeable Pavement solutions can only be applied to Street or Stone subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Vegetative_Swale':
            if 'VEGETATION' not in subcatchment_upper:
                print(f"Error: Vegetative Swale solutions can only be applied to Vegetation subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Infiltration_Trench':
            if not any(x in subcatchment_upper for x in ['STREET', 'VEGETATION', 'STONE']):
                print(f"Error: Infiltration Trench solutions can only be applied to Street, Vegetation, or Stone Paver subcatchments. Skipping {subcatchment_name}.")
                continue
        else:
            print(f"Error: Unknown LID process '{lid_process}'. Skipping {subcatchment_name}.")
            continue
        
        # Prepare the new LID_USAGE entry
        new_lid_usage = f"{subcatchment_name}\t{lid_process}\t{number}\t{area}\t{width}\t{init_sat}\t{from_imp}\t{to_perv}\t{rpt_file}\t{drain_to}\t{from_perv}\n"
        new_lid_usages.append(new_lid_usage)
    
    if not new_lid_usages:
        print("No valid LID usages to add. Exiting function.")
        return
    
    # Insert the new LID_USAGE entries at the end of LID_USAGE section
    lines[end:end] = new_lid_usages
    
    # Write the changes back to the file
    with open(file_path, 'w') as file:
        file.writelines(lines)

# Function to determine if a LID process can be applied to a subcatchment
def can_apply_lid(subcatchment, lid_process):
    subcatchment_upper = subcatchment.upper()
    if lid_process == 'Green_Roof':
        return 'ROOF' in subcatchment_upper
    elif lid_process == 'Permeable_Pavement':
        return 'STREET' in subcatchment_upper or 'STONE' in subcatchment_upper
    elif lid_process == 'Vegetative_Swale':
        return 'VEGETATION' in subcatchment_upper
    elif lid_process == 'Infiltration_Trench':
        return any(x in subcatchment_upper for x in ['STREET', 'VEGETATION', 'STONE'])
    else:
        print(f"Warning: Unknown LID process '{lid_process}'. No LID will be applied.")
        return False

# Function to retrieve the width of a subcatchment
def get_subcatchment_width(subcatchment_name):
    return subcatchment_frame.loc[subcatchment_frame['Subcatchment'] == subcatchment_name, 'Width'].values[0]

# Updated function to apply LID to subcatchments if needed
def apply_lid_to_subcatchments_if_needed(file_path, lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, calculations_df, subcatchment_list):
    if calculations_df.empty:
        print("Results DataFrame is empty. No LID applications needed.")
        return pd.DataFrame(columns=["Subcatchment", "Converted", "LID Type", "Width"])
    
    converted_subcatchments = []

    # Always apply LID to subcatchments in the provided list if constraints allow
    for subcatchment in subcatchment_list:
        if can_apply_lid(subcatchment, lid_process):
            width = get_subcatchment_width(subcatchment)
            add_lid_usage_to_subcatchment(file_path, [subcatchment], lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv)
            converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": True, "LID Type": lid_process, "Width": width})
            #print(f"Converted subcatchment: {subcatchment} to {lid_process} with width {width}.")
        else:
            #print(f"{lid_process} cannot be applied to subcatchment: {subcatchment} due to constraints.")
            converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": False, "LID Type": lid_process, "Width": None})
    
    # Iterate through each subcatchment in calculations_df to check conditions
    for idx, row in calculations_df.iterrows():
        initial_subcatchment = row['Subcatchment']
        h_condition = row['Condition h']
        t_condition = row['Condition t']
        connected_subcatchments = row['Connected Subcatchments']

        # Check if either condition is not respected
        if h_condition == 'Not Respected' or t_condition == 'Not Respected':
            # Apply LID to all connected subcatchments if constraints allow and LID not already applied
            for subcatchment in connected_subcatchments:
                if can_apply_lid(subcatchment, lid_process):
                    width = get_subcatchment_width(subcatchment)
                    add_lid_usage_to_subcatchment(file_path, [subcatchment], lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv)
                    converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": True, "LID Type": lid_process, "Width": width})
                    #print(f"Converted connected subcatchment: {subcatchment} to {lid_process} with width {width}.")
                else:
                    #print(f"{lid_process} cannot be applied to connected subcatchment: {subcatchment} due to constraints.")
                    converted_subcatchments.append({"Subcatchment": subcatchment, "Converted": False, "LID Type": lid_process, "Width": None})

    # Create a DataFrame from the list of converted subcatchments
    converted_subcatchments_df = pd.DataFrame(converted_subcatchments, columns=["Subcatchment", "Converted", "LID Type", "Width"])
    return converted_subcatchments_df

# Usage example
lid_process = 'Infiltration_Trench'
number = 1
area = 20
init_sat = 0
from_imp = 0
to_perv = 0
rpt_file = '*'
drain_to = '*'
from_perv = 0

# Call the function and capture the returned DataFrame
converted_infiltration_trench_df = apply_lid_to_subcatchments_if_needed(
    file_path, lid_process, number, area, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, calculations_df, infiltration_trench_list)

print(converted_infiltration_trench_df)
########################################################################################################################################### Using Pandas ExcelWriter to write each DataFrame to a different sheet in the same Excel file
# Check if the directory exists
directory = os.path.dirname(file_path4)
if not os.path.exists(directory):
    print(f"Directory does not exist: {directory}")
else:
    try:
        writer = pd.ExcelWriter(file_path4, engine='xlsxwriter')
        try:
            results_df.to_excel(writer, sheet_name='Results', index=False)
            totals_df.to_excel(writer, sheet_name='Totals', index=False)
            calculations_df.to_excel(writer, sheet_name='Calculations', index=False)
            converted_infiltration_trench_df.to_excel(writer, sheet_name='Converted Vegetative Swale', index=False)
        finally:
            writer.close()  # Ensure the writer is closed properly and the file is saved
        
        # Check if the file was created
        if os.path.exists(file_path4):
            print(f"Data successfully written to {file_path4}")
        else:
            print(f"Failed to write data to {file_path4}")
    except Exception as e:
        print(f"An error occurred: {e}")
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
########################################################################################################################################################
#MODEL RUN#########################################################################################################################################################
# Create and run the simulation specifying report and output files
with Simulation(file_path, rpt_file_path, out_file_path) as sim:
    sim.execute()
print("Simulation completed. Report and output files are saved.")
#ETRACTION OF INFORMATIONS #########################################################################################################################################################
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
#########################################################################################################################################################
# Save the DataFrame to an Excel file
#all_flooding_data.to_excel(excel_output_file_path, index_label='Index')
# Save the DataFrame to a CSV file
all_flooding_data.to_csv(csv_output_file_path, index_label='Index')
print("Data saved to csv and excel successfully.")
print(all_flooding_data)
#########################################################################################################################################################