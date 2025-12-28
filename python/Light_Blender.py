# Light_Blender.py
# Last modified: Dec 28, 2025
# V 0.1.3
# FG
# Update: Collapsible menus for each AOV and working Mute and Solo controls
# Light mixer tool based on modular building blocks on a different
# py file to edit each light and then add all of the together to
# reconstruct the beauty. Completely additive workflow.

import nuke
import os

#-----------------------------
#DEV toggle, to remove when publishing

DEV_FORCE_BLOCKS = False
DEV_BLOCK_COUNT = 6 # Lower it if Non-Commercial limitations

#-----------------------------

# -----------------------------
# Helper functions
# -----------------------------
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


# -----------------------------
# Paste a single AOV block
# -----------------------------
# CHANGE THE USER NAME !!!!!! === TO ADD AN AUTOMATIC USER NAME DETECTION ===
BLOCK_PATH = r"C:\Users\ArguruAdmin\.nuke\python\Light_Blender_BuildingBlocks\bb_rgba_default.nk"

# -----------------------------
# Layout multiple blocks horizontally and connect with Merge plus
# -----------------------------
def layout_blocks(aovs, grp):
    """
    Build and wire Light Blender blocks inside the group.
    Currently NC-safe: assumes only 1 AOV.
    """

    grp.begin()
    try:
        # --- Locate Group IO nodes ONCE ---
        group_input = nuke.toNode("Input1")
        group_output = nuke.toNode("Output1")

        if not group_input or not group_output:
            raise RuntimeError("Group Input/Output nodes not found")

        # -----------------------------
        # Layout constants
        # -----------------------------
        PIPE_Y = -120
        PIPE_START_X = -200
        PIPE_SPACING = 600

        BLOCK_Y = 40
        MERGE_Y = 22

        OUTPUT_OFFSET_X = 300

        # Position group inputs
        group_input.setXYpos(PIPE_START_X - 200, PIPE_Y)

        # -----------------------------
        # Build horizontal input pipe
        # -----------------------------
        pipe_dots = []
        pipe_source = group_input

        for i in range(len(aovs)):
            dot = nuke.nodes.Dot()
            dot.setInput(0, pipe_source)
            dot.setXYpos(PIPE_START_X + i * PIPE_SPACING, PIPE_Y)

            pipe_dots.append(dot)
            pipe_source = dot

        # Prepare for merge chaining
        previous_merge = None

        # --- Loop over AOVs (currently 1 due to NC limit) ---
        for i, aov in enumerate(aovs):

            # --- STEP 0: Clear selection (very important) ---
            for n in nuke.selectedNodes():
                n.setSelected(False)

            # --- STEP 1: Paste building block ---
            bb_path = r"C:\Users\ArguruAdmin\.nuke\python\Light_Blender_BuildingBlocks\bb_rgba_default.nk"
            nuke.nodePaste(bb_path)

            # EVERYTHING BELOW THIS LINE RELATES TO THE PASTED BLOCK
            # =====================================================

            # --- STEP 1a: Collect pasted nodes ---
            pasted_nodes = nuke.selectedNodes()
            if not pasted_nodes:
                raise RuntimeError("No nodes were pasted")

            # --- Exposure expression linking ---
            exposure_node = None
            for n in pasted_nodes:
                if n.Class() == "EXPTool" and "Exposure_RGB" in n.name():
                    exposure_node = n
                    break

            if exposure_node:
                knob_name = f"{aov}_exposure"
                exposure_node["red"].setExpression(f"parent.{knob_name}")
                exposure_node["green"].setExpression(f"parent.{knob_name}")
                exposure_node["blue"].setExpression(f"parent.{knob_name}")
                exposure_node["name"].setValue(f"Exposure_{aov}")

            # --- Mute / Solo multiply expression linking ---
            for n in pasted_nodes:
                if n.Class() == "Multiply" and n.name().endswith("_RGB"):

                    # Build Nuke-safe any-solo expression
                    any_solo_expr = " || ".join(
                        [f"parent.{other}_solo" for other in aovs]
                    )

                    gain_expr = (
                        f"({any_solo_expr}) ? "
                        f"(parent.{aov}_solo ? 1 : 0) : "
                        f"(parent.{aov}_mute ? 0 : 1)"
                    )

                    n["value"].setExpression(gain_expr)
                    n["name"].setValue(f"Multiply_{aov}")

            # --- STEP 1b: Find DotIn / DotOut ---
            dot_in = None
            dot_out = None

            for n in pasted_nodes:
                if n.Class() == "Dot":
                    if n.name().startswith("DotIn"):
                        dot_in = n
                    elif n.name().startswith("DotOut"):
                        dot_out = n

            if not dot_in or not dot_out:
                raise RuntimeError("Building block missing DotIn or DotOut")

            # --- Sanitize DotIn: remove any existing connections ---
            while dot_in.inputs():
                dot_in.setInput(0, None)

            # Ensure Shuffle is only driven by DotIn
            for n in pasted_nodes:
                if n.Class() == "Shuffle2":
                    n.setInput(0, dot_in)

                    # Set input layer (RGBA_<AOV>)
                    if "in1" in n.knobs():
                        n["in1"].setValue(aov)

            # --- STEP 2: Connect FIRST block to Group Input ---
            # (Because this is the first and only block for now)
            dot_in.setInput(0, pipe_dots[i])


            # --- STEP 3: Rename block elements to match AOV ---
            dot_in.setName(f"DotIn_{aov}")
            dot_out.setName(f"DotOut_{aov}")

            # --- STEP 4: Anchor block under its pipe dot ---
            anchor_x = pipe_dots[i].xpos()
            anchor_y = BLOCK_Y

            dx = anchor_x - dot_in.xpos()
            dy = anchor_y - dot_in.ypos()

            for n in pasted_nodes:
                n.setXYpos(n.xpos() + dx, n.ypos() + dy)

            # -----------------------------
            # Merge logic
            # -----------------------------
            MERGE_OFFSET_Y = 120
            MERGE_X_OFFSET = -34
            OUTPUT_OFFSET_Y = 200
            OUTPUT_OFFSET_X = -34

            if i == 0:
                previous_merge = dot_out
            else:
                merge = nuke.nodes.Merge2(operation="plus")

                merge.setXYpos(
                    dot_out.xpos() + MERGE_X_OFFSET,
                    dot_out.ypos() + MERGE_OFFSET_Y
                )

                merge.setInput(0, previous_merge)  # A = accumulated
                merge.setInput(1, dot_out)         # B = this AOV

                merge.setName(f"Merge_{aov}")
                previous_merge = merge

        # -----------------------------
        # RGBA branch output dot
        # -----------------------------
        RGBA_OUT_OFFSET_Y = 80
        RGBA_OUT_OFFSET_X = 34

        rgba_out_dot = nuke.nodes.Dot()
        rgba_out_dot.setInput(0, previous_merge)

        rgba_out_dot.setXYpos(
            previous_merge.xpos() + RGBA_OUT_OFFSET_X,
            previous_merge.ypos() + RGBA_OUT_OFFSET_Y
        )

        rgba_out_dot.setName("RGBA_OUT")
        rgba_out_dot["label"].setValue("RGBA_OUT")

        # -----------------------------
        # Final output connection
        # -----------------------------
        group_output.setInput(0, rgba_out_dot)
        group_output.setXYpos(
            rgba_out_dot.xpos() + OUTPUT_OFFSET_X,
            rgba_out_dot.ypos() + OUTPUT_OFFSET_Y
        )


    finally:
        grp.end()

