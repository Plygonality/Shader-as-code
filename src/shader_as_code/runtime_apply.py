"""Self-contained bpy apply/dump runtime.

This module has no shader-as-code imports so it can be exec'd inside Blender via
Plygon-mcp ``execute_blender_code``. The graph JSON is the source of truth;
the .blend is the cache.
"""

from __future__ import annotations

FORMAT = "shader-as-code"
FORMAT_VERSION = 1

_SOCKET_BL_IDNAME = {
    "FLOAT": "NodeSocketFloat",
    "INT": "NodeSocketInt",
    "BOOLEAN": "NodeSocketBoolean",
    "VECTOR": "NodeSocketVector",
    "ROTATION": "NodeSocketRotation",
    "MATRIX": "NodeSocketMatrix",
    "COLOR": "NodeSocketColor",
    "STRING": "NodeSocketString",
    "SHADER": "NodeSocketShader",
    "OBJECT": "NodeSocketObject",
    "COLLECTION": "NodeSocketCollection",
    "MATERIAL": "NodeSocketMaterial",
    "TEXTURE": "NodeSocketTexture",
    "IMAGE": "NodeSocketImage",
    "MENU": "NodeSocketMenu",
}

_SOCKET_FROM_BL = {
    "NodeSocketFloat": "FLOAT",
    "NodeSocketFloatFactor": "FLOAT",
    "NodeSocketFloatAngle": "FLOAT",
    "NodeSocketFloatDistance": "FLOAT",
    "NodeSocketFloatUnsigned": "FLOAT",
    "NodeSocketInt": "INT",
    "NodeSocketIntUnsigned": "INT",
    "NodeSocketBool": "BOOLEAN",
    "NodeSocketBoolean": "BOOLEAN",
    "NodeSocketVector": "VECTOR",
    "NodeSocketVectorEuler": "VECTOR",
    "NodeSocketVectorXYZ": "VECTOR",
    "NodeSocketVectorTranslation": "VECTOR",
    "NodeSocketVectorDirection": "VECTOR",
    "NodeSocketRotation": "ROTATION",
    "NodeSocketMatrix": "MATRIX",
    "NodeSocketColor": "COLOR",
    "NodeSocketString": "STRING",
    "NodeSocketShader": "SHADER",
    "NodeSocketObject": "OBJECT",
    "NodeSocketCollection": "COLLECTION",
    "NodeSocketMaterial": "MATERIAL",
    "NodeSocketTexture": "TEXTURE",
    "NodeSocketImage": "IMAGE",
    "NodeSocketMenu": "MENU",
}

_NODE_SKIP_PROPS = {
    "rna_type",
    "type",
    "bl_idname",
    "bl_label",
    "bl_description",
    "bl_icon",
    "bl_static_type",
    "bl_width_default",
    "bl_width_min",
    "bl_width_max",
    "bl_height_default",
    "bl_height_min",
    "bl_height_max",
    "name",
    "label",
    "location",
    "location_absolute",
    "width",
    "height",
    "dimensions",
    "inputs",
    "outputs",
    "internal_links",
    "parent",
    "select",
    "show_options",
    "show_preview",
    "show_texture",
    "hide",
    "mute",
    "use_custom_color",
    "color",
    "width_hidden",
    "warning_propagation",
}


