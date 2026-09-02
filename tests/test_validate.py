from __future__ import annotations

from shader_as_code import Graph, GraphData, InterfaceItem, Link, Node, validate
from shader_as_code.types import SocketType


def test_valid_graph_has_no_errors() -> None:
    g = Graph("Ok")
    g.output_shader(g.principled_bsdf(id="bsdf"))
    assert validate(g.to_data()) == []


def test_unwired_output() -> None:
    g = Graph("Bad")
    g.principled_bsdf(id="bsdf")
    g.output_shader(g.emission(id="emit"))
    data = g.to_data()
    data.links = [ln for ln in data.links if ln.to_node != "Group Output"]
    codes = {e.code for e in validate(data)}
    assert "unwired_output" in codes


def test_dangling_link() -> None:
    g = Graph("Bad")
    g.output_shader(g.principled_bsdf(id="bsdf"))
    data = g.to_data()
    data.links.append(Link("missing", "BSDF", "Group Output", "BSDF"))
    codes = {e.code for e in validate(data)}
    assert "dangling_link" in codes


def test_unknown_socket_on_catalog_node() -> None:
    data = GraphData(
        name="Bad",
        interface_outputs=[InterfaceItem("BSDF", SocketType.SHADER)],
        nodes=[
            Node(id="Group Input", type="NodeGroupInput"),
            Node(id="Group Output", type="NodeGroupOutput"),
            Node(id="bsdf", type="ShaderNodeBsdfPrincipled"),
        ],
        links=[Link("bsdf", "Nope", "Group Output", "BSDF")],
    )
    codes = {e.code for e in validate(data)}
    assert "unknown_socket" in codes


def test_invalid_enum_property() -> None:
    g = Graph("Bad")
    g.output_shader(g.math("NOT_A_REAL_OP", 1, 2, id="math"))
    codes = {e.code for e in validate(g.to_data())}
    assert "invalid_property" in codes
