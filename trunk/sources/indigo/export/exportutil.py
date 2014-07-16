# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Yves Collé
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

import mathutils

from decimal import *

from indigo.core.util import get_worldscale


def getTransform(scene, obj, matrix, xml_format='matrix'):
        #------------------------------------------------------------------------------
        # get appropriate loc, rot, scale data
        if matrix is not None:
            lv, rm, sv = matrix.decompose()
        else:
            lv, rm, sv = obj.matrix_world.decompose()

        rm = rm.to_matrix()
        #------------------------------------------------------------------------------
        # Process loc, rot, scale data
        # get a rotation matrix that doesn't include scale info ...
        # ... apply the world scale ...
        # ... and invert it ...
        ws = get_worldscale(scene)

        # ... then apply non-uniform scaling to rotation matrix
        sv_axes = mathutils.Matrix.Identity(3)
        for i in range(3):
            rm = rm * mathutils.Matrix.Scale(1/sv[i], 3, sv_axes.row[i])

        rm_inverted = rm.inverted() * ws

        xform = {
            'pos': [str(co*ws) for co in lv],
        }

        if xml_format=='quat':
            rmq = rm_inverted.to_quaternion()
            xform['rotation_quaternion'] = {
                'axis': list(rmq.axis),
                'angle': [-rmq.angle]
            }

        elif xml_format=='matrix':
            # convert the matrix to list of strings
            rmr = []
            for row in rm_inverted.col:
                rmr.extend(row)

            xform['rotation'] = { 'matrix': rmr }

        return xform

def matrixListToKeyframes(scene, obj, matrix_list):
    if matrix_list[0][1] == None:
        base_matrix = obj.matrix_world
    else:
        base_matrix = matrix_list[0][1]

    rm_0, sm_0 = base_matrix.decompose()[1:]

    # insert keyframes
    keyframes = []
    for p in matrix_list:
        time = p[0]
        matrix = p[1]
    
        # Diff matrix is the transform from base_matrix to matrix.
        diff_matrix = matrix * base_matrix.inverted()

        if matrix==None or matrix_list[0][1]==None:
            matrix_kf = matrix
        else:
            # construct keyframes with rotation differences from base rotation
            # and absolute positions
            lm_k, rm_k, sm_k = matrix.decompose()

            diff_matrix.transpose()

            # Get the rotation component of the difference matrix.
            r_diff = diff_matrix.decompose()[1]

            matrix_kf = mathutils.Matrix.Translation(lm_k) * \
                        mathutils.Matrix.Rotation(r_diff.angle, 4, r_diff.axis)

        xform = getTransform(scene, obj, matrix_kf, xml_format='quat')

        xform['time'] = [time]

        keyframes.append(xform)
        
    t0 = Decimal(matrix_list[0][0])
    if t0 > Decimal(0.0):
        keyframes.insert(0, dict(keyframes[0]))
        keyframes[0]['time'] = [0.0]
    
    tn = Decimal(matrix_list[-1][0])
    if tn < Decimal(1.0):
        keyframes.append(dict(keyframes[-1]))
        keyframes[-1]['time'] = [1.0]
        
    return keyframes