def apply_graph_dict(
    data,
    bpy,
    *,
    material_name=None,
    object_name=None,
    replace=True,
):
    """Rebuild a Shader Node tree from a shader-as-code dump.

    Returns the node tree. GROUP dumps land in ``bpy.data.node_groups`` as
    ``ShaderNodeTree``. MATERIAL dumps rebuild a material's node tree.
    """
    _validate_payload(data)
    name = data["name"]
    kind = data.get("kind", "GROUP")
    if kind == "GROUP":
        tree = _get_or_create_group(bpy, name, replace)
        _apply_into_tree(tree, data)
        if material_name or object_name:
            _use_group_on_material(
                bpy,
                material_name or name,
                tree,
                object_name=object_name,
            )
        return tree
    if kind == "MATERIAL":
        mat = _get_or_create_material(bpy, material_name or name)
        mat.use_nodes = True
        tree = mat.node_tree
        _apply_into_tree(tree, data)
        if object_name:
            _assign_material(bpy, object_name, mat)
        return tree
    if kind == "WORLD":
        world = bpy.data.worlds.get(name)
        if world is None:
            world = bpy.data.worlds.new(name)
        world.use_nodes = True
        _apply_into_tree(world.node_tree, data)
        return world.node_tree
    if kind == "LIGHT":
        light = bpy.data.lights.get(name)
        if light is None:
            light = bpy.data.lights.new(name, "POINT")
        light.use_nodes = True
        _apply_into_tree(light.node_tree, data)
        return light.node_tree
    raise ValueError(f"Unsupported graph kind: {kind!r}")


def dump_tree(tree, *, blender="4.2", kind=None, name=None):
    """Serialize a live ShaderNodeTree into a shader-as-code dict."""
    interface = _dump_interface(tree)
    nodes = [_dump_node(node) for node in tree.nodes]
    links = [_dump_link(link) for link in tree.links]
    if kind is None:
        kind = _infer_kind(tree)
    nodes_sorted = sorted(nodes, key=lambda n: n["id"])
    links_sorted = sorted(
        links,
        key=lambda ln: (ln["from"][0], ln["from"][1], ln["to"][0], ln["to"][1]),
    )
    payload = {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "name": name or tree.name,
        "kind": kind,
        "blender": blender,
    }
    id_properties = _dump_id_properties(tree)
    if id_properties:
        payload["id_properties"] = id_properties
    payload["interface"] = interface
    payload["nodes"] = nodes_sorted
    payload["links"] = links_sorted
    return payload


def dump_tree_by_name(bpy, name, *, blender="4.2"):
    tree = bpy.data.node_groups.get(name)
    if tree is not None:
        return dump_tree(tree, blender=blender, kind="GROUP")
    materials = getattr(bpy.data, "materials", None)
    if materials is not None:
        mat = materials.get(name)
        if mat is not None and getattr(mat, "node_tree", None) is not None:
            return dump_tree(mat.node_tree, blender=blender, kind="MATERIAL", name=mat.name)
    worlds = getattr(bpy.data, "worlds", None)
    if worlds is not None:
        world = worlds.get(name)
        if world is not None and getattr(world, "node_tree", None) is not None:
            return dump_tree(world.node_tree, blender=blender, kind="WORLD", name=world.name)
    lights = getattr(bpy.data, "lights", None)
    if lights is not None:
        light = lights.get(name)
        if light is not None and getattr(light, "node_tree", None) is not None:
            return dump_tree(light.node_tree, blender=blender, kind="LIGHT", name=light.name)
    raise KeyError(f"No shader tree named {name!r}")


def _validate_payload(data):
    if data.get("format") not in (None, FORMAT):
        raise ValueError(f"Unsupported graph format: {data.get('format')!r}")
    version = data.get("version", FORMAT_VERSION)
    if int(version) != FORMAT_VERSION:
        raise ValueError(f"Unsupported shader-as-code version: {version}")
    if "name" not in data:
        raise ValueError("Graph dump is missing 'name'")


def _get_or_create_group(bpy, name, replace):
    tree = bpy.data.node_groups.get(name)
    if tree is None:
        return bpy.data.node_groups.new(name, "ShaderNodeTree")
    if not replace:
        raise ValueError(f"Node group {name!r} already exists")
    return tree


def _get_or_create_material(bpy, name):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    return mat


def _apply_into_tree(tree, data):
    _clear_tree(tree)
    _build_interface(tree, data.get("interface") or {})
    created = _build_nodes(tree, data.get("nodes") or [])
    _build_links(tree, data.get("links") or [], created)
    _set_id_properties(tree, data.get("id_properties") or {})


