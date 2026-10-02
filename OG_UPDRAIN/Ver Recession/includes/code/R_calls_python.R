#### Section Title ####
library(reticulate)
# Specify the Python environment
use_python("C:/Users/Diego/miniforge3/envs/swmmgis")
# Define the Python script path
python_script <- "C:/Users/Diego/Gama_Workspace/IAHR/includes/code/SWMM.py"
# Run the Python script
py_run_file(python_script)