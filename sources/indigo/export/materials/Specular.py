# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Indigo Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
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
from indigo.export import xml_builder
from indigo.export.materials.Base        import EmissionChannelMaterial, BumpChannelMaterial, DisplacementChannelMaterial, ExponentChannelMaterial, MaterialBase
from indigo.export.materials.spectra    import rgb, uniform

class SpecularMedium(xml_builder):
    
    def build_xml_element(self, context):
        xml = self.Element('medium')
        self.build_subelements(context, self.get_format(), xml)
        return xml
    
    def __init__(self, name, property_group):
        self.medium_name = name
        self.property_group = property_group
    
    def get_format(self):
        medium_type = self.property_group.medium_type
        
        fmt = {
            'name': [self.medium_name + '_medium'],
            'precedence': [self.property_group.precedence],
            medium_type: {}
        }
        
        if medium_type == 'basic':
            fmt[medium_type] = {
                'ior': [self.property_group.medium_ior],
                'cauchy_b_coeff': [self.property_group.medium_cauchy_b]
            }
            if self.property_group.medium_basic_SP_type == 'rgb':
                fmt[medium_type]['absorption_coefficient_spectrum'] = rgb([(1.0-i)*self.property_group.medium_basic_SP_rgb_gain for i in self.property_group.medium_basic_SP_rgb])
            elif self.property_group.medium_basic_SP_type == 'uniform':
                fmt[medium_type]['absorption_coefficient_spectrum'] = uniform([
                    self.property_group.medium_basic_SP_uniform_val * \
                    10**self.property_group.medium_basic_SP_uniform_exp
                ])
            
            if self.property_group.sss:
                if self.property_group.sss_scatter_SP_type == 'rgb':
                    SCS = rgb([i*self.property_group.sss_scatter_SP_rgb_gain for i in self.property_group.sss_scatter_SP_rgb])
                elif self.property_group.sss_scatter_SP_type == 'uniform':
                    SCS = uniform([
                        self.property_group.sss_scatter_SP_uniform_val * \
                        10**self.property_group.sss_scatter_SP_uniform_exp
                    ])
                
                if self.property_group.sss_phase_function == 'uniform':
                    PF = { 'uniform': {} }
                elif self.property_group.sss_phase_function == 'hg':
                    if self.property_group.sss_phase_hg_SP_type == 'rgb':
                        PF_HG_GS = rgb([i*self.property_group.sss_phase_hg_SP_rgb_gain for i in self.property_group.sss_phase_hg_SP_rgb])
                    elif self.property_group.sss_phase_hg_SP_type == 'uniform':
                        PF_HG_GS = uniform([
                            self.property_group.sss_phase_hg_SP_uniform_val * \
                            10**self.property_group.sss_phase_hg_SP_uniform_exp
                        ])
                    PF = {
                        'henyey_greenstein': {
                            'g_spectrum': PF_HG_GS
                        }
                    }
                fmt[medium_type]['subsurface_scattering'] = {
                    'scattering_coefficient_spectrum': SCS,
                    'phase_function': PF,
                }
        
        elif medium_type == 'dermis':
            fmt[medium_type] = {
                'hemoglobin_fraction': [self.property_group.medium_haemoglobin],
            }
        elif medium_type == 'epidermis':
            fmt[medium_type] = {
                'melanin_fraction': [self.property_group.medium_melanin],
                'melanin_type_blend': [self.property_group.medium_eumelanin],
            }
        
        return fmt

class SpecularMaterial(
    EmissionChannelMaterial,
    BumpChannelMaterial,
    DisplacementChannelMaterial,
    ExponentChannelMaterial,
    
    # MaterialBase needs to be last in this list
    MaterialBase
    ):
    def get_format(self):
        # will be specular or glossy_transparent
        element_name = self.property_group.type
        
        fmt = {
            'name': [self.material_name],
            element_name: {
                'internal_medium_name': [self.material_name + '_medium']
            }
        }
        
        if element_name == 'specular':
            if self.property_group.transparent:
                fmt[element_name]['transparent'] = ['true']
            else:
                fmt[element_name]['transparent'] = ['false']
                
            if self.property_group.arch_glass:
                fmt[element_name]['arch_glass'] = ['true']
            else:
                fmt[element_name]['arch_glass'] = ['false']
        else:
            fmt[element_name]['exponent'] = [self.property_group.exponent]
        
        fmt[element_name].update(self.get_channels())
        
        return fmt