def _set_id_properties(tree, props):
    for key, value in props.items():
        try:
            tree[key] = value
        except Exception:
            pass


def _dump_id_properties(tree):
    items = getattr(tree, "items", None)
    if not callable(items):
        stored = getattr(tree, "_id_props", None)
        if isinstance(stored, dict):
            return {str(k): _jsonify(v) for k, v in stored.items()}
        return {}
    dumped = {}
    try:
        for key, value in items():
            dumped[str(key)] = _jsonify(value)
    except Exception:
        return dumped
    return dumped


def _infer_kind(tree):
    types = {getattr(n, "bl_idname", None) or getattr(n, "type", "") for n in tree.nodes}
    if "ShaderNodeOutputMaterial" in types and "NodeGroupOutput" not in types:
        return "MATERIAL"
    if "ShaderNodeOutputWorld" in types and "NodeGroupOutput" not in types:
        return "WORLD"
    if "ShaderNodeOutputLight" in types and "NodeGroupOutput" not in types:
        return "LIGHT"
    return "GROUP"


def _clear_tree(tree):
    tree.nodes.clear()
    interface = getattr(tree, "interface", None)
    if interface is None:
        return
    clearer = getattr(interface, "clear", None)
    if callable(clearer):
        clearer()
        return
    items = list(getattr(interface, "items_tree", []))
    for item in items:
        try:
            interface.remove(item)
        except Exception:
            pass


def _build_interface(tree, interface):
    iface = getattr(tree, "interface", None)
    if iface is None:
        return
    panels = {}
    new_panel = getattr(iface, "new_panel", None)
    for item in interface.get("inputs", []):
        panel_name = item.get("panel")
        if panel_name and panel_name not in panels and callable(new_panel):
            panels[panel_name] = new_panel(name=panel_name)
    for item in interface.get("inputs", []):
        _add_interface_socket(iface, item, "INPUT", panels.get(item.get("panel")))
    for item in interface.get("outputs", []):
        _add_interface_socket(iface, item, "OUTPUT", None)


def _add_interface_socket(iface, item, in_out, parent):
    socket_type = _SOCKET_BL_IDNAME.get(item.get("socket", "SHADER"), "NodeSocketShader")
    kwargs = {}
    if parent is not None:
        kwargs["parent"] = parent
    try:
        sock = iface.new_socket(name=item["name"], in_out=in_out, socket_type=socket_type, **kwargs)
    except TypeError:
        sock = iface.new_socket(name=item["name"], in_out=in_out, socket_type=socket_type)
        if parent is not None and hasattr(sock, "parent"):
            sock.parent = parent
    if item.get("default") is not None and hasattr(sock, "default_value"):
        _set_value(sock, "default_value", item["default"])
    if item.get("min") is not None and hasattr(sock, "min_value"):
        sock.min_value = item["min"]
    if item.get("max") is not None and hasattr(sock, "max_value"):
        sock.max_value = item["max"]
    if item.get("subtype") and hasattr(sock, "subtype"):
        try:
            sock.subtype = item["subtype"]
        except (TypeError, ValueError):
            pass
    if item.get("description") and hasattr(sock, "description"):
        sock.description = item["description"]
    return sock


def _build_nodes(tree, nodes):
    created = {}
    ordered = sorted(nodes, key=lambda n: 0 if n.get("type") == "NodeFrame" else 1)
    for spec in ordered:
        node = tree.nodes.new(spec["type"])
        node.name = spec["id"]
        if spec.get("label"):
            node.label = spec["label"]
        if spec.get("hide"):
            node.hide = True
        if spec.get("mute"):
            node.mute = True
        if spec.get("location") is not None:
            node.location = tuple(spec["location"])
        for key, value in (spec.get("properties") or {}).items():
            _set_value(node, key, value)
        for key, value in (spec.get("inputs") or {}).items():
            socket = _find_socket(node.inputs, key)
            if socket is not None:
                _set_value(socket, "default_value", value)
        created[spec["id"]] = node
    for spec in ordered:
        parent_id = spec.get("parent")
        if parent_id and parent_id in created:
            created[spec["id"]].parent = created[parent_id]
    return created


