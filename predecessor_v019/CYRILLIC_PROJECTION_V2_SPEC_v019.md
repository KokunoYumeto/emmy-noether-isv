# Noether Interslavic v019: deterministic Cyrillic projection v2

Status: implementation contract under pre-freeze audit; projection is deliberately blocked until the finite protection queue is closed and the four Latin sources receive their final immutable freeze.

## Objective

Produce the Cyrillic-script surface of the same maintained Interslavic edition from the frozen Latin sources. Cyrillic is not a separate translation, editorial lineage, or DOI. The projector must be self-contained, deterministic, brace-aware, fail closed on uncertainty, and preserve mathematical and TeX identity.

## Controlling orthography

Authority snapshot:

`../00_lane_control/marginal_intelligibility_20260811/authority_snapshots/snapshots/official_site/docs/learn/orthography.md`

- bytes: 16,443
- SHA-256: `90C609CC0E8709E8395964E9F20D6D4FB4E31159CBC2B1EA515A29D9D1C72044`
- standard correspondences used here: `ě -> є`, `y -> ы`, `j -> ј`, `lj -> љ`, `nj -> њ`, `dž -> дж`
- optional etymological letters have no Cyrillic alphabet of their own. Before standard Cyrillic projection they are simplified as specified by the authority: `ę -> e`, `ų -> u`, `å -> a`, `ė -> e`, `ȯ -> o`, `ć -> č`, `đ -> dž`; any other etymological diacritic is stripped only when an explicit table entry exists.

The v018 projector is rejected as an implementation base. It depends on an unbundled Python module and uses incompatible fallbacks including `ě -> е`, `lj -> ль`, `nj -> нь`, and `ę -> я`. Those choices may not silently carry into v019.

## Input contract

The implementation reads exactly four immutable UTF-8, NFC, LF-only, terminal-LF files from `source_latin/`, in this order:

1. `44-book-isv.tex`
2. `45-isv.tex`
3. `base-papers1-43-isv.tex`
4. `bib-isv.tex`

The projector must accept a separately frozen source manifest and refuse to run if any size or SHA-256 differs. Current mutable head hashes are audit context only and must not become final projection pins.

Default mode performs a full in-memory projection and validation without writing. `--apply` may create a previously absent staging directory only after every input, policy, parser, and output gate succeeds. Final promotion happens only after an independent second process reproduces the same bytes.

## Lexical conversion

Conversion is case preserving and longest-token-first. At minimum:

| Latin | Cyrillic |
|---|---|
| `dž` | `дж` |
| `lj` | `љ` |
| `nj` | `њ` |
| `a b c č d e ě f g h i j k l m n o p r s š t u v y z ž` | `а б ц ч д е є ф г х и ј к л м н о п р с ш т у в ы з ж` |

Uppercase and title-case variants are derived mechanically from this table. The implementation must normalize optional etymological characters to the standard Latin intermediary first, then apply the standard mapping. It must not guess a Cyrillic spelling for `q`, `w`, `x`, unsupported Latin diacritics, or foreign-language words.

Every convertible prose token is classified as one of:

- `converted_standard_isv`
- `converted_after_explicit_etymological_simplification`
- `preserved_protected_payload`
- `blocked_unmapped_or_ambiguous`

Any `blocked_unmapped_or_ambiguous` token aborts the projection and is emitted with file, line, column, enclosing TeX context, and a stable context hash. Resolution requires either an explicit mapping policy or exact protected markup in the Latin source; there is no heuristic foreign-word allow-list.

Personal names and eponyms use a role-based policy:

- an uninflected personal identity is preserved as one complete byte-exact `\foreign` island, including initials, particles, punctuation, and hyphens;
- an original-language work title, venue, series, publisher, or place is likewise preserved as a complete identity island, with typography outside the wrapper (for example, `\textit{\foreign{...}}`);
- a morphologically integrated Interslavic name or eponym is projected only after its complete Latin lemma/family and surface have an explicit reviewed decision;
- a partial foreign root plus projected case ending is forbidden; the complete approved token or phrase is projected, or the complete identity label is protected/recast;
- any unclassified name, mixed-role compound, variant stem, or stale locator blocks projection.

This policy preserves identity `Noether` but projects an approved integrated form such as `Neterovomu`; preserves identity `Schur` but may project reviewed `Šurov`; and forbids hybrids such as `\foreign{Brauer}ovom`. The official orthography and dictionary provide no general personal-name transcription system, so the projector must not invent one.

## TeX parser and protection policy

