# Povtorimo sestavjenje / Reproducible build

## Medžuslovjansky

Raspakujte arhiv v prazdny katalog. `source_latin/` jest jediny redagujemy jezyčny kanon; `source_cyrillic/` jest izvedena projekcija. Ne redagujte kirilicu kako oddělny prěklad.

1. `python test_project_isv_cyrillic_v6.py`
2. `python project_isv_cyrillic_v6.py --require-ready`
3. `python build_isv_release_v019.py --build`
4. `python qa_isv_release_v019.py`
5. `python build_linked_reader_v019.py`

Potrěbne sut Python 3, `pypdf`, XeLaTeX, Poppler (`pdftotext`, `pdffonts`, `pdftoppm`), PyMuPDF i Pillow za polnu vizualnu kontrolu. Build jest serijny i ne upotrěbja shell escape.

## English

Extract into an empty directory. `source_latin/` is the sole editable language canon; `source_cyrillic/` is derived. Do not edit Cyrillic as a separate translation.

Run the five commands above in order. Python 3, `pypdf`, XeLaTeX, Poppler, PyMuPDF, and Pillow are required for the complete build and visual QA. The build is serial and disables shell escape.
