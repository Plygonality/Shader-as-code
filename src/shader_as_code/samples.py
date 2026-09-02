"""Example graphs shipped with the library.

The seven Master-Node category masters are the goldens: Python is how you
author, JSON is what git diffs. Master-Node instantiates; it does not author.
"""

from __future__ import annotations

from shader_as_code.graph import Graph
from shader_as_code.masters import (
    MASTERS,
    build_dielectric,
    build_emissive,
    build_fabric,
    build_glass,
    build_layered,
    build_metal,
    build_surface,
)
from shader_as_code.types import GraphKind

__all__ = [
    "SAMPLES",
    "build_dielectric",
    "build_emissive",
    "build_fabric",
    "build_glass",
    "build_layered",
    "build_metal",
    "build_noise_roughness",
    "build_surface",
]


def build_noise_roughness() -> Graph:
    """Material tree: Principled roughness driven by a noise texture."""
    g = Graph("Noise Roughness", kind=GraphKind.MATERIAL)
    coord = g.tex_coord(id="texcoord")
    mapping = g.mapping(coord.uv, scale=(4.0, 4.0, 4.0), id="mapping")
    noise = g.noise_texture(vector=mapping.vector, scale=8.0, detail=4.0, id="noise")
    roughness = g.map_range(noise.fac, from_min=0.0, from_max=1.0, to_min=0.15, to_max=0.85, id="remap")
    bsdf = g.principled_bsdf(
        id="bsdf",
        base_color=(0.18, 0.18, 0.2, 1.0),
        roughness=roughness.result,
        metallic=0.0,
    )
    g.output_shader(bsdf)
    return g


SAMPLES = dict(MASTERS)
