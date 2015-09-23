# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Marco Goebel
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

import re, os, zipfile
from copy import deepcopy

import bpy        #@UnresolvedImport
import xml.etree.cElementTree as ET

from extensions_framework import declarative_property_group
from extensions_framework import util as efutil
from extensions_framework.validate import Logic_OR as LOR, Logic_AND as LAND

from indigo import IndigoAddon
from indigo.properties.material import MaterialChannel


Cha_Medium  = MaterialChannel('medium_type', spectrum=True, texture=True,  shader=True,  switch=False, spectrum_types={'rgb':True, 'rgbgain':True, 'uniform':True, 'blackbody': True, 'rgb_default':(0.0,0.0,0.0)}, label='Medium Settings')

Med_SSS_Scatter = MaterialChannel('sss_scatter', spectrum=True, texture=False, shader=False, switch=False, spectrum_types={'rgb':True, 'rgbgain':True, 'uniform':True})
Med_SSS_Phase = MaterialChannel('sss_phase_hg', spectrum=True, texture=False, shader=False, switch=False, spectrum_types={'rgb':True, 'rgbgain':True, 'uniform':True})
Med_Medium_Basic = MaterialChannel('medium_type', spectrum=True, texture=False, shader=False, switch=False, spectrum_types={'rgb':True, 'rgbgain':True, 'uniform':True}, master_colour=True)

@IndigoAddon.addon_register_class
class indigo_material_medium_data(declarative_property_group):
    '''
    Storage class for Indigo medium data. The
    indigo_medium object will store 1 or more of
    these in its CollectionProperty 'medium'.
    '''
    
    ef_attach_to = []    # not attached
    
    alert = {}
    
    controls = [
    'medium_type',
    'precedence',
    
    [ 'medium_ior', 'medium_cauchy_b' ],
    'max_extinction_coeff',
    ] + \
    Med_Medium_Basic.controls + \
    [ [  'medium_melanin', 'medium_eumelanin',],
    'medium_haemoglobin',
    [ 'medium_turbidity',],
    [ 'medium_posx', 'medium_posy', 'medium_posz', ],
    'sss',
    ] + \
    Med_SSS_Scatter.controls + \
    [
        
        'sss_phase_function',
    ] + \
    Med_SSS_Phase.controls
    

    visibility = {
        'medium_type':    { },
        'medium_ior':            { 'medium_type': 'basic' },
        'medium_cauchy_b':        { 'medium_type': 'basic' },
        'max_extinction_coeff':        { 'medium_type': 'basic' },

        'medium_basic_type':    { 'medium_type': 'basic' },
        'medium_haemoglobin':    { 'medium_type': 'dermis' },
        'medium_melanin':        { 'medium_type': 'epidermis' },
        'medium_eumelanin':        { 'medium_type': 'epidermis' },
        'medium_turbidity':        { 'medium_type': 'atmosphere' },
        'medium_posx':        { 'medium_type': 'atmosphere' },
        'medium_posy':        { 'medium_type': 'atmosphere' },
        'medium_posz':        { 'medium_type': 'atmosphere' },
        'sss':  { 'medium_type': 'basic' },
        'sss_scatter_type'    :    { 'sss': True },
        'sss_phase_function':    { 'sss': True },
        'sss_phase_hg_type':    { 'sss': True, 'sss_phase_function': 'hg' },
    }     

    enabled = {
        'sss': {'medium_type': 'basic'},
        }
    Med_SSS_Scatter_vis = deepcopy(Med_SSS_Scatter.visibility)
    
    for k,v in Med_SSS_Scatter_vis.items():
        v.update({ 'sss': True })
    
    visibility.update( Med_SSS_Scatter_vis )
    
    Med_SSS_Phase_vis = deepcopy(Med_SSS_Phase.visibility)
    
    for k,v in Med_SSS_Phase_vis.items():
        v.update({ 'sss': True, 'sss_phase_function': 'hg' })
    
    visibility.update( Med_SSS_Phase_vis )
    
    Med_Medium_Basic_vis = deepcopy(Med_Medium_Basic.visibility)
    
    for k,v in Med_Medium_Basic_vis.items():
        v.update({ 'medium_type': 'basic' })
    
    visibility.update( Med_Medium_Basic_vis )
    
    properties = [
        {
            'type': 'string',
            'attr': 'name',
            'name': ''
        },
	{
            'type': 'int',
            'attr': 'precedence',
            'name': 'Precedence',
            'description': 'Precedence',
            'default': 10,
            'min': 1,
            'max': 100
        },
        {
            'type': 'enum',
            'attr': 'medium_type',
            'name': 'Medium Type',
            'description': 'Medium Type',
            'default': 'basic',
            'items': [
                ('basic', 'Basic', 'basic'),
                ('dermis', 'Dermis', 'dermis'),
                ('epidermis', 'Epidermis', 'epidermis'),
              #  ('atmosphere', 'Atmosphere', 'atmosphere'),
            ]
        },
           {
            'type': 'bool',
            'attr': 'sss',
            'name': 'Subsurface scattering',
            'description': 'SSS',
            'default': False,
        },
                {
            'type': 'enum',
            'attr': 'sss_phase_function',
            'name': 'Phase Function',
            'description': 'Phase Function',
            'default': 'uniform',
            'items': [
                ('uniform', 'Uniform', 'uniform'),
                ('hg', 'Henyey Greenstein', 'hg')
            ]
        },
        {
            'type': 'float',
            'attr': 'medium_ior',
            'name': 'IOR',
            'description': 'IOR',
            'slider': True,
            'default': 1.5,
            'min': 0.0,
            'max': 20.0,
            'precision': 6
        },
        {
            'type': 'float',
            'attr': 'medium_cauchy_b',
            'name': 'Cauchy B',
            'description': 'Cauchy B',
            'default': 0.0,
            'slider': True,
            'min': 0.0,
            'max': 1.0,
            'precision': 6
        },
        {
            'type': 'float',
            'attr': 'max_extinction_coeff',
            'name': 'Max. ext. coeff',
            'description': 'max_extinction_coeff',
            'default': 1.0,
            'slider': True,
            'min': 0.0,
            'max': 1,
            'precision': 6
        },
        {
            'type': 'float',
            'attr': 'medium_haemoglobin',
            'name': 'Haemoglobin',
            'description': 'Haemoglobin',
            'slider': True,
            'default': 0.001,
            'min': 0.0,
            'max': 1.0
        },
        {
            'type': 'float',
            'attr': 'medium_melanin',
            'name': 'Melanin',
            'description': 'Melanin',
            'slider': True,
            'default': 0.15,
            'min': 0.0,
            'max': 1.0
        },
        {
            'type': 'float',
            'attr': 'medium_eumelanin',
            'name': 'Eumelanin',
            'description': 'Eumelanin',
            'slider': True,
            'default': 0.001,
            'min': 0.0,
            'max': 1.0
        },
        {
            'type': 'float',
            'attr': 'medium_turbidity',
            'name': 'Turbidity',
            'description': 'Turbidity',
            'slider': True,
            'default': 2.2,
            'min': 1.0,
            'max': 10.0
        },
        {
            'type': 'string',
            'attr': 'center',
            'name': 'center'
        },
        {
            'type': 'float',
            'attr': 'medium_posx',
            'name': 'X:',
            'description': 'Position X',
            'default': 0,
            'min': 0.0,
            'max': 360.0
        },
        {
            'type': 'float',
            'attr': 'medium_posy',
            'name': 'Y:',
            'description': 'Position Y',
            'default': 0,
            'min': 0.0,
            'max': 360.0
        },
        {
            'type': 'float',
            'attr': 'medium_posz',
            'name': 'Z',
            'description': 'Position Z',
            'default': 0,
            'min': 0.0,
            'max': 360.0
        },


    ] + Cha_Medium.properties    + \
        Med_Medium_Basic.properties + \
        Med_SSS_Scatter.properties + \
        Med_SSS_Phase.properties

