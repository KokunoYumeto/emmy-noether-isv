# Emmy Noether — Polno medžuslovjansko izdanje korpusa

[**Čitajte izdanje neposrědno v živom HTML-čitateljniku — latinica i kirilica**](https://kokunoyumeto.github.io/emmy-noether-isv/)

[**Čitajte polny povezany PDF-čitateljnik — latinica i kirilica**](release_v021/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf)

To jest polno medžuslovjansko izdanje matematičnogo korpusa Emmy Noether: statje 1–43, lekcijsko dělo 44, statja 45 i bibliografija. Ono jest prědvidženo za praktično čitanje govoriteljami slovjanskyh jezykov, uključajuči čitateljev bez anglijskogo jezyka; ne jest samo lingvističny eksperiment.

- Točny DOI izdanja: [10.5281/zenodo.22077468](https://doi.org/10.5281/zenodo.22077468)
- Stabilny DOI koncepta: [10.5281/zenodo.21926382](https://doi.org/10.5281/zenodo.21926382)
- Globalny katalog: [10.5281/zenodo.20412587](https://doi.org/10.5281/zenodo.20412587)
- Jezyk: Medžuslovjansky (`isv`)
- Zapisy: `isv-Latn` i `isv-Cyrl`
- Redakcijna versija: `NOETHER-ISV-v021`

## Čto jest kanon?

Četyri fajly v `source_latin/` sut jediny redagovateljny jezyčny kanon. Četyri fajly v `source_cyrillic/` sut deterministično izvedene zapisy togo samogo teksta i ne sut oddělny prěklad ili nezavisny svědok. Točna mašinno-čitljiva mapa jezyka, iztočnika, rolij, kontrolnyh sum i komand jest v [`CANON_INDEX.json`](CANON_INDEX.json). Tuto jasno označenje davaje drugoj Codex-sesiji ili drugomu orudju možnost povtoriti i prodolžiti izdanje bez izmysljenja konkurentnogo kanona.

Ako hočete prodolžiti redakciju:

1. prěčitajte `CANON_INDEX.json`;
2. autentifikujte zamrznute latinične fajly;
3. zapišite vsako materialno jezyčno rěšenje s točnym lokatorom, iztočnikami, neizvěstnostju i odklonjenymi alternativami;
4. ne redagujte kirilicu ručno — izvedite ju fail-closed projektorom v8;
5. poslě změny povtorite pregled rolij, dvojnu derivaciju i jezyčnu, matematičnu, TeX, fontovu, linkovu i vizualnu kontrolu.

## Čto prinosi v021

Versija v021 zamrzuje novu latiničnu glavu `ISV021-EDIT-0012`. Dvanadset zamrznutyh rěšenij priměnilo 4 053 lokalizovane popravky. Poslědnje dvije velike normalizacije zaměnile sut 1 599 pojavjenj opcionalnyh soglasnyh znakov standardnymi formami i 1 798 pojavjenj šestih opcionalnyh proširenih bukv osnovnymi čitateljskymi formami. Četyri originalne tuđe formy s `è` sut ohranjene bajt-po-bajtu; generično odstranjenje diakritik ne jest upotrěbjeno.

Finalny pregled latiničnogo teksta našel nula ne-rimskyh projekcijnyh blokatorov. Projektor v8 veže 5 290 zapisov rolij k novym lokatoram, uključajuči 722 točno prověrjene rimske označenja, i deterministično tvori kirilicu bez neprědvidženyh izměn. Vseh izhodnyh změn jest licencirano izměnami latiničnogo kanona; otvorenih projekcijnyh pogrěšek jest nula.

## Sostav izdanja

- [`docs/index.html`](docs/index.html) — živa GitHub Pages čitateljska površina s neposrědno pokazyvanim polnym PDF, skokami k latinici i kirilici, i rezervnymi vezami za dostavanje;
- `release_v021/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf` — glavno čitateljsko izdanje, 1 159 stranic;
- `source_latin/` — latinično medžuslovjansko izdanje, ktore možno redagovati;
- `source_cyrillic/` — deterministična kirilična projekcija;
- `docs/AI_INTERSLAVIC_NOETHER_METHODS_v021.pdf` — 13-stranična publikacija o jezyčnyh rěšenjah, avtoritetah, algoritmu, validaciji i granicah tvrdženij, s polnym medžuslovjanskim tekstom i polnym anglijskym paralelnym tekstom;
- `decision_records/` i `release_v021/evidence/` — zamrznute rěšenja, validacijske potvrđenja, sgrađanja i QA;
- `metadata/` — citovanje, Zenodo/DataCite odnosenja, iztočnik i obim;
- koren repozitorija — povtorime projektory, testy i build/QA orudja.

Dva samostojna čitateljnika sut sgrađene serijno v dvoh prohodah: 565 latiničnyh i 588 kiriličnyh stranic. Povezany čitateljnik imaje 1 159 stranic. Strukturna kontrola imaje 38 uspěšnyh kontrol i nula pogrěšek. Vizualna kontrola autentifikovala vseh 1 159 stranic i pregledala 129 reprezentativnyh izměnjenyh stranic, 60 susědnyh kontrol i vseh 13 stranic metodologije; vidimyh defektov ne najdeno.

## Status, avtorstvo i prava

Avtorami matematičnyh děl sut Emmy Noether i navedeni soavtori. Medžuslovjansky prěklad, redakcija, projekcija, metadane i tipografija sut izrabotane modelami/agentami s mašinnoju pomočju.

To jest naučno rabotno izdanje. Ono ne prošlo nezavisnu naučnu recenziju i ne tvrdži, že jest potvrđeno rodnymi govoriteljami, medžuslovjanskoju obćinoju, oficialnym standardom ili nezavisnoju institucijeju. Pogrěšky možno javno prijaviti v repozitoriju; slědujuče versije mogut jih popraviti bez změny historijskih versij.

CC0 jest priměnjen samo v toj měrě, v ktoroju obstajajut prava na projektom stvorjeny prěklad, redakciju, metadane, manifesty, orudja i dokazy. Originalne děla, německy redakcijny material, fonty, programy i drugy material tretjih stran ohranjajut svoj pravny status i licencije.

---

# English

[**Read the edition in the live HTML reader — Latin and Cyrillic**](https://kokunoyumeto.github.io/emmy-noether-isv/)

[**Read the complete linked Interslavic PDF — Latin and Cyrillic**](release_v021/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf)

This is the complete Interslavic edition of Emmy Noether's mathematical corpus: Papers 1–43, lecture work 44, Paper 45, and the bibliography. It is intended for practical reading by speakers of Slavic languages, including readers without English; it is not merely a linguistic experiment.

- Exact release DOI: [10.5281/zenodo.22077468](https://doi.org/10.5281/zenodo.22077468)
- Stable concept DOI: [10.5281/zenodo.21926382](https://doi.org/10.5281/zenodo.21926382)
- Global catalogue: [10.5281/zenodo.20412587](https://doi.org/10.5281/zenodo.20412587)
- Language: Interslavic (`isv`)
- Scripts: `isv-Latn` and `isv-Cyrl`
- Editorial release: `NOETHER-ISV-v021`

## What is canonical?

The four files under `source_latin/` are the sole editable language canon. The four files under `source_cyrillic/` are a deterministic representation of the same text, not a separate translation or independent witness. [`CANON_INDEX.json`](CANON_INDEX.json) is the exact machine-readable map of language, source authority, roles, hashes, and commands. This explicit map lets another Codex session or other tool reproduce and extend the edition without inventing a competing canon.

To extend the edition:

1. read `CANON_INDEX.json`;
2. authenticate the frozen Latin files;
3. record every material linguistic choice with an exact locator, sources, uncertainty, and rejected alternatives;
4. never edit Cyrillic independently—regenerate it with the fail-closed v8 projector;
5. after a change, repeat the role review, double derivation, and linguistic, mathematical, TeX, font, link, and visual validation.

## What v021 changes

Version v021 freezes a new Latin head, `ISV021-EDIT-0012`. Twelve sealed decisions apply 4,053 localized corrections. The final two large normalizations replace 1,599 occurrences of optional consonant spellings with standard forms and 1,798 occurrences of six optional extended letters with basic reader-facing forms. Four original foreign-source spellings containing `è` remain byte-identical; no generic diacritic stripping is used.

The final Latin review finds zero non-Roman projection blockers. Projector v8 binds 5,290 role records to the new locators, including 722 exactly verified Roman labels, and generates Cyrillic deterministically without unintended changes. Every output change is licensed by a Latin-canon change; open projection errors are zero.

## Release contents

- [`docs/index.html`](docs/index.html) — the live GitHub Pages surface, embedding the complete reader with Latin/Cyrillic jumps and direct-download fallbacks;
- `release_v021/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf` — the 1,159-page human-facing edition;
- `source_latin/` — editable Latin-script Interslavic;
- `source_cyrillic/` — deterministic Cyrillic projection;
- `docs/AI_INTERSLAVIC_NOETHER_METHODS_v021.pdf` — a 13-page publication-style methodology with complete Interslavic and complete parallel English texts;
- `decision_records/` and `release_v021/evidence/` — sealed decisions, validation receipts, builds, and QA;
- `metadata/` — citation, Zenodo/DataCite relations, source authority, and scope;
- repository root — reproducible projection, test, build, and QA tools.

The two component readers build serially in two passes: 565 Latin pages and 588 Cyrillic pages. The linked reader contains 1,159 pages. Structural QA reports 38 passing checks and zero errors. Visual QA authenticated all 1,159 pages and inspected 129 representative changed pages, 60 adjacent controls, and all 13 methods pages; no visible defects were found.

## Status, authorship, and rights

The mathematical works are by Emmy Noether and named co-authors. The Interslavic translation, editing, projection, metadata, and typesetting were produced by models/agents with machine assistance.

This is a scholarly working edition. It has not undergone independent scholarly peer review and does not claim certification by native speakers, the Interslavic community, an official standard, or an independent institution. Errors may be reported publicly in the repository; later versions can correct them without altering historical releases.

CC0 applies only to the extent that rights exist in project-created translation, editorial work, metadata, manifests, tools, and evidence. Original works, German editorial material, fonts, software, and other third-party material retain their own legal status and licences.
