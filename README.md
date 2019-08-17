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

# The configuration file, ```config.py```

# Creating a reference mask

The reference mask is a two-dimensional arrays of 

# Design principles

1. **Use open source tools whenever possible**. The only exceptions should be closed-source drivers for AO components such as cameras and deformable mirrors.

2. **Use human-readable configuration, initialization, and log files.** Whenever possible, use plain text files, along with delimiters. Configuration and initialization files should be written in Python whenever possible.
