"""Master-Node category masters authored as ShaderNodeTree graphs.

Master-Node instantiates these dumps. It does not author the graph.
ID properties (``mn.*``) mark a group as a category master.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from shader_as_code.graph import Graph
from shader_as_code.ir import FORMAT_VERSION
from shader_as_code.types import GraphKind, SocketType

PROP_IS_MASTER = "mn.is_master"
PROP_CATEGORY = "mn.category"
PROP_VERSION = "mn.version"
PROP_ORIGIN = "mn.origin"

Origin = Literal["framework", "user"]

CATEGORIES = (
    "surface",
    "metal",
    "dielectric",
    "glass",
    "fabric",
    "emissive",
    "layered",
)

TREE_PREFIX = "MN "

SocketKind = str


@dataclass(frozen=True)
class SocketSpec:
    name: str
    socket: SocketKind
    default: Any
    min: float | None = None
    max: float | None = None
    subtype: str = ""
    panel: str = ""
    description: str = ""


@dataclass(frozen=True)
class CategorySpec:
    id: str
    label: str
    description: str
    icon: str
    sockets: tuple[SocketSpec, ...]
    principled_map: dict[str, str]
    constants: dict[str, Any]

    @property
    def tree_name(self) -> str:
        return tree_name_for(self.id)

    def socket_map(self) -> dict[str, SocketSpec]:
        return {s.name: s for s in self.sockets}

    def panels(self) -> tuple[str, ...]:
        seen: list[str] = []
        for spec in self.sockets:
            if spec.panel and spec.panel not in seen:
                seen.append(spec.panel)
        return tuple(seen)


def tree_name_for(category: str) -> str:
    return f"{TREE_PREFIX}{category.replace('_', ' ').title()}"


def is_known_category(category: str) -> bool:
    return category in CATEGORIES


def master_props(
    category: str,
    *,
    origin: Origin = "framework",
    version: int = FORMAT_VERSION,
) -> dict[str, Any]:
    if not is_known_category(category):
        raise ValueError(f"unknown category: {category}")
    return {
        PROP_IS_MASTER: True,
        PROP_CATEGORY: category,
        PROP_VERSION: int(version),
        PROP_ORIGIN: origin,
    }


def _float(
    name: str,
    default: float,
    *,
    min: float = 0.0,
    max: float = 1.0,
    subtype: str = "FACTOR",
    panel: str = "",
    description: str = "",
) -> SocketSpec:
    return SocketSpec(
        name,
        "FLOAT",
        default,
        min=min,
        max=max,
        subtype=subtype,
        panel=panel,
        description=description,
    )


def _color(
    name: str,
    default: tuple[float, float, float, float],
    *,
    panel: str = "",
    description: str = "",
) -> SocketSpec:
    return SocketSpec(name, "COLOR", list(default), panel=panel, description=description)


SURFACE = CategorySpec(
    id="surface",
    label="Surface",
    description="General Principled surface. Start here when the category is not yet decided.",
    icon="MATERIAL",
    sockets=(
        _color("Base Color", (0.8, 0.8, 0.8, 1.0), description="Albedo"),
        _float("Metallic", 0.0, description="Dielectric to metal"),
        _float("Roughness", 0.4, description="Micro-surface roughness"),
        _float("IOR", 1.5, min=1.0, max=2.5, subtype="", description="Index of refraction"),
        _color("Emission Color", (0.0, 0.0, 0.0, 1.0), panel="Emission"),
        _float("Emission Strength", 0.0, min=0.0, max=50.0, subtype="", panel="Emission"),
        _float("Alpha", 1.0, panel="Alpha"),
    ),
    principled_map={
        "Base Color": "Base Color",
        "Metallic": "Metallic",
        "Roughness": "Roughness",
        "IOR": "IOR",
        "Emission Color": "Emission Color",
        "Emission Strength": "Emission Strength",
        "Alpha": "Alpha",
    },
    constants={},
)

METAL = CategorySpec(
    id="metal",
    label="Metal",
    description="Conductor. Metallic is locked on. Color is the F0 reflectance.",
    icon="MESH_CUBE",
    sockets=(
        _color("Color", (0.72, 0.72, 0.74, 1.0), description="F0 / reflectance"),
        _float("Roughness", 0.25, description="Brush, polish, grit"),
        _float("Anisotropy", 0.0, description="Brushed-metal stretch"),
        _float("Rotation", 0.0, description="Anisotropic tangent rotation"),
        _float("Coat Weight", 0.0, panel="Coat"),
        _float("Coat Roughness", 0.03, panel="Coat"),
    ),
    principled_map={
        "Color": "Base Color",
        "Roughness": "Roughness",
        "Anisotropy": "Anisotropic",
        "Rotation": "Anisotropic Rotation",
        "Coat Weight": "Coat Weight",
        "Coat Roughness": "Coat Roughness",
    },
    constants={"Metallic": 1.0, "Specular IOR Level": 1.0},
)

DIELECTRIC = CategorySpec(
    id="dielectric",
    label="Dielectric",
    description="Plastic, rubber, ceramic, painted non-metal.",
    icon="SPHERE",
    sockets=(
        _color("Color", (0.18, 0.18, 0.2, 1.0)),
        _float("Roughness", 0.45),
        _float("Specular", 0.5, description="Specular IOR level"),
        _float("IOR", 1.45, min=1.0, max=2.5, subtype=""),
        _float("Coat Weight", 0.0, panel="Coat"),
        _float("Coat Roughness", 0.05, panel="Coat"),
        _float("Sheen Weight", 0.0, panel="Sheen"),
        _color("Sheen Tint", (1.0, 1.0, 1.0, 1.0), panel="Sheen"),
    ),
    principled_map={
        "Color": "Base Color",
        "Roughness": "Roughness",
        "Specular": "Specular IOR Level",
        "IOR": "IOR",
        "Coat Weight": "Coat Weight",
        "Coat Roughness": "Coat Roughness",
        "Sheen Weight": "Sheen Weight",
        "Sheen Tint": "Sheen Tint",
    },
    constants={"Metallic": 0.0},
)

GLASS = CategorySpec(
    id="glass",
    label="Glass",
    description="Transmissive dielectric. Thin or solid, depending on the mesh.",
    icon="MESH_UVSPHERE",
    sockets=(
        _color("Color", (1.0, 1.0, 1.0, 1.0), description="Absorption / tint"),
        _float("Roughness", 0.0, description="Frost"),
        _float("IOR", 1.45, min=1.0, max=2.5, subtype=""),
        _float("Transmission", 1.0, description="How much light passes through"),
    ),
    principled_map={
        "Color": "Base Color",
        "Roughness": "Roughness",
        "IOR": "IOR",
        "Transmission": "Transmission Weight",
    },
    constants={"Metallic": 0.0, "Alpha": 1.0},
)

FABRIC = CategorySpec(
    id="fabric",
    label="Fabric",
    description="Cloth and soft goods. Sheen does the grazing lift.",
    icon="TEXTURE",
    sockets=(
        _color("Color", (0.35, 0.22, 0.18, 1.0)),
        _float("Roughness", 0.7),
        _float("Sheen Weight", 0.6, panel="Sheen"),
        _float("Sheen Roughness", 0.4, panel="Sheen"),
        _color("Sheen Tint", (0.95, 0.9, 0.85, 1.0), panel="Sheen"),
        _float("Subsurface", 0.05, panel="Volume", description="Thin-cloth scatter"),
    ),
    principled_map={
        "Color": "Base Color",
        "Roughness": "Roughness",
        "Sheen Weight": "Sheen Weight",
        "Sheen Roughness": "Sheen Roughness",
        "Sheen Tint": "Sheen Tint",
        "Subsurface": "Subsurface Weight",
    },
    constants={"Metallic": 0.0, "Specular IOR Level": 0.3},
)

EMISSIVE = CategorySpec(
    id="emissive",
    label="Emissive",
    description="Lights, screens, neon. Base surface stays dark.",
    icon="LIGHT",
    sockets=(
        _color("Color", (1.0, 0.85, 0.55, 1.0)),
        _float("Strength", 8.0, min=0.0, max=200.0, subtype=""),
        _float("Surface Roughness", 0.4, panel="Surface"),
        _color("Surface Color", (0.0, 0.0, 0.0, 1.0), panel="Surface"),
    ),
    principled_map={
        "Color": "Emission Color",
        "Strength": "Emission Strength",
        "Surface Roughness": "Roughness",
        "Surface Color": "Base Color",
    },
    constants={"Metallic": 0.0},
)

LAYERED = CategorySpec(
    id="layered",
    label="Layered",
    description="Clear coat over a base. Car paint, lacquer, wet look.",
    icon="NODE_MATERIAL",
    sockets=(
        _color("Base Color", (0.05, 0.12, 0.35, 1.0)),
        _float("Base Roughness", 0.35),
        _float("Metallic", 0.15),
        _float("Coat Weight", 1.0, panel="Coat"),
        _float("Coat Roughness", 0.03, panel="Coat"),
        _float("Coat IOR", 1.5, min=1.0, max=2.5, subtype="", panel="Coat"),
        _color("Coat Tint", (1.0, 1.0, 1.0, 1.0), panel="Coat"),
    ),
    principled_map={
        "Base Color": "Base Color",
        "Base Roughness": "Roughness",
        "Metallic": "Metallic",
        "Coat Weight": "Coat Weight",
        "Coat Roughness": "Coat Roughness",
        "Coat IOR": "Coat IOR",
        "Coat Tint": "Coat Tint",
    },
    constants={},
)

CATALOG: dict[str, CategorySpec] = {
    spec.id: spec
    for spec in (SURFACE, METAL, DIELECTRIC, GLASS, FABRIC, EMISSIVE, LAYERED)
}


def get_category(category: str) -> CategorySpec:
    try:
        return CATALOG[category]
    except KeyError as exc:
        raise KeyError(f"unknown category: {category}") from exc


def build_master(category: str) -> Graph:
    """Author one framework category master as a ShaderNodeTree group."""
    spec = get_category(category)
    g = Graph(spec.tree_name, kind=GraphKind.GROUP)
    g.mark_master(spec.id, origin="framework")
    refs = {}
    for sock in spec.sockets:
        socket_type = SocketType.COLOR if sock.socket == "COLOR" else SocketType.FLOAT
        refs[sock.name] = g.input(
            sock.name,
            socket_type,
            sock.default,
            min=sock.min,
            max=sock.max,
            subtype=sock.subtype or None,
            description=sock.description,
            panel=sock.panel,
        )
    inputs: dict[str, Any] = {
        principled: refs[master] for master, principled in spec.principled_map.items()
    }
    inputs.update(spec.constants)
    bsdf = g.node(
        "ShaderNodeBsdfPrincipled",
        id="bsdf",
        label=spec.label,
        inputs=inputs,
    )
    g.output_shader(bsdf)
    return g


def build_surface() -> Graph:
    return build_master("surface")


def build_metal() -> Graph:
    return build_master("metal")


def build_dielectric() -> Graph:
    return build_master("dielectric")


def build_glass() -> Graph:
    return build_master("glass")


def build_fabric() -> Graph:
    return build_master("fabric")


def build_emissive() -> Graph:
    return build_master("emissive")


def build_layered() -> Graph:
    return build_master("layered")


MASTERS = {
    "surface": build_surface,
    "metal": build_metal,
    "dielectric": build_dielectric,
    "glass": build_glass,
    "fabric": build_fabric,
    "emissive": build_emissive,
    "layered": build_layered,
}
