"""Structural validation of a graph dump. No bpy required."""

from __future__ import annotations

from dataclasses import dataclass

from shader_as_code.catalog import (
    GROUP_INPUT,
    GROUP_OUTPUT,
    LIGHT_OUTPUT,
    MATERIAL_OUTPUT,
    WORLD_OUTPUT,
    get_spec,
)
from shader_as_code.ir import GraphData, Link, Node
from shader_as_code.types import GraphKind


@dataclass
class GraphError:
    code: str
    message: str
    node: str | None = None

    def __str__(self) -> str:
        if self.node:
            return f"{self.code}: {self.node}: {self.message}"
        return f"{self.code}: {self.message}"


_OWNED_OUTPUT = {
    GraphKind.MATERIAL: MATERIAL_OUTPUT,
    GraphKind.WORLD: WORLD_OUTPUT,
    GraphKind.LIGHT: LIGHT_OUTPUT,
}


def validate(graph: GraphData) -> list[GraphError]:
    errors: list[GraphError] = []
    ids = [node.id for node in graph.nodes]
    if len(ids) != len(set(ids)):
        seen: set[str] = set()
        for node_id in ids:
            if node_id in seen:
                errors.append(
                    GraphError("duplicate_id", f"Node id {node_id!r} is used twice", node_id)
                )
            seen.add(node_id)
    nodes = graph.node_map()

    if graph.kind == GraphKind.GROUP:
        if not any(n.type == GROUP_INPUT for n in graph.nodes):
            errors.append(GraphError("missing_group_input", "Graph has no NodeGroupInput"))
        if not any(n.type == GROUP_OUTPUT for n in graph.nodes):
            errors.append(GraphError("missing_group_output", "Graph has no NodeGroupOutput"))
        if not graph.interface_outputs:
            errors.append(GraphError("missing_output", "Graph has no interface outputs"))
    else:
        needed = _OWNED_OUTPUT.get(graph.kind)
        if needed and not any(n.type == needed for n in graph.nodes):
            errors.append(GraphError("missing_output", f"Graph has no {needed}"))

    input_names = [item.name for item in graph.interface_inputs]
    output_names = [item.name for item in graph.interface_outputs]
    if len(input_names) != len(set(input_names)):
        errors.append(GraphError("duplicate_interface", "Duplicate interface input names"))
    if len(output_names) != len(set(output_names)):
        errors.append(GraphError("duplicate_interface", "Duplicate interface output names"))

    for node in graph.nodes:
        errors.extend(_validate_node(node))

    for link in graph.links:
        errors.extend(_validate_link(link, nodes, graph))

    if graph.kind == GraphKind.GROUP:
        output_nodes = [n for n in graph.nodes if n.type == GROUP_OUTPUT]
        if output_nodes:
            out_id = output_nodes[0].id
            wired = {ln.to_socket for ln in graph.links if ln.to_node == out_id}
            for item in graph.interface_outputs:
                if item.name not in wired:
                    errors.append(
                        GraphError(
                            "unwired_output",
                            f"Interface output {item.name!r} is not connected",
                            out_id,
                        )
                    )
    else:
        needed = _OWNED_OUTPUT.get(graph.kind)
        output_nodes = [n for n in graph.nodes if n.type == needed] if needed else []
        if output_nodes:
            out_id = output_nodes[0].id
            wired = {ln.to_socket for ln in graph.links if ln.to_node == out_id}
            if "Surface" not in wired:
                errors.append(
                    GraphError(
                        "unwired_output",
                        "Output Surface is not connected",
                        out_id,
                    )
                )
    return errors


def _validate_node(node: Node) -> list[GraphError]:
    errors: list[GraphError] = []
    spec = get_spec(node.type)
    if spec is None:
        return errors
    known_inputs = spec.input_map()
    for key in node.inputs:
        if key not in known_inputs:
            errors.append(
                GraphError(
                    "unknown_input",
                    f"Input {key!r} is not a catalog socket on {node.type}",
                    node.id,
                )
            )
    known_props = {p.name for p in spec.properties}
    for key in node.properties:
        if known_props and key not in known_props:
            errors.append(
                GraphError(
                    "unknown_property",
                    f"Property {key!r} is not a catalog property on {node.type}",
                    node.id,
                )
            )
            continue
        prop = next((p for p in spec.properties if p.name == key), None)
        if prop is not None and prop.items and node.properties[key] not in prop.items:
            errors.append(
                GraphError(
                    "invalid_property",
                    f"Property {key!r}={node.properties[key]!r} not in {prop.items}",
                    node.id,
                )
            )
    return errors


def _validate_link(link: Link, nodes: dict[str, Node], graph: GraphData) -> list[GraphError]:
    errors: list[GraphError] = []
    if link.from_node not in nodes:
        errors.append(GraphError("dangling_link", f"from_node {link.from_node!r} does not exist"))
        return errors
    if link.to_node not in nodes:
        errors.append(GraphError("dangling_link", f"to_node {link.to_node!r} does not exist"))
        return errors
    src = nodes[link.from_node]
    dst = nodes[link.to_node]
    if src.type == GROUP_INPUT:
        names = {item.name for item in graph.interface_inputs}
        if str(link.from_socket) not in names:
            errors.append(
                GraphError(
                    "unknown_socket",
                    f"Group Input has no socket {link.from_socket!r}",
                    src.id,
                )
            )
    else:
        spec = get_spec(src.type)
        if spec is not None and spec.outputs:
            known = spec.output_map()
            if str(link.from_socket) not in known:
                errors.append(
                    GraphError(
                        "unknown_socket",
                        f"Node {src.type} has no output {link.from_socket!r}",
                        src.id,
                    )
                )
    if dst.type == GROUP_OUTPUT:
        names = {item.name for item in graph.interface_outputs}
        if str(link.to_socket) not in names:
            errors.append(
                GraphError(
                    "unknown_socket",
                    f"Group Output has no socket {link.to_socket!r}",
                    dst.id,
                )
            )
    else:
        spec = get_spec(dst.type)
        if spec is not None and spec.inputs:
            known = spec.input_map()
            if str(link.to_socket) not in known:
                errors.append(
                    GraphError(
                        "unknown_socket",
                        f"Node {dst.type} has no input {link.to_socket!r}",
                        dst.id,
                    )
                )
    return errors
