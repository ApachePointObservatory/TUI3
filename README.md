# TUI3

Apache Point Observatory now offers TUI with full Python 3.x support. Users are encouraged to upgrade their system to the most recent version of Python 3.x. Support for TUI v2.6.x and earlier has been discontinued.


## Use One of Our Pyinstaller-Bundled Executables!

	1) Find the Releases section on the right hand side of this GitHub Repo page.
	2) Select the most recent release.
	3) Find the approproate binary release for your platform and download it (disk image for Mac platforms).
	4) Run TUI by opening the downloaded binary consistently with your platform. Windows and Mac users can double-click, while Linux users should execute the binary in the terminal.


## Installation Prerequisites

### MacOS

Install the latest version of Python 3.x on your system from Python.org. Update the ```pip``` package by doing ```pip install --upgrade pip``` from the command line.


### Linux

Many modern Linux distributions have package-managing software. Use of those utilities is encouraged. Consult your distro's documentation for more information. Install Python 3.x on your system and update the ```pip``` package by doing ```pip install --upgrade pip``` from the command line.


### Windows

Download the latest version of Python 3.x from Python.org and install it on your system.


### Accessing a Command Line Terminal.

In MacOS, open Finder, and open the /Applications/Utilities folder, then double-click Terminal.

Linux window managers include a terminal as a standard application. For example, GNOME Terminal can be accessed by hitting the Super Key, then typing "Terminal", and clicking the application icon.

Users may use PowerShell on Windows platforms. Also, the Windows command line is accessed from the Start Menu and typing "cmd", then clicking the "Command Prompt" application.


### Required Python Packages

The new ```pip``` installation method for this package should download and install dependencies automatically. Have a look at the ```pyproject.toml``` file to review those dependencies.

### Optional Packages

The following Python Packages and external software are optional, but increase the functionality of TUI3. Those are:

	* The Python pygame package
	* SAOImageDS9
	* XPA Library (unavailable for Windows)

If standard TUI sound output is desired, then install ```pygame``` by doing a ```pip install pygame``` from the command line. Note that for Mac and Linux platforms, the installation of ```pygame``` is required by the ```setup.py``` script.


## Install TUI3

If you have the git command line interface installed, navigate to a suitable source directory and do a ```git clone --branch <most recent release> --recurse-submodules https://github.com/ApachePointObservatory/TUI3.git```.

If you don't have git tools installed, open a browser and go to [the TUI3 repo](https://github.com/ApachePointObservatory/TUI3). Select the most recent source release in the upper-corner, and then download a zip file. Unzip to a suitable source directory.

[Download the RO package](https://github.com/ApachePointObservatory/RO3) and place it in the ```TUI3``` directory. Make sure that the top-level directory of the RO package is named ```RO``` (not RO3).

Next, do a ```cd TUI3``` followed by ```pip install .```.

Type ```tui``` into the command line to run TUI.

## Bug Reporting

We want to hear from you! Post an Issue on the issues tab if you find a bug.
