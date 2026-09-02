from __future__ import annotations

import base64
import importlib.util
import json
import tempfile
import unittest
import zlib
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "render_mermaid.py"
FIXTURES = Path(__file__).parent / "fixtures"
SPEC = importlib.util.spec_from_file_location("render_mermaid", SCRIPT)
assert SPEC and SPEC.loader
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def fake_png(width: int = 100, height: int = 80) -> bytes:
    return (
        renderer.PNG_SIGNATURE
        + b"\x00\x00\x00\rIHDR"
        + width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"data"
    )


def fake_rgba_png(pixel: tuple[int, int, int, int]) -> bytes:
    ihdr = (1).to_bytes(4, "big") * 2 + bytes((8, 6, 0, 0, 0))
    image_data = zlib.compress(b"\x00" + bytes(pixel))
    return (
        renderer.PNG_SIGNATURE
        + renderer._png_chunk(b"IHDR", ihdr)
        + renderer._png_chunk(b"IDAT", image_data)
        + renderer._png_chunk(b"IEND", b"")
    )


def fake_rgb_png(pixel: tuple[int, int, int]) -> bytes:
    ihdr = (1).to_bytes(4, "big") * 2 + bytes((8, 2, 0, 0, 0))
    image_data = zlib.compress(b"\x00" + bytes(pixel))
    return (
        renderer.PNG_SIGNATURE
        + renderer._png_chunk(b"IHDR", ihdr)
        + renderer._png_chunk(b"IDAT", image_data)
        + renderer._png_chunk(b"IEND", b"")
    )


def png_idat(payload: bytes) -> bytes:
    parts: list[bytes] = []
    offset = len(renderer.PNG_SIGNATURE)
    while offset + 12 <= len(payload):
        length = int.from_bytes(payload[offset : offset + 4], "big")
        kind = payload[offset + 4 : offset + 8]
        start = offset + 8
        if kind == b"IDAT":
            parts.append(payload[start : start + length])
        offset = start + length + 4
        if kind == b"IEND":
            break
    return zlib.decompress(b"".join(parts))


