# Emmy Noether — Polno medžuslovjansko izdanje korpusa

[**Čitajte polny povezany PDF-čitateljnik — latinica i kirilica**](release_v020/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf)

To jest polno medžuslovjansko izdanje matematičnogo korpusa Emmy Noether: statje 1–43, lekcijsko dělo 44, statja 45 i bibliografija. Ono jest prědvidženo za praktično čitanje govoriteljami slovjanskyh jezykov, vključajuči čitateljev bez anglijskogo jezyka; ne jest samo lingvističny eksperiment.

- Točny DOI izdanja: [10.5281/zenodo.22058530](https://doi.org/10.5281/zenodo.22058530)
- Stabilny DOI koncepta: [10.5281/zenodo.21926382](https://doi.org/10.5281/zenodo.21926382)
- Globalny katalog: [10.5281/zenodo.20412587](https://doi.org/10.5281/zenodo.20412587)
- Jezyk: Medžuslovjansky (`isv`)
- Zapisy: `isv-Latn` i `isv-Cyrl`
- Redakcijna versija: `NOETHER-ISV-v020`

## Čto jest kanon?

Četyri fajly v `source_latin/` sut jediny redagovateljny jezyčny kanon. Četyri fajly v `source_cyrillic/` sut deterministično izvedene zapisy togo samogo teksta i ne sut oddělny prěklad ili nezavisny svědok. Točna mašinno-čitljiva mapa jezyka, iztočnika, rolij, kontrolnyh sum i komand jest v [`CANON_INDEX.json`](CANON_INDEX.json). Tuto jasno označenje davaje drugoj Codex-sesiji ili drugomu orudju možnost povtoriti i prodolžiti izdanje bez izmysljenja konkurentnogo kanona.

Ako hočete prodolžiti redakciju:

1. prěčitajte `CANON_INDEX.json`;
2. autentifikujte zamrznute latinične fajly;
3. zapišite vsako materialno jezyčno rěšenje s točnym lokatorom, iztočnikami, neizvěstnostju i odklonjenymi alternativami;
4. ne redagujte kirilicu ručno — izvedite ju fail-closed projektorom v7;
5. poslě změny povtorite pregled vsih rolij, dvojnu derivaciju i jezyčnu, matematičnu, TeX, fontovu, linkovu i vizualnu kontrolu.

## Čto prinosi v020

Latiničny kanon ostavaje bajt-po-bajtu jednakovy s v019. Popravka se odnosi na pravila, ktore rěšajut, ktore vidime česti teksta trěba transliterovati i ktore trěba ohraniti — na priměr obykle medžuslovjanske slova, imena, rimske označenja, originalne citaty i bibliografične zapisy.

Vseh 4 560 naslědženyh zapisov rolij bylo pregledano. Popravljeno bylo 364 nepravilnyh klasifikacij i dodano osam nedostajučih granic imen. Vseh 372 efektov bylo prověrjeno: 346 označajut ohranjenje i 26 projekciju. Izvod změnil 125 linij, vse izključivo v 309 iztočnikovyh linijah dozvoljenyh pregledom; latinične fajly ne sut změnjene. V rezultatu obične medžuslovjanske slova više ne ostavajut slučajno latiničnymi, a originalne imena, rimske označenja i podobne funkcionalne elementy više ne sut slučajno pokiriljene.

## Sostav izdanja

- `release_v020/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf` — glavno čitateljsko izdanje, 1 159 stranic;
- `source_latin/` — latinično medžuslovjansko izdanje, ktore možno redagovati;
- `source_cyrillic/` — deterministična kirilična projekcija;
- `docs/AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf` — publikacijska metodologija o jezyčnyh rěšenjah, avtoritetah, algoritmu, popravkah, validaciji i granicah tvrdženij;
- `decision_records/` i `release_v020/evidence/` — pregled rolij, validacijske potvrđenja, sgrađanja i QA;
- `metadata/` — citovanje, Zenodo/DataCite odnosenja, iztočnik i obim;
- koren repozitorija — povtorime projektory, testy i build/QA orudja.

Sgrađanje dvoh samostojnyh čitateljnikov teče serijno v dvoh prohodah; rezultat imaje 565 latiničnyh i 588 kiriličnyh stranic. Povezany čitateljnik imaje 1 159 stranic. Strukturna kontrola imaje 38 uspěšnyh kontrol i nula pogrěšek. Vizualna kontrola pokryvaje vseh 86 izměnjenyh kiriličnyh stranic, 103 susědne neizměnjene kontrolne stranice i novy uvodny material.

## Status, avtorstvo i prava

Avtorami matematičnyh děl sut Emmy Noether i navedeni soavtori. Medžuslovjansky prěklad, redakcija, projekcija, metadane i tipografija sut izrabotane modelami/agentami s mašinnoju pomočju.

To jest naučno rabotno izdanje. Ono ne prošlo nezavisnu naučnu recenziju i ne tvrdži, že jest potvrđeno rodnymi govoriteljami, medžuslovjanskoju obćinoju, oficialnym standardom ili nezavisnoju institucijeju. Pogrěšky možno javno prijaviti v repozitoriju; slědujuče versije mogut jih popraviti bez změny historijskih versij.

CC0 jest priměnjen samo v toj měrě, v ktoroju obstajajut prava na projektom stvorjeny prěklad, redakciju, metadane, manifesty, orudja i dokazy. Originalne děla, německy redakcijny material, fonty, programy i drugy material tretjih stran ohranjajut svoj pravny status i licencije.

---

# English

[**Read the complete linked Interslavic PDF — Latin and Cyrillic**](release_v020/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf)

This is the complete Interslavic edition of Emmy Noether's mathematical corpus: Papers 1–43, lecture work 44, Paper 45, and the bibliography. It is intended for practical reading by speakers of Slavic languages, including readers without English; it is not merely a linguistic experiment.

- Exact release DOI: [10.5281/zenodo.22058530](https://doi.org/10.5281/zenodo.22058530)
- Stable concept DOI: [10.5281/zenodo.21926382](https://doi.org/10.5281/zenodo.21926382)
- Global catalogue: [10.5281/zenodo.20412587](https://doi.org/10.5281/zenodo.20412587)
- Language: Interslavic (`isv`)
- Scripts: `isv-Latn` and `isv-Cyrl`
- Editorial release: `NOETHER-ISV-v020`

## What is canonical?

The four files under `source_latin/` are the sole editable language canon. The four files under `source_cyrillic/` are a deterministic representation of the same text, not a separate translation or independent witness. [`CANON_INDEX.json`](CANON_INDEX.json) is the exact machine-readable map of language, source authority, roles, hashes, and commands. This explicit map lets another Codex session or other tool reproduce and extend the edition without inventing a competing canon.

To extend the edition:

1. read `CANON_INDEX.json`;
2. authenticate the frozen Latin files;
3. record every material linguistic choice with an exact locator, sources, uncertainty, and rejected alternatives;
4. never edit Cyrillic independently—regenerate it with the fail-closed v7 projector;
5. after a change, repeat the complete role review, double derivation, and linguistic, mathematical, TeX, font, link, and visual validation.

## What v020 changes

The Latin canon remains byte-for-byte identical to v019. The correction concerns the rules that decide which visible text should be transliterated and which should be preserved—for example ordinary Interslavic words, names, Roman labels, original quotations, and bibliographic forms.

All 4,560 inherited role records were reviewed. The review corrected 364 misclassifications and added eight missing name boundaries. All 372 effects were verified: 346 preservation decisions and 26 projection decisions. The derivation changed 125 lines, all exclusively within 309 source lines licensed by the review; no Latin source byte changed. As a result, ordinary Interslavic words no longer remain accidentally Latin, while original names, Roman labels, and similar functional material are no longer accidentally Cyrillicized.

## Release contents

- `release_v020/public/00_NOETHER_INTERSLAVIC_COMPLETE_LINKED_READER.pdf` — the 1,159-page human-facing edition;
- `source_latin/` — editable Latin-script Interslavic;
- `source_cyrillic/` — deterministic Cyrillic projection;
- `docs/AI_INTERSLAVIC_NOETHER_METHODS_v020.pdf` — publication-style methodology covering linguistic decisions, authorities, algorithm, corrections, validation, and claim boundaries;
- `decision_records/` and `release_v020/evidence/` — role review, validation receipts, builds, and QA;
- `metadata/` — citation, Zenodo/DataCite relations, source authority, and scope;
- repository root — reproducible projection, test, build, and QA tools.

The two component readers build serially in two passes: 565 Latin pages and 588 Cyrillic pages. The linked reader contains 1,159 pages. Structural QA reports 38 passing checks and zero errors. Visual QA covers all 86 changed Cyrillic pages, 103 adjacent unchanged controls, and the new front matter.

## Status, authorship, and rights

The mathematical works are by Emmy Noether and named co-authors. The Interslavic translation, editing, projection, metadata, and typesetting were produced by models/agents with machine assistance.

This is a scholarly working edition. It has not undergone independent scholarly peer review and does not claim certification by native speakers, the Interslavic community, an official standard, or an independent institution. Errors may be reported publicly in the repository; later versions can correct them without altering historical releases.

CC0 applies only to the extent that rights exist in project-created translation, editorial work, metadata, manifests, tools, and evidence. Original works, German editorial material, fonts, software, and other third-party material retain their own legal status and licences.
