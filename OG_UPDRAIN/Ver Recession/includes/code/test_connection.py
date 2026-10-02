#=====================================================================================================
import pyswmm
import swmmio
import swmmtoolbox.swmmtoolbox as swmmtoolbox
from swmm.toolkit import solver
from swmm_api.input_file import read_inp_file, section_labels as sections
from swmm_api.input_file.sections import RainGage
#--------------------------
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import math
import re
import os
import asyncio
import shutil
import networkx as nx
import plotly.graph_objs as go
#--------------------------
from io import StringIO
from swmmio import Model
from pyswmm import Simulation
from pyswmm import Subcatchments
from pyswmm import Links
from pyswmm import Nodes
from datetime import datetime
from pandas.plotting import table
from collections import defaultdict
#=====================================================================================================
# Function to read the SWMM input file
def read_inp_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()
    return lines
# Paths to the original and backup files
file_path = r"C:\Users\mpa010\Desktop\SWMM\MS5 (Smaller model)\SWMM model\MS6.inp"
# Function to write to the SWMM input file
def write_inp_file(file_path, lines):
    with open(file_path, 'w') as file:
        file.writelines(lines)


# Read the original file
sections = read_inp_file(file_path)
#=====================================================================================================
backup_file_path = r"C:\Users\mpa010\Desktop\SWMM\MS5 (Smaller model)\SWMM model\MS6_backup.inp"

#RESET THE MODEL TO THE INITIAL STATE
# Function to reset the model to the original configuration
def reset_model_to_original():
    shutil.copyfile(backup_file_path, file_path)
    print("Model has been reset to the original configuration.")

# At the end of your work, call this function to restore the original model
reset_model_to_original()
#=======================================SECTIONS==================================================
#==================================================================================================
import pandas as pd

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
#======================================================================================================================
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
#================================================================================================================================================
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

  # Replace with your actual file path

subcatchment_frame = extract_subcatchments(file_path)
polygon_frame = extract_polygons(file_path)

subcatchment_complete = merge_subcatchments_and_polygons(subcatchment_frame, polygon_frame)
first_row_df = subcatchment_complete.to_string()
print(first_row_df)

#======================================================================================================================================
#==============================================================LIDS===================================================================
# Lists of subcatchments to convert
#green_roofs = ['Roof_s3854', 'Roof_s3254']
#infiltration_trench_list = ['Street_s1973', 'Street_s1352']
# Initialize the results DataFrame

#ADDITIONAL PART TO FACILITATE THE CONVERSION=====================================================================
infiltration_trench_list = pd.read_csv('../includes/infiltration_swale_subcatchments.csv')['x'].tolist()
#================================================================================================================

results_df = pd.DataFrame(columns=["Initial Subcatchment", "Direct Subcatchments", "Nested Subcatchments"])

# Define a function to process a given subcatchment and its connected subcatchments
def process_subcatchment(subcatchment_of_interest):
    print(f"Processing subcatchment: {subcatchment_of_interest}")
    
    # Retrieve direct subcatchments connected to the subcatchment of interest
    direct_subcatchments = subcatchment_frame[subcatchment_frame['Outlet'] == subcatchment_of_interest]['Subcatchment'].tolist()
    print(f"Direct subcatchments for {subcatchment_of_interest}: {direct_subcatchments}")
    
    # Initialize a list to store all nested subcatchments
    nested_subcatchments = []

    # Function to recursively find all nested subcatchments
    def find_nested_subcatchments(subcatchments):
        for subcatchment in subcatchments:
            # Retrieve subcatchments where the current subcatchment is the outlet
            current_nested = subcatchment_frame[subcatchment_frame['Outlet'] == subcatchment]['Subcatchment'].tolist()
            # Add to the nested subcatchments list
            nested_subcatchments.extend(current_nested)
            # Recurse on the newly found subcatchments
            find_nested_subcatchments(current_nested)

    # Start the recursion with the direct subcatchments
    find_nested_subcatchments(direct_subcatchments)

    # Remove duplicates from the nested subcatchments list
    nested_subcatchments = list(set(nested_subcatchments))

    # Append the results to the DataFrame
    results_df.loc[len(results_df)] = [subcatchment_of_interest, direct_subcatchments, nested_subcatchments]

# Process each subcatchment in the list
for subcatchment in infiltration_trench_list:
    process_subcatchment(subcatchment)

# Print the results DataFrame
print(results_df)

#==================================================================================================================

#----------------------------------------------INFILTRATION TRENCH ANALYSIS----------------------------
# Define a dictionary for ψm values based on land use type
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

