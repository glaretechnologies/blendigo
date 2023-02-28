import bpy
from .. core import RENDERER_BL_IDNAME
from bl_ui.properties_material import MaterialButtonsPanel
from .. nodes.node_editor_ui import IR_mat_template_ID

class IR_MATERIAL_MT_context_menu(bpy.types.Menu):
    bl_label = "Material Specials"

    def draw(self, _context):
        layout = self.layout

        layout.operator("blendigo.cxt_menu_material_copy", icon='COPYDOWN')
        layout.operator("object.material_slot_copy")
        layout.operator("blendigo.cxt_menu_material_paste", icon='PASTEDOWN')
        layout.operator("object.material_slot_remove_unused")

class IR_MATERIAL_PT_context_material(bpy.types.Panel, MaterialButtonsPanel):
    ''' Blendigo replacement for EEVEE_MATERIAL_PT_context_material '''
    COMPAT_ENGINES = {RENDERER_BL_IDNAME}
    bl_label = ""
    bl_options = {"HIDE_HEADER"}
    bl_order = 1

    @classmethod
    def poll(cls, context):
        ob = context.object
        mat = context.material

        if (ob and ob.type == 'GPENCIL') or (mat and mat.grease_pencil):
            return False

        return (ob or mat) and (context.engine in cls.COMPAT_ENGINES)

    def draw(self, context):
        layout = self.layout

        mat = context.material
        ob = context.object
        slot = context.material_slot
        space = context.space_data

        if ob:
            is_sortable = len(ob.material_slots) > 1
            rows = 3
            if (is_sortable):
                rows = 5

            row = layout.row()

            row.template_list("MATERIAL_UL_matslots", "", ob, "material_slots", ob, "active_material_index", rows=rows)

            col = row.column(align=True)
            col.operator("object.material_slot_add", icon='ADD', text="")
            col.operator("object.material_slot_remove", icon='REMOVE', text="")

            col.separator()

            col.menu("IR_MATERIAL_MT_context_menu", icon='DOWNARROW_HLT', text="")

            if is_sortable:
                col.separator()

                col.operator("object.material_slot_move", icon='TRIA_UP', text="").direction = 'UP'
                col.operator("object.material_slot_move", icon='TRIA_DOWN', text="").direction = 'DOWN'

            if ob.mode == 'EDIT':
                row = layout.row(align=True)
                row.operator("object.material_slot_assign", text="Assign")
                row.operator("object.material_slot_select", text="Select")
                row.operator("object.material_slot_deselect", text="Deselect")

        if ob:
            # Custom template_ID to replace the default copy/new, unlink buttons
            row = IR_mat_template_ID(layout, ob.active_material)

            if slot:
                row = row.row()
                icon_link = 'MESH_DATA' if slot.link == 'DATA' else 'OBJECT_DATA'
                row.prop(slot, "link", icon=icon_link, icon_only=True)
            else:
                row.label()
        elif mat:
            layout.template_ID(space, "pin_id")

        if mat and not mat.indigo_material.node_tree:
            layout.operator("blendigo.mat_nodetree_new", icon='NODETREE', text="Use Blendigo Material Nodes")
