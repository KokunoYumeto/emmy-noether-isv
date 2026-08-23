# Povtorimo sestavjenje / Reproducible build

## Medžuslovjansky

Raspakujte arhiv v prazdny katalog. Najprvo čitajte `PUBLIC_RELEASE_README.md` i mašinny indeks `CANON_INDEX.json`. Četyri fajly v `source_latin/` sut jediny redagovateljny jezyčny kanon. `source_cyrillic/` jest deterministično izvedeny zapis i ne smije byti redagovany kako oddělny prěklad.

1. `python test_project_isv_cyrillic_v7.py`
2. `python project_isv_cyrillic_v7.py --full-report`
3. `python project_isv_cyrillic_v7.py --write-output-dir source_cyrillic`
4. Sravnite četiri izvedene fajly s kontrolnymi sumami v `CANON_INDEX.json`.
5. `python build_isv_release_v020.py --build`
6. `python qa_isv_release_v020.py`
7. `python build_linked_reader_v020.py`
8. `python build_methods_v020.py`
9. `python analyze_cyrillic_pdf_delta_v020.py`
10. `python render_linked_reader_visual_assets_v020.py`
11. `python render_methods_visual_assets_v020.py`
12. `python build_visual_qa_receipt_v020.py`
13. `python build_release_packages_v020.py`
14. `python verify_release_packages_v020.py`

Iztočnikovy arhiv sadrži točny javny povezany čitateljnik v019 pod `comparison/`, zato možno povtoriti renderovanu razliku naslědnika bez neprikrepljenogo dostavanja. Projektor jest fail-closed: on otkazyvaje rabotu, ako iztočnik, manifest rolij ili licencovane granice změn ne sut točno autentifikovane. Potrěbne sut Python 3, `pypdf`, XeLaTeX, Poppler (`pdftotext`, `pdffonts`, `pdftoppm`), PyMuPDF, Pillow i PyYAML za polno sgrađanje, vizualnu kontrolu i paketovanje. Sgrađanje jest serijno i ne upotrěbja shell escape.

Za novu jezyčnu redakciju najprvo dodajte iztočnikovo vezano rěšenje s motivacijoju, dokazami, neizvěstnostju i odklonjenymi alternativami. Potom povtorite cělu kontrolu rolij i ne prěnosite avtomatično stare granice na změnjeny tekst.

## English

Extract the archive into an empty directory. Read `PUBLIC_RELEASE_README.md` and the machine index `CANON_INDEX.json` first. The four files in `source_latin/` are the sole editable language canon. `source_cyrillic/` is deterministically derived and must not be edited as a separate translation.

Run the fourteen steps above in order. The source archive includes the exact public v019 linked reader under `comparison/`, so the rendered successor delta can be reproduced without an unpinned download. The projector fails closed if the source, reviewed role manifest, or licensed delta boundaries do not authenticate exactly. Python 3, `pypdf`, XeLaTeX, Poppler, PyMuPDF, Pillow, and PyYAML are required for the complete build, visual QA, and packaging. Builds are serial and shell escape is disabled.

For a new linguistic edit, first append a source-bound decision with motivation, evidence, uncertainty, and rejected alternatives. Then repeat the complete role review; do not silently transplant old boundaries onto changed source text.