@IndigoAddon.addon_register_class
class indigo_material_medium(declarative_property_group):
    ''' container for the medium list'''
    ef_attach_to = ['Material','Scene']
    
    controls    = Cha_Medium.controls
    visibility    = Cha_Medium.visibility
    enabled        = Cha_Medium.enabled
    properties    = Cha_Medium.properties
    
    controls = [
        'medium_select',
        [ 'op_me_add',  'op_me_remove', ],
        ]
    
    visibility = {}
        
    properties = [
        
        {
            'type': 'collection',
            'ptype': indigo_material_medium_data,
            'name': 'medium',
            'attr': 'medium',
            'items': []
        },
        {
            'type': 'int',
            'name': 'medium_index',
            'attr': 'medium_index',
        },
         {
            'type': 'template_list',
            'listtype_name': 'UI_UL_list',
            'list_id': 'mediumlist',
            'name': 'medium_select',
            'attr': 'medium_select',
            'trg': lambda s, c: s.scene.indigo_material_medium,
            'trg_attr': 'medium_index',
            'src': lambda s, c: s.scene.indigo_material_medium,
            'src_attr': 'medium',
        },
        {
            'type': 'operator',
            'attr': 'op_me_add',
            'operator': 'indigo.medium_add',
            'text': 'Add',
            'icon': 'ZOOMIN',
        },
        {
            'type': 'operator',
            'attr': 'op_me_remove',
            'operator': 'indigo.medium_remove',
            'text': 'Remove',
            'icon': 'ZOOMOUT',
        },
    ]
    
    
    def enumerate(self):
        en = {
            'default': 1,
        }
        idx = 1
        for name, me in lambda s,c: s.scene.indigo_material_medium.items():
              en[name] = idx
              idx += 1
        return en
