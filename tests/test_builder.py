from __future__ import annotations

from shader_as_code import Graph, SocketType, validate
from shader_as_code.samples import build_metal, build_noise_roughness, build_surface
from shader_as_code.types import GraphKind


def test_principled_to_output_wires_bsdf() -> None:
    g = Graph("Surface")
    bsdf = g.principled_bsdf(base_color=(0.2, 0.3, 0.4, 1.0), roughness=0.4, id="bsdf")
    g.output_shader(bsdf)
    data = g.to_data()
    assert data.name == "Surface"
    assert {n.id for n in data.nodes} >= {"bsdf", "Group Input", "Group Output"}
    links = {(ln.from_node, ln.from_socket, ln.to_node, ln.to_socket) for ln in data.links}
    assert ("bsdf", "BSDF", "Group Output", "BSDF") in links
    node = data.node_map()["bsdf"]
    assert node.inputs["Base Color"] == [0.2, 0.3, 0.4, 1.0]
    assert node.inputs["Roughness"] == 0.4
    assert validate(data) == []


def test_input_socket_is_group_input_ref() -> None:
    g = Graph("Tinted")
    color = g.input_color("Color", (1, 0, 0, 1))
    bsdf = g.principled_bsdf(base_color=color, id="bsdf")
    g.output_shader(bsdf.bsdf)
    data = g.to_data()
    assert data.interface_inputs[0].name == "Color"
    assert data.interface_inputs[0].socket == SocketType.COLOR
    link = next(ln for ln in data.links if ln.to_node == "bsdf")
    assert link.from_node == "Group Input"
    assert link.from_socket == "Color"


def test_unknown_bl_idname_allowed() -> None:
    g = Graph("Custom")
    node = g.node("ShaderNodeBsdfHairPrincipled", id="hair", inputs={"Melanin": 0.8})
    g.output_shader(node)
    data = g.to_data()
    assert data.node_map()["hair"].type == "ShaderNodeBsdfHairPrincipled"
    assert data.node_map()["hair"].inputs["Melanin"] == 0.8
    assert validate(data) == []


def test_duplicate_ids_get_suffix() -> None:
    g = Graph("Dup")
    g.principled_bsdf(id="bsdf")
    second = g.principled_bsdf(id="bsdf")
    g.output_shader(second)
    assert second.id == "bsdf_2"


def test_handle_attr_and_index() -> None:
    g = Graph("Attr")
    bsdf = g.principled_bsdf(id="bsdf")
    assert bsdf.bsdf.socket == "BSDF"
    assert bsdf["BSDF"].node == "bsdf"
    assert bsdf[0].socket == "BSDF"
    g.output_shader(bsdf)


def test_samples_validate() -> None:
    for build in (build_surface, build_metal, build_noise_roughness):
        errors = validate(build().to_data())
        assert errors == [], errors


def test_material_kind_uses_material_output() -> None:
    g = Graph("Noise Roughness", kind=GraphKind.MATERIAL)
    bsdf = g.principled_bsdf(id="bsdf")
    g.output_shader(bsdf)
    data = g.to_data()
    types = {n.type for n in data.nodes}
    assert "ShaderNodeOutputMaterial" in types
    assert "NodeGroupOutput" not in types
    links = {(ln.from_node, ln.from_socket, ln.to_node, ln.to_socket) for ln in data.links}
    assert ("bsdf", "BSDF", "Material Output", "Surface") in links
    assert validate(data) == []