# Create an empty dataframe for an infiltration trench
infiltration_trench = pd.DataFrame(columns=["Name", "A (m2)", "% Imp.", "% Perv.", "ψm Imp.", "ψm perv.", "AE imp.", "AE perv.", "Ared imp.", "Ared perv.", "Ared"])

# Function to add subcatchments to infiltration trench dataframe
def add_subcatchment_to_dataframe(subcatchment, dataframe):
    # Retrieve area and impervious percentage for the subcatchment
    area_ha = subcatchment_frame.loc[subcatchment_frame['Subcatchment'] == subcatchment, 'Area'].values[0]
    area_m2 = float(area_ha) * 10000  # Convert from hectares to square meters
    imperv = subcatchment_frame.loc[subcatchment_frame['Subcatchment'] == subcatchment, 'Imperv%'].values[0]
    imperv = float(imperv)
    perv = 100 - imperv

    # Determine ψm values based on subcatchment name
    psi_m = get_psi_m(subcatchment)
    if psi_m is None:
        raise ValueError(f"No ψm value found for subcatchment: {subcatchment}")

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

    # Create an empty dataframe for each subcatchment's infiltration trench
    infiltration_trench = pd.DataFrame(columns=["Name", "A (m2)", "% Imp.", "% Perv.", "ψm Imp.", "ψm perv.", "AE imp.", "AE perv.", "Ared imp.", "Ared perv.", "Ared"])
    
    # Combine both direct and nested subcatchments
    all_subcatchments = row["Direct Subcatchments"] + row["Nested Subcatchments"]
    unique_subcatchments = set(all_subcatchments)  # Remove duplicates

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
# Print the totals DataFrame
print(totals_df)

#======================================================
# Load the data from the Excel file
timeseries_df = pd.read_excel(r'C:\Users\mpa010\Desktop\design\timeseries.xlsx')

# Define constants
kf = 0.00010  # m/s
fA = 1
fZ = 1.2
A_P_min = 50  # Minimum percolation area in m²
A_P_max = 100  # Maximum percolation area in m²
A_P_mean = (A_P_min + A_P_max) / 2
DesignA = A_P_mean

# Create a DataFrame to store the results for each subcatchment
results_summary = []

# Iterate through each row in the totals_df
for index, row in totals_df.iterrows():
    subcatchment_name = row['Subcatchment']
    total_ared = row['Ared total']

    # Make a copy of the original DataFrame for calculations
    infiltration_trench_df = timeseries_df.copy()

    # Perform calculations and create new columns in the copy of the DataFrame
    infiltration_trench_df['qln'] = infiltration_trench_df['Intensity [mm/min]'] * kf
    infiltration_trench_df['Vin [m3]'] = (total_ared + DesignA) * infiltration_trench_df['Intensity [m3/min]'] * infiltration_trench_df['T [min]']
    infiltration_trench_df['Vout [m3]'] = (60 * DesignA) * infiltration_trench_df['T [min]'] * (kf/2)
    infiltration_trench_df['Storage Volume'] = (infiltration_trench_df['Vin [m3]'] - infiltration_trench_df['Vout [m3]']) * fA * fZ
    infiltration_trench_df['hmax [m]'] = (infiltration_trench_df['Storage Volume'] / DesignA)
    infiltration_trench_df['t hempty [h]'] = (infiltration_trench_df['hmax [m]'] / (kf / 2)) / 60

    # Define the conditions
    max_hmax = 0.30  # Maximum value for hmax
    max_t_empty = 24  # Maximum value for t empty in hours

    # Check the conditions
    hmax_condition = (infiltration_trench_df['hmax [m]'] < max_hmax).all()
    t_empty_condition = (infiltration_trench_df['t hempty [h]'] < max_t_empty).all()

    # Collect results for the current subcatchment
    subcatchment_result = {
        'Subcatchment': subcatchment_name,
        'hmax_condition': hmax_condition,
        't_empty_condition': t_empty_condition,
        'LID_necessity': not (hmax_condition and t_empty_condition),
        'Details': infiltration_trench_df
    }

    # Append the results to the summary list
    results_summary.append(subcatchment_result)

    # Print the results for the current subcatchment
    print(f"Results for subcatchment: {subcatchment_name}")
    if hmax_condition:
        print("The condition for hmax [m] is respected.")
    else:
        print("The condition for hmax [m] is NOT respected.")

    if t_empty_condition:
        print("The condition for t empty [h] is respected.")
    else:
        print("The condition for t empty [h] is NOT respected.")

    if not hmax_condition or not t_empty_condition:
        print("There is a necessity to convert to LID all the nested subcatchments.")
    print("\n")

