#!/usr/bin/env python3
"""Fail-closed v019 Interslavic Latin-to-Cyrillic projection preflight.

This is the append-only successor to the historical v018 regex masker.  It
does not import, patch, or execute that implementation.  The scanner assigns
every source scalar exactly one semantic role, recognizes TeX controls before
interpreting math delimiters, validates an exact environment stack, and keeps
the default command line strictly read-only.

The current Latin corpus is intentionally expected to remain blocked until
its finite lexical/name/protection queue is closed.  A blocked scan is a
successful audit result, not permission to emit a reader.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA = "noether-isv-cyrillic-projection-v2-preflight-1"
ROOT = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIR = ROOT / "source_latin"
DEFAULT_FIXTURES = ROOT / "cyrillic_projection_v2_fixtures.json"
SOURCE_ORDER = (
    "44-book-isv.tex",
    "45-isv.tex",
    "base-papers1-43-isv.tex",
    "bib-isv.tex",
)
EDIT0149_AUDIT_SOURCE_PINS = {
    "44-book-isv.tex": (
        168_422,
        "68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F",
    ),
    "45-isv.tex": (
        26_014,
        "20B9123DFD81C0A3B3445A6CCAE8F711843F79C8D1DF75DF02406AF3A66A480F",
    ),
    "base-papers1-43-isv.tex": (
        1_892_315,
        "2A35A7530685CF1A32AFDF92807D9FCFDD090FF2767211ABBE8B0D8DF0E29AA3",
    ),
    "bib-isv.tex": (
        9_939,
        "71E4746C77776B1E504EF79EA9C097644219BFDF482004F1D4AAE45DA1C490C5",
    ),
}

# Official standard-script correspondences documented in
# CYRILLIC_PROJECTION_V2_SPEC_v019.md.  q/w/x are deliberately absent.
STANDARD_SINGLE = {
    "a": "а",
    "b": "б",
    "c": "ц",
    "č": "ч",
    "d": "д",
    "e": "е",
    "ě": "є",
    "f": "ф",
    "g": "г",
    "h": "х",
    "i": "и",
    "j": "ј",
    "k": "к",
    "l": "л",
    "m": "м",
    "n": "н",
    "o": "о",
    "p": "п",
    "r": "р",
    "s": "с",
    "š": "ш",
    "t": "т",
    "u": "у",
    "v": "в",
    "y": "ы",
    "z": "з",
    "ž": "ж",
}
STANDARD_DIGRAPHS = {"dž": "дж", "lj": "љ", "nj": "њ"}
ETYMOLOGICAL_SIMPLIFICATION = {
    "ę": "e",
    "ų": "u",
    "å": "a",
    "ė": "e",
    "ȯ": "o",
    "ć": "č",
    "đ": "dž",
    # The maintained Latin sources also use these explicit etymological
    # spellings.  They have no separate standard Cyrillic surface.
    "ò": "o",
    "ĺ": "l",
    "ľ": "l",
    "ń": "n",
    "ň": "n",
    "ŕ": "r",
    "ř": "r",
    "ť": "t",
    "ď": "d",
    "ś": "s",
    "ź": "z",
}
SUPPORTED_LATIN = frozenset(STANDARD_SINGLE) | frozenset(ETYMOLOGICAL_SIMPLIFICATION)
LETTER_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
ROMAN_RE = re.compile(
    r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})"
)

# These are mathematical proof-end identity literals, not Interslavic prose.
# Keeping an exact finite table avoids both a letter-wide q exemption and a
# context heuristic.
STRUCTURAL_IDENTITY_LITERALS = (
    "q. e. d.",
    "q.e.d.",
    "Q. E. D.",
    "Q.E.D.",
)
MAPPING_BLOCK_REASONS = frozenset(
    {"unmapped_or_ambiguous_letter", "wrong_script_in_latin_source"}
)

MATH_ENVIRONMENTS = frozenset(
    {
        "align",
        "align*",
        "aligned",
        "array",
        "cases",
        "displaymath",
        "equation",
        "equation*",
        "gather",
        "gather*",
        "gathered",
        "math",
        "matrix",
        "multline",
        "multline*",
        "pmatrix",
        "smallmatrix",
        "split",
        "vmatrix",
    }
)
FOREIGN_ENVIRONMENTS = frozenset({"otherlanguage", "otherlanguage*"})
VERBATIM_ENVIRONMENTS = frozenset(
    {"verbatim", "verbatim*", "lstlisting", "minted", "filecontents", "filecontents*"}
)
CODE_ENVIRONMENTS = frozenset({"tikzpicture", "picture"})

MATH_TEXT_COMMANDS = frozenset(
    {
        "text",
        "textrm",
        "textit",
        "textbf",
        "textnormal",
        "mbox",
        "hbox",
        "intertext",
        "footnote",
        "footnotetext",
    }
)
FOREIGN_COMMANDS = {"foreign": 1, "isvforeign": 1, "foreignlanguage": 2}

PRESERVED_ARGUMENT_COMMANDS: dict[str, tuple[str, ...]] = {
    "label": ("protected_identity_arg",),
    "ref": ("protected_identity_arg",),
    "pageref": ("protected_identity_arg",),
    "eqref": ("protected_identity_arg",),
    "autoref": ("protected_identity_arg",),
    "Cref": ("protected_identity_arg",),
    "cref": ("protected_identity_arg",),
    "cite": ("protected_identity_arg",),
    "citep": ("protected_identity_arg",),
    "citet": ("protected_identity_arg",),
    "nocite": ("protected_identity_arg",),
    "url": ("protected_identity_arg",),
    "path": ("protected_identity_arg",),
    "bibitem": ("protected_identity_arg",),
    "input": ("protected_identity_arg",),
    "include": ("protected_identity_arg",),
    "bibliography": ("protected_identity_arg",),
    "bibliographystyle": ("protected_identity_arg",),
    "includegraphics": ("protected_identity_arg",),
    "index": ("protected_identity_arg",),
    "tag": ("protected_identity_arg",),
    "setlength": ("protected_identity_arg", "protected_identity_arg"),
    "addtolength": ("protected_identity_arg", "protected_identity_arg"),
    "setcounter": ("protected_identity_arg", "protected_identity_arg"),
    "addtocounter": ("protected_identity_arg", "protected_identity_arg"),
    "rule": ("protected_identity_arg", "protected_identity_arg"),
    "hspace": ("protected_identity_arg",),
    "hspace*": ("protected_identity_arg",),
    "vspace": ("protected_identity_arg",),
    "vspace*": ("protected_identity_arg",),
    "geometry": ("protected_identity_arg",),
    "thispagestyle": ("protected_identity_arg",),
    "pagestyle": ("protected_identity_arg",),
    "pagenumbering": ("protected_identity_arg",),
    "enlargethispage": ("protected_identity_arg",),
    "newlength": ("protected_identity_arg",),
    "mcell": ("protected_math",),
    "diagbox": ("protected_math", "protected_math"),
}

ROLE_COMMANDS: dict[str, tuple[str, ...]] = {
    "srcfn": ("protected_identity_arg", "visible_prose"),
    "tocline": ("visible_prose", "protected_identity_arg"),
    "tocsec": ("protected_identity_arg", "visible_prose", "protected_identity_arg"),
    "noethpIIsrcfnmark": ("protected_identity_arg",),
    "noethpIIsrcfntext": ("protected_identity_arg", "visible_prose"),
    "addcontentsline": (
        "protected_identity_arg",
        "protected_identity_arg",
        "visible_prose",
    ),
    "href": ("protected_identity_arg", "visible_prose"),
    "texorpdfstring": ("visible_metadata", "visible_metadata"),
}

# These controls may be followed by an empty delimiter group, but do not take
# a required natural-language argument.  Treating them as ordinary unknown
# commands would create a false ambiguity hold; treating them as required-arg
# commands would reject valid bare uses such as ``\S\ 6``.
OPTIONAL_EMPTY_GROUP_COMMANDS = frozenset({"S", "glqq", "grqq"})

VISIBLE_ONE_ARGUMENT = frozenset(
    {
        "author",
        "caption",
        "chapter",
        "emph",
        "footnote",
        "footnotetext",
        "hbox",
        "mbox",
        "paragraph",
        "paragraph*",
        "part",
        "part*",
        "section",
        "section*",
        "subparagraph",
        "subparagraph*",
        "subsection",
        "subsection*",
        "subsubsection",
        "subsubsection*",
        "text",
        "textbf",
        "textit",
        "textnormal",
        "textrm",
        "textsf",
        "textsc",
        "textsuperscript",
        "texttt",
        "title",
        "underline",
        "uline",
    }
)
VISIBLE_TWO_ARGUMENT = frozenset({"textcolor", "colorbox"})
STYLE_SWITCHES = frozenset(
    {
        "bfseries",
        "centering",
        "em",
        "footnotesize",
        "Huge",
        "huge",
        "itshape",
        "large",
        "Large",
        "LARGE",
        "normalsize",
        "normalfont",
        "raggedleft",
        "raggedright",
        "rmfamily",
        "scriptsize",
        "sffamily",
        "small",
        "slshape",
        "tiny",
        "ttfamily",
        "upshape",
    }
)
DEFINITION_COMMANDS = frozenset(
    {
        "newcommand",
        "renewcommand",
        "providecommand",
        "DeclareRobustCommand",
        "newenvironment",
        "renewenvironment",
        "def",
        "gdef",
        "edef",
        "xdef",
        "DeclareMathOperator",
        "DeclareMathOperator*",
    }
)


class ProjectionError(ValueError):
    """A stable fail-closed parser or projection error."""

    def __init__(self, code: str, offset: int, detail: str):
        super().__init__(f"{code} at scalar {offset}: {detail}")
        self.code = code
        self.offset = offset
        self.detail = detail


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    role: str
    detail: str


@dataclass(frozen=True)
class Control:
    start: int
    end: int
    name: str
    is_word: bool


class SegmentBuilder:
    def __init__(self) -> None:
        self.cursor = 0
        self.segments: list[Segment] = []

    def add(self, start: int, end: int, role: str, detail: str = "") -> None:
        if start != self.cursor:
            raise RuntimeError(
                f"non-gap-free internal append: cursor={self.cursor}, span=({start},{end})"
            )
        if end < start:
            raise RuntimeError(f"negative internal span: ({start},{end})")
        if end == start:
            return
        if (
            self.segments
            and self.segments[-1].end == start
            and self.segments[-1].role == role
            and self.segments[-1].detail == detail
        ):
            prior = self.segments[-1]
            self.segments[-1] = Segment(prior.start, end, role, detail)
        else:
            self.segments.append(Segment(start, end, role, detail))
        self.cursor = end

    def finish(self, expected: int) -> tuple[Segment, ...]:
        if self.cursor != expected:
            raise RuntimeError(
                f"gap-free coverage failure: cursor={self.cursor}, expected={expected}"
            )
        prior = 0
        for segment in self.segments:
            if segment.start != prior or segment.end <= segment.start:
                raise RuntimeError(f"invalid segment ordering at {segment}")
            prior = segment.end
        return tuple(self.segments)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def read_control_at(text: str, start: int) -> Control:
    if start >= len(text) or text[start] != "\\":
        raise ProjectionError("internal_control_start", start, "expected backslash")
    if start + 1 >= len(text):
        raise ProjectionError("dangling_backslash", start, "control has no following scalar")
    next_char = text[start + 1]
    if next_char.isalpha() or next_char == "@":
        end = start + 2
        while end < len(text) and (text[end].isalpha() or text[end] == "@"):
            end += 1
        name = text[start + 1 : end]
        if end < len(text) and text[end] == "*":
            name += "*"
            end += 1
        return Control(start, end, name, True)
    return Control(start, start + 2, next_char, False)


def unescaped_comment_end(text: str, start: int) -> int:
    newline = text.find("\n", start)
    return len(text) if newline < 0 else newline + 1


def skip_space_and_comments(text: str, start: int) -> int:
    cursor = start
    while cursor < len(text):
        if text[cursor].isspace():
            cursor += 1
            continue
        if text[cursor] == "%":
            cursor = unescaped_comment_end(text, cursor)
            continue
        break
    return cursor


def raw_group_at(text: str, start: int, opening: str = "{", closing: str = "}") -> tuple[int, str]:
    if start >= len(text) or text[start] != opening:
        raise ProjectionError("missing_group", start, f"expected {opening!r}")
    depth = 1
    cursor = start + 1
    while cursor < len(text):
        char = text[cursor]
        if char == "%":
            cursor = unescaped_comment_end(text, cursor)
            continue
        if char == "\\":
            control = read_control_at(text, cursor)
            cursor = control.end
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return cursor + 1, text[start + 1 : cursor]
        cursor += 1
    raise ProjectionError("unclosed_group", start, f"missing {closing!r}")


def command_group_at(text: str, control: Control) -> tuple[int, int, str]:
    cursor = skip_space_and_comments(text, control.end)
    end, payload = raw_group_at(text, cursor)
    return cursor, end, payload


def strict_transport(data: bytes, label: str) -> str:
    if data.startswith(b"\xef\xbb\xbf"):
        raise ProjectionError("utf8_bom", 0, label)
    if b"\r" in data:
        raise ProjectionError("non_lf_newline", data.index(b"\r"), label)
    if not data.endswith(b"\n"):
        raise ProjectionError("missing_terminal_lf", len(data), label)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ProjectionError("invalid_utf8", error.start, label) from error
    if unicodedata.normalize("NFC", text) != text:
        raise ProjectionError("non_nfc", 0, label)
    return text


def _find_verbatim_end(text: str, start: int, environment: str) -> tuple[int, int]:
    needle = "\\end{" + environment + "}"
    cursor = start
    while True:
        found = text.find(needle, cursor)
        if found < 0:
            raise ProjectionError(
                "unclosed_verbatim_environment", start, f"missing {needle}"
            )
        line_start = text.rfind("\n", 0, found) + 1
        if text[line_start:found].strip() == "":
            return found, found + len(needle)
        cursor = found + 1


def validate_structure(text: str) -> dict[str, Any]:
    """Validate TeX structure without regex masking or cross-pass sentinels."""

    brace_stack: list[int] = []
    environment_stack: list[tuple[str, int]] = []
    math_stack: list[tuple[str, str, int]] = []
    controls = 0
    comments = 0
    environment_pairs = 0
    math_pairs = 0
    document_pairs = 0
    cursor = 0

    while cursor < len(text):
        char = text[cursor]
        if char == "%":
            comments += 1
            cursor = unescaped_comment_end(text, cursor)
            continue
        if char == "\\":
            control = read_control_at(text, cursor)
            controls += 1
            if control.name in {"verb", "verb*"}:
                if control.end >= len(text) or text[control.end] == "\n":
                    raise ProjectionError("malformed_verb", cursor, "missing delimiter")
                delimiter = text[control.end]
                end = text.find(delimiter, control.end + 1)
                newline = text.find("\n", control.end + 1)
                if end < 0 or (newline >= 0 and newline < end):
                    raise ProjectionError("malformed_verb", cursor, "delimiter not closed on line")
                cursor = end + 1
                continue
            if control.name in {"begin", "end"}:
                group_start, group_end, environment = command_group_at(text, control)
                if not environment or any(ch.isspace() for ch in environment):
                    raise ProjectionError(
                        "invalid_environment_name", group_start, repr(environment)
                    )
                if control.name == "begin":
                    environment_stack.append((environment, cursor))
                    if environment in VERBATIM_ENVIRONMENTS:
                        raw_end_start, raw_end = _find_verbatim_end(
                            text, group_end, environment
                        )
                        environment_stack.pop()
                        environment_pairs += 1
                        cursor = raw_end
                        continue
                else:
                    if not environment_stack:
                        raise ProjectionError(
                            "unmatched_environment_end", cursor, environment
                        )
                    expected, opened = environment_stack[-1]
                    if environment != expected:
                        raise ProjectionError(
                            "mismatched_environment_end",
                            cursor,
                            f"opened {expected!r} at {opened}, closed {environment!r}",
                        )
                    environment_stack.pop()
                    environment_pairs += 1
                    if environment == "document":
                        document_pairs += 1
                cursor = group_end
                continue
            if not control.is_word and control.name in {"(", "["}:
                closer = ")" if control.name == "(" else "]"
                math_stack.append(("control", closer, cursor))
            elif not control.is_word and control.name in {")",
                "]",
            }:
                if not math_stack or math_stack[-1][:2] != ("control", control.name):
                    expected = math_stack[-1][1] if math_stack else None
                    raise ProjectionError(
                        "mismatched_math_delimiter",
                        cursor,
                        f"observed \\{control.name}; expected {expected!r}",
                    )
                math_stack.pop()
                math_pairs += 1
            cursor = control.end
            continue
        if char == "$":
            delimiter = "$$" if text.startswith("$$", cursor) else "$"
            if math_stack and math_stack[-1][:2] == ("dollar", delimiter):
                math_stack.pop()
                math_pairs += 1
            elif math_stack and math_stack[-1][0] == "dollar":
                raise ProjectionError(
                    "mismatched_dollar_delimiter",
                    cursor,
                    f"observed {delimiter!r}; expected {math_stack[-1][1]!r}",
                )
            else:
                math_stack.append(("dollar", delimiter, cursor))
            cursor += len(delimiter)
            continue
        if char == "{":
            brace_stack.append(cursor)
        elif char == "}":
            if not brace_stack:
                raise ProjectionError("unmatched_closing_brace", cursor, "}")
            brace_stack.pop()
        cursor += 1

    if brace_stack:
        raise ProjectionError("unclosed_brace", brace_stack[-1], "{")
    if environment_stack:
        environment, opened = environment_stack[-1]
        raise ProjectionError("unclosed_environment", opened, environment)
    if math_stack:
        kind, delimiter, opened = math_stack[-1]
        raise ProjectionError("unclosed_math", opened, f"{kind}:{delimiter}")
    if document_pairs != 1:
        raise ProjectionError(
            "document_environment_count", 0, f"expected 1, observed {document_pairs}"
        )
    return {
        "brace_balance": 0,
        "unmatched_braces": 0,
        "comment_count": comments,
        "control_count": controls,
        "environment_pairs": environment_pairs,
        "unmatched_environments": 0,
        "math_delimiter_pairs": math_pairs,
        "unmatched_math_delimiters": 0,
        "document_pairs": document_pairs,
    }


class TexSegmenter:
    """Command-aware, gap-free semantic role segmenter."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.builder = SegmentBuilder()
        self.environment_stack: list[tuple[str, int]] = []
        self.unknown_argument_commands: list[dict[str, Any]] = []
        self.foreign_spans: list[tuple[int, int, str]] = []
        self.math_spans: list[tuple[int, int, str]] = []

    def _add_to(self, end: int, role: str, detail: str = "") -> None:
        start = self.pos
        self.builder.add(start, end, role, detail)
        self.pos = end

    def _consume_comment(self) -> None:
        self._add_to(unescaped_comment_end(self.text, self.pos), "protected_comment", "comment")

    def _consume_interarg(self, role: str = "protected_control") -> None:
        while self.pos < len(self.text):
            if self.text[self.pos].isspace():
                start = self.pos
                while self.pos < len(self.text) and self.text[self.pos].isspace():
                    self.pos += 1
                self.builder.add(start, self.pos, role, "inter_argument_space")
                continue
            if self.text[self.pos] == "%":
                self._consume_comment()
                continue
            break

    def _consume_raw_group(self, role: str, detail: str) -> tuple[int, int]:
        if self.pos >= len(self.text) or self.text[self.pos] != "{":
            raise ProjectionError("missing_required_argument", self.pos, detail)
        start = self.pos
        end, _ = raw_group_at(self.text, start)
        self._add_to(end, role, detail)
        return start, end

    def _consume_optional_raw(self, role: str, detail: str) -> bool:
        self._consume_interarg()
        if self.pos >= len(self.text) or self.text[self.pos] != "[":
            return False
        start = self.pos
        end, _ = raw_group_at(self.text, start, "[", "]")
        self._add_to(end, role, detail)
        return True

    def _parse_group(self, text_role: str, detail: str) -> None:
        if self.pos >= len(self.text) or self.text[self.pos] != "{":
            raise ProjectionError("missing_required_argument", self.pos, detail)
        self._add_to(self.pos + 1, "protected_structure", "group_open")
        self._parse_visible(text_role=text_role, stop_on_brace=True)
        if self.pos >= len(self.text) or self.text[self.pos] != "}":
            raise ProjectionError("unclosed_group", self.pos, detail)
        self._add_to(self.pos + 1, "protected_structure", "group_close")

    def _parse_optional_visible(self, text_role: str, detail: str) -> bool:
        self._consume_interarg()
        if self.pos >= len(self.text) or self.text[self.pos] != "[":
            return False
        self._add_to(self.pos + 1, "protected_structure", "optional_open")
        depth = 1
        while self.pos < len(self.text):
            if self.text[self.pos] == "]":
                depth -= 1
                self._add_to(self.pos + 1, "protected_structure", "optional_close")
                if depth == 0:
                    return True
                continue
            if self.text[self.pos] == "[":
                depth += 1
                self._add_to(self.pos + 1, "protected_structure", "optional_open")
                continue
            self._parse_visible_atom(text_role, extra_plain_stops="[]")
        raise ProjectionError("unclosed_optional_argument", self.pos, detail)

    def _parse_newtheorem(self, control: Control) -> None:
        self._add_to(control.end, "protected_control", "newtheorem")
        self._consume_interarg()
        self._consume_raw_group("protected_identity_arg", "newtheorem_environment")
        self._consume_optional_raw("protected_identity_arg", "newtheorem_shared_counter")
        self._consume_interarg()
        self._parse_group("visible_metadata", "newtheorem_display_name")
        self._consume_optional_raw("protected_identity_arg", "newtheorem_within_counter")

    def _parse_definition(self, control: Control) -> None:
        name = control.name
        self._add_to(control.end, "protected_definition", name)
        self._consume_interarg("protected_definition")
        if name in {"def", "gdef", "edef", "xdef"}:
            while self.pos < len(self.text) and self.text[self.pos] != "{":
                if self.text[self.pos] == "%":
                    self._consume_comment()
                elif self.text[self.pos] == "\\":
                    nested = read_control_at(self.text, self.pos)
                    self._add_to(nested.end, "protected_definition", "definition_signature")
                else:
                    self._add_to(self.pos + 1, "protected_definition", "definition_signature")
            self._consume_raw_group("protected_definition", "definition_body")
            return
        if name in {"newenvironment", "renewenvironment"}:
            self._consume_raw_group("protected_definition", "environment_name")
            self._consume_optional_raw("protected_definition", "argument_count")
            self._consume_optional_raw("protected_definition", "default_argument")
            self._consume_interarg("protected_definition")
            self._consume_raw_group("protected_definition", "environment_begin_body")
            self._consume_interarg("protected_definition")
            self._consume_raw_group("protected_definition", "environment_end_body")
            return
        if self.pos < len(self.text) and self.text[self.pos] == "{":
            self._consume_raw_group("protected_definition", "defined_control")
        elif self.pos < len(self.text) and self.text[self.pos] == "\\":
            defined = read_control_at(self.text, self.pos)
            self._add_to(defined.end, "protected_definition", "defined_control")
        else:
            raise ProjectionError(
                "missing_required_argument", self.pos, "defined_control"
            )
        if name in {"newcommand", "renewcommand", "providecommand", "DeclareRobustCommand"}:
            self._consume_optional_raw("protected_definition", "argument_count")
            self._consume_optional_raw("protected_definition", "default_argument")
            self._consume_interarg("protected_definition")
            self._consume_raw_group("protected_definition", "definition_body")
        else:
            self._consume_interarg("protected_definition")
            self._consume_raw_group("protected_definition", "operator_body")

    def _parse_role_arguments(self, control: Control, roles: Sequence[str]) -> None:
        self._add_to(control.end, "protected_control", control.name)
        # Citation-like commands may carry optional identity notes.
        while self._consume_optional_raw("protected_identity_arg", f"{control.name}_optional"):
            pass
        for order, role in enumerate(roles, 1):
            self._consume_interarg()
            if role.startswith("visible"):
                self._parse_group(role, f"{control.name}_arg{order}")
            else:
                self._consume_raw_group(role, f"{control.name}_arg{order}")

    def _parse_optional_empty_group_command(self, control: Control) -> None:
        self._add_to(control.end, "protected_control", control.name)
        self._consume_interarg()
        if self.pos >= len(self.text) or self.text[self.pos] != "{":
            return
        end, payload = raw_group_at(self.text, self.pos)
        if payload:
            self.unknown_argument_commands.append(
                {"command": control.name, "offset": control.start}
            )
            self._add_to(
                end,
                "ambiguous_command_arg",
                f"nonempty_delimiter_group:{control.name}",
            )
            return
        self._add_to(end, "protected_structure", f"empty_delimiter:{control.name}")

    def _parse_footnotemark(self, control: Control) -> None:
        self._add_to(control.end, "protected_control", control.name)
        self._consume_optional_raw("protected_identity_arg", "footnotemark_selector")

    def _parse_verb(self, control: Control) -> None:
        self._add_to(control.end, "protected_control", control.name)
        if self.pos >= len(self.text) or self.text[self.pos] == "\n":
            raise ProjectionError("malformed_verb", control.start, "missing delimiter")
        delimiter = self.text[self.pos]
        end = self.text.find(delimiter, self.pos + 1)
        newline = self.text.find("\n", self.pos + 1)
        if end < 0 or (newline >= 0 and newline < end):
            raise ProjectionError(
                "malformed_verb", control.start, "delimiter not closed on line"
            )
        self._add_to(end + 1, "protected_verbatim", control.name)

    def _parse_foreign(self, control: Control) -> None:
        self._add_to(control.end, "protected_control", control.name)
        start = control.start
        for order in range(FOREIGN_COMMANDS[control.name]):
            self._consume_interarg()
            self._consume_raw_group("protected_foreign", f"{control.name}_arg{order + 1}")
        self.foreign_spans.append((start, self.pos, control.name))

    def _parse_visible_command(self, control: Control, text_role: str) -> None:
        self._add_to(control.end, "protected_control", control.name)
        if control.name == "item":
            self._parse_optional_visible(text_role, "item_label")
            return
        if control.name in VISIBLE_TWO_ARGUMENT:
            self._consume_interarg()
            self._consume_raw_group("protected_identity_arg", f"{control.name}_selector")
        if control.name in {
            "chapter",
            "part",
            "part*",
            "section",
            "section*",
            "subsection",
            "subsection*",
            "subsubsection",
            "subsubsection*",
            "paragraph",
            "paragraph*",
            "subparagraph",
            "subparagraph*",
            "caption",
        }:
            self._parse_optional_visible(text_role, f"{control.name}_short")
        else:
            self._consume_optional_raw("protected_identity_arg", f"{control.name}_optional")
        self._consume_interarg()
        self._parse_group(text_role, f"{control.name}_visible")

    def _peek_environment_command(self) -> tuple[Control, int, int, str] | None:
        if self.pos >= len(self.text) or self.text[self.pos] != "\\":
            return None
        control = read_control_at(self.text, self.pos)
        if control.name not in {"begin", "end"}:
            return None
        group_start, group_end, environment = command_group_at(self.text, control)
        return control, group_start, group_end, environment

    def _consume_environment_header(
        self, control: Control, group_end: int, environment: str
    ) -> None:
        self._add_to(control.end, "protected_structure", control.name)
        if self.pos < group_end:
            self._add_to(group_end, "protected_structure", f"environment:{environment}")

    def _parse_environment(self, control: Control, group_end: int, environment: str) -> None:
        if control.name != "begin":
            raise ProjectionError("internal_environment_start", control.start, environment)
        opened = control.start
        self._consume_environment_header(control, group_end, environment)
        self.environment_stack.append((environment, opened))

        if environment in FOREIGN_ENVIRONMENTS:
            self._consume_interarg()
            self._consume_raw_group("protected_foreign", f"{environment}_language")
            content_role = "protected_foreign"
        elif environment in VERBATIM_ENVIRONMENTS:
            raw_end_start, raw_end = _find_verbatim_end(self.text, self.pos, environment)
            self._add_to(raw_end_start, "protected_verbatim", environment)
            end_control = read_control_at(self.text, self.pos)
            _, end_group_end, end_environment = command_group_at(self.text, end_control)
            if end_environment != environment:
                raise ProjectionError(
                    "mismatched_environment_end", self.pos, f"{environment}/{end_environment}"
                )
            self._consume_environment_header(end_control, end_group_end, end_environment)
            self.environment_stack.pop()
            return
        elif environment in CODE_ENVIRONMENTS:
            content_role = "protected_code"
        elif environment in MATH_ENVIRONMENTS:
            self._parse_math_environment(environment, opened)
            return
        else:
            content_role = "visible_prose"

        if environment in {"tabular", "array"}:
            self._consume_interarg()
            self._consume_raw_group("protected_identity_arg", f"{environment}_columns")
        elif environment == "adjustbox":
            self._consume_interarg()
            self._consume_raw_group("protected_identity_arg", "adjustbox_options")
        elif environment in {"minipage"}:
            self._consume_interarg()
            self._consume_raw_group("protected_identity_arg", f"{environment}_width")
        elif environment in {"enumerate", "description", "itemize"}:
            self._consume_optional_raw("protected_identity_arg", f"{environment}_options")

        if content_role.startswith("protected"):
            self._parse_protected_environment_content(environment, content_role, opened)
        else:
            self._parse_visible(text_role=content_role, stop_environment=environment)
            self._consume_matching_environment_end(environment, opened)

    def _consume_matching_environment_end(self, environment: str, opened: int) -> None:
        event = self._peek_environment_command()
        if event is None or event[0].name != "end":
            raise ProjectionError("unclosed_environment", opened, environment)
        control, _, group_end, observed = event
        if observed != environment:
            raise ProjectionError(
                "mismatched_environment_end",
                control.start,
                f"opened {environment!r} at {opened}, closed {observed!r}",
            )
        self._consume_environment_header(control, group_end, observed)
        expected, expected_opened = self.environment_stack.pop()
        if (expected, expected_opened) != (environment, opened):
            raise RuntimeError("environment stack identity failure")

    def _parse_protected_environment_content(
        self, environment: str, role: str, opened: int
    ) -> None:
        while self.pos < len(self.text):
            event = self._peek_environment_command()
            if event is not None:
                control, _, group_end, observed = event
                if control.name == "end":
                    if observed != environment:
                        raise ProjectionError(
                            "mismatched_environment_end",
                            control.start,
                            f"opened {environment!r} at {opened}, closed {observed!r}",
                        )
                    self._consume_matching_environment_end(environment, opened)
                    return
                self._parse_environment(control, group_end, observed)
                continue
            if self.text[self.pos] == "%":
                self._consume_comment()
            elif self.text[self.pos] == "\\":
                control = read_control_at(self.text, self.pos)
                self._add_to(control.end, role, environment)
            else:
                start = self.pos
                while self.pos < len(self.text) and self.text[self.pos] not in "%\\":
                    self.pos += 1
                self.builder.add(start, self.pos, role, environment)
        raise ProjectionError("unclosed_environment", opened, environment)

    def _parse_math_environment(self, environment: str, opened: int) -> None:
        content_start = self.pos
        while self.pos < len(self.text):
            event = self._peek_environment_command()
            if event is not None:
                control, _, group_end, observed = event
                if control.name == "end":
                    if observed != environment:
                        raise ProjectionError(
                            "mismatched_environment_end",
                            control.start,
                            f"opened {environment!r} at {opened}, closed {observed!r}",
                        )
                    self._consume_matching_environment_end(environment, opened)
                    self.math_spans.append((opened, self.pos, f"environment:{environment}"))
                    return
                self._parse_environment(control, group_end, observed)
                continue
            if self.text[self.pos] == "%":
                self._consume_comment()
                continue
            if self.text[self.pos] == "\\":
                control = read_control_at(self.text, self.pos)
                if control.name in MATH_TEXT_COMMANDS:
                    self._add_to(control.end, "protected_math", control.name)
                    self._consume_optional_raw("protected_math", f"{control.name}_optional")
                    self._consume_interarg("protected_math")
                    self._parse_group("visible_math_text", f"{control.name}_visible")
                elif control.name in FOREIGN_COMMANDS:
                    self._parse_foreign(control)
                elif not control.is_word and control.name == "\\":
                    self._add_to(control.end, "protected_math", "rowbreak")
                    self._consume_optional_raw("protected_math", "rowbreak_spacing")
                else:
                    self._add_to(control.end, "protected_math", environment)
                continue
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos] not in "%\\":
                self.pos += 1
            self.builder.add(start, self.pos, "protected_math", environment)
        raise ProjectionError("unclosed_environment", opened, environment)

    def _parse_delimited_math(self, opener: str, closer: str, opened: int) -> None:
        while self.pos < len(self.text):
            if self.text[self.pos] == "%":
                self._consume_comment()
                continue
            if opener in {"$", "$$"} and self.text.startswith(closer, self.pos):
                self._add_to(self.pos + len(closer), "protected_math", f"close:{closer}")
                self.math_spans.append((opened, self.pos, f"delimiter:{opener}"))
                return
            if self.text[self.pos] == "\\":
                control = read_control_at(self.text, self.pos)
                if opener.startswith("\\") and not control.is_word and control.name == closer[-1]:
                    self._add_to(control.end, "protected_math", f"close:{closer}")
                    self.math_spans.append((opened, self.pos, f"delimiter:{opener}"))
                    return
                if not control.is_word and control.name in {")",
                    "]",
                }:
                    raise ProjectionError(
                        "mismatched_math_delimiter",
                        control.start,
                        f"opened {opener!r}, closed \\{control.name}",
                    )
                if control.name in MATH_TEXT_COMMANDS:
                    self._add_to(control.end, "protected_math", control.name)
                    self._consume_optional_raw("protected_math", f"{control.name}_optional")
                    self._consume_interarg("protected_math")
                    self._parse_group("visible_math_text", f"{control.name}_visible")
                elif control.name in FOREIGN_COMMANDS:
                    self._parse_foreign(control)
                elif control.name == "begin":
                    _, group_end, environment = command_group_at(self.text, control)
                    self._parse_environment(control, group_end, environment)
                else:
                    self._add_to(control.end, "protected_math", opener)
                continue
            start = self.pos
            stop_chars = "%\\" + ("$" if opener in {"$", "$$"} else "")
            while self.pos < len(self.text) and self.text[self.pos] not in stop_chars:
                self.pos += 1
            self.builder.add(start, self.pos, "protected_math", opener)
        raise ProjectionError("unclosed_math", opened, opener)

    def _parse_command(self, text_role: str) -> None:
        control = read_control_at(self.text, self.pos)
        if not control.is_word and control.name in {"(", "["}:
            opener = "\\" + control.name
            closer = "\\" + (")" if control.name == "(" else "]")
            opened = control.start
            self._add_to(control.end, "protected_math", f"open:{opener}")
            self._parse_delimited_math(opener, closer, opened)
            return
        if not control.is_word and control.name in {")",
            "]",
        }:
            raise ProjectionError(
                "unmatched_math_delimiter", control.start, "\\" + control.name
            )
        if not control.is_word:
            detail = "rowbreak" if control.name == "\\" else "control_symbol"
            self._add_to(control.end, "protected_control", detail)
            if control.name == "\\":
                self._consume_optional_raw("protected_control", "rowbreak_spacing")
            return
        if control.name == "begin":
            _, group_end, environment = command_group_at(self.text, control)
            self._parse_environment(control, group_end, environment)
            return
        if control.name == "end":
            _, _, environment = command_group_at(self.text, control)
            raise ProjectionError("unmatched_environment_end", control.start, environment)
        if control.name == "newtheorem" or control.name == "newtheorem*":
            self._parse_newtheorem(control)
            return
        if control.name in {"verb", "verb*"}:
            self._parse_verb(control)
            return
        if control.name in DEFINITION_COMMANDS:
            self._parse_definition(control)
            return
        if control.name in FOREIGN_COMMANDS:
            self._parse_foreign(control)
            return
        if control.name in ROLE_COMMANDS:
            self._parse_role_arguments(control, ROLE_COMMANDS[control.name])
            return
        if control.name in PRESERVED_ARGUMENT_COMMANDS:
            self._parse_role_arguments(control, PRESERVED_ARGUMENT_COMMANDS[control.name])
            return
        if control.name in VISIBLE_ONE_ARGUMENT or control.name in VISIBLE_TWO_ARGUMENT:
            self._parse_visible_command(control, text_role)
            return
        if control.name == "item":
            self._parse_visible_command(control, text_role)
            return
        if control.name in OPTIONAL_EMPTY_GROUP_COMMANDS:
            self._parse_optional_empty_group_command(control)
            return
        if control.name == "footnotemark":
            self._parse_footnotemark(control)
            return
        if control.name in STYLE_SWITCHES:
            self._add_to(control.end, "protected_control", control.name)
            return

        # Unknown commands remain protected themselves.  If they take immediate
        # braced arguments, those arguments are scanned but marked ambiguous so
        # they cannot silently enter a release projection.
        self._add_to(control.end, "protected_control", control.name)
        lookahead = skip_space_and_comments(self.text, self.pos)
        if lookahead < len(self.text) and self.text[lookahead] in "[{":
            self.unknown_argument_commands.append(
                {"command": control.name, "offset": control.start}
            )
            self._consume_interarg()
            while self.pos < len(self.text) and self.text[self.pos] == "[":
                self._consume_optional_raw(
                    "ambiguous_command_arg", f"unknown:{control.name}:optional"
                )
                self._consume_interarg()
            while self.pos < len(self.text) and self.text[self.pos] == "{":
                self._parse_group(
                    "ambiguous_command_arg", f"unknown:{control.name}:required"
                )
                self._consume_interarg()

    def _parse_visible_atom(self, text_role: str, extra_plain_stops: str = "") -> None:
        if self.pos >= len(self.text):
            return
        char = self.text[self.pos]
        structural_literal = self._structural_identity_literal_at(self.pos)
        if structural_literal is not None:
            self._add_to(
                self.pos + len(structural_literal),
                "protected_identity_literal",
                structural_literal,
            )
        elif char == "%":
            self._consume_comment()
        elif char == "\\":
            self._parse_command(text_role)
        elif char == "$":
            opener = "$$" if self.text.startswith("$$", self.pos) else "$"
            opened = self.pos
            self._add_to(self.pos + len(opener), "protected_math", f"open:{opener}")
            self._parse_delimited_math(opener, opener, opened)
        elif char == "{":
            self._parse_group(text_role, "ordinary_group")
        elif char == "}":
            return
        else:
            start = self.pos
            stop_chars = "%\\${}" + extra_plain_stops
            while self.pos < len(self.text) and self.text[self.pos] not in stop_chars:
                if self.pos > start and self._structural_identity_literal_at(self.pos):
                    break
                self.pos += 1
            self.builder.add(start, self.pos, text_role, "text")

    def _structural_identity_literal_at(self, start: int) -> str | None:
        if start > 0 and self.text[start - 1].isalpha():
            return None
        for literal in STRUCTURAL_IDENTITY_LITERALS:
            if not self.text.startswith(literal, start):
                continue
            end = start + len(literal)
            if end < len(self.text) and self.text[end].isalpha():
                continue
            return literal
        return None

    def _parse_visible(
        self,
        text_role: str,
        stop_on_brace: bool = False,
        stop_environment: str | None = None,
    ) -> None:
        while self.pos < len(self.text):
            if stop_on_brace and self.text[self.pos] == "}":
                return
            if stop_environment is not None:
                event = self._peek_environment_command()
                if event is not None and event[0].name == "end":
                    observed = event[3]
                    if observed != stop_environment:
                        raise ProjectionError(
                            "mismatched_environment_end",
                            event[0].start,
                            f"opened {stop_environment!r}, closed {observed!r}",
                        )
                    return
            if self.text[self.pos] == "}":
                raise ProjectionError("unmatched_closing_brace", self.pos, "}")
            self._parse_visible_atom(text_role)

    def _parse_preamble(self) -> None:
        brace_depth = 0
        while self.pos < len(self.text):
            if self.text[self.pos] == "%":
                self._consume_comment()
                continue
            if self.text[self.pos] == "\\":
                control = read_control_at(self.text, self.pos)
                if control.name == "newtheorem" or control.name == "newtheorem*":
                    self._parse_newtheorem(control)
                    continue
                if control.name == "begin" and brace_depth == 0:
                    _, group_end, environment = command_group_at(self.text, control)
                    if environment == "document":
                        self._parse_environment(control, group_end, environment)
                        return
                self._add_to(control.end, "protected_preamble", "control")
                continue
            char = self.text[self.pos]
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth -= 1
                if brace_depth < 0:
                    raise ProjectionError("unmatched_closing_brace", self.pos, "preamble")
            self._add_to(self.pos + 1, "protected_preamble", "preamble")
        raise ProjectionError("missing_document_environment", 0, "no \\begin{document}")

    def segment(self) -> tuple[Segment, ...]:
        self._parse_preamble()
        # Anything after the exact document end is preserved and cannot become
        # projectable merely by following it.
        while self.pos < len(self.text):
            if self.text[self.pos] == "%":
                self._consume_comment()
            else:
                self._add_to(self.pos + 1, "protected_preamble", "post_document")
        if self.environment_stack:
            environment, opened = self.environment_stack[-1]
            raise ProjectionError("unclosed_environment", opened, environment)
        return self.builder.finish(len(self.text))


