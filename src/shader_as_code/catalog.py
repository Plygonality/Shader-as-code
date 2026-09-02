"""Catalog of common Shader Nodes (Blender 4.2+).

Unknown nodes still work via ``Graph.node`` — the catalog exists so builders
can name sockets, skip defaults, and validate links without bpy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shader_as_code.types import SocketType

ST = SocketType

GROUP_INPUT = "NodeGroupInput"
GROUP_OUTPUT = "NodeGroupOutput"
MATERIAL_OUTPUT = "ShaderNodeOutputMaterial"
WORLD_OUTPUT = "ShaderNodeOutputWorld"
LIGHT_OUTPUT = "ShaderNodeOutputLight"


@dataclass(frozen=True)
class SocketSpec:
    identifier: str
    socket_type: SocketType
    default: Any = None
    multi: bool = False
    optional: bool = False


@dataclass(frozen=True)
class PropertySpec:
    name: str
    default: Any = None
    items: tuple[str, ...] = ()


@dataclass(frozen=True)
class NodeSpec:
    bl_idname: str
    method: str
    label: str
    inputs: tuple[SocketSpec, ...] = ()
    outputs: tuple[SocketSpec, ...] = ()
    properties: tuple[PropertySpec, ...] = ()

    def input_map(self) -> dict[str, SocketSpec]:
        return {s.identifier: s for s in self.inputs}

    def output_map(self) -> dict[str, SocketSpec]:
        return {s.identifier: s for s in self.outputs}

    def primary_output(self) -> SocketSpec | None:
        if not self.outputs:
            return None
        for sock in self.outputs:
            if sock.socket_type == SocketType.SHADER:
                return sock
        return self.outputs[0]


def _s(
    identifier: str,
    socket_type: SocketType,
    default: Any = None,
    *,
    multi: bool = False,
    optional: bool = False,
) -> SocketSpec:
    return SocketSpec(identifier, socket_type, default, multi=multi, optional=optional)


def _p(name: str, default: Any = None, *items: str) -> PropertySpec:
    return PropertySpec(name, default, items)


_WHITE = (1.0, 1.0, 1.0, 1.0)
_BLACK = (0.0, 0.0, 0.0, 1.0)
_GRAY = (0.8, 0.8, 0.8, 1.0)
_ZERO = (0.0, 0.0, 0.0)
_ONE = (1.0, 1.0, 1.0)

_SPECS: tuple[NodeSpec, ...] = (
    NodeSpec(GROUP_INPUT, "group_input", "Group Input", outputs=()),
    NodeSpec(GROUP_OUTPUT, "group_output", "Group Output", inputs=()),
    NodeSpec(
        MATERIAL_OUTPUT,
        "material_output",
        "Material Output",
        inputs=(
            _s("Surface", ST.SHADER, optional=True),
            _s("Volume", ST.SHADER, optional=True),
            _s("Displacement", ST.VECTOR, optional=True),
            _s("Thickness", ST.FLOAT, optional=True),
        ),
        properties=(_p("target", "ALL", "ALL", "EEVEE", "CYCLES"),),
    ),
    NodeSpec(
        WORLD_OUTPUT,
        "world_output",
        "World Output",
        inputs=(
            _s("Surface", ST.SHADER, optional=True),
            _s("Volume", ST.SHADER, optional=True),
        ),
        properties=(_p("target", "ALL", "ALL", "EEVEE", "CYCLES"),),
    ),
    NodeSpec(
        LIGHT_OUTPUT,
        "light_output",
        "Light Output",
        inputs=(_s("Surface", ST.SHADER, optional=True),),
        properties=(_p("target", "ALL", "ALL", "EEVEE", "CYCLES"),),
    ),
    NodeSpec(
        "ShaderNodeOutputAOV",
        "aov_output",
        "AOV Output",
        inputs=(
            _s("Color", ST.COLOR, _BLACK, optional=True),
            _s("Value", ST.FLOAT, 0.0, optional=True),
        ),
        properties=(_p("name", ""),),
    ),
    NodeSpec(
        "ShaderNodeBsdfPrincipled",
        "principled_bsdf",
        "Principled BSDF",
        inputs=(
            _s("Base Color", ST.COLOR, _GRAY),
            _s("Metallic", ST.FLOAT, 0.0),
            _s("Roughness", ST.FLOAT, 0.5),
            _s("IOR", ST.FLOAT, 1.5),
            _s("Alpha", ST.FLOAT, 1.0),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
            _s("Diffuse Roughness", ST.FLOAT, 0.0, optional=True),
            _s("Subsurface Weight", ST.FLOAT, 0.0, optional=True),
            _s("Subsurface Radius", ST.VECTOR, (1.0, 0.2, 0.1), optional=True),
            _s("Subsurface Scale", ST.FLOAT, 0.05, optional=True),
            _s("Subsurface IOR", ST.FLOAT, 1.4, optional=True),
            _s("Subsurface Anisotropy", ST.FLOAT, 0.0, optional=True),
            _s("Specular IOR Level", ST.FLOAT, 0.5, optional=True),
            _s("Specular Tint", ST.COLOR, _WHITE, optional=True),
            _s("Anisotropic", ST.FLOAT, 0.0, optional=True),
            _s("Anisotropic Rotation", ST.FLOAT, 0.0, optional=True),
            _s("Tangent", ST.VECTOR, optional=True),
            _s("Transmission Weight", ST.FLOAT, 0.0, optional=True),
            _s("Coat Weight", ST.FLOAT, 0.0, optional=True),
            _s("Coat Roughness", ST.FLOAT, 0.03, optional=True),
            _s("Coat IOR", ST.FLOAT, 1.5, optional=True),
            _s("Coat Tint", ST.COLOR, _WHITE, optional=True),
            _s("Coat Normal", ST.VECTOR, optional=True),
            _s("Sheen Weight", ST.FLOAT, 0.0, optional=True),
            _s("Sheen Roughness", ST.FLOAT, 0.5, optional=True),
            _s("Sheen Tint", ST.COLOR, _WHITE, optional=True),
            _s("Emission Color", ST.COLOR, _WHITE, optional=True),
            _s("Emission Strength", ST.FLOAT, 0.0, optional=True),
            _s("Thin Film Thickness", ST.FLOAT, 0.0, optional=True),
            _s("Thin Film IOR", ST.FLOAT, 1.33, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
        properties=(
            _p("distribution", "MULTI_GGX", "GGX", "MULTI_GGX"),
            _p("subsurface_method", "RANDOM_WALK", "BURLEY", "RANDOM_WALK", "RANDOM_WALK_SKIN"),
        ),
    ),
    NodeSpec(
        "ShaderNodeBsdfDiffuse",
        "diffuse_bsdf",
        "Diffuse BSDF",
        inputs=(
            _s("Color", ST.COLOR, _GRAY),
            _s("Roughness", ST.FLOAT, 0.0),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeBsdfGlossy",
        "glossy_bsdf",
        "Glossy BSDF",
        inputs=(
            _s("Color", ST.COLOR, _WHITE),
            _s("Roughness", ST.FLOAT, 0.5),
            _s("Anisotropy", ST.FLOAT, 0.0, optional=True),
            _s("Rotation", ST.FLOAT, 0.0, optional=True),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Tangent", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
        properties=(_p("distribution", "MULTI_GGX", "BECKMANN", "GGX", "MULTI_GGX"),),
    ),
    NodeSpec(
        "ShaderNodeBsdfGlass",
        "glass_bsdf",
        "Glass BSDF",
        inputs=(
            _s("Color", ST.COLOR, _WHITE),
            _s("Roughness", ST.FLOAT, 0.0),
            _s("IOR", ST.FLOAT, 1.45),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
        properties=(_p("distribution", "MULTI_GGX", "BECKMANN", "GGX", "MULTI_GGX"),),
    ),
    NodeSpec(
        "ShaderNodeBsdfRefraction",
        "refraction_bsdf",
        "Refraction BSDF",
        inputs=(
            _s("Color", ST.COLOR, _WHITE),
            _s("Roughness", ST.FLOAT, 0.0),
            _s("IOR", ST.FLOAT, 1.45),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
        properties=(_p("distribution", "BECKMANN", "BECKMANN", "GGX"),),
    ),
    NodeSpec(
        "ShaderNodeBsdfTransparent",
        "transparent_bsdf",
        "Transparent BSDF",
        inputs=(
            _s("Color", ST.COLOR, _WHITE),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeBsdfTranslucent",
        "translucent_bsdf",
        "Translucent BSDF",
        inputs=(
            _s("Color", ST.COLOR, _GRAY),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeBsdfSheen",
        "sheen_bsdf",
        "Sheen BSDF",
        inputs=(
            _s("Color", ST.COLOR, _GRAY),
            _s("Roughness", ST.FLOAT, 0.5),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSDF", ST.SHADER),),
        properties=(_p("distribution", "MICROFIBER", "ASHIKHMIN", "MICROFIBER"),),
    ),
    NodeSpec(
        "ShaderNodeSubsurfaceScattering",
        "subsurface_scattering",
        "Subsurface Scattering",
        inputs=(
            _s("Color", ST.COLOR, _GRAY),
            _s("Scale", ST.FLOAT, 1.0),
            _s("Radius", ST.VECTOR, (1.0, 0.2, 0.1)),
            _s("IOR", ST.FLOAT, 1.4, optional=True),
            _s("Roughness", ST.FLOAT, 1.0, optional=True),
            _s("Anisotropy", ST.FLOAT, 0.0, optional=True),
            _s("Normal", ST.VECTOR, optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("BSSRDF", ST.SHADER),),
        properties=(_p("falloff", "RANDOM_WALK", "BURLEY", "RANDOM_WALK", "RANDOM_WALK_SKIN"),),
    ),
    NodeSpec(
        "ShaderNodeEmission",
        "emission",
        "Emission",
        inputs=(
            _s("Color", ST.COLOR, _WHITE),
            _s("Strength", ST.FLOAT, 1.0),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("Emission", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeHoldout",
        "holdout",
        "Holdout",
        inputs=(_s("Weight", ST.FLOAT, optional=True),),
        outputs=(_s("Holdout", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeBackground",
        "background",
        "Background",
        inputs=(
            _s("Color", ST.COLOR, _GRAY),
            _s("Strength", ST.FLOAT, 1.0),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("Background", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeVolumePrincipled",
        "principled_volume",
        "Principled Volume",
        inputs=(
            _s("Color", ST.COLOR, (0.5, 0.5, 0.5, 1.0)),
            _s("Color Attribute", ST.STRING, "", optional=True),
            _s("Density", ST.FLOAT, 1.0),
            _s("Density Attribute", ST.STRING, "density", optional=True),
            _s("Anisotropy", ST.FLOAT, 0.0),
            _s("Absorption Color", ST.COLOR, _BLACK, optional=True),
            _s("Emission Strength", ST.FLOAT, 0.0),
            _s("Emission Color", ST.COLOR, _WHITE),
            _s("Blackbody Intensity", ST.FLOAT, 0.0, optional=True),
            _s("Blackbody Tint", ST.COLOR, _WHITE, optional=True),
            _s("Temperature", ST.FLOAT, 1000.0, optional=True),
            _s("Temperature Attribute", ST.STRING, "temperature", optional=True),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("Volume", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeVolumeAbsorption",
        "volume_absorption",
        "Volume Absorption",
        inputs=(
            _s("Color", ST.COLOR, _GRAY),
            _s("Density", ST.FLOAT, 1.0),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("Volume", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeVolumeScatter",
        "volume_scatter",
        "Volume Scatter",
        inputs=(
            _s("Color", ST.COLOR, _GRAY),
            _s("Density", ST.FLOAT, 1.0),
            _s("Anisotropy", ST.FLOAT, 0.0),
            _s("Weight", ST.FLOAT, optional=True),
        ),
        outputs=(_s("Volume", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeMixShader",
        "mix_shader",
        "Mix Shader",
        inputs=(
            _s("Fac", ST.FLOAT, 0.5),
            _s("Shader", ST.SHADER, optional=True),
            _s("Shader_001", ST.SHADER, optional=True),
        ),
        outputs=(_s("Shader", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeAddShader",
        "add_shader",
        "Add Shader",
        inputs=(
            _s("Shader", ST.SHADER, optional=True),
            _s("Shader_001", ST.SHADER, optional=True),
        ),
        outputs=(_s("Shader", ST.SHADER),),
    ),
    NodeSpec(
        "ShaderNodeTexCoord",
        "tex_coord",
        "Texture Coordinate",
        outputs=(
            _s("Generated", ST.VECTOR),
            _s("Normal", ST.VECTOR),
            _s("UV", ST.VECTOR),
            _s("Object", ST.VECTOR),
            _s("Camera", ST.VECTOR),
            _s("Window", ST.VECTOR),
            _s("Reflection", ST.VECTOR),
        ),
        properties=(
            _p("from_instancer", False),
        ),
    ),
    NodeSpec(
        "ShaderNodeUVMap",
        "uv_map",
        "UV Map",
        outputs=(_s("UV", ST.VECTOR),),
        properties=(
            _p("from_instancer", False),
            _p("uv_map", ""),
        ),
    ),
    NodeSpec(
        "ShaderNodeMapping",
        "mapping",
        "Mapping",
        inputs=(
            _s("Vector", ST.VECTOR, _ZERO),
            _s("Location", ST.VECTOR, _ZERO),
            _s("Rotation", ST.VECTOR, _ZERO),
            _s("Scale", ST.VECTOR, _ONE),
        ),
        outputs=(_s("Vector", ST.VECTOR),),
        properties=(_p("vector_type", "POINT", "POINT", "TEXTURE", "VECTOR", "NORMAL"),),
    ),
    NodeSpec(
        "ShaderNodeTexImage",
        "image_texture",
        "Image Texture",
        inputs=(_s("Vector", ST.VECTOR, optional=True),),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Alpha", ST.FLOAT),
        ),
        properties=(
            _p("interpolation", "Linear", "Linear", "Closest", "Cubic", "Smart"),
            _p("projection", "FLAT", "FLAT", "BOX", "SPHERE", "TUBE"),
            _p("extension", "REPEAT", "REPEAT", "EXTEND", "CLIP", "MIRROR"),
            _p("image", None),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexEnvironment",
        "environment_texture",
        "Environment Texture",
        inputs=(_s("Vector", ST.VECTOR, optional=True),),
        outputs=(_s("Color", ST.COLOR),),
        properties=(
            _p("interpolation", "Linear", "Linear", "Closest", "Cubic", "Smart"),
            _p("projection", "EQUIRECTANGULAR", "EQUIRECTANGULAR", "MIRROR_BALL"),
            _p("image", None),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexSky",
        "sky_texture",
        "Sky Texture",
        inputs=(_s("Vector", ST.VECTOR, optional=True),),
        outputs=(_s("Color", ST.COLOR),),
        properties=(
            _p("sky_type", "NISHITA", "PREETHAM", "HOSEK_WILKIE", "NISHITA"),
            _p("sun_disc", True),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexNoise",
        "noise_texture",
        "Noise Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Scale", ST.FLOAT, 5.0),
            _s("Detail", ST.FLOAT, 2.0),
            _s("Roughness", ST.FLOAT, 0.5),
            _s("Lacunarity", ST.FLOAT, 2.0),
            _s("Distortion", ST.FLOAT, 0.0),
        ),
        outputs=(
            _s("Fac", ST.FLOAT),
            _s("Color", ST.COLOR),
        ),
        properties=(
            _p("noise_dimensions", "3D", "1D", "2D", "3D", "4D"),
            _p(
                "noise_type",
                "FBM",
                "MULTIFRACTAL",
                "RIDGED_MULTIFRACTAL",
                "HYBRID_MULTIFRACTAL",
                "FBM",
                "HETERO_TERRAIN",
            ),
            _p("normalize", True),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexVoronoi",
        "voronoi_texture",
        "Voronoi Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Scale", ST.FLOAT, 5.0),
            _s("Detail", ST.FLOAT, 0.0, optional=True),
            _s("Roughness", ST.FLOAT, 0.5, optional=True),
            _s("Lacunarity", ST.FLOAT, 2.0, optional=True),
            _s("Randomness", ST.FLOAT, 1.0),
        ),
        outputs=(
            _s("Distance", ST.FLOAT),
            _s("Color", ST.COLOR),
            _s("Position", ST.VECTOR),
        ),
        properties=(
            _p("voronoi_dimensions", "3D", "1D", "2D", "3D", "4D"),
            _p("feature", "F1", "F1", "F2", "SMOOTH_F1", "DISTANCE_TO_EDGE", "N_SPHERE_RADIUS"),
            _p("distance", "EUCLIDEAN", "EUCLIDEAN", "MANHATTAN", "CHEBYCHEV", "MINKOWSKI"),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexWave",
        "wave_texture",
        "Wave Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Scale", ST.FLOAT, 5.0),
            _s("Distortion", ST.FLOAT, 0.0),
            _s("Detail", ST.FLOAT, 2.0),
            _s("Detail Scale", ST.FLOAT, 1.0),
            _s("Detail Roughness", ST.FLOAT, 0.5),
            _s("Phase Offset", ST.FLOAT, 0.0),
        ),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Fac", ST.FLOAT),
        ),
        properties=(
            _p("wave_type", "BANDS", "BANDS", "RINGS"),
            _p("bands_direction", "X", "X", "Y", "Z", "DIAGONAL"),
            _p("wave_profile", "SIN", "SIN", "SAW", "TRI"),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexGradient",
        "gradient_texture",
        "Gradient Texture",
        inputs=(_s("Vector", ST.VECTOR, optional=True),),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Fac", ST.FLOAT),
        ),
        properties=(
            _p(
                "gradient_type",
                "LINEAR",
                "LINEAR",
                "QUADRATIC",
                "EASING",
                "DIAGONAL",
                "SPHERICAL",
                "QUADRATIC_SPHERE",
                "RADIAL",
            ),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexMagic",
        "magic_texture",
        "Magic Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Scale", ST.FLOAT, 5.0),
            _s("Distortion", ST.FLOAT, 1.0),
        ),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Fac", ST.FLOAT),
        ),
        properties=(_p("turbulence_depth", 2),),
    ),
    NodeSpec(
        "ShaderNodeTexBrick",
        "brick_texture",
        "Brick Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Color1", ST.COLOR, (0.8, 0.8, 0.8, 1.0)),
            _s("Color2", ST.COLOR, (0.2, 0.2, 0.2, 1.0)),
            _s("Mortar", ST.COLOR, _BLACK),
            _s("Scale", ST.FLOAT, 5.0),
            _s("Mortar Size", ST.FLOAT, 0.02),
            _s("Mortar Smooth", ST.FLOAT, 0.1),
            _s("Bias", ST.FLOAT, 0.0),
            _s("Brick Width", ST.FLOAT, 0.5),
            _s("Row Height", ST.FLOAT, 0.25),
        ),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Fac", ST.FLOAT),
        ),
        properties=(_p("offset", 0.5), _p("squash", 1.0)),
    ),
    NodeSpec(
        "ShaderNodeTexChecker",
        "checker_texture",
        "Checker Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Color1", ST.COLOR, _GRAY),
            _s("Color2", ST.COLOR, (0.2, 0.2, 0.2, 1.0)),
            _s("Scale", ST.FLOAT, 5.0),
        ),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Fac", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexWhiteNoise",
        "white_noise_texture",
        "White Noise Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("W", ST.FLOAT, 0.0, optional=True),
        ),
        outputs=(
            _s("Value", ST.FLOAT),
            _s("Color", ST.COLOR),
        ),
        properties=(_p("noise_dimensions", "3D", "1D", "2D", "3D", "4D"),),
    ),
    NodeSpec(
        "ShaderNodeNormalMap",
        "normal_map",
        "Normal Map",
        inputs=(
            _s("Strength", ST.FLOAT, 1.0),
            _s("Color", ST.COLOR, (0.5, 0.5, 1.0, 1.0)),
        ),
        outputs=(_s("Normal", ST.VECTOR),),
        properties=(
            _p("space", "TANGENT", "TANGENT", "OBJECT", "WORLD", "BLENDER_OBJECT", "BLENDER_WORLD"),
            _p("uv_map", ""),
        ),
    ),
    NodeSpec(
        "ShaderNodeBump",
        "bump",
        "Bump",
        inputs=(
            _s("Strength", ST.FLOAT, 1.0),
            _s("Distance", ST.FLOAT, 1.0),
            _s("Height", ST.FLOAT, optional=True),
            _s("Normal", ST.VECTOR, optional=True),
        ),
        outputs=(_s("Normal", ST.VECTOR),),
        properties=(_p("invert", False),),
    ),
    NodeSpec(
        "ShaderNodeDisplacement",
        "displacement",
        "Displacement",
        inputs=(
            _s("Height", ST.FLOAT, 0.0),
            _s("Midlevel", ST.FLOAT, 0.5),
            _s("Scale", ST.FLOAT, 1.0),
            _s("Normal", ST.VECTOR, optional=True),
        ),
        outputs=(_s("Displacement", ST.VECTOR),),
        properties=(_p("space", "OBJECT", "OBJECT", "WORLD"),),
    ),
    NodeSpec(
        "ShaderNodeVectorDisplacement",
        "vector_displacement",
        "Vector Displacement",
        inputs=(
            _s("Vector", ST.COLOR, _BLACK),
            _s("Midlevel", ST.FLOAT, 0.0),
            _s("Scale", ST.FLOAT, 1.0),
        ),
        outputs=(_s("Displacement", ST.VECTOR),),
        properties=(_p("space", "TANGENT", "TANGENT", "OBJECT", "WORLD"),),
    ),
    NodeSpec(
        "ShaderNodeMath",
        "math",
        "Math",
        inputs=(
            _s("Value", ST.FLOAT, 0.5),
            _s("Value_001", ST.FLOAT, 0.5),
            _s("Value_002", ST.FLOAT, 0.5, optional=True),
        ),
        outputs=(_s("Value", ST.FLOAT),),
        properties=(
            _p(
                "operation",
                "ADD",
                "ADD",
                "SUBTRACT",
                "MULTIPLY",
                "DIVIDE",
                "MULTIPLY_ADD",
                "POWER",
                "LOGARITHM",
                "SQRT",
                "INVERSE_SQRT",
                "ABSOLUTE",
                "EXPONENT",
                "MINIMUM",
                "MAXIMUM",
                "LESS_THAN",
                "GREATER_THAN",
                "SIGN",
                "COMPARE",
                "SMOOTH_MIN",
                "SMOOTH_MAX",
                "ROUND",
                "FLOOR",
                "CEIL",
                "TRUNC",
                "FRACT",
                "MODULO",
                "FLOORED_MODULO",
                "WRAP",
                "SNAP",
                "PINGPONG",
                "SINE",
                "COSINE",
                "TANGENT",
                "ARCSINE",
                "ARCCOSINE",
                "ARCTANGENT",
                "ARCTAN2",
                "SINH",
                "COSH",
                "TANH",
                "RADIANS",
                "DEGREES",
            ),
            _p("use_clamp", False),
        ),
    ),
    NodeSpec(
        "ShaderNodeVectorMath",
        "vector_math",
        "Vector Math",
        inputs=(
            _s("Vector", ST.VECTOR, _ZERO),
            _s("Vector_001", ST.VECTOR, _ZERO),
            _s("Vector_002", ST.VECTOR, _ZERO, optional=True),
            _s("Scale", ST.FLOAT, 1.0, optional=True),
        ),
        outputs=(
            _s("Vector", ST.VECTOR),
            _s("Value", ST.FLOAT),
        ),
        properties=(
            _p(
                "operation",
                "ADD",
                "ADD",
                "SUBTRACT",
                "MULTIPLY",
                "DIVIDE",
                "MULTIPLY_ADD",
                "CROSS_PRODUCT",
                "PROJECT",
                "REFLECT",
                "REFRACT",
                "FACEFORWARD",
                "DOT_PRODUCT",
                "DISTANCE",
                "LENGTH",
                "SCALE",
                "NORMALIZE",
                "ABSOLUTE",
                "MINIMUM",
                "MAXIMUM",
                "FLOOR",
                "CEIL",
                "FRACTION",
                "MODULO",
                "WRAP",
                "SNAP",
                "SINE",
                "COSINE",
                "TANGENT",
            ),
        ),
    ),
    NodeSpec(
        "ShaderNodeMapRange",
        "map_range",
        "Map Range",
        inputs=(
            _s("Value", ST.FLOAT, 1.0),
            _s("From Min", ST.FLOAT, 0.0),
            _s("From Max", ST.FLOAT, 1.0),
            _s("To Min", ST.FLOAT, 0.0),
            _s("To Max", ST.FLOAT, 1.0),
            _s("Steps", ST.FLOAT, 4.0, optional=True),
        ),
        outputs=(_s("Result", ST.FLOAT),),
        properties=(
            _p("data_type", "FLOAT", "FLOAT", "FLOAT_VECTOR"),
            _p("interpolation_type", "LINEAR", "LINEAR", "STEPPED", "SMOOTHSTEP", "SMOOTHERSTEP"),
            _p("clamp", True),
        ),
    ),
    NodeSpec(
        "ShaderNodeClamp",
        "clamp",
        "Clamp",
        inputs=(
            _s("Value", ST.FLOAT, 1.0),
            _s("Min", ST.FLOAT, 0.0),
            _s("Max", ST.FLOAT, 1.0),
        ),
        outputs=(_s("Result", ST.FLOAT),),
        properties=(_p("clamp_type", "MINMAX", "MINMAX", "RANGE"),),
    ),
    NodeSpec(
        "ShaderNodeMix",
        "mix",
        "Mix",
        inputs=(
            _s("Factor", ST.FLOAT, 0.5),
            _s("A", ST.FLOAT, 0.0),
            _s("B", ST.FLOAT, 0.0),
        ),
        outputs=(_s("Result", ST.FLOAT),),
        properties=(
            _p("data_type", "FLOAT", "FLOAT", "VECTOR", "RGBA", "ROTATION"),
            _p("clamp_factor", True),
            _p("clamp_result", False),
            _p(
                "blend_type",
                "MIX",
                "MIX",
                "DARKEN",
                "MULTIPLY",
                "BURN",
                "LIGHTEN",
                "SCREEN",
                "DODGE",
                "ADD",
                "OVERLAY",
                "SOFT_LIGHT",
                "LINEAR_LIGHT",
                "DIFFERENCE",
                "EXCLUSION",
                "SUBTRACT",
                "DIVIDE",
                "HUE",
                "SATURATION",
                "COLOR",
                "VALUE",
            ),
        ),
    ),
    NodeSpec(
        "ShaderNodeInvert",
        "invert",
        "Invert Color",
        inputs=(
            _s("Fac", ST.FLOAT, 1.0),
            _s("Color", ST.COLOR, _BLACK),
        ),
        outputs=(_s("Color", ST.COLOR),),
    ),
    NodeSpec(
        "ShaderNodeGamma",
        "gamma",
        "Gamma",
        inputs=(
            _s("Color", ST.COLOR, _WHITE),
            _s("Gamma", ST.FLOAT, 1.0),
        ),
        outputs=(_s("Color", ST.COLOR),),
    ),
    NodeSpec(
        "ShaderNodeHueSaturation",
        "hue_saturation",
        "Hue/Saturation/Value",
        inputs=(
            _s("Hue", ST.FLOAT, 0.5),
            _s("Saturation", ST.FLOAT, 1.0),
            _s("Value", ST.FLOAT, 1.0),
            _s("Fac", ST.FLOAT, 1.0),
            _s("Color", ST.COLOR, _GRAY),
        ),
        outputs=(_s("Color", ST.COLOR),),
    ),
    NodeSpec(
        "ShaderNodeBrightContrast",
        "brightness_contrast",
        "Brightness/Contrast",
        inputs=(
            _s("Color", ST.COLOR, _BLACK),
            _s("Bright", ST.FLOAT, 0.0),
            _s("Contrast", ST.FLOAT, 0.0),
        ),
        outputs=(_s("Color", ST.COLOR),),
    ),
    NodeSpec(
        "ShaderNodeValToRGB",
        "color_ramp",
        "Color Ramp",
        inputs=(_s("Fac", ST.FLOAT, 0.5),),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Alpha", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeRGB",
        "rgb",
        "RGB",
        outputs=(_s("Color", ST.COLOR),),
    ),
    NodeSpec(
        "ShaderNodeValue",
        "value",
        "Value",
        outputs=(_s("Value", ST.FLOAT),),
    ),
    NodeSpec(
        "ShaderNodeRGBToBW",
        "rgb_to_bw",
        "RGB to BW",
        inputs=(_s("Color", ST.COLOR, _GRAY),),
        outputs=(_s("Val", ST.FLOAT),),
    ),
    NodeSpec(
        "ShaderNodeSeparateColor",
        "separate_color",
        "Separate Color",
        inputs=(_s("Color", ST.COLOR, _GRAY),),
        outputs=(
            _s("Red", ST.FLOAT),
            _s("Green", ST.FLOAT),
            _s("Blue", ST.FLOAT),
        ),
        properties=(_p("mode", "RGB", "RGB", "HSV", "HSL"),),
    ),
    NodeSpec(
        "ShaderNodeCombineColor",
        "combine_color",
        "Combine Color",
        inputs=(
            _s("Red", ST.FLOAT, 0.0),
            _s("Green", ST.FLOAT, 0.0),
            _s("Blue", ST.FLOAT, 0.0),
        ),
        outputs=(_s("Color", ST.COLOR),),
        properties=(_p("mode", "RGB", "RGB", "HSV", "HSL"),),
    ),
    NodeSpec(
        "ShaderNodeSeparateXYZ",
        "separate_xyz",
        "Separate XYZ",
        inputs=(_s("Vector", ST.VECTOR, _ZERO),),
        outputs=(
            _s("X", ST.FLOAT),
            _s("Y", ST.FLOAT),
            _s("Z", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeCombineXYZ",
        "combine_xyz",
        "Combine XYZ",
        inputs=(
            _s("X", ST.FLOAT, 0.0),
            _s("Y", ST.FLOAT, 0.0),
            _s("Z", ST.FLOAT, 0.0),
        ),
        outputs=(_s("Vector", ST.VECTOR),),
    ),
    NodeSpec(
        "ShaderNodeFresnel",
        "fresnel",
        "Fresnel",
        inputs=(
            _s("IOR", ST.FLOAT, 1.45),
            _s("Normal", ST.VECTOR, optional=True),
        ),
        outputs=(_s("Fac", ST.FLOAT),),
    ),
    NodeSpec(
        "ShaderNodeLayerWeight",
        "layer_weight",
        "Layer Weight",
        inputs=(
            _s("Blend", ST.FLOAT, 0.5),
            _s("Normal", ST.VECTOR, optional=True),
        ),
        outputs=(
            _s("Fresnel", ST.FLOAT),
            _s("Facing", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeNewGeometry",
        "geometry",
        "Geometry",
        outputs=(
            _s("Position", ST.VECTOR),
            _s("Normal", ST.VECTOR),
            _s("Tangent", ST.VECTOR),
            _s("True Normal", ST.VECTOR),
            _s("Incoming", ST.VECTOR),
            _s("Parametric", ST.VECTOR),
            _s("Backfacing", ST.FLOAT),
            _s("Pointiness", ST.FLOAT),
            _s("Random Per Island", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeAttribute",
        "attribute",
        "Attribute",
        outputs=(
            _s("Color", ST.COLOR),
            _s("Vector", ST.VECTOR),
            _s("Fac", ST.FLOAT),
            _s("Alpha", ST.FLOAT),
        ),
        properties=(
            _p("attribute_name", ""),
            _p("attribute_type", "GEOMETRY", "GEOMETRY", "OBJECT", "INSTANCER", "VIEW_LAYER"),
        ),
    ),
    NodeSpec(
        "ShaderNodeLightPath",
        "light_path",
        "Light Path",
        outputs=(
            _s("Is Camera Ray", ST.FLOAT),
            _s("Is Shadow Ray", ST.FLOAT),
            _s("Is Diffuse Ray", ST.FLOAT),
            _s("Is Glossy Ray", ST.FLOAT),
            _s("Is Singular Ray", ST.FLOAT),
            _s("Is Reflection Ray", ST.FLOAT),
            _s("Is Transmission Ray", ST.FLOAT),
            _s("Ray Length", ST.FLOAT),
            _s("Ray Depth", ST.FLOAT),
            _s("Diffuse Depth", ST.FLOAT),
            _s("Glossy Depth", ST.FLOAT),
            _s("Transparent Depth", ST.FLOAT),
            _s("Transmission Depth", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeObjectInfo",
        "object_info",
        "Object Info",
        outputs=(
            _s("Location", ST.VECTOR),
            _s("Color", ST.COLOR),
            _s("Alpha", ST.FLOAT),
            _s("Object Index", ST.FLOAT),
            _s("Material Index", ST.FLOAT),
            _s("Random", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeBlackbody",
        "blackbody",
        "Blackbody",
        inputs=(_s("Temperature", ST.FLOAT, 1500.0),),
        outputs=(_s("Color", ST.COLOR),),
    ),
    NodeSpec(
        "ShaderNodeWavelength",
        "wavelength",
        "Wavelength",
        inputs=(_s("Wavelength", ST.FLOAT, 500.0),),
        outputs=(_s("Color", ST.COLOR),),
    ),
    NodeSpec(
        "ShaderNodeShaderToRGB",
        "shader_to_rgb",
        "Shader to RGB",
        inputs=(_s("Shader", ST.SHADER, optional=True),),
        outputs=(
            _s("Color", ST.COLOR),
            _s("Alpha", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeVectorRotate",
        "vector_rotate",
        "Vector Rotate",
        inputs=(
            _s("Vector", ST.VECTOR, _ZERO),
            _s("Center", ST.VECTOR, _ZERO),
            _s("Axis", ST.VECTOR, (0.0, 0.0, 1.0)),
            _s("Angle", ST.FLOAT, 0.0),
            _s("Rotation", ST.VECTOR, _ZERO, optional=True),
        ),
        outputs=(_s("Vector", ST.VECTOR),),
        properties=(
            _p("rotation_type", "AXIS_ANGLE", "AXIS_ANGLE", "X_AXIS", "Y_AXIS", "Z_AXIS", "EULER_XYZ"),
            _p("invert", False),
        ),
    ),
    NodeSpec(
        "ShaderNodeVectorTransform",
        "vector_transform",
        "Vector Transform",
        inputs=(_s("Vector", ST.VECTOR, _ZERO),),
        outputs=(_s("Vector", ST.VECTOR),),
        properties=(
            _p("vector_type", "VECTOR", "POINT", "VECTOR", "NORMAL"),
            _p("convert_from", "WORLD", "WORLD", "OBJECT", "CAMERA"),
            _p("convert_to", "OBJECT", "WORLD", "OBJECT", "CAMERA"),
        ),
    ),
    NodeSpec(
        "ShaderNodeGroup",
        "group",
        "Group",
        properties=(_p("node_tree", None),),
    ),
    NodeSpec(
        "NodeReroute",
        "reroute",
        "Reroute",
        inputs=(_s("Input", ST.SHADER),),
        outputs=(_s("Output", ST.SHADER),),
    ),
    NodeSpec(
        "NodeFrame",
        "frame",
        "Frame",
        properties=(
            _p("label_size", 20),
            _p("shrink", True),
        ),
    ),
    NodeSpec(
        "ShaderNodeAmbientOcclusion",
        "ambient_occlusion",
        "Ambient Occlusion",
        inputs=(
            _s("Color", ST.COLOR, _WHITE),
            _s("Distance", ST.FLOAT, 1.0),
            _s("Normal", ST.VECTOR, optional=True),
        ),
        outputs=(
            _s("Color", ST.COLOR),
            _s("AO", ST.FLOAT),
        ),
        properties=(
            _p("inside", False),
            _p("only_local", False),
            _p("samples", 16),
        ),
    ),
    NodeSpec(
        "ShaderNodeBevel",
        "bevel",
        "Bevel",
        inputs=(
            _s("Radius", ST.FLOAT, 0.05),
            _s("Normal", ST.VECTOR, optional=True),
        ),
        outputs=(_s("Normal", ST.VECTOR),),
        properties=(_p("samples", 4),),
    ),
    NodeSpec(
        "ShaderNodeWireframe",
        "wireframe",
        "Wireframe",
        inputs=(_s("Size", ST.FLOAT, 0.01),),
        outputs=(_s("Fac", ST.FLOAT),),
        properties=(
            _p("use_pixel_size", False),
        ),
    ),
    NodeSpec(
        "ShaderNodeCameraData",
        "camera_data",
        "Camera Data",
        outputs=(
            _s("View Vector", ST.VECTOR),
            _s("View Z Depth", ST.FLOAT),
            _s("View Distance", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeTangent",
        "tangent",
        "Tangent",
        outputs=(_s("Tangent", ST.VECTOR),),
        properties=(
            _p("direction_type", "RADIAL", "RADIAL", "UV_MAP"),
            _p("axis", "Z", "X", "Y", "Z"),
            _p("uv_map", ""),
        ),
    ),
)

CATALOG: tuple[NodeSpec, ...] = _SPECS
CATALOG_BY_TYPE: dict[str, NodeSpec] = {spec.bl_idname: spec for spec in _SPECS}
CATALOG_BY_METHOD: dict[str, NodeSpec] = {spec.method: spec for spec in _SPECS}


def get_spec(bl_idname: str) -> NodeSpec | None:
    return CATALOG_BY_TYPE.get(bl_idname)


def values_equal(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return False
        return all(values_equal(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 1e-9
    return False