Regular-expression masking is insufficient. The implementation must tokenize TeX while tracking nested brace depth, comments, control sequences, environments, and math delimiters.

Byte-preserved domains:

- preamble and all material before `\begin{document}`, except explicitly declared visible metadata arguments. In particular, theorem display names in `\newtheorem` are visible text and may not be hidden by a blanket preamble-preservation rule;
- control-sequence names and control symbols;
- comments, including the terminating newline layout;
- math formulas and delimiter bytes, except visible natural-language arguments of explicitly allowed text commands;
- arguments of `\label`, `\ref`, `\pageref`, `\eqref`, `\cite`, `\Cref`, `\cref`, `\url`, `\href` URL slots, `\path`, `\bibitem`, and other identity/key commands;
- all arguments of `\foreign` and `\foreignlanguage`;
- command definitions, lengths, counters, package options, environment specifications, file names, and raw macro bodies unless a command-specific rule explicitly identifies a visible prose argument.

Convertible visible prose domains:

- ordinary document text outside math and protected commands;
- visible arguments of headings, emphasis, footnotes, list items, captions, and comparable prose containers;
- visible text arguments inside math for `\text`, `\textrm`, `\textit`, `\textbf`, `\mbox`, `\hbox`, and `\intertext`, while preserving the surrounding formula byte stream;
- argument 2 of the live two-argument `\srcfn`, whose pinned definition is `\newcommand{\srcfn}[2]{\footnote{#2}}`. Argument 1 is an unrendered source-footnote marker/identity slot and remains byte-exact. Argument 2 is rendered Interslavic prose and is projected, except for separately marked nested title, journal, author, abbreviation, or other `\foreign` islands.

The parser uses the following exact role table rather than inferring argument semantics:

| Command | Preserved identity arguments | Visible/projectable arguments |
|---|---|---|
| `\srcfn` | 1 | 2 |
| `\tocline` | 2 | 1 |
| `\tocsec` | 1, 3 | 2 |
| `\noethpIIsrcfnmark` | 1 | none |
| `\noethpIIsrcfntext` | 1 | 2 |
| `\addcontentsline` | 1, 2 | 3 |
| `\href` | 1 | 2 |
| `\newtheorem` | required environment name, optional shared-counter name, optional trailing within-counter name | required display name |

Ordinary `\newcommand`-style definitions are parsed as definitions, not as invocations, and their raw bodies remain preserved. For example, `\providecommand{\foreign}[1]{#1}` must not be consumed as a one-argument `\foreign` call. `\newtheorem` is the explicit exception governed by the metadata role above: the parser preserves the environment and counter identities but projects its visible display name. On sealed audit head `EDIT-0143`, the only currently present `\newtheorem` display-name payloads are `Teorem` and `Dodatok`; if unchanged at the final Latin freeze, those two payloads are visible/projectable.

Uppercase Roman numerals used as structural numbering are preserved through a reviewed freeze-time identity manifest. Every permitted occurrence is keyed by source file, byte offset, exact token, and stable context hash. A Roman-shaped token outside that manifest is blocked. The current 110-occurrence census may seed the manifest but does not authorize a general uppercase-Latin allow-list. Positive and adverse fixtures must prove exact-token boundaries, manifest matching, stale-context rejection, and rejection of an unlisted Roman-shaped word.

Unknown commands with braced arguments default to blocked, not convertible. A command may enter the visible-prose table only with fixture tests covering nesting, optional arguments, escaped braces, comments, and math.

## Determinism and receipts

The report is canonical UTF-8 JSON with sorted object keys, stable arrays, LF-only transport, and no absolute paths, host names, locale-derived strings, wall-clock timestamps, temporary paths, or nondeterministic iteration order.

For each file it records:

- input and output bytes/SHA-256;
- parser-policy and orthography-authority hashes;
- counts and ordered receipts for converted tokens, etymological simplifications, preserved spans, and blocked spans;
- ordered hashes of controls, environments, math spans/delimiters, comments, cross-reference keys, citation keys, URL/path payloads, and foreign-language payloads;
- line count, newline layout, brace balance, BOM state, Unicode normalization, and terminal-LF state.

The implementation projects the same frozen input twice in separate fresh processes. Both output files and both canonical reports must be byte-identical. A reverse structural comparison must prove that replacing each converted Cyrillic token with its recorded Latin source reconstructs the original bytes exactly.

## Mandatory gates

