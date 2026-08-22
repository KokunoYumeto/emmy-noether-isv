# Emmy Noether — Polno medžuslovjansko izdanje korpusa

[**Čitajte polny povezany PDF-čitateljnik — latinica i kirilica**](public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf)

To jest polno medžuslovjansko izdanje matematičnogo korpusa Emmy Noether: statje 1–43, lekcijsko dělo 44, statja 45 i bibliografija. Ono jest prědvidženo za praktično čitanje govoriteljami slovjanskyh jezykov, vključajuči čitateljev bez anglijskogo jezyka.

- Točny DOI izdanja: [10.5281/zenodo.22050935](https://doi.org/10.5281/zenodo.22050935)
- Stabilny DOI koncepta: [10.5281/zenodo.21926382](https://doi.org/10.5281/zenodo.21926382)
- Globalny katalog: [10.5281/zenodo.20412587](https://doi.org/10.5281/zenodo.20412587)
- Jezyk: Medžuslovjansky (`isv`)
- Zapisy: `isv-Latn` i `isv-Cyrl`
- Redakcijna versija: `NOETHER-ISV-v019`

## Čto jest kanon?

Čtyri fajly v `source_latin/` sut jediny redagujemy jezyčny kanon. Čtyri fajly v `source_cyrillic/` sut deterministično izvedeny zapis togo samogo teksta i ne sut oddělny prěklad ili nezavisny svědok. Točna mašinno-čitljiva mapa jezyka, avtoriteta, rolij, kontrolnyh sum i komandov jest v [`CANON_INDEX.json`](CANON_INDEX.json).

Ako hočete prodolžiti redakciju:

1. prěčitajte `CANON_INDEX.json`;
2. autentifikujte zamrznute latinične fajly;
3. zapisujte vsako materialno rěšenje dodatkom k `NORMALIZATION_DECISIONS_v019.jsonl`, s iztočnikami i odklonjenymi alternativami;
4. ne redagujte kirilicu ručno — izvedite ju projektorom v6;
5. poslě změny povtorite jezyčnu, matematičnu, TeX, fontovu i vizualnu kontrolu.

## Sostav izdanja

- `public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf` — glavno čitateljsko izdanje, 1 159 stranic;
- `source_latin/` — redagujemo latinično medžuslovjansko izdanje;
- `source_cyrillic/` — deterministična kirilična projekcija;
- `docs/AI_INTERSLAVIC_NOETHER_METHODS_v019.pdf` — publikacijska metodologija: jezyčne rěšenja, algoritm, neuspěh v5, popravka v6, validacija i granice tvrdženij;
- `evidence/` — redakcijny žurnal, inventar rolij, validacijske potvrđenja i QA;
- `metadata/` — citovanje, Zenodo/DataCite odnosenja, avtoritet i obim;
- koren repozitorija — povtorime projektory, testy i build/QA orudja s imenami `project_*`, `test_*`, `build_*`, `audit_*` i `qa_*`.

Scanner konečnogo latiničnogo teksta imaje `0` blokatorov i `0` nepodprtih projektovateljnym tokenov. Žurnal imaje 171 materialno redakcijno rěšenje. Projektor v6 deterministično konvertuje 164 563 slovne tokeny i ohranjaje pregledane imena, originalne naslove/citaty, rimske označenja i TeX-sintaksu. Dva samostojne čitateljnika sut sestavjene serijno v dveh prohodah: 565 latiničnyh i 588 kiriličnyh stranic.

## Status i prava

To jest naučno rabotno izdanje, izrabotano modelami/agentami s mašinnoju pomočju. Ono ne prošlo nezavisnu naučnu recenziju i ne tvrdi potvrđenje rodnymi govoriteljami, medžuslovjanskoju obćinoju, oficialnym standardom ili nezavisnoju institucijeju.

CC0 jest priměnjen samo v toj měrě, v ktoroju postavajut prava v projektom stvorjenom prěkladu, redakciji, metadanyh, manifestah, orudjah i dokazah. Originalne děla, německy redakcijny material, fonty, programy i drugy material tretjih stran ohranjajut svoj pravny status i licencije.

---

# English

[**Read the complete linked Interslavic PDF — Latin and Cyrillic**](public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf)

This is the complete Interslavic edition of Emmy Noether's mathematical corpus: Papers 1–43, lecture work 44, Paper 45, and the bibliography. It is intended for practical reading by speakers of Slavic languages, including readers without English.

- Exact release DOI: [10.5281/zenodo.22050935](https://doi.org/10.5281/zenodo.22050935)
- Stable concept DOI: [10.5281/zenodo.21926382](https://doi.org/10.5281/zenodo.21926382)
- Global catalogue: [10.5281/zenodo.20412587](https://doi.org/10.5281/zenodo.20412587)
- Language: Interslavic (`isv`)
- Scripts: `isv-Latn` and `isv-Cyrl`
- Editorial release: `NOETHER-ISV-v019`

## What is canonical?

The four files under `source_latin/` are the sole editable language canon. The four files under `source_cyrillic/` are a deterministic representation of the same text, not a separate translation or independent witness. [`CANON_INDEX.json`](CANON_INDEX.json) is the exact machine-readable map of language, authority, roles, hashes, and commands.

To extend the edition:

1. read `CANON_INDEX.json`;
2. authenticate the frozen Latin files;
3. append every material choice to `NORMALIZATION_DECISIONS_v019.jsonl`, including evidence and rejected alternatives;
4. do not edit Cyrillic independently — regenerate it with projector v6;
5. rerun linguistic, mathematical, TeX, font, and visual validation.

## Release contents

- `public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf` — the 1,159-page human-facing edition;
- `source_latin/` — editable Latin-script Interslavic;
- `source_cyrillic/` — deterministic Cyrillic projection;
- `docs/AI_INTERSLAVIC_NOETHER_METHODS_v019.pdf` — publication-style methodology covering choices, algorithm, the v5 failure, v6 correction, validation, and claim boundaries;
- `evidence/` — editorial ledger, role inventory, validation receipts, and QA;
- `metadata/` — citation, Zenodo/DataCite relations, authority, and scope;
- repository root — reproducible projection, tests, build, and QA tools named `project_*`, `test_*`, `build_*`, `audit_*`, and `qa_*`.

The final Latin scanner reports `0` blockers and `0` unsupported projectable tokens. The ledger records 171 material editorial decisions. Projector v6 deterministically converts 164,563 word tokens while preserving reviewed names, original titles/quotations, Roman labels, and TeX syntax. The two script readers build serially in two passes: 565 Latin pages and 588 Cyrillic pages.

## Review and rights

This is a scholarly working edition produced by models/agents with machine assistance. It has not undergone independent scholarly peer review and does not claim certification by native speakers, the Interslavic community, an official standard, or an independent institution.

CC0 applies only to the extent that rights exist in project-created translation, editorial work, metadata, manifests, tools, and evidence. Original works, German editorial material, fonts, software, and other third-party material retain their own legal status and licences.
