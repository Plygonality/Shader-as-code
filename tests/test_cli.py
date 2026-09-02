from __future__ import annotations

import json
from pathlib import Path

from shader_as_code.cli import main
from shader_as_code.samples import build_glass, build_metal


def test_cli_dump_diff_validate(tmp_path: Path, capsys) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(build_metal().dumps(), encoding="utf-8")
    b.write_text(build_glass().dumps(), encoding="utf-8")

    assert main(["validate", str(a)]) == 0
    assert capsys.readouterr().out.strip() == "ok"

    out = tmp_path / "canonical.json"
    assert main(["dump", str(a), "-o", str(out)]) == 0
    assert json.loads(out.read_text())["name"] == "MN Metal"

    assert main(["diff", str(a), str(a)]) == 0
    assert main(["diff", str(a), str(b)]) == 1
    captured = capsys.readouterr().out
    assert "+ node" in captured or "- node" in captured or "~" in captured

    assert main(["mermaid", str(a)]) == 0
    assert "flowchart LR" in capsys.readouterr().out

    assert main(["apply-script", str(a), "--material", "Metal"]) == 0
    script = capsys.readouterr().out
    assert "apply_graph_dict" in script

    assert main(["dump-script", "MN Metal"]) == 0
    dump_script = capsys.readouterr().out
    assert "dump_tree_by_name" in dump_script
