from __future__ import annotations

from shader_as_code.masters import (
    CATALOG,
    CATEGORIES,
    PROP_CATEGORY,
    PROP_IS_MASTER,
    PROP_ORIGIN,
    PROP_VERSION,
    build_master,
    get_category,
    tree_name_for,
)
from shader_as_code.validate import validate


def test_all_seven_categories_emit() -> None:
    assert tuple(CATALOG) == CATEGORIES
    for category in CATEGORIES:
        graph = build_master(category)
        data = graph.to_data()
        assert data.name == tree_name_for(category)
        assert data.kind.value == "GROUP"
        assert data.id_properties[PROP_IS_MASTER] is True
        assert data.id_properties[PROP_CATEGORY] == category
        assert data.id_properties[PROP_ORIGIN] == "framework"
        assert data.id_properties[PROP_VERSION] == 1
        assert validate(data) == []
        spec = get_category(category)
        input_names = [item.name for item in data.interface_inputs]
        assert input_names == [s.name for s in spec.sockets]
        assert data.interface_outputs[0].name == "BSDF"
        assert data.interface_outputs[0].socket.value == "SHADER"
        nodes = data.node_map()
        assert nodes["bsdf"].type == "ShaderNodeBsdfPrincipled"
        assert nodes["bsdf"].label == spec.label
        links = {(ln.from_node, ln.from_socket, ln.to_node, ln.to_socket) for ln in data.links}
        assert ("bsdf", "BSDF", "Group Output", "BSDF") in links
        for master_name, principled_name in spec.principled_map.items():
            assert ("Group Input", master_name, "bsdf", principled_name) in links
        for name, value in spec.constants.items():
            recorded = nodes["bsdf"].inputs.get(name)
            if recorded is not None:
                assert recorded == value or recorded == [value]


def test_metal_locks_conductor_constants() -> None:
    data = build_master("metal").to_data()
    inputs = data.node_map()["bsdf"].inputs
    assert inputs["Metallic"] == 1
    assert inputs["Specular IOR Level"] == 1


def test_unknown_category_rejected() -> None:
    try:
        build_master("wood")
    except KeyError as exc:
        assert "wood" in str(exc)
    else:
        raise AssertionError("expected KeyError")