def simplify_etymological(word: str) -> tuple[str, bool]:
    output: list[str] = []
    changed = False
    for char in word:
        folded = char.casefold()
        if folded in ETYMOLOGICAL_SIMPLIFICATION:
            replacement = ETYMOLOGICAL_SIMPLIFICATION[folded]
            if char.isupper():
                replacement = replacement.upper()
            output.append(replacement)
            changed = True
        else:
            output.append(char)
    return "".join(output), changed


def token_block_reasons(word: str) -> list[str]:
    reasons: list[str] = []
    for char in word:
        name = unicodedata.name(char, "")
        folded = char.casefold()
        if "CYRILLIC" in name:
            reasons.append("wrong_script_in_latin_source")
        elif "LATIN" not in name or folded not in SUPPORTED_LATIN:
            reasons.append("unmapped_or_ambiguous_letter")
    # One-letter I/V/M surfaces are ordinary Interslavic words or initials in
    # this corpus.  Only a syntactically canonical multi-letter numeral enters
    # the separate structural-identity hold class.
    if len(word) >= 2 and ROMAN_RE.fullmatch(word):
        reasons.append("unlisted_structural_roman_identity")
    return sorted(set(reasons))


def has_mapping_block(reasons: Iterable[str]) -> bool:
    return any(reason in MAPPING_BLOCK_REASONS for reason in reasons)


