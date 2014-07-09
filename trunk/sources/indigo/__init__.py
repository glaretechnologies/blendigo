# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.6 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Thomas Ludwig, Nicholas Chapman, Yves Collé
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#

bl_info = {
    "name": "Blendigo",
    "author": "Glare Technologies Ltd.",
    "version": (3, 6, 28, 0), # Script version
    "blender": (2, 6, 9), # The minimum Blender version required to run the script
    "api": 44136,
    "category": "Render",
    "location": "Render > Engine > Indigo",
    "warning": '',
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/Scripts/Blendigo",
    "tracker_url": "http://projects.blender.org/tracker/index.php?func=detail&aid=23362&group_id=153&atid=514",
    "description": "This Addon will allow you to render your scenes with the Indigo render engine."
}

import os
# This environment var allows the release script to 
# import bl_info without importing the rest of the addon
if os.getenv('BLENDIGO_RELEASE') == None:
    if 'core' in locals():
        import imp
        imp.reload(core)                                    #@UndefinedVariable
    else:
        from extensions_framework import Addon
        IndigoAddon = Addon(bl_info)
        register, unregister = IndigoAddon.init_functions()
    
        from indigo import core
