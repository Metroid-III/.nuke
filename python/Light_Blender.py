# Light_Blender.py
# Last modified: Dec 26, 2025
# V 0.1.0
# Light mixer tool based on modular building blocks on a different
# py file to edit each light and then add all of the together to
# reconstruct the beauty. Completely additive workflow.

import nuke
import os


def get_input_node(group):
    node = group.input(0)
    if not node:
        raise RuntimeError("Light_Blender: No node connected to input")
    return node


def extract_aovs(node, prefix):
    layers = set()
    for ch in node.channels():
        layer = ch.split(".")[0]
        if layer.startswith(prefix):
            layers.add(layer)
    return sorted(layers)


def store_aovs(group, aov_list):
    knob_name = "_light_blender_aovs"
    if knob_name not in group.knobs():
        k = nuke.String_Knob(knob_name, "")
        k.setVisible(False)
        group.addKnob(k)
    group[knob_name].setValue(",".join(aov_list))


def create():
    # Create the group node
    grp = nuke.nodes.Group(name="Light_Blender")

    # Enter the group context
    grp.begin()
    # ---- DEV VISUAL IDENTIFICATION ----

    # DEV label
    grp["label"].setValue("DEV\nLight_Blender")

    # Tile color
    grp["tile_color"].setValue(0x265DB2FF)

    # White label font
    grp["note_font_color"].setValue(0xFFFFFFFF)


    try:
        # Input and Output nodes
        input_node = nuke.nodes.Input(name="Input1")
        output_node = nuke.nodes.Output(name="Output1")

        # Basic connection
        output_node.setInput(0, input_node)

        # Layout
        input_node.setXYpos(0, 0)
        output_node.setXYpos(0, 100)

    finally:
        # Always exit the group context
        grp.end()

    # ---- USER INTERFACE ----

    # Tab for clarity
    grp.addKnob(nuke.Tab_Knob("light_blender", "Light Blender"))

    # Python button (placeholder logic)
    build_btn = nuke.PyScript_Knob(
        "build",
        "Build From Read",
        "print('Light_Blender build button pressed')"
    )

    grp.addKnob(build_btn)

    return grp
