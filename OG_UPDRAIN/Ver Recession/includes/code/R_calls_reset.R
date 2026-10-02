#### Section Title ####

library(reticulate)

# Specify the Python environment
use_python("C:/Users/mpa010/AppData/Local/anaconda/python.exe")

# Define the Python script path
python_script <- "C:/Users/mpa010/Desktop/Thesis/Software/GAMA/Impacts Workshop/includes/code/Reset.py"

# Run the Python script
py_run_file(python_script)
