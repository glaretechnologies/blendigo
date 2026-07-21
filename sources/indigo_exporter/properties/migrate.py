'''Convert legacy material texture references to image references.

Blendigo used to store, per material channel, the *name* of a
bpy.data.textures entry.  A name is not a user reference, so those Texture
datablocks ended up with zero users and Blender discarded them when the .blend
was saved -- which is why assigned textures kept disappearing.  Channels now
hold a real bpy.types.Image pointer instead.

This module converts old files on load, for as long as their Texture
datablocks still exist.  Textures that were already lost to the zero-user
pruning cannot be recovered; those channels are reported and left empty.
'''

import bpy
from bpy.app.handlers import persistent


def _texture_channels(indigo_material):
    '''Yield (property_group, prefix) for every texture channel of a material.

    prefix is e.g. 'colour_TX_'.  Discovered from RNA rather than hardcoded so
    this cannot drift out of step with properties/material.py.
    '''
    for prop in indigo_material.bl_rna.properties:
        if not prop.identifier.startswith('indigo_material_'):
            continue
        group = getattr(indigo_material, prop.identifier, None)
        if group is None or not hasattr(group, 'bl_rna'):
            continue
        for sub in group.bl_rna.properties:
            if sub.identifier.endswith('_TX_image'):
                yield group, sub.identifier[:-len('image')]


def _load_image(path):
    try:
        return bpy.data.images.load(bpy.path.abspath(path), check_existing=True)
    except RuntimeError:
        return None


def _image_from_legacy_texture(tex_name):
    '''Find (or load) the image that a legacy Indigo texture referred to.'''
    tex = bpy.data.textures.get(tex_name)
    if tex is None:
        return None

    legacy = getattr(tex, 'indigo_texture', None)
    if legacy is None:
        return None

    if legacy.image_ref == 'file':
        img = _load_image(legacy.path) if legacy.path else None
    else:
        img = bpy.data.images.get(legacy.image)
        if img is None:
            # Fall back to the image slot on the Texture datablock itself.
            img = getattr(tex, 'image', None)

    if img is None:
        return None

    # Gamma and A/B/C were per-texture; they are now per-image.  If several
    # legacy textures shared one image with different settings, the last one
    # migrated wins.
    img.indigo_image.gamma = legacy.gamma
    img.indigo_image.A = legacy.A
    img.indigo_image.B = legacy.B
    img.indigo_image.C = legacy.C
    return img


@persistent
def migrate_legacy_textures(_dummy):
    from .. export import indigo_log

    migrated = 0
    lost = []

    for mat in bpy.data.materials:
        indigo_material = getattr(mat, 'indigo_material', None)
        if indigo_material is None:
            continue

        for group, prefix in _texture_channels(indigo_material):
            tex_name = getattr(group, prefix + 'texture', '')
            if not tex_name:
                continue

            if getattr(group, prefix + 'image') is not None:
                # Already migrated; just drop the stale name.
                setattr(group, prefix + 'texture', '')
                continue

            img = _image_from_legacy_texture(tex_name)
            if img is None:
                lost.append('%s.%s -> "%s"' % (mat.name, prefix[:-4], tex_name))
                continue

            setattr(group, prefix + 'image', img)
            setattr(group, prefix + 'texture', '')
            migrated += 1

    if migrated:
        indigo_log('Migrated %i Indigo material texture(s) to image references' % migrated)
    if lost:
        indigo_log(
            'Could not migrate %i Indigo material texture(s), the referenced textures '
            'no longer exist in this file: %s' % (len(lost), ', '.join(lost)),
            message_type='WARNING')


def register():
    if migrate_legacy_textures not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(migrate_legacy_textures)


def unregister():
    if migrate_legacy_textures in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(migrate_legacy_textures)
