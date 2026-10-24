# Matematične označenja v latinskom i kirilskom tekstu

Medžuslovjansky prěklad ima latinsku i kirilsku formu. Čisla, bukvy v označenjah formul, odstavkov i pododstavkov dolžny ostati jednaki v oběh pismennostjah.

[Kirilica](README.cyrl.md) · [Program Python](preserve_source_identifiers.py)

Program čita dva odgovarjajuče iztočnika LaTeX: latinsky i kirilsky. V kirilskom tekstu ohranjaje matematične označenja po latinskom iztočniku. Obrabotava označenja v komandah `mbox`, bukvene točky spiskov, otkazy k formulam i paragrafam, a takože označenja sostavjene iz čisel i bukv. Obyčny tekst ostavaje v kirilici. Pri nesoglasju redov označenij program konči s pogrěškoju.

## Upotrěba

Trěbny jest Python 3. Dopolniteljni pakety ne sut potrěbni.

```text
python preserve_source_identifiers.py latin.tex cyrillic.tex cyrillic-identifiers.tex
```

Tretji fajl jest rezultat. Jesm li on uže stvorjeny, program jego ne zaměnjaje. Vsaky par fajlov obračunajte oddělno. Rezultat možno kompilovati s ostalymi iztočnikami odgovarjajučego izdanja.

Program služit za ohranjenje označenij poslě prěvoda pisma. Ne prěkladaje prozu, ne tvori polny kirilsky tekst iz samogo latinskogo teksta i ne prověrjaje praviljnost matematičnyh tvrđenij.

Program stvorjeny AI: OpenAI Codex — GPT-6 Astra, usilje Ultra, 24 oktobra 2026. Matematične děla ostavajut dělami Emmy Noether i nazvanyh soavtorov.
