#----------------------------------------------------------
# menu.py
# Version: 1.0.0
# Last Updated: Sept 15, 2025
#----------------------------------------------------------

import nuke
import platform
#import KnobScripter

# Define where .nuke directory is on each OS's network
Win_Dir = 'C:/Users/ArguruAdmin/.nuke'
Linux_Dir = '/home/arguru/.nuke'
MacOSX_Dir = ''

# Set global directory
system_os = platform.system()
if system_os == "Windows":
	dir = Win_Dir
elif system_os == "Linux":
	dir = Linux_Dir
elif system_os == "Darwin":
	dir = MacOSX_Dir
else:
	dir = None