def issue_inventory_sha256(issues: Sequence[dict[str, Any]]) -> str:
    return sha256_bytes(canonical_json_bytes(list(issues)))


def project_word(word: str) -> tuple[str, str]:
    reasons = token_block_reasons(word)
    if reasons:
        raise ProjectionError("blocked_token", 0, f"{word!r}: {','.join(reasons)}")
    simplified, etymological = simplify_etymological(word)
    lower = simplified.casefold()
    output: list[str] = []
    index = 0
    while index < len(simplified):
        pair = lower[index : index + 2]
        if pair in STANDARD_DIGRAPHS:
            mapped = STANDARD_DIGRAPHS[pair]
            source_pair = simplified[index : index + 2]
            if source_pair.isupper():
                mapped = mapped.upper()
            elif source_pair[:1].isupper():
                mapped = mapped[:1].upper() + mapped[1:]
            output.append(mapped)
            index += 2
            continue
        source_char = simplified[index]
        folded = source_char.casefold()
        if folded not in STANDARD_SINGLE:
            raise ProjectionError("internal_mapping_gap", index, source_char)
        mapped = STANDARD_SINGLE[folded]
        output.append(mapped.upper() if source_char.isupper() else mapped)
        index += 1
    classification = (
        "converted_after_explicit_etymological_simplification"
        if etymological
        else "converted_standard_isv"
    )
    return "".join(output), classification


