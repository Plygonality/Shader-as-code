"""Minimal in-memory bpy stand-in for apply/dump tests."""

from __future__ import annotations

from typing import Any


class _Prop:
    def __init__(self, identifier: str, readonly: bool = False) -> None:
        self.identifier = identifier
        self.is_readonly = readonly


class _Rna:
    def __init__(self, names: list[str]) -> None:
        self.properties = [_Prop(n) for n in names]


class FakeSocket:
    def __init__(self, name: str, identifier: str | None = None, default: Any = None) -> None:
        self.name = name
        self.identifier = identifier or name
        self.default_value = default
        self.is_linked = False
        self.links: list[FakeLink] = []


class FakeSockets(list):
    def __iter__(self):
        return super().__iter__()


class FakeNode:
    def __init__(self, bl_idname: str, name: str) -> None:
        self.bl_idname = bl_idname
        self.type = bl_idname
        self.name = name
        self.label = ""
        self.location = [0.0, 0.0]
        self.hide = False
        self.mute = False
        self.parent = None
        self.inputs = FakeSockets()
        self.outputs = FakeSockets()
        self.properties: dict[str, Any] = {}
        self.bl_rna = _Rna([])
        self.node_tree = None

    def __setattr__(self, key: str, value: Any) -> None:
        if key in {
            "bl_idname",
            "type",
            "name",
            "label",
            "location",
            "hide",
            "mute",
            "parent",
            "inputs",
            "outputs",
            "properties",
            "bl_rna",
            "node_tree",
        } or key.startswith("_"):
            object.__setattr__(self, key, value)
            return
        object.__setattr__(self, key, value)
        props = object.__getattribute__(self, "__dict__").get("properties")
        if isinstance(props, dict):
            props[key] = value
        rna = object.__getattribute__(self, "__dict__").get("bl_rna")
        if rna is not None and all(p.identifier != key for p in rna.properties):
            rna.properties.append(_Prop(key))


class FakeLink:
    def __init__(self, from_socket: FakeSocket, to_socket: FakeSocket, from_node: FakeNode, to_node: FakeNode):
        self.from_socket = from_socket
        self.to_socket = to_socket
        self.from_node = from_node
        self.to_node = to_node


class FakeLinks(list):
    def new(self, from_socket: FakeSocket, to_socket: FakeSocket) -> FakeLink:
        from_node = from_socket._node  # type: ignore[attr-defined]
        to_node = to_socket._node  # type: ignore[attr-defined]
        link = FakeLink(from_socket, to_socket, from_node, to_node)
        from_socket.is_linked = True
        to_socket.is_linked = True
        from_socket.links.append(link)
        to_socket.links.append(link)
        self.append(link)
        return link


class FakePanel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.item_type = "PANEL"


class FakeInterfaceItem:
    def __init__(self, name: str, in_out: str, socket_type: str) -> None:
        self.name = name
        self.in_out = in_out
        self.socket_type = socket_type
        self.item_type = "SOCKET"
        self.default_value = None
        self.min_value = None
        self.max_value = None
        self.description = ""
        self.subtype = None
        self.parent = None
        self.panel = None


class FakeInterface:
    def __init__(self) -> None:
        self.items_tree: list[Any] = []
        self._tree: FakeTree | None = None

    def clear(self) -> None:
        self.items_tree.clear()

    def new_panel(self, name: str, description: str = "", default_closed: bool = False) -> FakePanel:
        panel = FakePanel(name)
        self.items_tree.append(panel)
        return panel

    def new_socket(
        self,
        name: str,
        in_out: str,
        socket_type: str,
        parent: Any = None,
    ) -> FakeInterfaceItem:
        item = FakeInterfaceItem(name, in_out, socket_type)
        item.parent = parent
        if parent is not None:
            item.panel = getattr(parent, "name", None)
        self.items_tree.append(item)
        if self._tree is not None:
            sync_interface_sockets(self._tree)
        return item

    def remove(self, item: Any) -> None:
        self.items_tree.remove(item)


class FakeNodes:
    def __init__(self) -> None:
        self._order: list[FakeNode] = []
        self._tree: FakeTree | None = None

    def new(self, bl_idname: str) -> FakeNode:
        node = FakeNode(bl_idname, bl_idname)
        _seed_sockets(node)
        self._order.append(node)
        if self._tree is not None:
            sync_interface_sockets(self._tree)
            _seed_group_node(node, self._tree)
        return node

    def clear(self) -> None:
        self._order.clear()

    def __iter__(self):
        return iter(self._order)

    def __len__(self) -> int:
        return len(self._order)

    def __getitem__(self, index: int) -> FakeNode:
        return self._order[index]


