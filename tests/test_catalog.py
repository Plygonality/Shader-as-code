from __future__ import annotations

from shader_as_code.catalog import CATALOG, CATALOG_BY_METHOD, CATALOG_BY_TYPE


def test_catalog_ids_unique() -> None:
    types = [s.bl_idname for s in CATALOG]
    methods = [s.method for s in CATALOG]
    assert len(types) == len(set(types))
    assert len(methods) == len(set(methods))
    assert CATALOG_BY_TYPE["ShaderNodeBsdfPrincipled"].method == "principled_bsdf"
    assert CATALOG_BY_METHOD["image_texture"].bl_idname == "ShaderNodeTexImage"
    assert CATALOG_BY_METHOD["mapping"].bl_idname == "ShaderNodeMapping"
    assert CATALOG_BY_METHOD["tex_coord"].bl_idname == "ShaderNodeTexCoord"
    assert CATALOG_BY_METHOD["normal_map"].bl_idname == "ShaderNodeNormalMap"


def test_principled_has_core_sockets() -> None:
    spec = CATALOG_BY_TYPE["ShaderNodeBsdfPrincipled"]
    names = spec.input_map()
    for ident in (
        "Base Color",
        "Metallic",
        "Roughness",
        "IOR",
        "Emission Color",
        "Coat Weight",
        "Sheen Weight",
        "Transmission Weight",
    ):
        assert ident in names
    assert spec.primary_output().identifier == "BSDF"
