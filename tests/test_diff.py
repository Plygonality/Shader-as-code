from __future__ import annotations

from shader_as_code import Graph, diff_graphs, format_diff
from shader_as_code.samples import build_metal


def test_identical_graphs_empty_diff() -> None:
    a = build_metal().to_data()
    b = build_metal().to_data()
    diff = diff_graphs(a, b)
    assert diff.is_empty()
    assert format_diff(diff) == "No differences.\n"


def test_added_and_removed_nodes() -> None:
    old = Graph("G")
    old.output_shader(old.principled_bsdf(id="bsdf"))
    new = Graph("G")
    new.output_shader(new.emission(id="emit"))
    diff = diff_graphs(old.to_data(), new.to_data())
    assert [n["id"] for n in diff.nodes_added] == ["emit"]
    assert [n["id"] for n in diff.nodes_removed] == ["bsdf"]
    assert any("bsdf.BSDF" in format_diff(diff) for _ in [0])


def test_changed_input_and_link() -> None:
    old = Graph("G")
    old.output_shader(old.principled_bsdf(roughness=0.5, id="bsdf"))
    new = Graph("G")
    roughness = new.input_float("Roughness", 0.25)
    new.output_shader(new.principled_bsdf(roughness=roughness, metallic=1.0, id="bsdf"))
    diff = diff_graphs(old.to_data(), new.to_data())
    assert diff.interface_inputs is not None
    assert diff.links_added
    changed_ids = [c.id for c in diff.nodes_changed]
    assert "bsdf" in changed_ids


def test_layout_ignored_by_default() -> None:
    a = Graph("G")
    a.output_shader(a.principled_bsdf(id="bsdf", location=(0, 0)))
    b = Graph("G")
    b.output_shader(b.principled_bsdf(id="bsdf", location=(100, 50)))
    assert diff_graphs(a.to_data(autolayout=False), b.to_data(autolayout=False)).is_empty()
    diff = diff_graphs(
        a.to_data(autolayout=False),
        b.to_data(autolayout=False),
        include_layout=True,
    )
    assert not diff.is_empty()
    assert any(c.id == "bsdf" for c in diff.nodes_changed)


def test_id_properties_diff() -> None:
    old = Graph("G")
    old.output_shader(old.principled_bsdf(id="bsdf"))
    new = Graph("G")
    new.mark_master("metal")
    new.output_shader(new.principled_bsdf(id="bsdf"))
    diff = diff_graphs(old.to_data(), new.to_data())
    assert diff.id_properties is not None
    assert diff.id_properties["to"]["mn.category"] == "metal"
