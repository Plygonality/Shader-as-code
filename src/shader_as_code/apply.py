"""Apply / dump helpers and Plygon-mcp script generation.

The useful artifact is the graph JSON plus this library. Plygon-mcp is how an
agent pushes a dump into a live Blender session and screenshots the viewport.
Master-Node instantiates category masters from these dumps.
"""

from __future__ import annotations

import json
from pathlib import Path

from shader_as_code.dump import to_dict
from shader_as_code.ir import GraphData
from shader_as_code.runtime_apply import apply_graph_dict, dump_tree, dump_tree_by_name

_RUNTIME_PATH = Path(__file__).with_name("runtime_apply.py")


def apply(graph: GraphData | dict, bpy=None, **kwargs):
    """Apply a graph inside Blender. Imports ``bpy`` if omitted."""
    if bpy is None:
        bpy = __import__("bpy")
    payload = graph if isinstance(graph, dict) else to_dict(graph)
    return apply_graph_dict(payload, bpy, **kwargs)


def dump_from_bpy(tree, *, blender: str = "4.2", kind: str | None = None, name: str | None = None) -> dict:
    return dump_tree(tree, blender=blender, kind=kind, name=name)


def to_apply_script(
    graph: GraphData | dict,
    *,
    material_name: str | None = None,
    object_name: str | None = None,
    replace: bool = True,
) -> str:
    """Self-contained bpy script. Paste into Plygon-mcp ``execute_blender_code``."""
    payload = graph if isinstance(graph, dict) else to_dict(graph)
    runtime = _RUNTIME_PATH.read_text(encoding="utf-8")
    call = (
        "apply_graph_dict(\n"
        f"    {json.dumps(payload, indent=2)},\n"
        "    __import__('bpy'),\n"
        f"    material_name={material_name!r},\n"
        f"    object_name={object_name!r},\n"
        f"    replace={replace!r},\n"
        ")\n"
    )
    return runtime + "\n\n" + call


def to_dump_script(tree_name: str, *, blender: str = "4.2") -> str:
    """Self-contained bpy script that prints a graph dump as JSON."""
    runtime = _RUNTIME_PATH.read_text(encoding="utf-8")
    call = (
        "import json\n"
        f"result = dump_tree_by_name(__import__('bpy'), {tree_name!r}, blender={blender!r})\n"
        "print(json.dumps(result, indent=2))\n"
    )
    return runtime + "\n\n" + call


__all__ = [
    "apply",
    "apply_graph_dict",
    "dump_from_bpy",
    "dump_tree",
    "dump_tree_by_name",
    "to_apply_script",
    "to_dump_script",
]