1. Four source size/hash pins and the frozen Latin manifest match.
2. Orthography authority and projector source pins match.
3. Strict UTF-8, NFC, no BOM, LF-only, terminal LF.
4. Parser reaches EOF with balanced braces, environments, math state, and no unresolved command argument.
5. Zero blocked or ambiguous visible-prose tokens.
6. Exact equality of line layout, comments, control names, environment stream, math delimiters/formula skeleton, xref/cite keys, URL/path payloads, and foreign payloads.
7. Every changed byte belongs to a declared visible-prose token or explicit script metadata field.
8. Expected standard Cyrillic inventory is present; forbidden mixed-script residue in convertible prose is zero.
9. Second-process output and report are byte-identical to the first.
10. Recorded inverse replay reconstructs all four Latin inputs byte-for-byte.

## Required fixtures

Before corpus projection, unit fixtures must cover ordinary prose; uppercase/title case; all standard digraphs; every etymological simplification; nested emphasis/footnotes/headings; escaped braces; comments; inline/display math; `\text` inside math; labels/refs/cites; URLs and href label text; foreign spans; all commands in the exact role table; command definitions that resemble invocations; visible theorem names in `\newtheorem`; Roman-numeral identity tokens and adverse uppercase-Latin controls; unknown commands; malformed TeX; and unmapped foreign tokens. Each fixture has exact input, expected output or expected failure, and SHA-256 receipt.

## Pre-freeze protection audit (2026-08-16)

The EDIT-0143 source set contains 131 real `\foreign` invocations. After those spans and the structural domains above are masked, the exact visible-token gate still reports 642 unsupported occurrences: 613 in papers 1--43, 7 in work 44, 14 in paper 45, and 8 in the bibliography. This is a blocker census, not an instruction to wrap every token as foreign material.

The first mechanically safe markup tranche contains 147 identity spans. Of these, 146 cover 147 alphabet-gate blockers, while the final span protects an allowed-letter English title that the alphabet gate cannot detect:

- 131 original-language title or venue spans already delimited by `\emph` in papers 1--43;
- 2 Russian/Ukrainian comparator words;
- 8 quoted/original titles in paper 45, including the allowed-letter title `Modular Systems`;
- 4 book citation abbreviations;
- 2 composite book citations.

The earlier 155-span audit overlay left 486 unsupported occurrences / 144 unique tokens. Its nine provisional additions were eight standalone-name candidates plus one eponym candidate; that overlay is historical audit evidence, not a complete name manifest. A later closed 66-family audit found at least 561 uninflected identity candidates and 698 integrated/eponym candidates across the four sources. Those figures are exact within the closed lexicon but are deliberately only lower bounds, because an unsupported-character detector cannot discover allowed-letter names. The role-based policy above therefore requires a fresh exhaustive manifest and family decisions before freeze rather than promoting the nine-span overlay. Of the current blockers, 110 occurrences are exact Roman numerals and belong to the reviewed identity manifest rather than `\foreign` markup.

Before the Latin freeze, the lane must also:

1. resolve the visible theorem labels in paper 45's preamble;
2. perform the bibliography-structure pass;
3. normalize or adjudicate genuine Interslavic lexical residuals rather than hiding them in `\foreign`, including audited forms such as `dělimości`, `právě`, `identičnosť`, `cěločislovosť`, `treťjego`, `biquadratičnu`, `odpowědajut`, `najwyšego`, and `zürihsko`;
4. separately classify every remaining `q`, `w`, `x`, or `ü` occurrence as a lexical normalization, abbreviation, or foreign identity; no letter-wide fallback is permitted;
5. rerun the gap-free scanner to zero under the documented identity classes;
6. complete the role-classified identity/integrated-name manifest, manually auditing allowed-letter names and titles, and close every integrated family decision without partial-root hybrids.

Audit authority: sealed head `ISV019-EDIT-0143`; state 14,777 bytes / SHA-256 `855EF4CCBAB9CB844157AB0474944A4D9980AF1CDD5889D784F7BF471787C529`. This section records the finite implementation boundary; it does not certify any candidate markup that has not yet been applied and independently replayed.

## Release boundary

The Cyrillic surface may be built and packaged only after:

- the Latin normalization ledger is closed and independently replayed;
- the four-source Latin freeze exists;
- this v2 projector and fixture suite pass independent review;
- two clean projections are byte-identical;
- Latin and Cyrillic readers independently pass text, math, TeX, font, link, structural, and visual QA.

The release metadata describes Latin and Cyrillic as scripts of one Interslavic edition and one DOI lineage. It must disclose that the Cyrillic surface is a deterministic projection and identify the exact Latin source and projector hashes.