class DetectionTests(unittest.TestCase):
    def test_detects_supported_diagram_types(self) -> None:
        cases = {
            "flowchart TD\n A --> B": "flowchart",
            "graph LR\n A --> B": "flowchart",
            "sequenceDiagram\n A->>B: hello": "sequence",
            "stateDiagram-v2\n [*] --> Ready": "state",
            "classDiagram\n A <|-- B": "class",
            "erDiagram\n USER ||--o{ ORDER : places": "er",
            "mindmap\n root((Topic))": "mindmap",
            "timeline\n 2026 : Launch": "timeline",
            "gantt\n title Plan": "gantt",
            "gitGraph\n commit": "gitgraph",
            "journey\n title Signup": "journey",
            "pie\n \"Done\" : 70": "pie",
            "quadrantChart\n x-axis Low --> High": "quadrant",
            "architecture-beta\n service api[API]": "architecture-native",
            "block\n columns 2\n A B": "block",
            "block-beta\n columns 2\n A B": "block",
            "kanban\n todo[Todo]": "kanban",
            "sankey\n A,B,1": "sankey",
            "sankey-beta\n A,B,1": "sankey",
            "xychart\n line [1,2]": "xychart",
            "xychart-beta\n line [1,2]": "xychart",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(renderer.detect_diagram_type(source), expected)

    def test_ignores_frontmatter_and_comments(self) -> None:
        source = """---
title: Example
config:
  theme: neutral
---
%% comment
sequenceDiagram
  A->>B: hello
"""
        self.assertEqual(renderer.detect_diagram_type(source), "sequence")

    def test_detection_is_case_insensitive(self) -> None:
        self.assertEqual(renderer.detect_diagram_type("CLASSDIAGRAM\n A"), "class")
        self.assertEqual(renderer.detect_diagram_type("GitGraph\n commit"), "gitgraph")

    def test_selects_architecture_only_for_layered_lr_flowcharts(self) -> None:
        architecture = "flowchart LR\n subgraph API\n A --> B\n end"
        process = "flowchart TD\n subgraph API\n A --> B\n end"
        self.assertEqual(renderer.resolve_preset(architecture), "architecture")
        self.assertEqual(renderer.resolve_preset(process), "process")

    def test_explicit_preset_wins(self) -> None:
        self.assertEqual(
            renderer.resolve_preset("flowchart TD\n A --> B", "architecture"),
            "architecture",
        )

    def test_selects_named_presets_for_extended_types(self) -> None:
        cases = {
            "classDiagram\n A": "class",
            "erDiagram\n A ||--|| B : owns": "er",
            "mindmap\n root((A))": "mindmap",
            "timeline\n 2026 : A": "timeline",
            "gantt\n title A": "gantt",
            "gitGraph\n commit": "gitgraph",
            "journey\n title A": "journey",
            "pie\n \"A\" : 1": "pie",
            "quadrantChart\n A: [0.5, 0.5]": "quadrant",
            "architecture-beta\n service api[API]": "architecture-native",
            "block\n A B": "block",
            "kanban\n todo[Todo]": "kanban",
            "sankey\n A,B,1": "sankey",
            "xychart\n line [1,2]": "xychart",
        }
        for source, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(renderer.resolve_preset(source), expected)

    def test_extended_fixtures_match_their_named_presets(self) -> None:
        for expected in (
            "class",
            "er",
            "mindmap",
            "timeline",
            "gantt",
            "gitgraph",
            "journey",
            "pie",
            "quadrant",
            "architecture-native",
            "block",
            "kanban",
            "sankey",
            "xychart",
        ):
            with self.subTest(expected=expected):
                source = renderer.read_mermaid(FIXTURES / f"{expected}.mmd")
                self.assertEqual(renderer.detect_diagram_type(source), expected)
                self.assertEqual(renderer.resolve_preset(source), expected)


class ThemeTests(unittest.TestCase):
    def test_theme_defaults_resolve_to_expected_looks(self) -> None:
        self.assertEqual(renderer.resolve_look("cursor"), "classic")
        self.assertEqual(renderer.resolve_look("dark"), "classic")
        self.assertEqual(renderer.resolve_look("ocean"), "classic")
        self.assertEqual(renderer.resolve_look("forest"), "classic")
        self.assertEqual(renderer.resolve_look("aurora"), "neo")
        self.assertEqual(renderer.resolve_look("docs"), "neo")
        self.assertEqual(renderer.resolve_look("minimal"), "classic")
        self.assertEqual(renderer.resolve_look("docs", "classic"), "classic")

    def test_docs_config_uses_global_html_labels(self) -> None:
        config = renderer.build_config("docs", "process", "neo")
        self.assertTrue(config["htmlLabels"])
        self.assertNotIn("htmlLabels", config["flowchart"])
        self.assertEqual(config["look"], "neo")
        self.assertIn("edgeLabel", config["themeCSS"])

    def test_accent_recolors_flowchart_and_pie(self) -> None:
        themed = renderer.apply_theme(
            "flowchart TD\n A --> B",
            "cursor",
            "process",
            "classic",
            True,
            accent="#E11D48",
        )
        self.assertIn("stroke:#E11D48", themed)
        self.assertIn('"pie1":"#E11D48"', themed)

    def test_named_styles_expose_dark_ocean_forest(self) -> None:
        self.assertIn("dark", renderer.THEMES)
        self.assertIn("ocean", renderer.THEMES)
        self.assertIn("forest", renderer.THEMES)
        themed = renderer.apply_theme(
            "flowchart TD\n A --> B", "ocean", "process", "classic", True
        )
        self.assertIn("stroke:#0E7490", themed)

    def test_cursor_flowchart_receives_paper_semantic_classes(self) -> None:
        themed = renderer.apply_theme(
            "flowchart TD\n A --> B", "cursor", "process", "classic", True
        )
        self.assertIn("classDef accent fill:#EFF6FF", themed)
        self.assertIn("linkStyle default stroke:#52525B", themed)
        self.assertNotIn("drop-shadow", themed)

    def test_cursor_sankey_receives_muted_palette(self) -> None:
        source = "sankey\nVisitors,Registered,6\nVisitors,Exited,4"
        themed = renderer.apply_theme(source, "cursor", "sankey", "classic", True)
        self.assertIn('"Visitors":"#2563EB"', themed)

    def test_engine_auto_tries_local_first(self) -> None:
        self.assertEqual(
            renderer.engine_chain("auto"),
            ("local",),
        )
        self.assertEqual(renderer.engine_chain("local"), ("local",))

    def test_local_launcher_skips_windows_cmd_shims(self) -> None:
        command = renderer._mmdc_command()
        self.assertTrue(command)
        self.assertFalse(any(part.lower().endswith((".cmd", ".bat")) for part in command))
        self.assertNotIn("npx", Path(command[0]).stem.lower())

    def test_npx_cache_roots_cover_unix_and_windows(self) -> None:
        roots = {path.as_posix() for path in renderer._npx_cache_roots()}
        self.assertTrue(any(root.endswith(".npm/_npx") for root in roots))

    def test_chromium_lookup_does_not_crash(self) -> None:
        path = renderer.chromium_executable()
        if path:
            self.assertTrue(Path(path).is_file())

    def test_aurora_config_uses_transparent_canvas_and_vivid_palette(self) -> None:
        config = renderer.build_config("aurora", "xychart", "neo")
        variables = config["themeVariables"]
        self.assertEqual(variables["background"], "transparent")
        self.assertEqual(variables["primaryColor"], "#F7F9FF")
        self.assertEqual(variables["quadrantPointFill"], "#3F72F2")
        self.assertEqual(
            variables["xyChart"]["plotColorPalette"],
            "#3F72F2,#7C5CE7,#19A987,#F0A13B,#E45F7A",
        )
        self.assertIn("drop-shadow", config["themeCSS"])

    def test_aurora_flowchart_receives_vivid_semantic_classes(self) -> None:
        themed = renderer.apply_theme(
            "flowchart TD\n A --> B", "aurora", "process", "neo", True
        )
        self.assertIn("classDef accent fill:#526FE6", themed)
        self.assertIn("linkStyle default stroke:#7184AE", themed)

    def test_aurora_sankey_receives_vivid_source_palette(self) -> None:
        source = "sankey\nVisitors,Registered,6\nVisitors,Exited,4"
        themed = renderer.apply_theme(source, "aurora", "sankey", "neo", True)
        self.assertIn('"Visitors":"#3F72F2"', themed)
        self.assertIn('"Registered":"#7C5CE7"', themed)

    def test_aurora_builds_valid_config_for_every_preset(self) -> None:
        for preset in renderer.PRESETS:
            with self.subTest(preset=preset):
                config = renderer.build_config("aurora", preset, "neo")
                self.assertEqual(config["theme"], "base")
                self.assertEqual(config["look"], "neo")
                self.assertEqual(
                    config["themeVariables"]["background"],
                    "transparent",
                )

    def test_sankey_receives_a_source_derived_restrained_palette(self) -> None:
        source = "sankey\nVisitors,Registered,6\nVisitors,Exited,4"
        themed = renderer.apply_theme(source, "docs", "sankey", "neo", True)
        self.assertIn('"linkColor":"gradient"', themed)
        self.assertIn('"nodeColors"', themed)
        self.assertIn('"Visitors":"#3D6EB5"', themed)
        self.assertIn('"Registered":"#6F91C5"', themed)

    def test_docs_theme_keeps_state_labels_readable(self) -> None:
        config = renderer.build_config("docs", "state", "neo")
        self.assertEqual(
            config["themeVariables"]["stateLabelColor"], "#0F172A"
        )

    def test_docs_theme_has_restrained_extended_diagram_palette(self) -> None:
        variables = renderer.build_config("docs", "pie", "neo")["themeVariables"]
        self.assertEqual(variables["pie1"], "#3D6EB5")
        self.assertEqual(variables["git1"], "#4A8B68")
        self.assertEqual(variables["attributeBackgroundColorEven"], "#F8FAFC")
        self.assertEqual(variables["critBkgColor"], "#F5F0E6")
        self.assertEqual(variables["quadrantPointFill"], "#3D6EB5")
        self.assertEqual(variables["pieStrokeColor"], "#F8FAFC")
        self.assertEqual(
            variables["xyChart"]["plotColorPalette"],
            "#3D6EB5,#4A8B68,#B08D4F,#7A6F92",
        )

    def test_flowchart_receives_semantic_class_definitions(self) -> None:
        themed = renderer.apply_theme(
            "flowchart TD\n A --> B", "docs", "process", "neo", True
        )
        self.assertIn("%%{init:", themed)
        self.assertIn('"look":"neo"', themed)
        self.assertIn("classDef process", themed)
        self.assertIn("classDef accent", themed)
        self.assertIn("linkStyle default", themed)

    def test_sequence_and_state_do_not_receive_flowchart_classes(self) -> None:
        for source, preset in (
            ("sequenceDiagram\n A->>B: hello", "sequence"),
            ("stateDiagram\n [*] --> Ready", "state"),
        ):
            with self.subTest(preset=preset):
                themed = renderer.apply_theme(source, "docs", preset, "neo", True)
                self.assertNotIn("classDef process", themed)
                self.assertNotIn("linkStyle default", themed)

    def test_extended_types_do_not_receive_flowchart_classes(self) -> None:
        cases = (
            ("classDiagram\n A", "class"),
            ("erDiagram\n A ||--|| B : owns", "er"),
            ("mindmap\n root((A))", "mindmap"),
            ("timeline\n 2026 : A", "timeline"),
            ("gantt\n title A", "gantt"),
            ("gitGraph\n commit", "gitgraph"),
            ("journey\n title A", "journey"),
            ("pie\n \"A\" : 1", "pie"),
            ("quadrantChart\n A: [0.5, 0.5]", "quadrant"),
            ("architecture-beta\n service api[API]", "architecture-native"),
            ("block\n A B", "block"),
            ("kanban\n todo[Todo]", "kanban"),
            ("sankey\n A,B,1", "sankey"),
            ("xychart\n line [1,2]", "xychart"),
        )
        for source, preset in cases:
            with self.subTest(preset=preset):
                themed = renderer.apply_theme(source, "docs", preset, "neo", True)
                self.assertNotIn("classDef process", themed)
                self.assertNotIn("linkStyle default", themed)

    def test_existing_config_is_preserved(self) -> None:
        source = """---
config:
  theme: neutral
---
flowchart TD
  A --> B
"""
        themed = renderer.apply_theme(source, "docs", "process", "neo", False)
        self.assertFalse(themed.startswith("%%{init:"))
        self.assertIn(source.strip(), themed)
        self.assertNotIn('"look":"neo"', themed)

    def test_existing_class_definition_is_not_duplicated(self) -> None:
        source = "flowchart TD\n A --> B\n classDef process fill:#fff"
        themed = renderer.apply_theme(source, "docs", "process", "neo", True)
        self.assertEqual(themed.count("classDef process"), 1)

    def test_existing_link_style_is_not_duplicated(self) -> None:
        source = "flowchart TD\n A --> B\n linkStyle default stroke:#000"
        themed = renderer.apply_theme(source, "docs", "process", "neo", True)
        self.assertEqual(themed.count("linkStyle default"), 1)

    def test_auto_neo_can_fallback_to_classic(self) -> None:
        raw = "flowchart TD\n A --> B"
        neo_source = renderer.apply_theme(raw, "docs", "process", "neo", True)
        original = renderer.render_formats
        calls: list[str] = []

        def fake_render_formats(source: str, formats: tuple[str, ...], engine: str, background: str = "#FFFFFF"):
            calls.append(source)
            if len(calls) == 1:
                raise SystemExit("neo unsupported")
            return {"png": fake_png()}

        renderer.render_formats = fake_render_formats
        try:
            payloads, final_source, look, used_fallback = (
                renderer.render_with_look_fallback(
                    raw,
                    neo_source,
                    ("png",),
                    "mermaid.ink",
                    "docs",
                    "process",
                    "neo",
                    True,
                    True,
                )
            )
        finally:
            renderer.render_formats = original

        self.assertEqual(payloads["png"], fake_png())
        self.assertEqual(look, "classic")
        self.assertTrue(used_fallback)
        self.assertIn('"look":"classic"', final_source)


class InputAndOutputTests(unittest.TestCase):
    def test_cli_defaults_to_verified_primary_engine(self) -> None:
        parser = renderer.build_parser()
        args = parser.parse_args(["diagram.mmd"])
        self.assertEqual(args.engine, "local")
        self.assertEqual(args.theme, "cursor")
        self.assertEqual(args.look, "auto")

    def test_cli_accepts_extended_presets(self) -> None:
        parser = renderer.build_parser()
        for preset in (
            "class",
            "er",
            "mindmap",
            "timeline",
            "gantt",
            "gitgraph",
            "journey",
            "pie",
            "quadrant",
            "architecture-native",
            "block",
            "kanban",
            "sankey",
            "xychart",
        ):
            with self.subTest(preset=preset):
                self.assertEqual(
                    parser.parse_args(["diagram.mmd", "--preset", preset]).preset,
                    preset,
                )

    def test_reads_fenced_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagram.md"
            path.write_text(
                "```mermaid\nflowchart TD\n A --> B\n```\n", encoding="utf-8"
            )
            self.assertEqual(renderer.read_mermaid(path), "flowchart TD\n A --> B")

    def test_validates_png_and_svg_signatures(self) -> None:
        renderer.validate_payload(fake_png(), "png")
        renderer.validate_payload(b"<?xml version='1.0'?><svg></svg>", "svg")

    def test_flattens_transparent_png_onto_document_background(self) -> None:
        flattened = renderer.flatten_png_background(
            fake_rgba_png((10, 20, 30, 0)),
            (248, 250, 252),
        )
        self.assertEqual(flattened[25], 2)
        self.assertEqual(png_idat(flattened), b"\x00\xf8\xfa\xfc")

    def test_preserves_opaque_png_without_alpha_channel(self) -> None:
        opaque = fake_rgb_png((10, 20, 30))
        self.assertIs(
            renderer.flatten_png_background(opaque, (248, 250, 252)),
            opaque,
        )

    def test_composites_transparent_png_onto_aurora_gradient(self) -> None:
        transparent = fake_rgba_png((10, 20, 30, 0))
        composited, degraded = renderer.apply_png_theme_background(
            transparent,
            "aurora",
        )
        expected = bytes(renderer.aurora_background_pixel(0, 0, 1, 1))
        self.assertEqual(composited[25], 2)
        self.assertEqual(png_idat(composited), b"\x00" + expected)
        self.assertFalse(degraded)

    def test_reports_aurora_degradation_for_opaque_png(self) -> None:
        opaque = fake_rgb_png((10, 20, 30))
        composited, degraded = renderer.apply_png_theme_background(
            opaque,
            "aurora",
        )
        self.assertIs(composited, opaque)
        self.assertTrue(degraded)

    def test_aurora_gradient_changes_across_canvas(self) -> None:
        top_left = renderer.aurora_background_pixel(0, 0, 100, 100)
        bottom_right = renderer.aurora_background_pixel(99, 99, 100, 100)
        self.assertNotEqual(top_left, bottom_right)
        self.assertGreater(sum(top_left), 600)
        self.assertGreater(sum(bottom_right), 600)

    def test_adds_svg_document_background(self) -> None:
        svg = b"<?xml version='1.0'?><svg><text>Hi</text></svg>"
        themed = renderer.add_svg_background(svg, "#F8FAFC")
        self.assertIn(b'<svg><rect width="100%" height="100%" fill="#F8FAFC"/>', themed)
        renderer.validate_payload(themed, "svg")

    def test_adds_aurora_svg_background_once(self) -> None:
        svg = b"<?xml version='1.0'?><svg><text>Hi</text></svg>"
        themed = renderer.add_svg_theme_background(svg, "aurora")
        self.assertIn(b'id="flowchart-aurora-background"', themed)
        self.assertIn(b'fill="url(#flowchart-aurora-linear)"', themed)
        self.assertIn(b'fill="url(#flowchart-aurora-violet)"', themed)
        self.assertEqual(
            renderer.add_svg_theme_background(themed, "aurora"),
            themed,
        )
        renderer.validate_payload(themed, "svg")

    def test_resolves_theme_background(self) -> None:
        self.assertEqual(renderer.theme_background("cursor"), "#FFFFFF")
        self.assertEqual(renderer.theme_background("dark"), "#18181B")
        self.assertEqual(renderer.theme_background("ocean"), "#F4FBFC")
        self.assertEqual(renderer.theme_background("forest"), "#F5FBF6")
        self.assertEqual(renderer.theme_background("aurora"), "#E8EEFF")
        self.assertEqual(renderer.theme_background("docs"), "#F8FAFC")
        self.assertEqual(renderer.hex_to_rgb("#F8FAFC"), (248, 250, 252))

    def test_rejects_invalid_image_payloads(self) -> None:
        with self.assertRaises(RuntimeError):
            renderer.validate_payload(b'{"error":"bad diagram"}', "png")
        with self.assertRaises(RuntimeError):
            renderer.validate_payload(b"<html>bad diagram</html>", "svg")

    def test_atomic_write_replaces_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.bin"
            path.write_bytes(b"old")
            renderer.atomic_write(path, b"new")
            self.assertEqual(path.read_bytes(), b"new")
            self.assertEqual(list(path.parent.glob(f".{path.name}.*.tmp")), [])

    def test_layout_warnings_detect_extreme_aspect_ratios(self) -> None:
        self.assertTrue(renderer.layout_warnings(fake_png(100, 300)))
        self.assertTrue(renderer.layout_warnings(fake_png(500, 100)))
        self.assertEqual(renderer.layout_warnings(fake_png(200, 100)), [])
        self.assertEqual(renderer.layout_warnings(fake_png(100, 300), "state"), [])

    def test_layout_warnings_allow_naturally_wide_diagrams(self) -> None:
        wide = fake_png(500, 100)
        for diagram_type in (
            "mindmap",
            "timeline",
            "gantt",
            "gitgraph",
            "journey",
        ):
            with self.subTest(diagram_type=diagram_type):
                self.assertEqual(renderer.layout_warnings(wide, diagram_type), [])

    def test_layout_warnings_still_review_structural_and_square_diagrams(self) -> None:
        wide = fake_png(500, 100)
        for diagram_type in ("class", "pie", "quadrant"):
            with self.subTest(diagram_type=diagram_type):
                self.assertTrue(renderer.layout_warnings(wide, diagram_type))
        self.assertTrue(renderer.layout_warnings(fake_png(700, 100), "er"))

    def test_layout_warnings_allow_compact_horizontal_er_overviews(self) -> None:
        self.assertEqual(renderer.layout_warnings(fake_png(520, 100), "er"), [])

    def test_layout_warnings_use_relaxed_second_wave_thresholds(self) -> None:
        self.assertEqual(
            renderer.layout_warnings(fake_png(600, 100), "architecture-native"),
            [],
        )
        self.assertEqual(renderer.layout_warnings(fake_png(700, 100), "kanban"), [])
        self.assertTrue(renderer.layout_warnings(fake_png(900, 100), "kanban"))

    def test_mermaid_ink_requests_png_explicitly(self) -> None:
        original_fetch = renderer.fetch
        captured: list[str] = []

        def fake_fetch(url: str, data: bytes | None = None, timeout: int = 90) -> bytes:
            captured.append(url)
            return fake_png()

        renderer.fetch = fake_fetch
        try:
            renderer.render_mermaid_ink("flowchart TD\n A --> B", "png")
        finally:
            renderer.fetch = original_fetch

        self.assertIn("type=png", captured[0])
        self.assertIn("scale=2", captured[0])

    def test_mermaid_ink_transport_does_not_reapply_theme(self) -> None:
        encoded = renderer.encode_mermaid_ink("flowchart TD\n A --> B")
        payload = encoded.removeprefix("pako:")
        payload += "=" * (-len(payload) % 4)
        state = json.loads(zlib.decompress(base64.urlsafe_b64decode(payload)))
        self.assertEqual(state["mermaid"], {})


class StructuredDataValidationTests(unittest.TestCase):
    def test_accepts_valid_sankey_csv_with_quoted_comma(self) -> None:
        renderer.validate_sankey_source(
            'sankey\n"New, visitors",Registered,620\nRegistered,Paid,210'
        )

    def test_rejects_invalid_sankey_rows(self) -> None:
        cases = (
            ("sankey\nA,B", "expected source,target,value"),
            ("sankey\nA,B,zero", "value must be numeric"),
            ("sankey\nA,B,0", "finite positive"),
            ("sankey\nA,B,nan", "finite positive"),
            ("sankey\n,B,1", "must not be empty"),
            ("sankey\n访问用户,Registered,1", "labels must use ASCII"),
        )
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, message):
                    renderer.validate_sankey_source(source)

    def test_accepts_valid_xy_categorical_series(self) -> None:
        renderer.validate_xychart_source(
            'xychart\n x-axis [Q1,Q2,Q3]\n y-axis "数量" 0 --> 100\n'
            ' bar [30,55,80]\n line [25,50,75]'
        )

    def test_accepts_valid_xy_numeric_axis(self) -> None:
        renderer.validate_xychart_source(
            'xychart horizontal\n x-axis "索引" -10 --> 10\n line [-2,0,3.5]'
        )

    def test_rejects_invalid_xy_series(self) -> None:
        cases = (
            (
                "xychart\n x-axis [Q1,Q2,Q3]\n bar [1,2]",
                "but x-axis has 3 categories",
            ),
            ("xychart\n line [1,nan]", "must be finite"),
            ("xychart\n line [1,label]", "must be plain numbers"),
            ("xychart\n title Empty", "requires at least one"),
            ("xychart\n y-axis 10 --> 0\n line [1]", "minimum must be below"),
        )
        for source, message in cases:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, message):
                    renderer.validate_xychart_source(source)

    def test_validation_dispatches_only_for_structured_data_types(self) -> None:
        with self.assertRaises(ValueError):
            renderer.validate_diagram_source("sankey\nA,B", "sankey")
        with self.assertRaises(ValueError):
            renderer.validate_diagram_source("xychart\n title Empty", "xychart")
        renderer.validate_diagram_source("block\n A B", "block")


if __name__ == "__main__":
    unittest.main()
