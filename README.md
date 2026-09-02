# shader-as-code

Shader Node trees as data. Git is the source of truth. The `.blend` is a cache.

Build graphs in Python. Dump them to JSON. Diff them like code.
[Master-Node](https://github.com/Plygonality/Master-Node) instantiates a category master from that dump. It does not author the graph.
[Plygon-mcp](https://github.com/Plygonality/Plygon-mcp) applies a graph and screenshots the viewport.

This is the shader sibling of [gn-as-code](https://github.com/Plygonality/gn-as-code). Same contract: typed builders, canonical JSON, structural diffs, golden tests, apply/dump scripts for bpy. Target is `ShaderNodeTree`, not `GeometryNodeTree`.

This is a library you import, not another `execute_python` wrapper. There is no N-panel here — that already lives in Master-Node.

```python
from pathlib import Path

from shader_as_code.samples import build_metal

Path("graphs/mn_metal.json").write_text(build_metal().dumps())
```

Or author any tree yourself:

```python
from shader_as_code import Graph

g = Graph("MN Metal")
g.mark_master("metal")
color = g.input_color("Color", (0.72, 0.72, 0.74, 1.0))
roughness = g.input_float("Roughness", 0.25, min=0.0, max=1.0, subtype="FACTOR")
bsdf = g.principled_bsdf(base_color=color, roughness=roughness, metallic=1.0, id="bsdf", label="Metal")
g.output_shader(bsdf)
```

## Why this repo exists

A shader tree in a `.blend` is a binary blob. You cannot review it, diff it, or let an agent iterate on it without opening Blender. Master-Node category masters should be generated from this, not hand-built in a `.blend`.

| Role | Job |
|---|---|
| **This library** | Typed builders, canonical JSON, structural diffs, golden tests. Authors the seven category masters. |
| **Master-Node** | Instantiates a dump as a `ShaderNodeTree` and draws the N-panel. Does not author the graph. |
| **Plygon-mcp** | Apply the JSON in a live Blender session and check the viewport |
| **The `.blend`** | Working cache, never the source of truth |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. No Blender required to build, dump, or diff.

## Quick demo

```bash
pip install -e ".[dev]"
python -c "from shader_as_code.samples import build_metal; print(build_metal().dumps())"
pytest -q
```

That prints the Metal category master as canonical JSON, then runs the suite.

## Graph JSON

Dumps are stable: nodes sorted by id, links sorted, defaults omitted, locations rounded.

```json
{
  "format": "shader-as-code",
  "version": 1,
  "name": "MN Metal",
  "kind": "GROUP",
  "blender": "4.2",
  "id_properties": {
    "mn.is_master": true,
    "mn.category": "metal",
    "mn.origin": "framework",
    "mn.version": 1
  },
  "interface": {
    "inputs": [{"name": "Color", "socket": "COLOR", "default": [0.72, 0.72, 0.74, 1.0]}],
    "outputs": [{"name": "BSDF", "socket": "SHADER"}]
  },
  "nodes": [
    {"id": "Group Input", "type": "NodeGroupInput"},
    {"id": "Group Output", "type": "NodeGroupOutput"},
    {"id": "bsdf", "type": "ShaderNodeBsdfPrincipled", "label": "Metal"}
  ],
  "links": [
    {"from": ["bsdf", "BSDF"], "to": ["Group Output", "BSDF"]}
  ]
}
```

`id` is the stable name. Rename nodes in the builder, not in Blender, so diffs stay readable.

`kind` is `GROUP` (a node group in `bpy.data.node_groups`), `MATERIAL`, `WORLD`, or `LIGHT`.

## Master-Node categories

The library emits all seven category masters from code, including `mn.*` ID properties:

| Category | Tree name | Locked Principled constants |
|---|---|---|
| `surface` | `MN Surface` | — |
| `metal` | `MN Metal` | Metallic 1, Specular IOR Level 1 |
| `dielectric` | `MN Dielectric` | Metallic 0 |
| `glass` | `MN Glass` | Metallic 0, Alpha 1 |
| `fabric` | `MN Fabric` | Metallic 0, Specular IOR Level 0.3 |
| `emissive` | `MN Emissive` | Metallic 0 |
| `layered` | `MN Layered` | — |

```python
from shader_as_code.masters import build_master, CATEGORIES

for category in CATEGORIES:
    graph = build_master(category)
    # id_properties: mn.is_master, mn.category, mn.version, mn.origin
```

Master-Node then instantiates. The N-panel binds to whichever master the active material uses.

## Diff

```python
from shader_as_code import diff_graphs, format_diff, loads

diff = diff_graphs(loads(old_json), loads(new_json))
print(format_diff(diff))
```

Locations are ignored unless you pass `include_layout=True`.

```bash
shader-as-code dump graph.json
shader-as-code diff old.json new.json
shader-as-code validate graph.json
shader-as-code mermaid graph.json
shader-as-code apply-script graph.json --material Metal
shader-as-code dump-script "MN Metal"
```

## Apply in Blender (via Plygon-mcp)

The agent authors a graph here, then asks Plygon-mcp to run a self-contained bpy script. Blender does not need this package installed.

```python
from shader_as_code.apply import to_apply_script
from shader_as_code.samples import build_metal

script = to_apply_script(build_metal().to_data(), material_name="Metal")
# Plygon-mcp: execute_blender_code(script) → get_viewport_screenshot()
```

Dump a live tree the other way:

```python
from shader_as_code.apply import to_dump_script

script = to_dump_script("MN Metal")
```

If you are already inside Blender:

```python
from shader_as_code.apply import apply, dump_from_bpy
apply(graph.to_data(), material_name="Metal")
```

GROUP dumps become `ShaderNodeTree` datablocks. MATERIAL dumps rebuild a material's node tree.

## Typed builders

Common Shader Nodes are methods on `Graph` (`principled_bsdf`, `mapping`, `image_texture`, `tex_coord`, `noise_texture`, `normal_map`, `mix_shader`, …). Pass a socket or a node handle to wire a link; pass a literal to set a default.

Anything not wrapped is still valid:

```python
g.node("ShaderNodeBsdfHairPrincipled", id="hair", inputs={"Melanin": 0.8})
```

Unknown `bl_idname`s are allowed. The catalog is how builders name sockets and skip defaults without bpy — Principled, mapping, image/environment/noise textures, BSDFs, converters.

## Tests

```bash
pytest -q
UPDATE_GOLDENS=1 pytest tests/test_golden.py   # rewrite fixtures after an intentional dump change
```

Goldens live in `tests/goldens/`. If a builder change is intentional, update them. If it is not, the test failed for a reason.

## Layout

```
src/shader_as_code/     library
examples/               sample graphs as Python
tests/goldens/          canonical JSON fixtures (the seven masters)
```