def line_tables(text: str) -> tuple[list[int], list[int], list[str]]:
    scalar_starts = [0]
    byte_starts = [0]
    lines = text.splitlines()
    scalar_cursor = 0
    byte_cursor = 0
    physical_lines = text.splitlines(keepends=True)
    for physical in physical_lines[:-1]:
        scalar_cursor += len(physical)
        byte_cursor += len(physical.encode("utf-8"))
        scalar_starts.append(scalar_cursor)
        byte_starts.append(byte_cursor)
    return scalar_starts, byte_starts, lines


def locator(
    text: str,
    scalar_offset: int,
    scalar_starts: Sequence[int],
    byte_starts: Sequence[int],
    lines: Sequence[str],
) -> dict[str, Any]:
    line_index = bisect.bisect_right(scalar_starts, scalar_offset) - 1
    column_zero = scalar_offset - scalar_starts[line_index]
    line = lines[line_index] if line_index < len(lines) else ""
    byte_offset = byte_starts[line_index] + len(line[:column_zero].encode("utf-8"))
    context_start = max(0, scalar_offset - 80)
    context_end = min(len(text), scalar_offset + 160)
    context = text[context_start:context_end].encode("utf-8")
    return {
        "line": line_index + 1,
        "column": column_zero + 1,
        "byte_offset": byte_offset,
        "line_sha256": sha256_bytes(line.encode("utf-8")),
        "context_sha256": sha256_bytes(context),
    }


