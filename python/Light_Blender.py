# Light_Blender.py
# Last modified: Jan 21, 2026
# V 0.1.7
# FG
# Update: Mute All button, unpremult and premult included along with
# alpha restore
# 
# 
# Light mixer tool based on modular building blocks on a different
# py file to edit each light and then add all of the together to
# reconstruct the beauty for a fully ADDITIVE WORKFLOW.

import nuke
import os

#-----------------------------
# Resolve user-specific paths (Multi OS)
#-----------------------------

USER_HOME = os.path.expanduser("~")

BLOCK_PATH = os.path.join(
    USER_HOME,
    ".nuke",
    "python",
    "Light_Blender_BuildingBlocks",
    "bb_rgba_default.nk"
)

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
        group_input = nuke.toNode("Unpremult1")
        group_output = nuke.toNode("Output1")
        input1 = nuke.toNode("Input1")

        # Keep Input1 aligned with Unpremult (visual cleanup)
        input1.setXYpos(
            group_input.xpos() - 100,
            group_input.ypos()
        )

        if not group_input or not group_output:
            raise RuntimeError("Group Input/Output nodes not found")

        # -----------------------------
        # Layout constants
        # -----------------------------
        PIPE_Y = -120
        PIPE_START_X = -200
        PIPE_SPACING = 600 # Temp value

        BLOCK_Y = 40
        MERGE_Y = 22

        OUTPUT_OFFSET_X = 300

        # Position group inputs
        group_input.setXYpos(PIPE_START_X - 200, PIPE_Y)

        # Align Input1 to Unpremult (this is the correct moment)
        input1.setXYpos(
            group_input.xpos() - 100,
            group_input.ypos()
        )

        # Keep Input2 (crypto / mask input) safely above Input1
        group_input2 = nuke.toNode("InputCrypto")
        if group_input2:
            group_input2.setXYpos(
                group_input.xpos(),
                group_input.ypos() - 80
            )

        # --- Paste template block to measure ---
        for n in nuke.selectedNodes():
            n.setSelected(False)

        before = set(nuke.allNodes())

        nuke.nodePaste(BLOCK_PATH)
        template_nodes = nuke.selectedNodes()

        after = set(nuke.allNodes())
        pasted_nodes = list(after - before)

        if not template_nodes:
            raise RuntimeError("Failed to paste template block")

        # Measure full footprint (including backdrops)
        min_x = min(n.xpos() for n in template_nodes)
        max_x = max(n.xpos() + n.screenWidth() for n in template_nodes)
        block_width = max_x - min_x

        # Optional vertical measure if needed later
        min_y = min(n.ypos() for n in template_nodes)

        BLOCK_PADDING = 200
        PIPE_SPACING = block_width + BLOCK_PADDING

        for n in template_nodes:
            nuke.delete(n)

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

            # --- STEP 1: Paste building block (selection-safe) ---
            for n in nuke.selectedNodes():
                n.setSelected(False)

            before = set(nuke.allNodes())
            nuke.nodePaste(BLOCK_PATH)
            after = set(nuke.allNodes())

            pasted_nodes = list(after - before)
            if not pasted_nodes:
                raise RuntimeError("No nodes were pasted")

            # EVERYTHING BELOW THIS LINE RELATES TO THE PASTED BLOCK
            # =====================================================

            # --- STEP 1a: Collect pasted nodes ---
            pasted_nodes = list(after - before)
            if not pasted_nodes:
                raise RuntimeError("No nodes were pasted")

            # --- STEP 1a.5: Assign AOV to Shuffle nodes ---
            for n in pasted_nodes:
                if n.Class() == "Shuffle2":
                    # Newer Nuke versions
                    if "in1" in n.knobs():
                        n["in1"].setValue(aov)
                    # Older Nuke versions
                    elif "in" in n.knobs():
                        n["in"].setValue(aov)

            # Compute block width once (after first paste)
            if i == 0:
                min_x = min(n.xpos() for n in pasted_nodes)
                max_x = max(n.xpos() for n in pasted_nodes)
                block_width = max_x - min_x
                PIPE_SPACING = block_width + 200

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

            # --- STEP 1b: Find DotIn / DotOut / DotCrypto ---
            dot_in = next(
                n for n in pasted_nodes
                if n.Class() == "Dot" and n.name().startswith("DotIn")
            )
            dot_out = None
            dot_crypto = None

            for n in pasted_nodes:
                if n.Class() == "Dot":
                    if n.name().startswith("DotIn"):
                        dot_in = n
                    elif n.name().startswith("DotOut"):
                        dot_out = n
                    elif n.name().startswith("DotCrypto"):
                        dot_crypto = n

            # --- Rename Multiply nodes per AOV ---
            for n in pasted_nodes:
                if n.Class() == "Multiply":
                    if n.name().endswith("_OnOff"):
                        n.setName(f"Multiply_OnOff_{aov}")
                    elif n.name().endswith("_Color"):
                        n.setName(f"Multiply_Color_{aov}")

            if not dot_in or not dot_out:
                raise RuntimeError("Building block missing DotIn or DotOut")

            # --- Sanitize DotIn: remove any existing connections ---
            while dot_in.inputs():
                dot_in.setInput(0, None)

            # --- STEP 2: Connect FIRST block to Group Input ---
            # Connect block input to its pipe dot
            dot_in.setInput(0, pipe_dots[i])
            # Connect DotCrypto
            dot_crypto.setInput(0, nuke.toNode("InputCrypto"))


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
        # HARD reset Output1
        # -----------------------------
        group_output.setInput(0, None)

        # -----------------------------
        # Alpha source dot
        # -----------------------------
        input_alpha = nuke.nodes.Dot(name="Input_Alpha")
        input_alpha.setInput(0, input1)
        input_alpha["hide_input"].setValue(True)

        # -----------------------------
        # Copy alpha
        # -----------------------------
        copy_alpha = nuke.nodes.Copy(name="Alpha_Restoration")
        copy_alpha.setInput(0, previous_merge)  # RGB
        copy_alpha.setInput(1, input_alpha)     # Alpha
        copy_alpha["from0"].setValue("alpha")
        copy_alpha["to0"].setValue("alpha")

        # -----------------------------
        # Premult
        # -----------------------------
        premult = nuke.nodes.Premult()
        premult.setInput(0, copy_alpha)

        # -----------------------------
        # Remove extra channels
        # -----------------------------
        remove = nuke.nodes.Remove()
        remove.setInput(0, premult)
        remove["operation"].setValue("keep")
        remove["channels"].setValue("rgba")

        # -----------------------------
        # FINAL RGBA OUT (ONLY ONE)
        # -----------------------------
        rgba_out_dot = nuke.nodes.Dot(name="RGBA_OUT")
        rgba_out_dot.setInput(0, remove)

        # -----------------------------
        # Group output
        # -----------------------------
        group_output.setInput(0, rgba_out_dot)
        group_output.setXYpos(
            rgba_out_dot.xpos() + OUTPUT_OFFSET_X,
            rgba_out_dot.ypos() + OUTPUT_OFFSET_Y
        )

        # -----------------------------
        # Cleanup: deselect everything inside the group
        # -----------------------------
        for n in nuke.allNodes():
            n.setSelected(False)

    finally:
        for n in nuke.allNodes():
            n.setSelected(False)

        grp.end()