def _build_links(tree, links, created):
    for spec in links:
        src_id, src_sock = spec["from"]
        dst_id, dst_sock = spec["to"]
        src = created.get(src_id)
        dst = created.get(dst_id)
        if src is None or dst is None:
            raise KeyError(f"Link references missing node: {src_id!r} -> {dst_id!r}")
        from_socket = _find_socket(src.outputs, src_sock)
        to_socket = _find_socket(dst.inputs, dst_sock)
        if from_socket is None or to_socket is None:
            raise KeyError(
                f"Link sockets not found: {src_id}.{src_sock} -> {dst_id}.{dst_sock}"
            )
        tree.links.new(from_socket, to_socket)


def _use_group_on_material(bpy, material_name, tree, object_name=None):
    mat = _get_or_create_material(bpy, material_name)
    mat.use_nodes = True
    ntree = mat.node_tree
    ntree.nodes.clear()
    group = ntree.nodes.new("ShaderNodeGroup")
    group.name = "Master"
    if hasattr(group, "node_tree"):
        group.node_tree = tree
    output = ntree.nodes.new("ShaderNodeOutputMaterial")
    output.name = "Material Output"
    from_socket = _find_socket(group.outputs, "BSDF") or (group.outputs[0] if group.outputs else None)
    to_socket = _find_socket(output.inputs, "Surface")
    if from_socket is not None and to_socket is not None:
        ntree.links.new(from_socket, to_socket)
    try:
        mat["mn.master"] = tree.name
    except Exception:
        pass
    if object_name:
        _assign_material(bpy, object_name, mat)
    return mat


def _assign_material(bpy, object_name, mat):
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        mesh = bpy.data.meshes.new(object_name)
        obj = bpy.data.objects.new(object_name, mesh)
        collection = bpy.context.scene.collection
        collection.objects.link(obj)
    slots = getattr(obj, "data", None)
    materials = getattr(slots, "materials", None)
    if materials is not None:
        if len(materials) == 0:
            materials.append(mat)
        else:
            materials[0] = mat
    if hasattr(obj, "active_material"):
        obj.active_material = mat
    return obj


def _find_socket(sockets, key):
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        index = int(key)
        if 0 <= index < len(sockets):
            return sockets[index]
        return None
    for socket in sockets:
        if getattr(socket, "identifier", None) == key:
            return socket
    for socket in sockets:
        if getattr(socket, "name", None) == key:
            return socket
    return None


def _set_value(owner, attr, value):
    if not hasattr(owner, attr) and attr not in ("image", "node_tree", "uv_map"):
        try:
            setattr(owner, attr, value)
            return
        except Exception:
            return
    current = getattr(owner, attr, None)
    try:
        setattr(owner, attr, value)
        return
    except Exception:
        pass
    if isinstance(value, (list, tuple)) and current is not None:
        try:
            if hasattr(current, "foreach_set"):
                current.foreach_set(list(value))
                return
        except Exception:
            pass
        try:
            for i, part in enumerate(value):
                current[i] = part
            return
        except Exception:
            pass
        if len(value) == 3:
            try:
                setattr(owner, attr, (*value, 1.0))
            except Exception:
                pass


