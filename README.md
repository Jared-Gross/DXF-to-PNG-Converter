# DXF to PNG Converter
This program can convert DXF files to image format with ease, with a GUI!

## Usage of the command-line interface
If the GUI is not required, one may run the application as follows:
```bash
python main.py --cli -i input.dxf -o output.png
```
Both input and output files are set relative to the script's root directory, i.e. should be located in the same directory.

## Setup with Anaconda
This assumes that you have the Conda package installed.
* Create a virtual environment: `conda env create --name dxf2png -f environment.yml`
* Activate the environment: `conda activate dxf2png`
* Run the program: `python main.py`
* Deactivate the environment when done: `conda deactivate`
