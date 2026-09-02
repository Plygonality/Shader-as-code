"""Canonical Shader Node graph IR.

The dump format is the source of truth. A ``.blend`` is a cache you apply into.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shader_as_code.types import GraphKind, JsonValue, SocketType, jsonify

FORMAT = "shader-as-code"
FORMAT_VERSION = 1


@dataclass
class InterfaceItem:
    name: str
    socket: SocketType
    default: JsonValue = None
    min: float | None = None
    max: float | None = None
    subtype: str | None = None
    description: str = ""
    panel: str = ""

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "socket": self.socket.value,
        }
        if self.default is not None:
            data["default"] = jsonify(self.default)
        if self.min is not None:
            data["min"] = jsonify(self.min)
        if self.max is not None:
            data["max"] = jsonify(self.max)
        if self.subtype:
            data["subtype"] = self.subtype
        if self.description:
            data["description"] = self.description
        if self.panel:
            data["panel"] = self.panel
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InterfaceItem:
        return cls(
            name=data["name"],
            socket=SocketType(data["socket"]),
            default=data.get("default"),
            min=data.get("min"),
            max=data.get("max"),
            subtype=data.get("subtype"),
            description=data.get("description", ""),
            panel=data.get("panel", ""),
        )


@dataclass
class Node:
    id: str
    type: str
    label: str = ""
    location: tuple[float, float] | None = None
    hide: bool = False
    mute: bool = False
    parent: str | None = None
    inputs: dict[str, JsonValue] = field(default_factory=dict)
    properties: dict[str, JsonValue] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
        }
        if self.label:
            data["label"] = self.label
        if self.location is not None:
            data["location"] = [jsonify(self.location[0]), jsonify(self.location[1])]
        if self.hide:
            data["hide"] = True
        if self.mute:
            data["mute"] = True
        if self.parent:
            data["parent"] = self.parent
        if self.inputs:
            data["inputs"] = {k: jsonify(v) for k, v in sorted(self.inputs.items())}
        if self.properties:
            data["properties"] = {k: jsonify(v) for k, v in sorted(self.properties.items())}
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        location = data.get("location")
        loc = None
        if location is not None:
            loc = (float(location[0]), float(location[1]))
        return cls(
            id=data["id"],
            type=data["type"],
            label=data.get("label", ""),
            location=loc,
            hide=bool(data.get("hide", False)),
            mute=bool(data.get("mute", False)),
            parent=data.get("parent"),
            inputs=dict(data.get("inputs") or {}),
            properties=dict(data.get("properties") or {}),
        )


@dataclass
class Link:
    from_node: str
    from_socket: str
    to_node: str
    to_socket: str

    def key(self) -> tuple[str, str, str, str]:
        return (self.from_node, self.from_socket, self.to_node, self.to_socket)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from": [self.from_node, self.from_socket],
            "to": [self.to_node, self.to_socket],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Link:
        if "from" in data:
            src, dst = data["from"], data["to"]
            return cls(str(src[0]), str(src[1]), str(dst[0]), str(dst[1]))
        return cls(
            data["from_node"],
            str(data["from_socket"]),
            data["to_node"],
            str(data["to_socket"]),
        )


@dataclass
class GraphData:
    name: str
    kind: GraphKind = GraphKind.GROUP
    blender: str = "4.2"
    interface_inputs: list[InterfaceItem] = field(default_factory=list)
    interface_outputs: list[InterfaceItem] = field(default_factory=list)
    nodes: list[Node] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    id_properties: dict[str, JsonValue] = field(default_factory=dict)

    def node_map(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    def canonical(self) -> GraphData:
        """Return a copy sorted for stable dumps and diffs."""
        return GraphData(
            name=self.name,
            kind=self.kind,
            blender=self.blender,
            interface_inputs=list(self.interface_inputs),
            interface_outputs=list(self.interface_outputs),
            nodes=sorted(self.nodes, key=lambda n: n.id),
            links=sorted(self.links, key=lambda ln: ln.key()),
            id_properties=dict(sorted(self.id_properties.items())),
        )

    def to_dict(self) -> dict[str, Any]:
        graph = self.canonical()
        payload: dict[str, Any] = {
            "format": FORMAT,
            "version": FORMAT_VERSION,
            "name": graph.name,
            "kind": graph.kind.value,
            "blender": graph.blender,
        }
        if graph.id_properties:
            payload["id_properties"] = {k: jsonify(v) for k, v in graph.id_properties.items()}
        payload["interface"] = {
            "inputs": [item.to_dict() for item in graph.interface_inputs],
            "outputs": [item.to_dict() for item in graph.interface_outputs],
        }
        payload["nodes"] = [node.to_dict() for node in graph.nodes]
        payload["links"] = [link.to_dict() for link in graph.links]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GraphData:
        fmt = data.get("format")
        if fmt not in (None, FORMAT):
            raise ValueError(f"Unsupported graph format: {fmt!r}")
        version = data.get("version", FORMAT_VERSION)
        if int(version) != FORMAT_VERSION:
            raise ValueError(f"Unsupported shader-as-code version: {version}")
        interface = data.get("interface") or {}
        kind_raw = data.get("kind", GraphKind.GROUP.value)
        return cls(
            name=data["name"],
            kind=GraphKind(kind_raw),
            blender=str(data.get("blender", "4.2")),
            interface_inputs=[InterfaceItem.from_dict(x) for x in interface.get("inputs", [])],
            interface_outputs=[InterfaceItem.from_dict(x) for x in interface.get("outputs", [])],
            nodes=[Node.from_dict(x) for x in data.get("nodes", [])],
            links=[Link.from_dict(x) for x in data.get("links", [])],
            id_properties=dict(data.get("id_properties") or {}),
        ).canonical()