# Display the summary DataFrame
for result in results_summary:
    print(f"Results for subcatchment: {result['Subcatchment']}")
    print(f"hmax condition respected: {result['hmax_condition']}")
    print(f"t empty condition respected: {result['t_empty_condition']}")
    if result['LID_necessity']:
        print("There is a necessity to convert to LID all the nested subcatchments.")
    print(result['Details'])
    print("\n")


#===============================================================================================================================================

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
    
    # Prepare the new LID_USAGE entries
    new_lid_usages = []
    for subcatchment_name in subcatchment_names:
        # Check constraints for applying LID usage
        subcatchment_upper = subcatchment_name.upper()
        if lid_process == 'Green_Roof':
            if 'ROOF' not in subcatchment_upper:
                print(f"Error: Green Roof solutions can only be applied to Roof subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Bio_Retention':
            if 'STREET' not in subcatchment_upper and 'VEGETATION' not in subcatchment_upper:
                print(f"Error: Bio-Retention solutions can only be applied to Street or Vegetation subcatchments. Skipping {subcatchment_name}.")
                continue
        elif lid_process == 'Vegetation_Swale':
            if 'STREET' not in subcatchment_upper and 'VEGETATION' not in subcatchment_upper:
                print(f"Error: Vegetation Swale solutions can only be applied to Street or Vegetation subcatchments. Skipping {subcatchment_name}.")
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
    elif lid_process == 'Bio_Retention':
        return 'STREET' in subcatchment_upper or 'VEGETATION' in subcatchment_upper
    elif lid_process == 'Vegetation_Swale':
        return 'STREET' in subcatchment_upper or 'VEGETATION' in subcatchment_upper
    elif lid_process == 'Infiltration_Trench':
        return any(x in subcatchment_upper for x in ['STREET', 'VEGETATION', 'STONE'])
    else:
        print(f"Warning: Unknown LID process '{lid_process}'. No LID will be applied.")
        return False


# Updated apply_lid_to_subcatchments_if_needed function
def apply_lid_to_subcatchments_if_needed(file_path, lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, results_df, infiltration_trench_list):
    all_subcatchments = set()
    for idx, row in results_df.iterrows():
        all_subcatchments.update(row['Direct Subcatchments'])
        all_subcatchments.update(row['Nested Subcatchments'])
    initial_subcatchment = results_df.iloc[0]['Initial Subcatchment']
    all_subcatchments.discard(initial_subcatchment)
    
    # Convert subcatchments in infiltration_trench_list to Infiltration Trench LID
    for subcatchment in infiltration_trench_list:
        if can_apply_lid(subcatchment, lid_process):
            add_lid_usage_to_subcatchment(file_path, [subcatchment], lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv)
            print(f"Converted subcatchment: {subcatchment} to {lid_process}.")
        else:
            print(f"{lid_process} cannot be applied to subcatchment: {subcatchment} due to constraints. Converting nested subcatchments.")
            # Retrieve nested subcatchments and convert them
            nested_subcatchments = results_df.loc[results_df['Initial Subcatchment'] == subcatchment, 'Nested Subcatchments'].iloc[0]
            nested_subcatchments.append(subcatchment)  # Include the current subcatchment
            for nested_sub in nested_subcatchments:
                if can_apply_lid(nested_sub, lid_process):
                    add_lid_usage_to_subcatchment(file_path, [nested_sub], lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv)
                    print(f"Converted nested subcatchment: {nested_sub} to {lid_process}.")
                else:
                    print(f"{lid_process} cannot be applied to nested subcatchment: {nested_sub} due to constraints.")

    # Check all subcatchments for LID application based on conditions
    subcatchments_to_apply_lid = []
    for subcatchment in all_subcatchments:
        if subcatchment in infiltration_trench_list:
            continue  # Skip already processed subcatchments
        if can_apply_lid(subcatchment, lid_process):
            subcatchments_to_apply_lid.append(subcatchment)
        else:
            print(f"LID process: {lid_process} cannot be applied to subcatchment: {subcatchment} due to constraints.")
    
    if subcatchments_to_apply_lid:
        add_lid_usage_to_subcatchment(file_path, subcatchments_to_apply_lid, lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv)
        print(f"Adding new LID usages: {lid_process} for subcatchments: {subcatchments_to_apply_lid}.")
    else:
        print("No subcatchments found eligible for LID application based on constraints.")


# Usage example
lid_process = 'Infiltration_Trench'
number = 1
area = 100
width = 0
init_sat = 0
from_imp = 0
to_perv = 0
rpt_file = '*'
drain_to = '*'
from_perv = 0

apply_lid_to_subcatchments_if_needed(file_path, lid_process, number, area, width, init_sat, from_imp, to_perv, rpt_file, drain_to, from_perv, results_df, infiltration_trench_list)

#========================================================================================================================================================