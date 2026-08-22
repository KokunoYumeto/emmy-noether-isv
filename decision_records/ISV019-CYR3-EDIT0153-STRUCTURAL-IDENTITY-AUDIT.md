# EDIT0153 Cyrillic v3 structural-identity audit

Date: 2026-08-20 (Europe/Berlin)

Status: **validated candidate; not registered or adopted**

## Scope and claim boundary

This audit validates an append-only, read-only v3 overlay for the deterministic
Interslavic Latin-to-Cyrillic preflight. It does not change the registered Latin
source cohort, the EDIT0153 metadata graph, any producer, the canon registry, or
any public artifact. It writes no Cyrillic output.

The words *canon* and *canonical* remain work-scoped. Nothing here asserts an
official Interslavic standard, native/community approval, peer review,
comprehension testing, or a canonical critical edition.

The controlling registered predecessor is `CANON-REGISTRY-0005`, whose
Interslavic head is `ISV019-EDIT-0153`. The bounded registry validator and lane
verifier both passed immediately before this audit.

## Decision

The v2 scanner reported 1,095 blocked occurrences at EDIT0153. Its two
overlapping views were 489 unsupported occurrences and 704 Roman-identity
holds. The disjoint human role partition was:

- lexical: 0;
- foreign/title/citation identities: 307;
- integrated names/eponyms: 66;
- structural Roman identities: 722.

The new manifest reviews the complete last class at exact source locators. It
admits 722 identities without changing their Latin bytes:

- 704 uppercase multi-letter Roman numerals;
- 18 uppercase single-letter `X` occurrences, all in explicit `Teorem X`
  headings or references;
- 116 of the 722 also carried a v2 mapping-block reason and therefore overlap
  the unsupported view.

The manifest deliberately excludes one-letter `I`, `V`, and `M`. Those tokens
mix ordinary words, initials, and genuine Roman labels and require a separate
context review. It also cannot certify allowed-letter personal names or titles
that unsupported-letter detection never exposes.

After admitting only the 722 manifested identities, v3 remains fail-closed:

| Measure | Registered v2 | Candidate v3 |
|---|---:|---:|
| Blocked union | 1,095 | 373 |
| Unsupported | 489 | 373 |
| Roman-identity holds | 704 | 0 |
| Parse errors | 0 | 0 |
| Coverage failures | 0 | 0 |
| Unknown argument commands | 0 | 0 |

All 373 remaining blockers are in `base-papers1-43-isv.tex`. The book, Paper
45, and bibliography each reach zero blockers under this reviewed overlay.
Their shared remaining inventory SHA-256 is
`257F1118DC0D31C708180F1AC29E2CDEFD5F257712C3E52EB9146B86ACBC0236`.

Those 373 occurrences are the finite next policy frontier: 307
foreign/title/citation identities plus 66 integrated name/eponym forms. The
count is a workflow census, not a linguistic-completion percentage.

## Exact candidate and evidence pins

- v2 scanner: `project_isv_cyrillic_v2.py`, 74,914 bytes,
  `FD51B4D9936653CB9968AF8F91BAB08E18331741BC482CCA39AEF69F0B5AF3F2`.
- v3 overlay: `project_isv_cyrillic_v3.py`, 24,314 bytes,
  `84B845424CB2501289220727B1300280894512EDD137DC13B188A577049AF1B7`.
- clean-room harness: `test_project_isv_cyrillic_v3.py`, 10,239 bytes,
  `FA6EA677A55EC10A7375FEAADCD9C3A24F796012E5E02F9F0C08CE763D004365`.
- manifest builder:
  `build_edit0153_structural_identity_manifest_v019.py`, 11,477 bytes,
  `EAE12F1B7617F6E47F2F8E8439C2F8D11C9B2ED855229992BE28C245644F42DA`.
- structural manifest:
  `decision_records/ISV019-CYR2-EDIT0153-STRUCTURAL-IDENTITY-MANIFEST.json`,
  692,764 bytes,
  `E6249BDEFEA6713EADAE5AF23C313D38E3DB3EB0DAAC3107A161BC0A0BC3E6E9`.
- manifest canonical receipt excluding its receipt field:
  `D5D33712D70B9541E2D5A05ED134291F87C141B2CE6A29212EB657C1F940D683`.

