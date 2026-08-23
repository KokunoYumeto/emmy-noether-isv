#!/usr/bin/env python3
"""Fail-closed completeness inventory for the final ISV019 projection gate.

This is deliberately an inventory, not a projector and not an applicator.  It
authenticates the sealed EDIT0171 Latin head, reuses the frozen v2 TeX
segmenter, and emits stable locators for the three remaining review surfaces:

* unprotected style spans which may be original-language titles or venues;
* unprotected personal-name/initial sequences whose letters are otherwise
  valid Interslavic and therefore invisible to the blocker scanner; and
* visible one-letter I/V/M tokens which mix lexical Interslavic with Roman
  structural labels and initials.

Default execution is read-only and prints canonical JSON.  ``--write`` writes
only the declared machine index below; it never modifies sources, producers,
state, ledgers, projectors, or release artifacts.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Sequence


sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_latin"
DECISION_DIR = ROOT / "decision_records"
OUTPUT_PATH = DECISION_DIR / "ISV019-FINAL-PROJECTION-COMPLETENESS-INVENTORY.json"
V2_PATH = ROOT / "project_isv_cyrillic_v2.py"
V4_PATH = ROOT / "project_isv_cyrillic_v4.py"
STATE_PATH = ROOT / "00_SESSION_INDEPENDENT_STATE_v019.json"
DICTIONARY_PATH = (
    ROOT.parents[3]
    / "01_methodology"
    / "claude_fable_program"
    / "data"
    / "interslavic_dictionary_official_snapshot_20260816"
    / "source_sheet_basic.csv"
)

SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)

SOURCE_PINS = {
    "44-book-isv.tex": (
        168_422,
        "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    ),
    "45-isv.tex": (
        26_053,
        "5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91",
    ),
    "base-papers1-43-isv.tex": (
        1_894_721,
        "79D093D3C17D26F37EF9C1F5E71FFF387D58EFE5BE2EAB7C283F4C00BB8F2C7A",
    ),
    "bib-isv.tex": (
        10_019,
        "032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553",
    ),
}
V2_PIN = (
    74_914,
    "FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2",
)
V4_PIN = (
    34_849,
    "A63A6F697A99F5A8D64C0B69D24875C3031C8EFE7DE8A137DE8F844CD460E341",
)
STATE_PIN = (
    29_865,
    "234B3EF72F9F081C9D3244CB410D9ACECD03732E16CA46215E39B5E4A6C3943F",
)
DICTIONARY_PIN = (
    8_101_157,
    "0A30B582D341424FF05F05D0FBF1D2B5AA06B561D9B3816219D9865505918561",
)

VISIBLE_ROLES = frozenset({"visible_prose", "visible_math_text", "visible_metadata"})
STYLE_COMMANDS = frozenset({"emph", "textit", "textsc"})
NAME_PARTICLES = r"(?:van|von|der|de|des|du|della|di|la|le)"
CAPITAL = r"[A-ZÀ-ÖØ-ÞČĆĐĚĽĹŃŇŘŚŠŤŹŽÅȦÉÜÖÄÆŒ]"
LETTER = r"[^\W\d_]"
TEX_SPACE = r"(?:\\[ ,;:]|~|\s)"
INITIAL_NAME_RE = re.compile(
    rf"(?<!{LETTER})"
    rf"(?:(?:{CAPITAL}\.){TEX_SPACE}+)+"
    rf"(?:{NAME_PARTICLES}{TEX_SPACE}+)*"
    rf"{CAPITAL}{LETTER}+(?:[-'’]{CAPITAL}?{LETTER}+)?"
    rf"(?:{TEX_SPACE}+(?:{NAME_PARTICLES}{TEX_SPACE}+)*{CAPITAL}{LETTER}+)?"
)
FULL_NAME_RE = re.compile(
    rf"(?<!{LETTER}){CAPITAL}{LETTER}{{2,}}{TEX_SPACE}+{CAPITAL}{LETTER}{{2,}}"
)
ONE_LETTER_RE = re.compile(r"(?<![^\W\d_])[IVM](?![^\W\d_])")

# Exact physical lines whose unprotected style payloads were read in context
# and adjudicated as original-language titles, venues, or complete identities.
# Two mixed lines (16117 and 16129) are handled by exact payload below.
FOREIGN_STYLE_LINES = {
    "45-isv.tex": frozenset({37}),
    "base-papers1-43-isv.tex": frozenset(
        {
            61, 165, 176, 195, 261, 274, 398, 549,
            3643, 3649, 3662, 3699, 3701, 3703, 3705, 3707, 3711, 3987,
            6626, 6753, 8443, 8445, 8726, 8730, 8892, 8904, 8976, 8978,
            9154, 9195, 9297, 9516, 9522, 9532, 9534, 9790, 9832, 9835,
            9849, 9866, 9872, 9876, 9879, 9883, 9889, 9907, 9922, 9937,
            9995, 10031, 10033, 10035, 10093, 10122, 10643, 10651, 10726,
            10729, 10731, 10885, 10896, 10898, 10927, 10953, 10955, 10957,
            11527, 12036, 12341, 13695, 13813, 13869,
            14560, 15205, 15983, 15985, 15991, 16112, 16131, 16133,
            16309, 16491, 16601, 16719, 16923, 17210, 17273, 18787, 18789,
            18861, 18897, 19535, 19668, 19671, 19679, 19740,
            19744, 19746, 19989, 22738, 22745, 22782,
        }
    ),
    "bib-isv.tex": frozenset({228}),
}
FOREIGN_STYLE_EXACT_MIXED = frozenset(
    {
        ("base-papers1-43-isv.tex", 16117, "Idealtheorie in Ringbereichen"),
        ("base-papers1-43-isv.tex", 16129, "Algebraische Theorie der Ringe III"),
        ("base-papers1-43-isv.tex", 11214, "Schmeidler"),
        ("base-papers1-43-isv.tex", 13711, "Zur Theorie der Moduln"),
        ("base-papers1-43-isv.tex", 14220, "The algebraic theory of modular systems"),
        ("base-papers1-43-isv.tex", 15164, "Der Endlichkeitssatz der Invarianten endlicher Gruppen"),
        ("base-papers1-43-isv.tex", 19490, "Kleines Lehrbuch der Algebra"),
        ("base-papers1-43-isv.tex", 19674, "Math. Zeitschr."),
        ("base-papers1-43-isv.tex", 19674, "Ber. Berl. Ak."),
        ("base-papers1-43-isv.tex", 19674, "Atti"),
    }
)

UNINFLECTED_INITIAL_NAME_SURFACES = frozenset(
    {
        "A. A. Albert", "A. Capelli", "A. Clebsch", "A. Speiser",
        "B.~G. Teubner", "C. Chevalley", "D. Hilbert", "E. Artin",
        "E. Fischer", "E. Hecke", "E. Landau", "E. Lasker", "E. Noether",
        "E. Pascal", "E. Steinitz", "E. Study", "E. Zermelo", "F. Klein",
        "F. Mertens", "F. S. Macaulay", "F. Seidelmann", "G. Bucht",
        "G. Castelnuovo", "G. Frobenius", "G. Hamel", "G. Maisano",
        "H. Blumberg", "H. Brandt", "H. Grell", "H. Hasse", "H. Kapferer",
        "H. Lebesgue", "I. Schur", "J. Deruyts", "J. Levitzki", "J. Schur",
        "K. Hentzelt", "K.~Hentzelt", "K. Shoda", "M. Deuring",
        "M. Herzberger", "M. Noether", "O. Ore", "O. Schmidt", "P. Gordan",
        "P. Urysohn", "R. Brauer", "R. Courant",
    }
)
UNINFLECTED_FULL_NAME_SURFACES = frozenset(
    {"Emmy Noether", "Grete Hermann", "Julius Springer", "Kurt Hentzelt", "Masazo Sono"}
)
FOREIGN_LEXICON_PROTECT_SURFACES = frozenset(
    {
        "Abelschen", "Abh", "Abstrakter", "Abt", "Acc", "Ak", "Akad",
        "algebraic", "Algebraische", "algebraischen", "Algebras", "Algebren",
        "Allgemeine", "allgemeine", "Amer", "and", "Ann", "Annalen", "Artin",
        "Atti", "Aufbau", "aus", "Ausdehnungslehre", "Ausgabe", "Bd", "Ber",
        "Berichte", "Berl", "Bologna", "Brauer", "Cambridge", "Castelnuovo",
        "Circ", "Congresso", "Das", "delle", "den", "Der", "der",
        "Determinantentheorie", "Deuring", "di", "Die", "Differentialgleichungen",
        "DMV", "Eine", "eine", "Emmy", "endlichen", "endlicher", "Engel",
        "Erlangen", "Festschrift", "Formel", "Formen", "Fraenkel", "Frobenius",
        "Funktionen", "Gebilde", "Geometrie", "Ges", "Gleichungen", "Grassmann",
        "Grundlagen", "Gruppen", "Hasse", "Hermann", "Hilbert", "Idealtheorie",
        "ihre", "Invariante", "Invarianten", "invarianten", "Invariantensysteme",
        "Invariantentheorie", "Jahresb", "Jahresber", "Jan", "jan", "Jordan",
        "Journal", "kleine", "Krull", "Kurven", "Lehrbuch", "Leipzig", "les",
        "Linc", "linearen", "Math", "math", "Mathematiker", "Mathematische",
        "Methoden", "mit", "Modular", "modular", "Moduln", "Moscou", "neue",
        "Noether", "Nullstellentheorie", "of", "On", "Ore", "Phys",
        "Polynomideale", "Probleme", "Rec", "Reine", "Rend", "Riemann",
        "Ringbereichen", "Ringe", "Satz", "Schmeidler", "Schur", "Sitzungsber",
        "Sitzungsberichte", "Soc", "sulla", "Sur", "System", "Systems", "systems",
        "Teil", "Teubner", "The", "the", "Theorie", "theory", "Tracts", "Trans",
        "Uber", "und", "van", "Variabeln", "Ver", "Vol", "Volle", "Von", "von",
        "Zahlbericht", "Zahlen", "Zahlentheorie", "Zeit", "Zeitschr", "Zeitschrift",
        "Zs", "zu", "Zur",
    }
)

ROMAN_LEFT_RE = re.compile(
    r"(?:Glava|Teorem\w*|Definicij\w*|Lem\w*|Satz|Čest|čest|tom|Tom|"
    r"poglavj\w*|odděl\w*|děl|Děl|kniga|svezok|aksiom\w*|dokaz|Dokaz|"
    r"formula|Formula|§)\s*(?:\\(?:emph|textit|textbf)\{)?\s*$",
    re.UNICODE,
)
ROMAN_NEIGHBOR_RE = re.compile(r"^(?:\s|~|\\,|\\;)*(?:--|---|–|-|,|/|i)\s*(?:I|V|X|L|C|D|M)")
ONE_LETTER_EXACT_STRUCTURAL = frozenset(
    {("base-papers1-43-isv.tex", 9847, 67, "I")}
)


def in_ranges(start: int, end: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(left <= start and end <= right for left, right in ranges)


def one_letter_disposition(
    filename: str,
    line: int,
    column: int,
    text: str,
    start: int,
    surface: str,
    protected_ranges: Sequence[tuple[int, int]],
) -> str:
    if (filename, line, column, surface) in ONE_LETTER_EXACT_STRUCTURAL:
        return "PRESERVE_STRUCTURAL_ROMAN_LABEL"
    if in_ranges(start, start + 1, protected_ranges):
        return "PRESERVE_COVERED_BY_ALLOWED_LETTER_FOREIGN_RANGE"
    before = text[max(0, start - 120) : start]
    after = text[start + 1 : min(len(text), start + 121)]
    if surface == "M":
        return "PRESERVE_FOREIGN_INITIAL_OR_CITATION_ABBREVIATION"
    if re.match(r"^\.(?:\\[ ,;:]|~|\s)*(?:\\foreign\{)?[A-ZÀ-ÖØ-ÞČĆĐĚŠŽ]", after):
        return "PRESERVE_DOTTED_INITIAL_OR_ROMAN_ORDINAL"
    if after.lstrip().startswith((".", ":", ")", "]")):
        return "PRESERVE_STRUCTURAL_ROMAN_LABEL"
    if ROMAN_LEFT_RE.search(before):
        return "PRESERVE_STRUCTURAL_ROMAN_LABEL"
    if ROMAN_NEIGHBOR_RE.match(after) or re.search(
        r"(?:I|V|X|L|C|D|M)(?:\s|~|\\,|\\;)*(?:--|---|–|-|,|/)\s*$",
        before,
    ):
        return "PRESERVE_STRUCTURAL_ROMAN_LABEL"
    compact_before = before.rstrip()
    compact_after = after.lstrip()
    if compact_before.endswith(("(", "[", "{")) and compact_after.startswith((")", "]", ".", ":")):
        return "PRESERVE_STRUCTURAL_ROMAN_LABEL"
    if re.search(r"\\item\[\s*$", before) and re.match(r"^[.\]]", compact_after):
        return "PRESERVE_STRUCTURAL_ROMAN_LABEL"
    return "PROJECT_LEXICAL_INTERSLAVIC_WORD"


def style_disposition(filename: str, line: int, payload: str) -> str:
    if line in FOREIGN_STYLE_LINES.get(filename, frozenset()):
        return "PROTECT_COMPLETE_ORIGINAL_LANGUAGE_STYLE_PAYLOAD"
    if (filename, line, payload) in FOREIGN_STYLE_EXACT_MIXED:
        return "PROTECT_COMPLETE_ORIGINAL_LANGUAGE_STYLE_PAYLOAD"
    return "KEEP_PROJECTABLE_INTERSLAVIC_STYLE_PAYLOAD"


def name_disposition(surface: str) -> str:
    if surface in UNINFLECTED_INITIAL_NAME_SURFACES or surface in UNINFLECTED_FULL_NAME_SURFACES:
        return "PROTECT_COMPLETE_UNINFLECTED_IDENTITY"
    return "KEEP_PROJECTABLE_INTEGRATED_OR_NONNAME_CANDIDATE"


class AuditError(RuntimeError):
    pass


_LINE_TABLE_CACHE: dict[int, tuple[str, tuple[list[int], list[int], list[str]]]] = {}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def describe(data: bytes) -> dict[str, Any]:
    return {"bytes": len(data), "sha256": sha256(data)}


def pin_tuple(data: bytes) -> tuple[int, str]:
    return len(data), sha256(data)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def read_exact(
    path: Path,
    pin: tuple[int, str],
    label: str,
    *,
    canonical_transport: bool = True,
) -> bytes:
    require(path.exists() and path.is_file() and not path.is_symlink(), f"unsafe {label}: {path}")
    raw = path.read_bytes()
    require(pin_tuple(raw) == pin, f"{label} pin drift: {pin_tuple(raw)}")
    if canonical_transport:
        require(not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw, f"transport drift: {label}")
    return raw


def load_v2() -> Any:
    read_exact(V2_PATH, V2_PIN, "frozen v2 projector")
    spec = importlib.util.spec_from_file_location("isv019_final_audit_v2", V2_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v2 projector")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    require(tuple(module.SOURCE_ORDER) == SOURCE_ORDER, "v2 source order drift")
    return module


def role_at(segments: Sequence[Any], scalar_offset: int) -> str:
    lo = 0
    hi = len(segments)
    while lo < hi:
        mid = (lo + hi) // 2
        item = segments[mid]
        if scalar_offset < item.start:
            hi = mid
        elif scalar_offset >= item.end:
            lo = mid + 1
        else:
            return item.role
    raise AuditError(f"no role for scalar offset {scalar_offset}")


def context(text: str, start: int, end: int, width: int = 90) -> str:
    return text[max(0, start - width) : min(len(text), end + width)].replace("\n", " ")


def locator(v2: Any, text: str, start: int) -> dict[str, Any]:
    key = id(text)
    cached = _LINE_TABLE_CACHE.get(key)
    if cached is None or cached[0] is not text:
        cached = (text, v2.line_tables(text))
        _LINE_TABLE_CACHE[key] = cached
    scalar_starts, byte_starts, lines = cached[1]
    return v2.locator(text, start, scalar_starts, byte_starts, lines)


def iter_controls(v2: Any, text: str) -> Iterable[Any]:
    cursor = 0
    while cursor < len(text):
        char = text[cursor]
        if char == "%":
            cursor = v2.unescaped_comment_end(text, cursor)
            continue
        if char == "\\":
            control = v2.read_control_at(text, cursor)
            yield control
            cursor = control.end
            continue
        cursor += 1


def command_spans(v2: Any, text: str, names: set[str] | frozenset[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for control in iter_controls(v2, text):
        if control.name not in names:
            continue
        next_scalar = v2.skip_space_and_comments(text, control.end)
        # Macro declarations contain a literal control name (for example
        # ``\providecommand{\foreign}[1]{#1}``) rather than an invocation.
        if next_scalar >= len(text) or text[next_scalar] != "{":
            continue
        group_start, group_end, payload = v2.command_group_at(text, control)
        rows.append(
            {
                "command_start": control.start,
                "command_end": group_end,
                "payload_start": group_start + 1,
                "payload_end": group_end - 1,
                "command": control.name,
                "payload": payload,
            }
        )
    return rows


def protected_by_foreign(start: int, end: int, foreign: Sequence[dict[str, Any]]) -> bool:
    return any(item["payload_start"] <= start and end <= item["payload_end"] for item in foreign)


def record(
    v2: Any,
    filename: str,
    text: str,
    segments: Sequence[Any],
    start: int,
    end: int,
    surface: str,
    kind: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "file": filename,
        "kind": kind,
        "surface": surface,
        "surface_sha256": sha256(surface.encode("utf-8")),
        "scalar_span": [start, end],
        "role": role_at(segments, start),
        **locator(v2, text, start),
        "context": context(text, start, end),
        **extra,
    }


def style_inventory(
    v2: Any,
    filename: str,
    text: str,
    segments: Sequence[Any],
    foreign: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in command_spans(v2, text, STYLE_COMMANDS):
        if protected_by_foreign(item["payload_start"], item["payload_end"], foreign):
            continue
        if "\\foreign{" in item["payload"] or "\\isvforeign{" in item["payload"]:
            continue
        role = role_at(segments, item["payload_start"])
        if role not in VISIBLE_ROLES:
            continue
        rows.append(
            record(
                v2,
                filename,
                text,
                segments,
                item["payload_start"],
                item["payload_end"],
                item["payload"],
                "unprotected_style_payload",
                command=item["command"],
                disposition=style_disposition(
                    filename,
                    locator(v2, text, item["payload_start"])["line"],
                    item["payload"],
                ),
            )
        )
    return rows


def name_inventory(
    v2: Any,
    filename: str,
    text: str,
    segments: Sequence[Any],
    foreign: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for segment in segments:
        if segment.role not in VISIBLE_ROLES:
            continue
        raw = text[segment.start : segment.end]
        for pattern, subtype in (
            (INITIAL_NAME_RE, "initial_plus_surname"),
            (FULL_NAME_RE, "two_capitalized_words"),
        ):
            for match in pattern.finditer(raw):
                start = segment.start + match.start()
                end = segment.start + match.end()
                if (start, end) in seen or protected_by_foreign(start, end, foreign):
                    continue
                seen.add((start, end))
                rows.append(
                    record(
                        v2,
                        filename,
                        text,
                        segments,
                        start,
                        end,
                        match.group(0),
                        "unprotected_name_candidate",
                        subtype=subtype,
                        disposition=name_disposition(match.group(0)),
                    )
                )
    return sorted(rows, key=lambda row: row["scalar_span"])


def one_letter_inventory(
    v2: Any,
    filename: str,
    text: str,
    segments: Sequence[Any],
    protected_ranges: Sequence[tuple[int, int]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment in segments:
        if segment.role not in VISIBLE_ROLES:
            continue
        raw = text[segment.start : segment.end]
        for match in ONE_LETTER_RE.finditer(raw):
            start = segment.start + match.start()
            loc = locator(v2, text, start)
            rows.append(
                record(
                    v2,
                    filename,
                    text,
                    segments,
                    start,
                    start + 1,
                    match.group(0),
                    "visible_one_letter",
                    disposition=one_letter_disposition(
                        filename,
                        loc["line"],
                        loc["column"],
                        text,
                        start,
                        match.group(0),
                        protected_ranges,
                    ),
                )
            )
    return rows


def foreign_lexicon_hit_inventory(
    v2: Any,
    filename: str,
    text: str,
    segments: Sequence[Any],
    lexicon: frozenset[str],
) -> list[dict[str, Any]]:
    """Locate visible words also attested inside an explicit foreign island.

    This is evidence for review, not an automatic language decision: cognates
    and short function words can legitimately occur in both languages.
    """

    rows: list[dict[str, Any]] = []
    for segment in segments:
        if segment.role not in VISIBLE_ROLES:
            continue
        raw = text[segment.start : segment.end]
        for match in v2.LETTER_RE.finditer(raw):
            surface = match.group(0)
            if len(surface) < 2 or surface.casefold() not in lexicon:
                continue
            start = segment.start + match.start()
            rows.append(
                record(
                    v2,
                    filename,
                    text,
                    segments,
                    start,
                    segment.start + match.end(),
                    surface,
                    "unprotected_foreign_lexicon_hit",
                    disposition=(
                        "PROTECT_ATTESTED_FOREIGN_CITATION_OR_IDENTITY_TOKEN"
                        if surface in FOREIGN_LEXICON_PROTECT_SURFACES
                        else "KEEP_PROJECTABLE_AMBIGUOUS_OR_INTERSLAVIC_LEXICON_HIT"
                    ),
                )
            )
    return rows


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    result = {
        "occurrences": len(rows),
        "inventory_sha256": sha256(canonical_json(list(rows))),
        "by_file": dict(sorted(Counter(row["file"] for row in rows).items())),
        "by_surface": dict(sorted(Counter(row["surface"] for row in rows).items())),
    }
    dispositions = Counter(row["disposition"] for row in rows if "disposition" in row)
    if dispositions:
        result["by_disposition"] = dict(sorted(dispositions.items()))
    return result


def build() -> dict[str, Any]:
    v2 = load_v2()
    read_exact(V4_PATH, V4_PIN, "sealed v4 preflight")
    read_exact(STATE_PATH, STATE_PIN, "sealed EDIT0171 state")
    read_exact(
        DICTIONARY_PATH,
        DICTIONARY_PIN,
        "official dictionary snapshot",
        canonical_transport=False,
    )

    sources: list[dict[str, Any]] = []
    styles: list[dict[str, Any]] = []
    names: list[dict[str, Any]] = []
    one_letters: list[dict[str, Any]] = []
    foreign_lexicon_hits: list[dict[str, Any]] = []
    corpus: dict[str, tuple[bytes, str, Sequence[Any], list[dict[str, Any]]]] = {}
    foreign_lexicon: set[str] = set()
    for filename in SOURCE_ORDER:
        raw = read_exact(SOURCE_DIR / filename, SOURCE_PINS[filename], filename)
        text = v2.strict_transport(raw, filename)
        segments = v2.TexSegmenter(text).segment()
        foreign = command_spans(v2, text, frozenset({"foreign", "isvforeign"}))
        corpus[filename] = (raw, text, segments, foreign)
        for island in foreign:
            foreign_lexicon.update(
                match.group(0).casefold()
                for match in v2.LETTER_RE.finditer(island["payload"])
                if len(match.group(0)) >= 2
            )

    frozen_lexicon = frozenset(foreign_lexicon)
    for filename in SOURCE_ORDER:
        raw, text, segments, foreign = corpus[filename]
        current_styles = style_inventory(v2, filename, text, segments, foreign)
        current_names = name_inventory(v2, filename, text, segments, foreign)
        current_lexicon_hits = foreign_lexicon_hit_inventory(
            v2, filename, text, segments, frozen_lexicon
        )
        protected_ranges = [
            tuple(row["scalar_span"])
            for row in current_styles + current_names + current_lexicon_hits
            if row["disposition"].startswith("PROTECT")
        ]
        current_one = one_letter_inventory(
            v2, filename, text, segments, protected_ranges
        )
        styles.extend(current_styles)
        names.extend(current_names)
        one_letters.extend(current_one)
        foreign_lexicon_hits.extend(current_lexicon_hits)
        sources.append(
            {
                "path": f"source_latin/{filename}",
                **describe(raw),
                "scalars": len(text),
                "lines": len(text.splitlines()),
                "segment_count": len(segments),
                "segment_sha256": v2.segment_digest(segments),
                "foreign_islands": len(foreign),
                "unprotected_style_payloads": len(current_styles),
                "unprotected_name_candidates": len(current_names),
                "visible_one_letter_tokens": len(current_one),
                "unprotected_foreign_lexicon_hits": len(current_lexicon_hits),
            }
        )

    require(len(one_letters) == 690, f"one-letter live census drift: {len(one_letters)}")
    result = {
        "schema": "noether-isv-final-projection-completeness-inventory-v1",
        "status": "READ_ONLY_REVIEW_INVENTORY_NOT_A_RELEASE_GATE",
        "scope": {
            "sealed_head": "ISV019-EDIT-0171",
            "purpose": (
                "locate allowed-letter false negatives and classify visible I/V/M "
                "before deterministic Cyrillic projection"
            ),
            "source_order": list(SOURCE_ORDER),
        },
        "dependencies": {
            "v2_projector": {"path": V2_PATH.name, "bytes": V2_PIN[0], "sha256": V2_PIN[1]},
            "v4_preflight": {"path": V4_PATH.name, "bytes": V4_PIN[0], "sha256": V4_PIN[1]},
            "sealed_state": {"path": STATE_PATH.name, "bytes": STATE_PIN[0], "sha256": STATE_PIN[1]},
            "official_dictionary": {
                "path": str(DICTIONARY_PATH),
                "bytes": DICTIONARY_PIN[0],
                "sha256": DICTIONARY_PIN[1],
            },
        },
        "sources": sources,
        "summaries": {
            "unprotected_style_payloads": summarise(styles),
            "unprotected_name_candidates": summarise(names),
            "visible_one_letter_tokens": summarise(one_letters),
            "unprotected_foreign_lexicon_hits": summarise(foreign_lexicon_hits),
        },
        "unprotected_style_payloads": styles,
        "unprotected_name_candidates": names,
        "visible_one_letter_tokens": one_letters,
        "foreign_lexicon": {
            "unique_casefold_tokens": len(frozen_lexicon),
            "casefold_inventory_sha256": sha256(canonical_json(sorted(frozen_lexicon))),
        },
        "unprotected_foreign_lexicon_hits": foreign_lexicon_hits,
        "closure_rule": (
            "Every occurrence must receive an explicit locator-bound disposition; "
            "uninflected foreign identities must be protected as whole islands; "
            "morphologically integrated Interslavic name forms remain projectable; "
            "ordinary I/V words project while Roman labels and foreign initials remain Latin."
        ),
    }
    result["inventory_sha256_excluding_this_field"] = sha256(canonical_json(result))
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help=f"write {OUTPUT_PATH.name}")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = build()
        payload = canonical_json(result)
        if args.write:
            require(OUTPUT_PATH.parent.exists(), f"missing output directory: {OUTPUT_PATH.parent}")
            OUTPUT_PATH.write_bytes(payload)
            require(OUTPUT_PATH.read_bytes() == payload, "output readback mismatch")
        print(payload.decode("utf-8"), end="")
        return 0
    except Exception as error:
        failure = {
            "schema": "noether-isv-final-projection-completeness-inventory-failure-v1",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        print(canonical_json(failure).decode("utf-8"), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
