"""Typed Shader Node graph builder.

A ``Graph`` is both the authoring API and the in-memory IR. Call ``to_dict`` /
``dumps`` when you want the version-controlled artifact.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from shader_as_code.catalog import (
    CATALOG_BY_METHOD,
    GROUP_INPUT,
    GROUP_OUTPUT,
    LIGHT_OUTPUT,
    MATERIAL_OUTPUT,
    WORLD_OUTPUT,
    NodeSpec,
    get_spec,
    values_equal,
)
from shader_as_code.ir import GraphData, InterfaceItem, Link, Node
from shader_as_code.types import GraphKind, JsonValue, SocketType, jsonify

InputValue = Any

_NODE_KW = frozenset({"label", "location", "hide", "mute", "parent"})

_KIND_OUTPUT = {
    GraphKind.GROUP: ("Group Output", GROUP_OUTPUT),
    GraphKind.MATERIAL: ("Material Output", MATERIAL_OUTPUT),
    GraphKind.WORLD: ("World Output", WORLD_OUTPUT),
    GraphKind.LIGHT: ("Light Output", LIGHT_OUTPUT),
}


def _snake_to_socket(name: str) -> str:
    specials = {
        "value_001": "Value_001",
        "value_002": "Value_002",
        "vector_001": "Vector_001",
        "vector_002": "Vector_002",
        "shader_001": "Shader_001",
        "color_001": "Color_001",
        "color1": "Color1",
        "color2": "Color2",
        "ior": "IOR",
        "bsdf": "BSDF",
        "rgb": "RGB",
        "uv": "UV",
        "fac": "Fac",
        "aov": "AOV",
        "from_min": "From Min",
        "from_max": "From Max",
        "to_min": "To Min",
        "to_max": "To Max",
        "specular_ior_level": "Specular IOR Level",
        "coat_ior": "Coat IOR",
        "subsurface_ior": "Subsurface IOR",
        "thin_film_ior": "Thin Film IOR",
        "true_normal": "True Normal",
        "is_camera_ray": "Is Camera Ray",
        "is_shadow_ray": "Is Shadow Ray",
        "is_diffuse_ray": "Is Diffuse Ray",
        "is_glossy_ray": "Is Glossy Ray",
        "is_singular_ray": "Is Singular Ray",
        "is_reflection_ray": "Is Reflection Ray",
        "is_transmission_ray": "Is Transmission Ray",
        "ray_length": "Ray Length",
        "ray_depth": "Ray Depth",
        "view_z_depth": "View Z Depth",
        "view_distance": "View Distance",
        "view_vector": "View Vector",
        "random_per_island": "Random Per Island",
        "object_index": "Object Index",
        "material_index": "Material Index",
        "uv_map": "UV Map",
    }
    if name in specials:
        return specials[name]
    return name.replace("_", " ").title()


@dataclass(frozen=True)
class SocketRef:
    """A named output (or group-input) socket that can be wired into another node."""

    node: str
    socket: str
    socket_type: SocketType | None = None

    def as_link_src(self) -> tuple[str, str]:
        return self.node, self.socket


@dataclass
class NodeHandle:
    """Handle to a node already in the graph. Attribute access yields output sockets."""

    graph: Graph
    id: str
    spec: NodeSpec | None = None

    def out(self, socket: str) -> SocketRef:
        spec = self.spec
        socket_type = None
        if spec is not None:
            found = spec.output_map().get(socket)
            if found is None:
                lowered = {s.identifier.lower(): s for s in spec.outputs}
                found = lowered.get(socket.lower())
            if found is not None:
                socket = found.identifier
                socket_type = found.socket_type
        return SocketRef(self.id, socket, socket_type)

    def __getitem__(self, socket: str | int) -> SocketRef:
        if isinstance(socket, int):
            if self.spec is None or socket >= len(self.spec.outputs):
                return SocketRef(self.id, str(socket))
            spec = self.spec.outputs[socket]
            return SocketRef(self.id, spec.identifier, spec.socket_type)
        return self.out(socket)

    def __getattr__(self, name: str) -> SocketRef:
        if name.startswith("_"):
            raise AttributeError(name)
        if self.spec is not None:
            ident = _snake_to_socket(name)
            outputs = self.spec.output_map()
            if ident in outputs:
                return self.out(ident)
            lowered = {key.lower(): key for key in outputs}
            if ident.lower() in lowered:
                return self.out(lowered[ident.lower()])
            if name.lower() in ("shader", "bsdf") and "BSDF" in outputs:
                return self.out("BSDF")
            if name.lower() == "shader" and "Shader" in outputs:
                return self.out("Shader")
        return self.out(_snake_to_socket(name))

    def as_socket(self) -> SocketRef:
        if self.spec is not None:
            primary = self.spec.primary_output()
            if primary is not None:
                return SocketRef(self.id, primary.identifier, primary.socket_type)
            if len(self.spec.outputs) == 1:
                only = self.spec.outputs[0]
                return SocketRef(self.id, only.identifier, only.socket_type)
        return SocketRef(self.id, "BSDF", SocketType.SHADER)


class Graph:
    """Author a Shader Node tree as data."""

    def __init__(
        self,
        name: str,
        *,
        kind: GraphKind | str = GraphKind.GROUP,
        blender: str = "4.2",
    ) -> None:
        self.name = name
        self.kind = GraphKind(kind)
        self.blender = blender
        self._inputs: list[InterfaceItem] = []
        self._outputs: list[InterfaceItem] = []
        self._nodes: dict[str, Node] = {}
        self._links: list[Link] = []
        self._used_ids: set[str] = set()
        self._id_properties: dict[str, JsonValue] = {}
        self._input_node_id = "Group Input"
        out_id, _out_type = _KIND_OUTPUT[self.kind]
        self._output_node_id = out_id
        self._ensure_io_nodes()

    # --- master markers ----------------------------------------------------

    def set_id_property(self, key: str, value: JsonValue) -> None:
        self._id_properties[key] = jsonify(value)

    def mark_master(
        self,
        category: str,
        *,
        origin: str = "framework",
        version: int = 1,
    ) -> None:
        from shader_as_code.masters import master_props

        for key, value in master_props(category, origin=origin, version=version).items():
            self.set_id_property(key, value)

    # --- interface ---------------------------------------------------------

    def input(
        self,
        name: str,
        socket: SocketType | str,
        default: JsonValue = None,
        *,
        min: float | None = None,
        max: float | None = None,
        subtype: str | None = None,
        description: str = "",
        panel: str = "",
    ) -> SocketRef:
        sock = socket if isinstance(socket, SocketType) else SocketType(socket)
        item = InterfaceItem(
            name=name,
            socket=sock,
            default=jsonify(default) if default is not None else None,
            min=min,
            max=max,
            subtype=subtype,
            description=description,
            panel=panel,
        )
        existing = next((i for i in self._inputs if i.name == name), None)
        if existing is not None:
            self._inputs[self._inputs.index(existing)] = item
        else:
            self._inputs.append(item)
        return SocketRef(self._input_node_id, name, sock)

    def input_float(
        self,
        name: str,
        default: float = 0.0,
        *,
        min: float | None = None,
        max: float | None = None,
        subtype: str | None = None,
        description: str = "",
        panel: str = "",
    ) -> SocketRef:
        return self.input(
            name,
            SocketType.FLOAT,
            default,
            min=min,
            max=max,
            subtype=subtype,
            description=description,
            panel=panel,
        )

    def input_int(
        self,
        name: str,
        default: int = 0,
        *,
        min: float | None = None,
        max: float | None = None,
        description: str = "",
        panel: str = "",
    ) -> SocketRef:
        return self.input(
            name,
            SocketType.INT,
            default,
            min=min,
            max=max,
            description=description,
            panel=panel,
        )

    def input_bool(
        self,
        name: str,
        default: bool = False,
        *,
        description: str = "",
        panel: str = "",
    ) -> SocketRef:
        return self.input(name, SocketType.BOOLEAN, default, description=description, panel=panel)

    def input_vector(
        self,
        name: str,
        default: Sequence[float] = (0.0, 0.0, 0.0),
        *,
        description: str = "",
        panel: str = "",
    ) -> SocketRef:
        return self.input(
            name, SocketType.VECTOR, tuple(default), description=description, panel=panel
        )

    def input_color(
        self,
        name: str,
        default: Sequence[float] = (0.8, 0.8, 0.8, 1.0),
        *,
        description: str = "",
        panel: str = "",
    ) -> SocketRef:
        return self.input(
            name, SocketType.COLOR, tuple(default), description=description, panel=panel
        )

    def input_shader(self, name: str = "Shader", *, description: str = "") -> SocketRef:
        return self.input(name, SocketType.SHADER, description=description)

    def output(
        self,
        source: InputValue,
        name: str = "BSDF",
        socket: SocketType | str | None = None,
    ) -> SocketRef:
        if self.kind != GraphKind.GROUP:
            return self._output_owned(source, name)
        sock = None if socket is None else (
            socket if isinstance(socket, SocketType) else SocketType(socket)
        )
        if isinstance(source, SocketRef) and sock is None:
            sock = source.socket_type
        if isinstance(source, NodeHandle) and sock is None:
            source = source.as_socket()
            sock = source.socket_type
        if sock is None:
            sock = SocketType.SHADER
        item = InterfaceItem(name=name, socket=sock)
        existing = next((i for i in self._outputs if i.name == name), None)
        if existing is not None:
            self._outputs[self._outputs.index(existing)] = item
        else:
            self._outputs.append(item)
        self._connect(source, self._output_node_id, name)
        return SocketRef(self._output_node_id, name, sock)

    def output_shader(self, source: InputValue, name: str = "BSDF") -> SocketRef:
        if self.kind == GraphKind.GROUP:
            return self.output(source, name, SocketType.SHADER)
        return self._output_owned(source, "Surface")

    def _output_owned(self, source: InputValue, socket: str) -> SocketRef:
        self._connect(source, self._output_node_id, socket)
        return SocketRef(self._output_node_id, socket, SocketType.SHADER)

    # --- generic node spawn ------------------------------------------------

    def node(
        self,
        bl_idname: str,
        *,
        id: str | None = None,
        label: str = "",
        location: Sequence[float] | None = None,
        hide: bool = False,
        mute: bool = False,
        parent: str | None = None,
        inputs: dict[str, InputValue] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> NodeHandle:
        spec = get_spec(bl_idname)
        node_id = self._fresh_id(id or (spec.method if spec else bl_idname))
        recorded_inputs: dict[str, JsonValue] = {}
        for key, value in (inputs or {}).items():
            ident = self._resolve_input_ident(spec, key)
            if isinstance(value, (SocketRef, NodeHandle)):
                self._connect(value, node_id, ident)
                continue
            if spec is not None:
                sock = spec.input_map().get(ident)
                if sock is not None and sock.default is not None and values_equal(value, sock.default):
                    continue
            recorded_inputs[ident] = jsonify(value)
        recorded_props: dict[str, JsonValue] = {}
        for key, value in (properties or {}).items():
            if spec is not None:
                prop = next((p for p in spec.properties if p.name == key), None)
                if prop is not None and values_equal(value, prop.default):
                    continue
            recorded_props[key] = jsonify(value)
        loc = None if location is None else (float(location[0]), float(location[1]))
        self._nodes[node_id] = Node(
            id=node_id,
            type=bl_idname,
            label=label,
            location=loc,
            hide=hide,
            mute=mute,
            parent=parent,
            inputs=recorded_inputs,
            properties=recorded_props,
        )
        return NodeHandle(self, node_id, spec)

    def link(self, source: InputValue, target: NodeHandle | str, socket: str) -> None:
        node_id = target.id if isinstance(target, NodeHandle) else target
        self._connect(source, node_id, socket)

    # --- typed factories ---------------------------------------------------

    def principled_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfPrincipled", id=id, kwargs=kwargs)

    def diffuse_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfDiffuse", id=id, kwargs=kwargs)

    def glossy_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfGlossy", id=id, kwargs=kwargs)

    def glass_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfGlass", id=id, kwargs=kwargs)

    def transparent_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfTransparent", id=id, kwargs=kwargs)

    def translucent_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfTranslucent", id=id, kwargs=kwargs)

    def refraction_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfRefraction", id=id, kwargs=kwargs)

    def sheen_bsdf(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBsdfSheen", id=id, kwargs=kwargs)

    def emission(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeEmission", id=id, kwargs=kwargs)

    def holdout(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeHoldout", id=id, kwargs=kwargs)

    def background(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeBackground", id=id, kwargs=kwargs)

    def mix_shader(
        self,
        fac: InputValue = 0.5,
        shader: InputValue = None,
        shader_001: InputValue = None,
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Fac": fac}
        if shader is not None:
            inputs["Shader"] = shader
        if shader_001 is not None:
            inputs["Shader_001"] = shader_001
        return self.node("ShaderNodeMixShader", id=id, inputs=inputs, **node_kw)

    def add_shader(
        self,
        shader: InputValue = None,
        shader_001: InputValue = None,
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {}
        if shader is not None:
            inputs["Shader"] = shader
        if shader_001 is not None:
            inputs["Shader_001"] = shader_001
        return self.node("ShaderNodeAddShader", id=id, inputs=inputs, **node_kw)

    def material_output(
        self,
        surface: InputValue = None,
        *,
        volume: InputValue = None,
        displacement: InputValue = None,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {}
        if surface is not None:
            inputs["Surface"] = surface
        if volume is not None:
            inputs["Volume"] = volume
        if displacement is not None:
            inputs["Displacement"] = displacement
        return self.node(MATERIAL_OUTPUT, id=id or "Material Output", inputs=inputs, **node_kw)

    def mapping(
        self,
        vector: InputValue = None,
        *,
        location: InputValue = (0.0, 0.0, 0.0),
        rotation: InputValue = (0.0, 0.0, 0.0),
        scale: InputValue = (1.0, 1.0, 1.0),
        vector_type: str = "POINT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {
            "Location": location,
            "Rotation": rotation,
            "Scale": scale,
        }
        if vector is not None:
            inputs["Vector"] = vector
        return self.node(
            "ShaderNodeMapping",
            id=id,
            inputs=inputs,
            properties={"vector_type": vector_type},
            **node_kw,
        )

    def tex_coord(self, *, from_instancer: bool = False, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node(
            "ShaderNodeTexCoord",
            id=id,
            properties={"from_instancer": from_instancer},
            **node_kw,
        )

    def uv_map(
        self,
        *,
        uv_map: str = "",
        from_instancer: bool = False,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeUVMap",
            id=id,
            properties={"uv_map": uv_map, "from_instancer": from_instancer},
            **node_kw,
        )

    def image_texture(
        self,
        *,
        vector: InputValue = None,
        image: str | None = None,
        interpolation: str = "Linear",
        projection: str = "FLAT",
        extension: str = "REPEAT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {}
        if vector is not None:
            inputs["Vector"] = vector
        properties: dict[str, Any] = {
            "interpolation": interpolation,
            "projection": projection,
            "extension": extension,
        }
        if image is not None:
            properties["image"] = image
        return self.node(
            "ShaderNodeTexImage",
            id=id,
            inputs=inputs,
            properties=properties,
            **node_kw,
        )

    def noise_texture(
        self,
        *,
        scale: InputValue = 5.0,
        detail: InputValue = 2.0,
        roughness: InputValue = 0.5,
        lacunarity: InputValue = 2.0,
        distortion: InputValue = 0.0,
        vector: InputValue = None,
        noise_dimensions: str = "3D",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {
            "Scale": scale,
            "Detail": detail,
            "Roughness": roughness,
            "Lacunarity": lacunarity,
            "Distortion": distortion,
        }
        if vector is not None:
            inputs["Vector"] = vector
        return self.node(
            "ShaderNodeTexNoise",
            id=id,
            inputs=inputs,
            properties={"noise_dimensions": noise_dimensions},
            **node_kw,
        )

    def voronoi_texture(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeTexVoronoi", id=id, kwargs=kwargs)

    def normal_map(
        self,
        color: InputValue = (0.5, 0.5, 1.0, 1.0),
        *,
        strength: InputValue = 1.0,
        space: str = "TANGENT",
        uv_map: str = "",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeNormalMap",
            id=id,
            inputs={"Strength": strength, "Color": color},
            properties={"space": space, "uv_map": uv_map},
            **node_kw,
        )

    def bump(
        self,
        height: InputValue = None,
        *,
        strength: InputValue = 1.0,
        distance: InputValue = 1.0,
        normal: InputValue = None,
        invert: bool = False,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Strength": strength, "Distance": distance}
        if height is not None:
            inputs["Height"] = height
        if normal is not None:
            inputs["Normal"] = normal
        return self.node(
            "ShaderNodeBump",
            id=id,
            inputs=inputs,
            properties={"invert": invert},
            **node_kw,
        )

    def displacement(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeDisplacement", id=id, kwargs=kwargs)

    def math(
        self,
        operation: str,
        value: InputValue = 0.5,
        value_001: InputValue = 0.5,
        value_002: InputValue | None = None,
        *,
        use_clamp: bool = False,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Value": value, "Value_001": value_001}
        if value_002 is not None:
            inputs["Value_002"] = value_002
        return self.node(
            "ShaderNodeMath",
            id=id,
            inputs=inputs,
            properties={"operation": operation, "use_clamp": use_clamp},
            **node_kw,
        )

    def vector_math(
        self,
        operation: str,
        vector: InputValue = (0.0, 0.0, 0.0),
        vector_001: InputValue | None = None,
        *,
        scale: InputValue | None = None,
        vector_002: InputValue | None = None,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Vector": vector}
        if vector_001 is not None:
            inputs["Vector_001"] = vector_001
        if vector_002 is not None:
            inputs["Vector_002"] = vector_002
        if scale is not None:
            inputs["Scale"] = scale
        return self.node(
            "ShaderNodeVectorMath",
            id=id,
            inputs=inputs,
            properties={"operation": operation},
            **node_kw,
        )

    def map_range(
        self,
        value: InputValue,
        *,
        from_min: InputValue = 0.0,
        from_max: InputValue = 1.0,
        to_min: InputValue = 0.0,
        to_max: InputValue = 1.0,
        clamp: bool = True,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeMapRange",
            id=id,
            inputs={
                "Value": value,
                "From Min": from_min,
                "From Max": from_max,
                "To Min": to_min,
                "To Max": to_max,
            },
            properties={"clamp": clamp},
            **node_kw,
        )

    def clamp(
        self,
        value: InputValue,
        *,
        min: InputValue = 0.0,
        max: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeClamp",
            id=id,
            inputs={"Value": value, "Min": min, "Max": max},
            **node_kw,
        )

    def mix(
        self,
        factor: InputValue = 0.5,
        a: InputValue = 0.0,
        b: InputValue = 0.0,
        *,
        data_type: str = "FLOAT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeMix",
            id=id,
            inputs={"Factor": factor, "A": a, "B": b},
            properties={"data_type": data_type},
            **node_kw,
        )

    def mix_color(
        self,
        factor: InputValue = 0.5,
        a: InputValue = (0.5, 0.5, 0.5, 1.0),
        b: InputValue = (0.5, 0.5, 0.5, 1.0),
        *,
        blend_type: str = "MIX",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeMix",
            id=id,
            inputs={"Factor": factor, "A": a, "B": b},
            properties={"data_type": "RGBA", "blend_type": blend_type},
            **node_kw,
        )

    def separate_xyz(self, vector: InputValue, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("ShaderNodeSeparateXYZ", id=id, inputs={"Vector": vector}, **node_kw)

    def combine_xyz(
        self,
        x: InputValue = 0.0,
        y: InputValue = 0.0,
        z: InputValue = 0.0,
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("ShaderNodeCombineXYZ", id=id, inputs={"X": x, "Y": y, "Z": z}, **node_kw)

    def invert(
        self,
        color: InputValue,
        *,
        fac: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("ShaderNodeInvert", id=id, inputs={"Fac": fac, "Color": color}, **node_kw)

    def gamma(
        self,
        color: InputValue,
        gamma: InputValue = 1.0,
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("ShaderNodeGamma", id=id, inputs={"Color": color, "Gamma": gamma}, **node_kw)

    def hue_saturation(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeHueSaturation", id=id, kwargs=kwargs)

    def color_ramp(self, fac: InputValue = 0.5, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("ShaderNodeValToRGB", id=id, inputs={"Fac": fac}, **node_kw)

    def rgb(self, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("ShaderNodeRGB", id=id, **node_kw)

    def value(self, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("ShaderNodeValue", id=id, **node_kw)

    def fresnel(
        self,
        ior: InputValue = 1.45,
        *,
        normal: InputValue = None,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"IOR": ior}
        if normal is not None:
            inputs["Normal"] = normal
        return self.node("ShaderNodeFresnel", id=id, inputs=inputs, **node_kw)

    def layer_weight(self, *, id: str | None = None, **kwargs: Any) -> NodeHandle:
        return self._typed_node("ShaderNodeLayerWeight", id=id, kwargs=kwargs)

    def geometry(self, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("ShaderNodeNewGeometry", id=id, **node_kw)

    def __getattr__(self, name: str) -> Any:
        spec = CATALOG_BY_METHOD.get(name)
        if spec is None:
            raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

        def factory(*args: Any, id: str | None = None, **kwargs: Any) -> NodeHandle:
            inputs: dict[str, InputValue] = {}
            properties: dict[str, Any] = {}
            positional = list(args)
            for sock in spec.inputs:
                if sock.identifier in kwargs:
                    inputs[sock.identifier] = kwargs.pop(sock.identifier)
                elif positional:
                    inputs[sock.identifier] = positional.pop(0)
            for prop in spec.properties:
                if prop.name in kwargs:
                    properties[prop.name] = kwargs.pop(prop.name)
            node_kw = kwargs
            return self.node(
                spec.bl_idname,
                id=id,
                inputs=inputs,
                properties=properties,
                **node_kw,
            )

        factory.__name__ = spec.method
        factory.__doc__ = f"Create a {spec.label} ({spec.bl_idname}) node."
        return factory

    # --- layout ------------------------------------------------------------

    def autolayout(self, *, x_step: float = 280.0, y_step: float = 140.0) -> None:
        """Assign stable left-to-right locations from topology. Existing locations win."""
        levels = self._levels()
        for level, ids in enumerate(levels):
            count = len(ids)
            for i, node_id in enumerate(sorted(ids)):
                node = self._nodes[node_id]
                if node.location is not None:
                    continue
                y = (count - 1) * y_step / 2.0 - i * y_step
                node.location = (level * x_step, y)

    # --- serialize ---------------------------------------------------------

    def to_data(self, *, autolayout: bool = True) -> GraphData:
        if autolayout:
            self.autolayout()
        return GraphData(
            name=self.name,
            kind=self.kind,
            blender=self.blender,
            interface_inputs=list(self._inputs),
            interface_outputs=list(self._outputs),
            nodes=list(self._nodes.values()),
            links=list(self._links),
            id_properties=dict(self._id_properties),
        ).canonical()

    def to_dict(self, *, autolayout: bool = True) -> dict[str, Any]:
        from shader_as_code.dump import to_dict

        return to_dict(self.to_data(autolayout=autolayout))

    def dumps(self, *, autolayout: bool = True) -> str:
        from shader_as_code.dump import dumps

        return dumps(self.to_data(autolayout=autolayout))

    def to_mermaid(self) -> str:
        from shader_as_code.dump import to_mermaid

        return to_mermaid(self.to_data(autolayout=False))

    @classmethod
    def from_data(cls, data: GraphData) -> Graph:
        graph = cls(data.name, kind=data.kind, blender=data.blender)
        graph._inputs = list(data.interface_inputs)
        graph._outputs = list(data.interface_outputs)
        graph._nodes = {node.id: node for node in data.nodes}
        graph._links = list(data.links)
        graph._id_properties = dict(data.id_properties)
        graph._used_ids = set(graph._nodes)
        if "Group Input" in graph._nodes:
            graph._input_node_id = "Group Input"
        out_id, _ = _KIND_OUTPUT[graph.kind]
        if out_id in graph._nodes:
            graph._output_node_id = out_id
        elif "Group Output" in graph._nodes:
            graph._output_node_id = "Group Output"
        return graph

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Graph:
        return cls.from_data(GraphData.from_dict(data))

    # --- internals ---------------------------------------------------------

    def _typed_node(self, bl_idname: str, *, id: str | None, kwargs: dict[str, Any]) -> NodeHandle:
        spec = get_spec(bl_idname)
        node_kw = {k: kwargs.pop(k) for k in list(kwargs) if k in _NODE_KW}
        properties: dict[str, Any] = {}
        inputs: dict[str, InputValue] = {}
        prop_names = {p.name for p in spec.properties} if spec else set()
        for key, value in kwargs.items():
            if value is None:
                continue
            if key in prop_names:
                properties[key] = value
            else:
                inputs[key] = value
        return self.node(bl_idname, id=id, inputs=inputs, properties=properties, **node_kw)

    def _ensure_io_nodes(self) -> None:
        if self.kind == GraphKind.GROUP:
            if self._input_node_id not in self._nodes:
                self._nodes[self._input_node_id] = Node(id=self._input_node_id, type=GROUP_INPUT)
                self._used_ids.add(self._input_node_id)
            if self._output_node_id not in self._nodes:
                self._nodes[self._output_node_id] = Node(id=self._output_node_id, type=GROUP_OUTPUT)
                self._used_ids.add(self._output_node_id)
            return
        out_id, out_type = _KIND_OUTPUT[self.kind]
        if out_id not in self._nodes:
            self._nodes[out_id] = Node(id=out_id, type=out_type)
            self._used_ids.add(out_id)

    def _fresh_id(self, base: str) -> str:
        candidate = base
        n = 1
        while candidate in self._used_ids:
            n += 1
            candidate = f"{base}_{n}"
        self._used_ids.add(candidate)
        return candidate

    def _resolve_input_ident(self, spec: NodeSpec | None, key: str) -> str:
        if spec is None:
            return key
        if key in spec.input_map():
            return key
        ident = _snake_to_socket(key)
        if ident in spec.input_map():
            return ident
        lowered = {s.identifier.lower(): s.identifier for s in spec.inputs}
        if key.lower() in lowered:
            return lowered[key.lower()]
        if ident.lower() in lowered:
            return lowered[ident.lower()]
        return key

    def _as_socket(self, value: InputValue) -> SocketRef:
        if isinstance(value, SocketRef):
            return value
        if isinstance(value, NodeHandle):
            return value.as_socket()
        raise TypeError(f"Expected a socket or node handle, got {type(value)!r}")

    def _connect(self, source: InputValue, to_node: str, to_socket: str) -> None:
        ref = self._as_socket(source)
        spec = get_spec(self._nodes[to_node].type) if to_node in self._nodes else None
        ident = self._resolve_input_ident(spec, to_socket)
        link = Link(ref.node, ref.socket, to_node, ident)
        if any(existing.key() == link.key() for existing in self._links):
            return
        self._links.append(link)

    def _levels(self) -> list[list[str]]:
        incoming: dict[str, set[str]] = {node_id: set() for node_id in self._nodes}
        for link in self._links:
            if link.from_node in incoming and link.to_node in incoming:
                incoming[link.to_node].add(link.from_node)
        levels: list[list[str]] = []
        remaining = set(self._nodes)
        while remaining:
            ready = [n for n in remaining if incoming[n].isdisjoint(remaining)]
            if not ready:
                ready = sorted(remaining)
            levels.append(ready)
            remaining.difference_update(ready)
        return levels