def _dump_interface(tree):
    inputs = []
    outputs = []
    iface = getattr(tree, "interface", None)
    if iface is None:
        return {"inputs": inputs, "outputs": outputs}
    items = list(getattr(iface, "items_tree", []))
    for item in items:
        item_type = getattr(item, "item_type", "SOCKET")
        if item_type not in ("SOCKET", None) and item_type != "SOCKET":
            continue
        in_out = getattr(item, "in_out", None)
        if in_out not in ("INPUT", "OUTPUT"):
            continue
        payload = {
            "name": item.name,
            "socket": _socket_kind(
                getattr(item, "socket_type", None) or getattr(item, "bl_socket_idname", "SHADER")
            ),
        }
        if hasattr(item, "default_value"):
            dumped = _jsonify(item.default_value)
            if dumped is not None:
                payload["default"] = dumped
        if hasattr(item, "min_value") and item.min_value is not None:
            payload["min"] = _jsonify(item.min_value)
        if hasattr(item, "max_value") and item.max_value is not None:
            payload["max"] = _jsonify(item.max_value)
        if getattr(item, "description", ""):
            payload["description"] = item.description
        if getattr(item, "subtype", None):
            payload["subtype"] = item.subtype
        parent = getattr(item, "parent", None)
        if parent is not None and getattr(parent, "item_type", None) == "PANEL":
            payload["panel"] = parent.name
        elif getattr(item, "panel", None):
            payload["panel"] = item.panel
        if in_out == "INPUT":
            inputs.append(payload)
        else:
            outputs.append(payload)
    return {"inputs": inputs, "outputs": outputs}


def _dump_node(node):
    payload = {
        "id": node.name,
        "type": getattr(node, "bl_idname", None) or node.type,
    }
    if getattr(node, "label", ""):
        payload["label"] = node.label
    loc = getattr(node, "location", None)
    if loc is not None:
        payload["location"] = [_jsonify(loc[0]), _jsonify(loc[1])]
    if getattr(node, "hide", False):
        payload["hide"] = True
    if getattr(node, "mute", False):
        payload["mute"] = True
    parent = getattr(node, "parent", None)
    if parent is not None:
        payload["parent"] = parent.name
    inputs = {}
    for socket in node.inputs:
        if getattr(socket, "is_linked", False):
            continue
        if not hasattr(socket, "default_value"):
            continue
        ident = getattr(socket, "identifier", None) or socket.name
        try:
            inputs[ident] = _jsonify(socket.default_value)
        except Exception:
            continue
    if inputs:
        payload["inputs"] = inputs
    properties = _dump_properties(node)
    if properties:
        payload["properties"] = properties
    return payload


def _dump_properties(node):
    props = {}
    bl_rna = getattr(node, "bl_rna", None)
    if bl_rna is None:
        for key, value in getattr(node, "properties", {}).items():
            props[key] = _jsonify(value)
        return props
    for prop in bl_rna.properties:
        ident = prop.identifier
        if ident in _NODE_SKIP_PROPS or getattr(prop, "is_readonly", False):
            continue
        try:
            value = getattr(node, ident)
        except Exception:
            continue
        dumped = _jsonify(value)
        if dumped is None or callable(dumped):
            continue
        props[ident] = dumped
    return props


def _dump_link(link):
    return {
        "from": [
            link.from_node.name,
            getattr(link.from_socket, "identifier", None) or link.from_socket.name,
        ],
        "to": [
            link.to_node.name,
            getattr(link.to_socket, "identifier", None) or link.to_socket.name,
        ],
    }


def _socket_kind(bl_idname):
    if not bl_idname:
        return "SHADER"
    if bl_idname in _SOCKET_FROM_BL:
        return _SOCKET_FROM_BL[bl_idname]
    key = str(bl_idname).replace("NodeSocket", "").upper()
    if key in _SOCKET_BL_IDNAME:
        return key
    return str(bl_idname)


def _jsonify(value):
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        rounded = round(float(value), 6)
        return int(rounded) if rounded == int(rounded) else rounded
    if isinstance(value, bytes):
        return value.decode("utf-8")
    to_list = getattr(value, "to_list", None)
    if callable(to_list):
        return _jsonify(to_list())
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if hasattr(value, "x") and hasattr(value, "y"):
        parts = [value.x, value.y]
        if hasattr(value, "z"):
            parts.append(value.z)
        if hasattr(value, "w"):
            parts.append(value.w)
        return _jsonify(parts)
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    identifier = getattr(value, "identifier", None)
    if isinstance(identifier, str) and identifier not in ("rna_type",):
        return identifier
    return None