def project_segments(
    text: str, segments: Sequence[Segment], label: str
) -> tuple[str, list[dict[str, Any]], Counter[str], Counter[str]]:
    scalar_starts, byte_starts, lines = line_tables(text)
    output: list[str] = []
    issues: list[dict[str, Any]] = []
    conversion_classes: Counter[str] = Counter()
    issue_types: Counter[str] = Counter()
    visible_roles = {"visible_prose", "visible_math_text", "visible_metadata"}

    for segment in segments:
        raw = text[segment.start : segment.end]
        if segment.role not in visible_roles:
            output.append(raw)
            continue
        local_cursor = 0
        for match in LETTER_RE.finditer(raw):
            output.append(raw[local_cursor : match.start()])
            word = match.group(0)
            reasons = token_block_reasons(word)
            if reasons:
                output.append(word)
                absolute = segment.start + match.start()
                for reason in reasons:
                    issue_types[reason] += 1
                issues.append(
                    {
                        "file": label,
                        "token": word,
                        "token_casefold": word.casefold(),
                        "token_sha256": sha256_bytes(word.encode("utf-8")),
                        "scalar_offset": absolute,
                        "role": segment.role,
                        "reasons": reasons,
                        **locator(
                            text,
                            absolute,
                            scalar_starts,
                            byte_starts,
                            lines,
                        ),
                    }
                )
            else:
                projected, classification = project_word(word)
                output.append(projected)
                conversion_classes[classification] += 1
            local_cursor = match.end()
        output.append(raw[local_cursor:])
    return "".join(output), issues, conversion_classes, issue_types


