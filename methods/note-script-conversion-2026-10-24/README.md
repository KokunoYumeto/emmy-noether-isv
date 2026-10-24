# Kirilica v kratkyh primětkah

[Kirilica](README.cyrl.md) · [Program Python](project_note.py) · [Polny prěvodnik pisma](../../project_isv_cyrillic_v8.py)

Program prěobražaje kratke medžuslovjanske primětky iz latinice v kirilicu. Funkcija `project_note` daje kirilske formy sedmi primětok k §7 statje31 Emmy Noether. Cěly medžuslovjansky prěklad ima dva pisma; kirilska forma ne jest drugy prěklad.

## Upotrěba

Trěbny jest Python 3. Dopolniteljni pakety ne sut potrěbni. Vhodny fajl ima kodovanje UTF-8.

```text
python project_note.py notes-latin.tex notes-cyrillic.tex
```

Drugy fajl jest rezultat. Jest li on uže stvorjeny, program jego ne zaměnjaje.

## Pravila i obseg

Ohranjaje imena komand LaTeX, naslov `Idealtheorie` i rimsko čislo `II`. Bukvy ostalogo teksta prěobražaje po tabeli v programu, s oddělnymi pravilami za `dž`, `lj`, `nj` i jih formy s velikoju počętnoju bukvoju. Historične bukvy `ѧ` i `ѫ` sut tehnične odgovarjajuče formy za `ę` i `ų` v toj funkciji; ne sut čestju standardnoj kirilskoj abecedy.

Funkcija ne razpoznavaje matematične oblasti, adresy URL ani proizvoljne argumenty komand. Ona jest za te kratke primětky; za cěly dokument upotrěbite polny prěvodnik pisma. Matematične označenja možno ohraniti s [oddělnym programom](../source-identifiers-2026-10-24/README.md).

Standardne odgovarjajuče bukvy i obě abecedy opisuje [Jan van Steenbergen, pravopis medžuslovjanskogo jezyka](https://interslavic.fun/learn/orthography/). Ta funkcija ohranjaje svoje točno zapisane pravila za povtorjenje rezultata.

Program i obě formy togo opisa stvorjene AI: OpenAI Codex — GPT-6 Astra, usilje Ultra, 24 oktobra 2026. Avtorka matematičnoj statje jest Emmy Noether. [Licencija projektovogo koda](../../LICENSE).
