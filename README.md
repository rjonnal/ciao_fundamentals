# CIAO: community-inspired adaptive optics
Python tools for controlling, simulating, and characterizing adaptive optics (AO) systems

# Setup and installation

1. Install [Notepad++](https://notepad-plus-plus.org/download)
2. Install [Git](https://git-scm.com/download/win)
3. Install [Anaconda for Python 2.7](https://www.anaconda.com/distribution/#download-section)
4. Install Alpao drivers
5. Clone this repository
6. Install the [Visual C++ compiler for Python 2.7](https://www.microsoft.com/en-us/download/details.aspx?id=44266)
7. Install [Basler Pylon 5.2](https://www.baslerweb.com/en/sales-support/downloads/software-downloads/pylon-5-2-0-windows/)
8. Install [pypylon](https://github.com/basler/pypylon/releases/download/1.4.0/pypylon-1.4.0-cp27-cp27m-win_amd64.whl). First download, then use 'pip install pypylon...amd64.whl'.

# 

# The configuration file, ```config.py```



# Creating mask files

The reference mask is a two-dimensional arrays of zeros and ones which specifies which of the Shack-Hartmann lenslets to use. The mirror mask specifies, similarly, the logical locations of active mirror actuators. 

The program ```ciao/calibration/make_mask.py``` can be used to generate both mask files. Premade masks can be found in ```ciao/calibration/example_masks/```.

The program is run at the command line using ```python make_mask.py N rad mask_filename.txt```, where ```N``` specifies the size of the (square) mask, ```rad``` specifies the radius of the inscribed active area, and ```mask_filename.txt``` is the file in which to store the output.

# Design principles

1. **Use open source tools whenever possible**. The only exceptions should be closed-source drivers for AO components such as cameras and deformable mirrors.

2. **Use human-readable configuration, initialization, and log files.** Whenever possible, use plain text files, along with delimiters. Configuration and initialization files should be written in Python whenever possible.

# Topics for conversation

1. Other than condition number, what algorithmic or numerical tests can be employed to predict the performance of a given poke/control matrix?

2. What rules of thumb should be employed when deciding whether a spot should be used? Put differently, how should one choose ```rad``` when generating a SHWS mask, as described above?