def segment_digest(segments: Sequence[Segment]) -> str:
    rows = [[segment.start, segment.end, segment.role, segment.detail] for segment in segments]
    return sha256_bytes(canonical_json_bytes(rows))


def scan_text(text: str, label: str = "fixture.tex") -> dict[str, Any]:
    structural = validate_structure(text)
    segmenter = TexSegmenter(text)
    segments = segmenter.segment()
    projected, issues, conversions, issue_types = project_segments(text, segments, label)
    role_counts: Counter[str] = Counter()
    role_scalars: Counter[str] = Counter()
    protected_stream: list[str] = []
    visible_roles = {"visible_prose", "visible_math_text", "visible_metadata"}
    for segment in segments:
        role_counts[segment.role] += 1
        role_scalars[segment.role] += segment.end - segment.start
        if segment.role not in visible_roles:
            protected_stream.append(text[segment.start : segment.end])
    if sum(role_scalars.values()) != len(text):
        raise RuntimeError("role scalar totals are not gap-free")
    protected_bytes = "".join(protected_stream).encode("utf-8")
    mapping_issues = [item for item in issues if has_mapping_block(item["reasons"])]
    identity_issues = [
        item
        for item in issues
        if "unlisted_structural_roman_identity" in item["reasons"]
    ]
    return {
        "label": label,
        "input_bytes": len(text.encode("utf-8")),
        "input_sha256": sha256_bytes(text.encode("utf-8")),
        "input_scalars": len(text),
        "line_count": len(text.splitlines()),
        "structural": structural,
        "segment_count": len(segments),
        "segment_sha256": segment_digest(segments),
        "role_counts": dict(sorted(role_counts.items())),
        "role_scalars": dict(sorted(role_scalars.items())),
        "coverage": {
            "start": 0,
            "end": len(text),
            "gaps": 0,
            "overlaps": 0,
            "status": "PASS",
        },
        "protected_stream": {
            "bytes": len(protected_bytes),
            "sha256": sha256_bytes(protected_bytes),
            "projection_copy_policy": "byte-exact source slices in source order",
            "status": "PASS",
        },
        "unknown_argument_commands": segmenter.unknown_argument_commands,
        "foreign_spans": [
            {
                "start": start,
                "end": end,
                "kind": kind,
                "sha256": sha256_bytes(text[start:end].encode("utf-8")),
            }
            for start, end, kind in segmenter.foreign_spans
        ],
        "math_spans": [
            {
                "start": start,
                "end": end,
                "kind": kind,
                "sha256": sha256_bytes(text[start:end].encode("utf-8")),
            }
            for start, end, kind in segmenter.math_spans
        ],
        "conversion_classes": dict(sorted(conversions.items())),
        "issue_type_counts": dict(sorted(issue_types.items())),
        "blocked_occurrences": len(issues),
        "blocked_inventory_sha256": issue_inventory_sha256(issues),
        "unique_blocked_surfaces": len({item["token"] for item in issues}),
        "unique_blocked_casefolds": len({item["token_casefold"] for item in issues}),
        "unsupported_occurrences": len(mapping_issues),
        "unsupported_inventory_sha256": issue_inventory_sha256(mapping_issues),
        "unique_unsupported_surfaces": len({item["token"] for item in mapping_issues}),
        "unique_unsupported_casefolds": len(
            {item["token_casefold"] for item in mapping_issues}
        ),
        "roman_identity_hold_occurrences": len(identity_issues),
        "roman_identity_inventory_sha256": issue_inventory_sha256(identity_issues),
        "unique_roman_identity_hold_surfaces": len(
            {item["token"] for item in identity_issues}
        ),
        "unique_roman_identity_hold_casefolds": len(
            {item["token_casefold"] for item in identity_issues}
        ),
        "issues": issues,
        "diagnostic_projection_bytes": len(projected.encode("utf-8")),
        "diagnostic_projection_sha256": sha256_bytes(projected.encode("utf-8")),
        "projected_text": projected,
        "status": (
            "BLOCKED_FAIL_CLOSED"
            if issues or segmenter.unknown_argument_commands
            else "READY_IN_MEMORY_ONLY"
        ),
    }