# -----------------------------
# Build button callback
# -----------------------------
def build_from_read(grp):
    #Sanity check next line
    print("BUILD CALLED WITH:", grp, type(grp))
    try:
        input_node = get_input_node(grp)

        prefix = grp["aov_prefix"].value()
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
        assign_multiply_expressions(grp, aovs)

        # Hide build button after successful build
        if "build" in grp.knobs():
            grp["build"].setVisible(False)

        nuke.message(f"Pasted {len(aovs)} RGBA blocks.")

    except Exception as e:
        nuke.message(str(e))

# -----------------------------
# Mute All
# -----------------------------
def toggle_mute_all(grp):
    aovs = grp["_light_blender_aovs"].value().split(",")
    if not aovs or aovs == [""]:
        return

    # Determine current state
    any_unmuted = any(not grp[f"{aov}_mute"].value() for aov in aovs)

    for aov in aovs:
        grp[f"{aov}_mute"].setValue(1 if any_unmuted else 0)

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

        # Add color knob
        color_knob = nuke.Color_Knob(f"{aov}_color", "Color")
        color_knob.setValue([1.0, 1.0, 1.0])
        grp.addKnob(color_knob)

        # ---- End group ----
        end = nuke.Tab_Knob(
            f"light_group_{i}_end", "", -1)
        grp.addKnob(end)

def assign_multiply_expressions(grp, aovs):
    grp.begin()
    try:
        all_nodes = nuke.allNodes()

        for aov in aovs:
            any_solo_expr = " || ".join(
                [f"parent.{other}_solo" for other in aovs]
            )

            gain_expr = (
                f"({any_solo_expr}) ? "
                f"(parent.{aov}_solo ? 1 : 0) : "
                f"(parent.{aov}_mute ? 0 : 1)"
            )

            for n in all_nodes:
                if n.Class() != "Multiply":
                    continue

                if n.name() == f"Multiply_OnOff_{aov}":
                    n["value"].setExpression(gain_expr)

                elif n.name() == f"Multiply_Color_{aov}":
                    n["value"].setExpression(f"parent.{aov}_color")

    finally:
        grp.end()

# Deselect everything when creating the node
for n in nuke.allNodes():
            n.setSelected(False)

# -----------------------------
# Main create() function
# -----------------------------
def create():
    grp = nuke.nodes.Group(name="Light_Mixer")

    # ---- DEV VISUALS ----
    grp["label"].setValue("DEV")
    grp["tile_color"].setValue(0x265DB2FF)
    grp["note_font_color"].setValue(0xFFFFFFFF)

    grp.begin()
    try:
        input1 = nuke.nodes.Input(name="Input1")
        input2 = nuke.nodes.Input(name="InputCrypto")

        unpremult = nuke.nodes.Unpremult(name="Unpremult1")
        unpremult.setInput(0, input1)

        output_node = nuke.nodes.Output(name="Output1")

        # Layout
        input1.setXYpos(0, 0)
        input2.setXYpos(0, 80)
        unpremult.setXYpos(100, 0)
        output_node.setXYpos(0, 180)

    finally:
        grp.end()

    # ---- USER INTERFACE ----
    grp.addKnob(nuke.Tab_Knob("light_blender", "Light Blender"))
    prefix_knob = nuke.String_Knob("aov_prefix", "AOV Prefix")
    prefix_knob.setValue("Beauty_")
    grp.addKnob(prefix_knob)

    # Mute All button
    mute_all_btn = nuke.PyScript_Knob(
        "mute_all",
        "Mute / Unmute All",
        "import Light_Blender; Light_Blender.toggle_mute_all(nuke.thisNode())"
    )
    grp.addKnob(mute_all_btn)

    build_btn = nuke.PyScript_Knob("build", "Build From Read")
    build_btn = nuke.PyScript_Knob(
        "build",
        "Build From Read",
        "import nuke, Light_Blender; Light_Blender.build_from_read(nuke.thisNode())"
    )
    build_btn.setFlag(nuke.STARTLINE)
    grp.addKnob(build_btn)

    # -----------------------------
    # UI focus: select node and open properties
    # -----------------------------
    grp.setSelected(True)
    nuke.show(grp)

    return grp