class FakeTree:
    def __init__(self, name: str) -> None:
        self.name = name
        self.bl_idname = "ShaderNodeTree"
        self.type = "SHADER"
        self.nodes = FakeNodes()
        self.nodes._tree = self
        self.links = FakeLinks()
        self.interface = FakeInterface()
        self.interface._tree = self
        self._id_props: dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any:
        return self._id_props[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._id_props[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._id_props.get(key, default)

    def items(self):
        return self._id_props.items()

    def keys(self):
        return self._id_props.keys()


class FakeMaterial:
    def __init__(self, name: str) -> None:
        self.name = name
        self.use_nodes = True
        self.node_tree = FakeTree(name)
        self._id_props: dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any:
        return self._id_props[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._id_props[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._id_props.get(key, default)


class FakeMaterials(dict):
    def new(self, name: str) -> FakeMaterial:
        mat = FakeMaterial(name)
        self[name] = mat
        return mat

    def get(self, name: str, default=None):
        return dict.get(self, name, default)


class FakeMesh:
    def __init__(self, name: str) -> None:
        self.name = name
        self.materials: list[Any] = []


class FakeMeshes(dict):
    def new(self, name: str) -> FakeMesh:
        mesh = FakeMesh(name)
        self[name] = mesh
        return mesh


class FakeObject:
    def __init__(self, name: str, data: Any = None) -> None:
        self.name = name
        self.data = data if data is not None else FakeMesh(name)
        self.active_material = None


class FakeObjectMap(dict):
    def link(self, obj: FakeObject) -> None:
        self[obj.name] = obj

    def get(self, name: str, default=None):
        return dict.get(self, name, default)


class FakeIDMap(dict):
    def get(self, name: str, default=None):
        return dict.get(self, name, default)


class FakeCollection:
    def __init__(self) -> None:
        self.objects = FakeObjectMap()


class FakeScene:
    def __init__(self) -> None:
        self.collection = FakeCollection()


class FakeContext:
    def __init__(self) -> None:
        self.scene = FakeScene()


class FakeWorld:
    def __init__(self, name: str) -> None:
        self.name = name
        self.use_nodes = True
        self.node_tree = FakeTree(name)


class FakeWorlds(dict):
    def new(self, name: str) -> FakeWorld:
        world = FakeWorld(name)
        self[name] = world
        return world

    def get(self, name: str, default=None):
        return dict.get(self, name, default)


class FakeLight:
    def __init__(self, name: str, type_: str = "POINT") -> None:
        self.name = name
        self.type = type_
        self.use_nodes = True
        self.node_tree = FakeTree(name)


class FakeLights(dict):
    def new(self, name: str, type_: str = "POINT") -> FakeLight:
        light = FakeLight(name, type_)
        self[name] = light
        return light

    def get(self, name: str, default=None):
        return dict.get(self, name, default)


class FakeBpy:
    def __init__(self) -> None:
        self.data = type("Data", (), {})()
        groups = FakeIDMap()

        def new_group(name: str, type_: str = "ShaderNodeTree") -> FakeTree:
            tree = FakeTree(name)
            groups[name] = tree
            return tree

        groups.new = new_group  # type: ignore[method-assign]
        self.data.node_groups = groups
        objects = FakeIDMap()

        def new_object(name: str, data: Any = None) -> FakeObject:
            obj = FakeObject(name, data)
            objects[name] = obj
            return obj

        objects.new = new_object  # type: ignore[method-assign]
        self.data.objects = objects
        self.data.meshes = FakeMeshes()
        self.data.materials = FakeMaterials()
        self.data.worlds = FakeWorlds()
        self.data.lights = FakeLights()
        self.context = FakeContext()


def _seed_sockets(node: FakeNode) -> None:
    from shader_as_code.catalog import GROUP_INPUT, GROUP_OUTPUT, get_spec

    if node.bl_idname in (GROUP_INPUT, GROUP_OUTPUT):
        return
    spec = get_spec(node.bl_idname)
    if spec is None:
        _add_in(node, "Shader")
        _add_out(node, "BSDF")
        return
    for sock in spec.inputs:
        _add_in(node, sock.identifier, sock.default)
    for sock in spec.outputs:
        _add_out(node, sock.identifier)


def _seed_group_node(node: FakeNode, tree: FakeTree) -> None:
    if node.bl_idname != "ShaderNodeGroup":
        return
    if node.outputs:
        return
    _add_out(node, "BSDF")


def _add_in(node: FakeNode, name: str, default: Any = None) -> FakeSocket:
    sock = FakeSocket(name, name, default)
    sock._node = node  # type: ignore[attr-defined]
    node.inputs.append(sock)
    return sock


def _add_out(node: FakeNode, name: str) -> FakeSocket:
    sock = FakeSocket(name, name)
    sock._node = node  # type: ignore[attr-defined]
    node.outputs.append(sock)
    return sock


def sync_interface_sockets(tree: FakeTree) -> None:
    """Mirror group interface onto Group Input / Group Output sockets."""
    inputs = [n for n in tree.nodes if n.bl_idname == "NodeGroupInput"]
    outputs = [n for n in tree.nodes if n.bl_idname == "NodeGroupOutput"]
    in_items = [i for i in tree.interface.items_tree if getattr(i, "in_out", None) == "INPUT"]
    out_items = [i for i in tree.interface.items_tree if getattr(i, "in_out", None) == "OUTPUT"]
    for node in inputs:
        node.outputs = FakeSockets()
        for item in in_items:
            _add_out(node, item.name)
    for node in outputs:
        node.inputs = FakeSockets()
        for item in out_items:
            _add_in(node, item.name)