def _public_file_report(result: dict[str, Any]) -> dict[str, Any]:
    excluded = {"projected_text"}
    return {key: value for key, value in result.items() if key not in excluded}


def scan_corpus(source_dir: Path = DEFAULT_SOURCE_DIR) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    all_issues: list[dict[str, Any]] = []
    source_manifest: list[dict[str, Any]] = []
    for filename in SOURCE_ORDER:
        path = source_dir / filename
        if not path.is_file():
            raise ProjectionError("missing_source", 0, filename)
        data = path.read_bytes()
        text = strict_transport(data, filename)
        result = scan_text(text, filename)
        files.append(_public_file_report(result))
        all_issues.extend(result["issues"])
        source_manifest.append(
            {"file": filename, "bytes": len(data), "sha256": sha256_bytes(data)}
        )

    mapping_issues = [item for item in all_issues if has_mapping_block(item["reasons"])]
    identity_issues = [
        item
        for item in all_issues
        if "unlisted_structural_roman_identity" in item["reasons"]
    ]

    summary_by_file = {
        item["label"]: {
            "blocked_occurrences": item["blocked_occurrences"],
            "blocked_inventory_sha256": item["blocked_inventory_sha256"],
            "unique_blocked_surfaces": item["unique_blocked_surfaces"],
            "unique_blocked_casefolds": item["unique_blocked_casefolds"],
            "unsupported_occurrences": item["unsupported_occurrences"],
            "unsupported_inventory_sha256": item["unsupported_inventory_sha256"],
            "unique_unsupported_surfaces": item["unique_unsupported_surfaces"],
            "unique_unsupported_casefolds": item["unique_unsupported_casefolds"],
            "roman_identity_hold_occurrences": item[
                "roman_identity_hold_occurrences"
            ],
            "roman_identity_inventory_sha256": item[
                "roman_identity_inventory_sha256"
            ],
            "unique_roman_identity_hold_surfaces": item[
                "unique_roman_identity_hold_surfaces"
            ],
            "unique_roman_identity_hold_casefolds": item[
                "unique_roman_identity_hold_casefolds"
            ],
            "unknown_argument_commands": len(item["unknown_argument_commands"]),
        }
        for item in files
    }
    report = {
        "schema": SCHEMA,
        "classification": (
            "read-only deterministic projection preflight; blocked output is not a release"
        ),
        "source_manifest": source_manifest,
        "source_order": list(SOURCE_ORDER),
        "parser_policy": {
            "command_aware_delimiters": True,
            "control_sequence_tokenization": True,
            "exact_environment_stack": True,
            "matched_environment_names": True,
            "gap_free_roles": True,
            "placeholder_masking": False,
            "parity_escape_heuristic": False,
            "default_write_count": 0,
        },
        "summary": {
            "files": len(files),
            "blocked_occurrences": len(all_issues),
            "blocked_inventory_sha256": issue_inventory_sha256(all_issues),
            "unique_blocked_surfaces": len({item["token"] for item in all_issues}),
            "unique_blocked_casefolds": len(
                {item["token_casefold"] for item in all_issues}
            ),
            "unsupported_occurrences": len(mapping_issues),
            "unsupported_inventory_sha256": issue_inventory_sha256(mapping_issues),
            "unique_unsupported_surfaces": len(
                {item["token"] for item in mapping_issues}
            ),
            "unique_unsupported_casefolds": len(
                {item["token_casefold"] for item in mapping_issues}
            ),
            "roman_identity_hold_occurrences": len(identity_issues),
            "roman_identity_inventory_sha256": issue_inventory_sha256(identity_issues),
            "unique_roman_identity_hold_surfaces": len(
                {item["token"] for item in identity_issues}
            ),
            "unique_roman_identity_hold_casefolds": len(
                {item["token_casefold"] for item in identity_issues}
            ),
            "parse_errors": 0,
            "coverage_failures": 0,
            "unknown_argument_commands": sum(
                len(item["unknown_argument_commands"]) for item in files
            ),
            "by_file": summary_by_file,
            "status": (
                "BLOCKED_FAIL_CLOSED"
                if all_issues
                or any(item["unknown_argument_commands"] for item in files)
                else "READY_IN_MEMORY_ONLY"
            ),
        },
        "files": files,
        "limitations": [
            "Allowed-letter personal names and titles require a separate reviewed role manifest.",
            "A successful preflight does not freeze Latin sources or authorize publication.",
            "No projected file is written by this module.",
        ],
    }
    audit_pins_match = all(
        EDIT0149_AUDIT_SOURCE_PINS[item["file"]]
        == (item["bytes"], item["sha256"])
        for item in source_manifest
    )
    if audit_pins_match:
        report["edit0149_legacy_census_reconciliation"] = {
            "scope": "exact sealed ISV019-EDIT-0149 four-source head",
            "legacy": {
                "unsupported_occurrences": 519,
                "unique_surface_tokens": 139,
                "unique_casefold_tokens": 135,
                "auditor_inventory_receipts": {
                    "aggregate_exact_surface": {
                        "bytes": 2230,
                        "sha256": "98BC5C7A3DFC708063E89A739C3322D2600791A6087E329C93D73FE80655BC68",
                    },
                    "aggregate_casefold": {
                        "bytes": 2192,
                        "sha256": "FD26DEF766B34640D5CE1837802002AC96C78F443815D26E6C9F08C75FDE809E",
                    },
                    "per_file_exact_surface": {
                        "bytes": 6008,
                        "sha256": "28B50DDC25E10C7193C71FB7D60ACB6989E8295879A33F32A7139CD7909A9EBD",
                    },
                    "per_file_casefold": {
                        "bytes": 5902,
                        "sha256": "2AF310D6DBDDA1BDFA69A9D5BD5340523D69C7730C2EBBC5464162205AA28C96",
                    },
                },
            },
            "v2": {
                "unsupported_occurrences": len(mapping_issues),
                "unique_surface_tokens": len(
                    {item["token"] for item in mapping_issues}
                ),
                "unique_casefold_tokens": len(
                    {item["token_casefold"] for item in mapping_issues}
                ),
            },
            "delta": {
                "unsupported_occurrences": len(mapping_issues) - 519,
                "unique_surface_tokens": len(
                    {item["token"] for item in mapping_issues}
                )
                - 139,
                "unique_casefold_tokens": len(
                    {item["token_casefold"] for item in mapping_issues}
                )
                - 135,
            },
            "role_policy_swap": {
                "exact_surface_multiset_delta": {
                    "added": {
                        "IX": 19,
                        "W": 32,
                        "X": 5,
                        "XI": 20,
                        "XII": 11,
                        "XIII": 10,
                        "XIV": 12,
                        "XIX": 3,
                        "XV": 7,
                        "XVI": 6,
                        "XVII": 9,
                        "XXII": 1,
                    },
                    "added_total": 135,
                    "removed": {
                        "Q": 1,
                        "klx": 2,
                        "lx": 6,
                        "max": 4,
                        "q": 23,
                        "width": 2,
                        "x": 91,
                    },
                    "removed_total": 129,
                    "net": 6,
                },
                "newly_visible_mapping_blocks": {
                    "x_bearing_roman_numerals_in_base": 98,
                    "W_initials_in_base": 31,
                    "W_initial_in_bibliography": 1,
                    "total": 130,
                },
                "legacy_false_positives_now_protected": {
                    "klx_in_base": 2,
                    "lx_in_base": 6,
                    "max_in_base": 4,
                    "q_or_Q_in_base": 24,
                    "width_in_base": 2,
                    "x_or_X_in_math_or_control_boundaries_in_base": 86,
                    "total": 124,
                },
                "net_occurrence_delta": 6,
            },
            "uniqueness_policy": "Unicode casefold is authoritative in v2; exact surfaces are also reported",
        }
    report["report_sha256_excluding_this_field"] = sha256_bytes(canonical_json_bytes(report))
    return report