# -----------------------------
# Build button callback
# -----------------------------
def build_from_read(grp):
    #Sanity check next line
    print("BUILD CALLED WITH:", grp, type(grp))
    try:
        input_node = get_input_node(grp)

        prefix = "RGBA_"
        aovs = extract_aovs(input_node, prefix)

        # --- DEV: force multiple blocks for layout testing START ---
        if DEV_FORCE_BLOCKS:
            aovs = [f"RGBA_DEV_{i}" for i in range(DEV_BLOCK_COUNT)]
        # --- DEV: force multiple blocks for layout testing END ---

        if not aovs:
            nuke.message(f"No AOVs found with prefix: {prefix}")
            return

        store_aovs(grp, aovs)
        build_light_controls_ui(grp, aovs)
        layout_blocks(aovs, grp)

        # Hide build button after successful build
        if "build" in grp.knobs():
            grp["build"].setVisible(False)

        nuke.message(f"Pasted {len(aovs)} RGBA blocks.")

    except Exception as e:
        nuke.message(str(e))

# -----------------------------
# Build Light Controls UI
# -----------------------------
def build_light_controls_ui(grp, aovs, prefix="RGBA_"):

    # Prevent rebuilding
    ui_built = "_light_controls_built" in grp.knobs()

    if not ui_built:
        marker = nuke.String_Knob("_light_controls_built", "")
        marker.setVisible(False)
        grp.addKnob(marker)

    # -----------------------------
    # Section header (single line)
    # -----------------------------
    header = nuke.Text_Knob(
        "light_controls_header",
        "",
        "<b>Light Controls</b>"
    )
    header.setFlag(nuke.STARTLINE)
    grp.addKnob(header)

    # -----------------------------
    # One collapsible group per AOV
    # -----------------------------
    solo_expr_terms = []

    for i, aov in enumerate(aovs):
        clean_name = aov.replace(prefix, "", 1)

        # ---- Begin collapsible group (expanded by default) ----
        begin = nuke.Tab_Knob(
            f"light_group_{i}",
            clean_name,
            1 # Expanded by default
        )
        grp.addKnob(begin)

        # ---- Exposure ----
        exp_knob = nuke.Double_Knob(
            f"{aov}_exposure",
            "Exposure"
        )
        exp_knob.setRange(-5, 5)
        exp_knob.setValue(0.0)
        grp.addKnob(exp_knob)

        # ---- Mute / Solo ----
        mute_knob = nuke.Boolean_Knob(f"{aov}_mute", "Mute")
        solo_knob = nuke.Boolean_Knob(f"{aov}_solo", "Solo")

        grp.addKnob(mute_knob)
        grp.addKnob(solo_knob)

        #solo_knob.setFlag(nuke.STARTLINE)

        solo_expr_terms.append(f"{aov}_solo")

        # ---- End group ----
        end = nuke.Tab_Knob(
            f"light_group_{i}_end", "", -1)
        grp.addKnob(end)

# -----------------------------
# Main create() function
# -----------------------------
def create():
    grp = nuke.nodes.Group(name="Light_Blender")

    # ---- DEV VISUALS ----
    grp["label"].setValue("DEV\nLight_Blender")
    grp["tile_color"].setValue(0x265DB2FF)
    grp["note_font_color"].setValue(0xFFFFFFFF)

    grp.begin()
    try:
        input_node = nuke.nodes.Input(name="Input1")
        output_node = nuke.nodes.Output(name="Output1")
        output_node.setInput(0, input_node)
        input_node.setXYpos(0, 0)
        output_node.setXYpos(0, 100)
    finally:
        grp.end()

    # ---- USER INTERFACE ----
    grp.addKnob(nuke.Tab_Knob("light_blender", "Light Blender"))
    build_btn = nuke.PyScript_Knob("build", "Build From Read")
    build_btn = nuke.PyScript_Knob(
        "build",
        "Build From Read",
        "import nuke, Light_Blender; Light_Blender.build_from_read(nuke.thisNode())"
    )
    grp.addKnob(build_btn)

    return grp
