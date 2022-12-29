import bpy
from bl_ui.space_node import NODE_HT_header, NODE_MT_editor_menus
from .. core import RENDERER_BL_IDNAME

original_draw = None

def IR_mat_template_ID(layout, material):
    row = layout.row(align=True)
    row.operator("blendigo.material_select", icon='MATERIAL', text="")

    if material:
        row.prop(material, "name", text="")
        if material.users > 1:
            sub = row.row()
            sub.operator("blendigo.material_copy", text=str(material.users))
            sub.ui_units_x = 2
        row.prop(material, "use_fake_user", text="")
        row.operator("blendigo.material_copy", text="", icon='DUPLICATE')
        row.operator("blendigo.material_unlink", text="", icon='X')
    else:
        row.operator("blendigo.material_new", text="New", icon='ADD')
    return row

def IndigoNodeEditorHeader(panel, context):
    layout = panel.layout

    snode = context.space_data
    assert snode.tree_type == 'IR_MaterialNodeTree'
    id_from = snode.id_from
    # print(id_from)
    tool_settings = context.tool_settings
    types_that_support_material = {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META',
                                   'GPENCIL', 'VOLUME', 'HAIR', 'POINTCLOUD'}

    layout.template_header()

    ob = context.object
    ###########################################################################################
    # Blendigo UI header code
    NODE_MT_editor_menus.draw_collapsible(context, layout)

    ob = context.object

    if ob:
        layout.separator_spacer()
        ob_type = ob.type

        has_material_slots = not snode.pin and ob_type in types_that_support_material

        row = layout.row()
        row.enabled = has_material_slots
        row.popover(panel="NODE_PT_material_slots")
        row.ui_units_x = 4

        row = layout.row()
        row.enabled = has_material_slots

        # id_from is the material the node tree is attached to
        mat = id_from if isinstance(id_from, bpy.types.Material) else ob.active_material
        IR_mat_template_ID(row, mat)

        if mat and not mat.indigo_material.node_tree:
            layout.operator("blendigo.mat_nodetree_new", icon="NODETREE", text="Use Blendigo Material Nodes")
    # End of Blendigo UI header code
    ###########################################################################################
    
    # Put pin next to ID block
    # if not is_compositor:
    layout.prop(snode, "pin", text="", emboss=False)

    layout.separator_spacer()

    layout.operator("node.tree_path_parent", text="", icon='FILE_PARENT')

    # Snap
    row = layout.row(align=True)
    row.prop(tool_settings, "use_snap", text="")
    row.prop(tool_settings, "snap_node_element", icon_only=True)
    if tool_settings.snap_node_element != 'GRID':
        row.prop(tool_settings, "snap_target", text="")

    # Overlay toggle & popover
    if not hasattr(snode, 'overlay'):
        # Blender 2.93
        return
    overlay = snode.overlay
    row = layout.row(align=True)
    row.prop(overlay, "show_overlays", icon='OVERLAY', text="")
    sub = row.row(align=True)
    sub.active = overlay.show_overlays
    sub.popover(panel="NODE_PT_overlay", text="")

def IR_draw_switch(panel, context):
    snode = context.space_data
    if snode.tree_type == 'IR_MaterialNodeTree':
        IndigoNodeEditorHeader(panel, context)
    else:
        original_draw(panel, context)

# subscribe to msg bus to change ShaderEditorNodeTree to Blendigo nodes
from bpy.app.handlers import persistent
@persistent
def node_tree_handler(scene):
    bpy.msgbus.subscribe_rna(
        key=subscribe_to,
        owner=handle,
        args=(bpy.context,),
        notify=change_node_tree,
    )

handle = object()
subscribe_to = bpy.types.RenderSettings, "engine" 

def change_node_tree(context):
    if context.scene.render.engine != RENDERER_BL_IDNAME:
        return
    for area in context.screen.areas:
        if area.type == "NODE_EDITOR":
            for space in area.spaces:
                if space.type == "NODE_EDITOR" and not space.pin and space.tree_type in {'ShaderNodeTree', ''}:
                    space.tree_type = 'IR_MaterialNodeTree'
                    return

def register():
    global original_draw
    original_draw = NODE_HT_header.draw
    NODE_HT_header.draw = IR_draw_switch

    bpy.app.timers.register(
        lambda: bpy.msgbus.subscribe_rna(
            key=subscribe_to,
            owner=handle,
            args=(bpy.context,),
            notify=change_node_tree,
        )
    )
    bpy.app.handlers.load_post.append(node_tree_handler)

def unregister():
    NODE_HT_header.draw = original_draw
    bpy.app.handlers.load_post.remove(node_tree_handler)
    bpy.msgbus.clear_by_owner(handle)
