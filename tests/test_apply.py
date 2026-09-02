from __future__ import annotations

from shader_as_code.apply import apply, dump_from_bpy, to_apply_script, to_dump_script
from shader_as_code.samples import build_metal, build_surface
from tests.fake_bpy import FakeBpy


def _ids(tree) -> set[str]:
    return {node.name for node in tree.nodes}


def _link_keys(tree) -> set[tuple[str, str, str, str]]:
    keys = set()
    for link in tree.links:
        keys.add(
            (
                link.from_node.name,
                link.from_socket.identifier,
                link.to_node.name,
                link.to_socket.identifier,
            )
        )
    return keys


def test_apply_metal_creates_nodes_and_links() -> None:
    bpy = FakeBpy()
    graph = build_metal().to_data()
    tree = apply(graph, bpy=bpy, material_name="Metal")
    assert tree.name == "MN Metal"
    assert tree.bl_idname == "ShaderNodeTree"
    assert tree["mn.is_master"] is True
    assert tree["mn.category"] == "metal"
    assert "bsdf" in _ids(tree)
    keys = _link_keys(tree)
    assert ("bsdf", "BSDF", "Group Output", "BSDF") in keys
    assert ("Group Input", "Color", "bsdf", "Base Color") in keys
    mat = bpy.data.materials["Metal"]
    assert mat["mn.master"] == "MN Metal"


def test_apply_then_dump_preserves_topology() -> None:
    bpy = FakeBpy()
    original = build_surface().to_data()
    tree = apply(original, bpy=bpy)
    dumped = dump_from_bpy(tree)
    assert dumped["name"] == original.name
    assert dumped["format"] == "shader-as-code"
    assert dumped["id_properties"]["mn.category"] == "surface"
    orig_ids = {n.id for n in original.nodes}
    dump_ids = {n["id"] for n in dumped["nodes"]}
    assert orig_ids == dump_ids
    orig_links = {(ln.from_node, ln.from_socket, ln.to_node, ln.to_socket) for ln in original.links}
    dump_links = {(ln["from"][0], ln["from"][1], ln["to"][0], ln["to"][1]) for ln in dumped["links"]}
    assert orig_links == dump_links
    rebuilt = apply(dumped, bpy=FakeBpy())
    assert _link_keys(rebuilt) == _link_keys(tree)


def test_apply_script_is_executable_python() -> None:
    script = to_apply_script(build_metal().to_data(), material_name="Metal")
    compile(script, "<apply>", "exec")
    assert "apply_graph_dict" in script
    assert '"name": "MN Metal"' in script
    dump_script = to_dump_script("MN Metal")
    compile(dump_script, "<dump>", "exec")
    assert "dump_tree_by_name" in dump_script
