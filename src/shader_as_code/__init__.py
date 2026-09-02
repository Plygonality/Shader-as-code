"""Shader Node trees as data.

This library is the graph. Master-Node instantiates category masters.
Plygon-mcp applies a dump and checks the viewport.
"""

from shader_as_code.diff import GraphDiff, diff_graphs, format_diff
from shader_as_code.dump import dumps, from_dict, loads, to_dict
from shader_as_code.graph import Graph, NodeHandle, SocketRef
from shader_as_code.ir import FORMAT, FORMAT_VERSION, GraphData, InterfaceItem, Link, Node
from shader_as_code.types import GraphKind, SocketType
from shader_as_code.validate import GraphError, validate

__all__ = [
    "FORMAT",
    "FORMAT_VERSION",
    "Graph",
    "GraphData",
    "GraphDiff",
    "GraphError",
    "GraphKind",
    "InterfaceItem",
    "Link",
    "Node",
    "NodeHandle",
    "SocketRef",
    "SocketType",
    "diff_graphs",
    "dumps",
    "format_diff",
    "from_dict",
    "loads",
    "to_dict",
    "validate",
]

__version__ = "0.1.0"
