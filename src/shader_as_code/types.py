"""Socket kinds, graph kinds, and JSON-safe value helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

Vec2 = tuple[float, float]
Vec3 = tuple[float, float, float]
Vec4 = tuple[float, float, float, float]
JsonValue = None | bool | int | float | str | list[Any] | dict[str, Any]


class GraphKind(str, Enum):
    """How Blender should host the ShaderNodeTree."""

    GROUP = "GROUP"
    MATERIAL = "MATERIAL"
    WORLD = "WORLD"
    LIGHT = "LIGHT"


class SocketType(str, Enum):
    """Stable socket kinds used in the dump format.

    These map to Blender ``NodeSocket*`` bl_idnames in apply/dump.
    """

    FLOAT = "FLOAT"
    INT = "INT"
    BOOLEAN = "BOOLEAN"
    VECTOR = "VECTOR"
    ROTATION = "ROTATION"
    MATRIX = "MATRIX"
    COLOR = "COLOR"
    STRING = "STRING"
    SHADER = "SHADER"
    OBJECT = "OBJECT"
    COLLECTION = "COLLECTION"
    MATERIAL = "MATERIAL"
    TEXTURE = "TEXTURE"
    IMAGE = "IMAGE"
    MENU = "MENU"

    def blender_socket(self) -> str:
        return _BLENDER_SOCKET[self]


_BLENDER_SOCKET: dict[SocketType, str] = {
    SocketType.FLOAT: "NodeSocketFloat",
    SocketType.INT: "NodeSocketInt",
    SocketType.BOOLEAN: "NodeSocketBoolean",
    SocketType.VECTOR: "NodeSocketVector",
    SocketType.ROTATION: "NodeSocketRotation",
    SocketType.MATRIX: "NodeSocketMatrix",
    SocketType.COLOR: "NodeSocketColor",
    SocketType.STRING: "NodeSocketString",
    SocketType.SHADER: "NodeSocketShader",
    SocketType.OBJECT: "NodeSocketObject",
    SocketType.COLLECTION: "NodeSocketCollection",
    SocketType.MATERIAL: "NodeSocketMaterial",
    SocketType.TEXTURE: "NodeSocketTexture",
    SocketType.IMAGE: "NodeSocketImage",
    SocketType.MENU: "NodeSocketMenu",
}

_FROM_BLENDER: dict[str, SocketType] = {
    **{v: k for k, v in _BLENDER_SOCKET.items()},
    "NodeSocketFloatFactor": SocketType.FLOAT,
    "NodeSocketFloatAngle": SocketType.FLOAT,
    "NodeSocketFloatDistance": SocketType.FLOAT,
    "NodeSocketFloatUnsigned": SocketType.FLOAT,
    "NodeSocketVectorEuler": SocketType.VECTOR,
    "NodeSocketVectorXYZ": SocketType.VECTOR,
    "NodeSocketVectorTranslation": SocketType.VECTOR,
    "NodeSocketVectorDirection": SocketType.VECTOR,
    "NodeSocketVectorAcceleration": SocketType.VECTOR,
    "NodeSocketVectorVelocity": SocketType.VECTOR,
    "NodeSocketColor": SocketType.COLOR,
    "NodeSocketShader": SocketType.SHADER,
    "NodeSocketBool": SocketType.BOOLEAN,
}


def socket_type_from_blender(bl_idname: str) -> SocketType:
    if bl_idname in _FROM_BLENDER:
        return _FROM_BLENDER[bl_idname]
    raise KeyError(f"Unknown Blender socket type: {bl_idname}")


def parse_socket_type(value: str) -> SocketType:
    key = value.strip().upper().replace("NODESOCKET", "")
    aliases = {
        "VALUE": SocketType.FLOAT,
        "RGBA": SocketType.COLOR,
        "STRING": SocketType.STRING,
        "VECTOR": SocketType.VECTOR,
        "SHADER": SocketType.SHADER,
        "BOOL": SocketType.BOOLEAN,
        "BOOLEAN": SocketType.BOOLEAN,
    }
    if key in aliases:
        return aliases[key]
    return SocketType[key]


def round_number(value: float, digits: int = 6) -> float:
    rounded = round(float(value), digits)
    if rounded == int(rounded):
        return int(rounded)
    return rounded


def jsonify(value: Any) -> JsonValue:
    """Convert Blender/Python values into JSON-safe, git-stable data."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return round_number(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): jsonify(v) for k, v in value.items()}
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [jsonify(v) for v in value]
    to_list = getattr(value, "to_list", None)
    if callable(to_list):
        return jsonify(to_list())
    if hasattr(value, "x") and hasattr(value, "y"):
        parts = [value.x, value.y]
        if hasattr(value, "z"):
            parts.append(value.z)
        if hasattr(value, "w"):
            parts.append(value.w)
        return jsonify(parts)
    return value
