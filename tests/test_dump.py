from __future__ import annotations

import json

from shader_as_code import Graph, dumps, from_dict, loads, to_dict
from shader_as_code.dump import fingerprint, to_mermaid
from shader_as_code.samples import build_metal


def test_roundtrip_dict() -> None:
    graph = build_metal()
    payload = graph.to_dict()
    restored = from_dict(payload)
    assert to_dict(restored) == payload


def test_dumps_is_stable() -> None:
    a = dumps(build_metal().to_data())
    b = dumps(build_metal().to_data())
    assert a == b
    json.loads(a)


def test_loads_roundtrip_text() -> None:
    text = build_metal().dumps()
    assert dumps(loads(text)) == text


def test_fingerprint_ignores_layout() -> None:
    g = Graph("A")
    bsdf = g.principled_bsdf(id="bsdf", location=(10, 20))
    g.output_shader(bsdf)
    other = Graph("A")
    bsdf2 = other.principled_bsdf(id="bsdf", location=(99, -4))
    other.output_shader(bsdf2)
    assert fingerprint(g.to_data()) == fingerprint(other.to_data())
    assert fingerprint(g.to_data(), include_layout=True) != fingerprint(
        other.to_data(), include_layout=True
    )


def test_canonical_node_order() -> None:
    g = Graph("Order")
    noise = g.noise_texture(id="noise")
    bsdf = g.principled_bsdf(roughness=noise.fac, id="bsdf")
    g.output_shader(bsdf)
    ids = [n["id"] for n in g.to_dict()["nodes"]]
    assert ids == sorted(ids)


def test_mermaid_contains_nodes_and_edges() -> None:
    text = to_mermaid(build_metal().to_data())
    assert text.startswith("flowchart LR")
    assert "bsdf" in text
    assert "-->" in text
