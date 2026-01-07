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


#=================================
#    ==== Arguru Tools ====
import nuke
import sys

try:
    from importlib import reload
except ImportError:
    pass


def create_light_blender():
    import Light_Blender

    # DEV ONLY: auto-reload on every invocation
    if "Light_Blender" in sys.modules:
        try:
            reload(Light_Blender)
            print("Light_Blender reloaded")
        except Exception as e:
            nuke.message(
                "Failed to reload Light_Blender:\n\n{}".format(e)
            )
            return

    Light_Blender.create()


# -------------------------
# Main menu
# -------------------------
arguru_menu = nuke.menu("Nuke").addMenu("Arguru")
arguru_menu.addCommand(
    "Light_Blender",
    "create_light_blender()",
    icon="Group.png"
)

# -------------------------
# Tab / Nodes menu
# -------------------------
nodes_menu = nuke.menu("Nodes")

# Optional: create Arguru category in Tab menu
arguru_nodes = nodes_menu.addMenu("Arguru")

arguru_nodes.addCommand(
    "Light_Blender",
    "create_light_blender()",
    icon="Group.png"
)