def run_fixtures(path: Path = DEFAULT_FIXTURES) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "noether-isv-cyrillic-v2-fixtures-1":
        raise RuntimeError("fixture schema mismatch")
    results: list[dict[str, Any]] = []
    for fixture in payload["fixtures"]:
        name = fixture["name"]
        source = fixture["input"]
        expected = fixture["expected"]
        try:
            result = scan_text(source, name + ".tex")
        except ProjectionError as error:
            if expected.get("error_code") != error.code:
                raise AssertionError(
                    f"{name}: expected error {expected.get('error_code')!r}, got {error.code!r}"
                ) from error
            results.append({"name": name, "status": "PASS", "error_code": error.code})
            continue
        if "error_code" in expected:
            raise AssertionError(f"{name}: expected {expected['error_code']}, scan succeeded")
        if "projected" in expected and result["projected_text"] != expected["projected"]:
            raise AssertionError(
                f"{name}: projection mismatch\nexpected={expected['projected']!r}\n"
                f"actual={result['projected_text']!r}"
            )
        observed_tokens = [item["token"] for item in result["issues"]]
        if "blocked_tokens" in expected and observed_tokens != expected["blocked_tokens"]:
            raise AssertionError(
                f"{name}: blocked tokens expected {expected['blocked_tokens']!r}, "
                f"observed {observed_tokens!r}"
            )
        if "unknown_argument_commands" in expected:
            observed_unknown = [
                item["command"] for item in result["unknown_argument_commands"]
            ]
            if observed_unknown != expected["unknown_argument_commands"]:
                raise AssertionError(
                    f"{name}: unknown commands expected "
                    f"{expected['unknown_argument_commands']!r}, observed {observed_unknown!r}"
                )
        for role, minimum in expected.get("minimum_role_counts", {}).items():
            if result["role_counts"].get(role, 0) < minimum:
                raise AssertionError(
                    f"{name}: role {role!r} expected >= {minimum}, "
                    f"observed {result['role_counts'].get(role, 0)}"
                )
        if result["coverage"]["status"] != "PASS":
            raise AssertionError(f"{name}: non-gap-free roles")
        results.append(
            {
                "name": name,
                "status": "PASS",
                "input_sha256": result["input_sha256"],
                "segment_sha256": result["segment_sha256"],
                "diagnostic_projection_sha256": result[
                    "diagnostic_projection_sha256"
                ],
            }
        )
    receipt = {
        "schema": "noether-isv-cyrillic-v2-fixture-run-1",
        "fixture_file": path.name,
        "fixture_file_sha256": sha256_bytes(path.read_bytes()),
        "fixture_count": len(results),
        "passed": len(results),
        "failed": 0,
        "results": results,
    }
    receipt["receipt_sha256_excluding_this_field"] = sha256_bytes(
        canonical_json_bytes(receipt)
    )
    return receipt


def compact_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": report["schema"],
        "source_manifest": report["source_manifest"],
        "summary": report["summary"],
        "report_sha256_excluding_this_field": report[
            "report_sha256_excluding_this_field"
        ],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only, fail-closed v019 Cyrillic projection preflight"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="directory containing exactly the four Latin source inputs",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=DEFAULT_FIXTURES,
        help="fixture JSON path",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="run deterministic fixture suite"
    )
    parser.add_argument(
        "--full-report",
        action="store_true",
        help="print the canonical full report instead of its compact summary",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help="return exit 2 when the corpus remains blocked",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            payload = run_fixtures(args.fixtures)
        else:
            report = scan_corpus(args.source_dir)
            payload = report if args.full_report else compact_summary(report)
    except (
        ProjectionError,
        AssertionError,
        RuntimeError,
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
    ) as error:
        failure = {
            "schema": "noether-isv-cyrillic-v2-failure-1",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stdout.buffer.write(canonical_json_bytes(failure))
        return 1
    sys.stdout.buffer.write(canonical_json_bytes(payload))
    if (
        not args.self_test
        and args.require_ready
        and payload.get("summary", {}).get("status") != "READY_IN_MEMORY_ONLY"
    ):
        return 2
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
