# TUI3

Apache Point Observatory now offers TUI with full Python 3.x support. Users are encouraged to upgrade their system to the most recent version of Python 3.x. Support for TUI v2.6.0 and earlier has been discontinued.


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

The Windows command line is accessed from the Start Menu and typing "cmd", then clicking the "Command Prompt" application.


### Required Python Packages

TUI 3.x needs the following packages to run:

	* astropy
	* matplotlib
	* numpy
	* pillow
	* pyobjc (MacOS only)
	* pywin32 (Windows only)

From a commandline, do the following command: ```pip install astropy matplotlib numpy pillow```.

On some platforms, administrative privileges are needed to do a system-wide package install. In these cases, it's OK to run ```pip install --user <package names here>```.

On some Windows platforms, ```pip``` can be executed by doing ```py -m pip install <package names here>``` from the Windows command line. However, most of the time the aforementioned commands will work.

Most Python distributions include pre-compiled TclTk support, but not always. Double check to make sure the package ```tkinter``` is installed and available to Python by doing ```python -m tkinter```. If not, consult your OS documentation to resolve the issue.


### Optional Packages

The following Python Packages and external software are optional, but increase the functionality of TUI3. Those are:

	* The Python pygame package
	* SAOImageDS9
	* XPA Library

If standard TUI sound output is desired, then install ```pygame``` by doing a ```pip install pygame``` from the command line. Note that for Mac and Linux platforms, the installation of ```pygame``` is required by the ```setup.py``` script.


## Install TUI3

### Download a Current Release from GitHub

Open a browser and go to [the TUI3 repo](https://github.com/ApachePointObservatory/TUI3). Select the most recent source release in the upper-corner, and then download a zip file. Unzip to a suitable source directory.

If you have the git command line interface installed, navigate to a suitable source directory and do a ```git clone --branch <most recent release> https://github.com/ApachePointObservatory/TUI3.git```.


### Linux

In your terminal window, navigate to the newly created TUI3 directory and issue the command ```python setup.py install```. Issue the command ```runtuiWithLog.py``` or ```runtui.py``` to run TUI.

Note that superuser privileges are needed to do a system-wide installation (recommended).

If your user account doesn't have administrative privileges, TUI3 can be installed in user context by appending the ```--prefix <path to your desired user installation of TUI>``` to the end of the aforementioned installation command. TUI's installation path will then need to be added to the ```PYTHONPATH``` environment variable.


### MacOS

From the TUI3 root directory, do ```python setup.py py2app```. A ```dmg``` image will be created in the ```dist/``` directory. Navigate to that file, open it, and drag-and-drop the TUI.app object into the Applications Folder in Finder. TUI3 should now be available in Finder.


### Windows

From the command prompt, navigate to the TUI3 directory and run ```python setup.py install```. The TUI3 executable should be installed in ```C:\Users\<your user directory>\AppData\Local\Programs\Python\Python<version>\Scripts\runtui.exe```. Navigate to it in File Explorer, right-click ```runtui.exe``` and click "Send to -> Desktop (create shortcut)". The resulting desktop shortcut can be double-clicked to run TUI3.


## Known Bugs

Below is a list of known bugs:

	* A suspected race condition exists when attempting to authenticate the TUI session on the APO Servers. This condition is most frequently encountered when the local session is connects via an ethernet interface as opposed to a wireless interface. "Cancel" the connection, and click "Connect" again, and continue to repeat until the connection succeeds.


## Bug Reporting

We want to hear from you! Contact us if you find a bug.