The manifest is locator-complete and gap-free for this structural class. Every
record binds file, token, casefold, token digest, scalar and byte offset, line,
column, role, reasons, line digest, context digest, and context excerpt. The v3
overlay accepts no identity merely by spelling or regular expression; it must
match one exact manifested current-head issue.

## Source and head barrier

The candidate pins and rechecks the exact registered Latin source cohort:

- `44-book-isv.tex`: 168,422 bytes,
  `68A7DF0DF4E5CA5FDF2237BD55D1788AB48E3094796910648D9DD0E8112BD46F`;
- `45-isv.tex`: 26,053 bytes,
  `5768230C3A7D338303B6DFC37D270CE554779C90598BD2230C23DC191CC55A91`;
- `base-papers1-43-isv.tex`: 1,892,324 bytes,
  `9490F4C09573ABC4FFC97AE80F2DF08330488B7EA2148AD6CC1C8B39756B02E9`;
- `bib-isv.tex`: 10,019 bytes,
  `032D5E90A96B34B16CAA99C40904EED3682C7D8A7241A1682795BDC3A0E8C553`.

It also pins the EDIT0153 state, ledger, worklog, and verifier in the independent
harness. The bounded before/after set contains 12 exact files and remained
byte-identical; lane `__pycache__` was absent before and after.

## Deterministic execution receipts

All stdout below is canonical UTF-8 JSON with exactly one terminal LF and no
CR; all stderr is empty (`E3B0C442...B855`).

- default preflight twice: exit 0, 4,207 bytes,
  `51E116B32A7842D46638AA3AF614EC887597C83AC1126EF2F54C1578EB9598E4`;
- embedded hostile self-test twice: exit 0, 3,455 bytes,
  `F8BFE9E0DC9114981904F62A2E18CCFA52D444401E1FF5DCA9833866DE324DC6`;
- `--require-ready`: exit 2, 4,207 bytes, same default digest, proving the
  remaining blockers fail closed;
- `--full-report`: exit 0, 3,419,523 bytes,
  `897A94C436FB50A5BF500ED0F31DFC9E6E959414313C390F823C7F33245689C6`;
- independent clean-room harness twice: exit 0, 1,753 bytes,
  `23CC116FAD9B22D286410D7E3C60EFB997685BB2F10C447C3685E3842848DC78`.

The embedded self-test rejects nine hostile inputs: missing or duplicate
manifest record, wrong line hash, wrong context excerpt, wrong source manifest,
wrong scanner pin, wrong head, duplicate JSON key, and CRLF transport.

The separate harness does not import the v3 transformation helpers. It reloads
the pinned v2 scanner, recomputes the exact 722-record subset and manifest
self-receipt, independently subtracts those locators, recomputes the 373-item
inventory, executes every public v3 mode, checks duplicated byte identity, and
rehashes its 12-file no-write barrier.

## Superseded pre-freeze output boundary

The first unregistered v3 draft was 24,117 bytes /
`ACF6AF277ED2C59ECEE55DA99CAA8D753E985BCCB5170B2F7249B60B813C87E6`.
Its `print(...)` boundary inherited the Windows console code page. The first
clean-room run rejected the full report because byte `0xF6` in `Weitzenböck`
was not valid UTF-8 (offset 456,312). That draft and its old stdout pins are
superseded and must not be registered.

The repair writes `canonical_json_bytes(payload)` directly to
`sys.stdout.buffer`. The corrected full report is valid UTF-8/LF and all modes
were recalibrated and independently replayed. No source, metadata, registry,
build, or public byte changed during the correction.

## Adoption cursor

The v3 files are validated evidence but are not yet the active projection
authority. A future append-only metadata decision may adopt their exact pins
without changing Latin sources. That decision must receive its own independent
preapply review, seal, worklog append, verifier passes, and monotonic canon
registry successor. Until then, the registered projection authority remains v2
and `derived_output` remains `null`.

After adoption, the next substantive projection work is the 373-item
foreign/name policy frontier, followed by the separate one-letter `I/V/M` and
allowed-letter-name completeness gates. No Cyrillic release artifact may be
generated or published until all fail-closed gates reach a reviewed ready state.
