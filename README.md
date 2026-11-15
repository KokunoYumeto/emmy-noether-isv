# Emmy Noether — Matematične děla po medžuslovjansky

Medžuslovjansky prěklad matematičnyh děl Emmy Noether (1882–1935): statje 1–43, lekcije *Algebra hiperkompleksnyh veličin* (zimny semestr 1929/30) v zapisu M. Deuringa, statja H. Kapferera s dodatkom, napisanym sovmestno s E. Noether, bibliografija i končne spisky. Prěklad ima dva pisma, latinicu i kirilicu ([kirilica niže](#emmy-noether--математичне-дєла-по-меджусловјанскы)); obě formy sut v PDF i v redagovateljnom LaTeX.

[**Čitajte osnovny tekst — PDF, 481 str.**](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/01-noether-isv-Latn-base.pdf) ·
[Tekst s redakcijnymi popravkami — PDF, 486 str.](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/04-noether-isv-Latn-emendations.pdf) ·
[Vse fajly izdanja od 27 oktobra 2026](https://github.com/KokunoYumeto/emmy-noether-isv/releases/tag/noether-isv-2026-11-15)

## Kako jest stvorjeno izdanje

Prěklad jest stvorjeny AI, modelami OpenAI Codex; ktory model prěložil tekst, ne jest zapisano. Popravky i tipografija stvorjene AI: OpenAI Codex — GPT-6 Astra, usilje Ultra, 23–24 oktobra 2026; Claude Opus 5.5 (Anthropic), 26–27 oktobra 2026, vključajuči formuly srovnane s německym tekstom, čitanym iz pečatnyh stranic Noether. Kirilska forma prědstavjaje taj sam prěklad v kirilskom pismu; ona ne jest drugy prěklad. Program za sestavjenje stvorjeny AI: OpenAI Codex — GPT-6 Astra, Ultra, 24 oktobra 2026.

## Status

Izdanje sodrživaje vse nazvane děla, ale statja 43 jest skraćena približno na tretinu polnogo teksta, a statje 41 i 42 približno na četyri petiny. Statje 23, 24, 30, 31, 32, 34, 37 i 41–43, takože česti statij 35 i 40, slědujut ranějšemu anglijskomu prěkladu, ktorogo formuly na něktoryh městah razlikujut se od německogo teksta. V statji 2 tri primětky německogo teksta (primětka o Σ₃ i citacije Gordan — Kerschensteiner, str. 92 i 134) sut označene jedino znakom `*` ili vključene v sosědny tekst. Fajly PDF ne imajut zakladok. Prěklad ne jest prověrjeny člověkom, zato v njem mogut ostati pogrěšky; na něktoryh městah formuly mogut ješče slědovati ranějšej německoj transkripciji. Popravky se prijimajut prěz [stranicu issues](https://github.com/KokunoYumeto/emmy-noether-isv/issues); navedite dělo, stranicu ili odsek, spornu frazu i iztočnik predložene popravky.

## Sodržanje i čitanje

Izdanje imaje osnovny tekst i tekst s redakcijnymi popravkami; za oba jest PDF, jedin fajl LaTeX i arhiv iztočnikov:

| Tekst | PDF | LaTeX | Iztočniki |
|---|---|---|---|
| Osnovny tekst: ohranjaje čitanja prvyh publikacij; redakcijne primětky objasnjajut sporne čitanja | [PDF, 481 str.](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/01-noether-isv-Latn-base.pdf) | [LaTeX](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/02-noether-isv-Latn-base.tex) | [ZIP](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/03-noether-isv-Latn-base-sources.zip) |
| Tekst s redakcijnymi popravkami: popravky sut vneseny v tekst, každa jest objasnjena v redakcijnoj primětkě | [PDF, 486 str.](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/04-noether-isv-Latn-emendations.pdf) | [LaTeX](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/05-noether-isv-Latn-emendations.tex) | [ZIP](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/06-noether-isv-Latn-emendations-sources.zip) |

[Kontrolne sumy SHA-256](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/07-noether-isv-Latn-SHA256SUMS.txt). Te same fajly sut v [`editions/2026-10-24-r2/isv-Latn/`](editions/2026-10-24-r2/isv-Latn/).

Fajl LaTeX sodrživa vse teksty i preambuly v redagovateljnoj formě. Program Python [`build.py`](editions/2026-10-24-r2/isv-Latn/build.py) izvlačuje iztočne fajly, kompiluje jih s XeLaTeX i sjedinjaje PDF česti v porědku čitanja; potrěbni sut Python 3, pypdf, pakety TeX i fonty ukazane v preambulah. ZIP ohranjaje iztočnu strukturu, taj sam fajl LaTeX i program.

Izdanje avgusta 2026 (v021) jest v [`source_latin/`](source_latin/) i [`source_cyrillic/`](source_cyrillic/) (LaTeX) i v [onlajnovom čitateljniku](https://kokunoyumeto.github.io/emmy-noether-isv/) (povezany PDF, 1 159 stranic, latinica i kirilica). [Matematičny medžuslovjansky — slovnik i metoda](https://kokunoyumeto.github.io/emmy-noether-isv/04_NOETHER_INTERSLAVIC_DICTIONARY.pdf) (takože v [HTML](https://kokunoyumeto.github.io/emmy-noether-isv/dictionary/book.html) i kako [slovnik s iskanjem](https://kokunoyumeto.github.io/emmy-noether-isv/dictionary/)) jest AI-stvorjena studija terminologije prěklada: 2016 iztočno-medžuslovjanskyh parov, 168 podrobnyh jezyčnyh i redakcijnyh izborov i dvanadset gramatičnyh ili pravopisnyh konvencij. Metodološko izloženje i sinteza slovnika sut izrabotane s OpenAI Codex — GPT-5.6 Sol, Ultra; rekonstrukcija terminologičnyh zapisov i daljnje dvojezyčne obrazloženja s OpenAI Codex — GPT-6 Astra, Ultra. [Program za matematične označenja](methods/source-identifiers-2026-10-24/README.md) · [Prěvod pisma v kratkyh primětkah](methods/note-script-conversion-2026-10-24/README.md). Německy tekst, izdanja na drugyh jezykah i znane razliky medžu izdanjami sut na [centralnoj stranici](https://kokunoyumeto.github.io/emmy-noether/).

## Avtori i iztočniki

- Matematične děla napisali Emmy Noether i soavtori, nazvani v njih: Werner Schmeidler (statja 17), R. Brauer (statja 32), R. Brauer i H. Hasse (statja 38). Lekcije 1929/30 obrabotal M. Deuring. Statja 45 jest dělo H. Kapferera s dodatkom, napisanym sovmestno s E. Noether. Podrobnosti o prvyh publikacijah, podpisy i citacije sut v samyh tekstah.
- Izdanje avgusta 2026 (v021) srovnalo prěklad s německym projektnym korpusom NOETH-DE-ED-0015 ([avtorstvo originalov](LICENSES/ORIGINAL_WORK_ATTRIBUTION.md)). Formuly izdanja od 27 oktobra 2026 sut srovnane s německym tekstom, ktory jest stranica po stranici srovnany s prvymi publikacijami ([izdanje noether-de-2026-10-26](https://github.com/KokunoYumeto/modern-latex-manuscripts/releases/tag/noether-de-2026-10-26)).

## Prava

Děla Emmy Noether sut v javnom dobru. V toj měrě, v kakoj izdatelj imaje prava na prěklad, popravky i tipografiju stvorjene AI, on jih daruje v javno dobro po [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Lekcije zapisane M. Deuringom, rabota H. Kapferera i prinos nazvanyh soavtorov ohranjajut svoj pravny status.

---

# Emmy Noether — Математичне дєла по меджусловјанскы

Меджусловјанскы прєклад математичных дєл Emmy Noether (1882–1935): статје 1–43, лекције *Алгебра хиперкомплексных величин* (зимны семестр 1929/30) в запису M. Deuringa, статја H. Kapferera с додатком, написаным совместно с E. Noether, библиографија и конечне спискы. Прєклад има два писма, латиницу и кирилицу ([латиница выше](#emmy-noether--matematične-děla-po-medžuslovjansky)); обє формы сут в PDF и в редаговатељном LaTeX.

[**Читајте основны текст — PDF, 502 стр.**](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/01-noether-isv-Cyrl-base.pdf) ·
[Текст с редакцијными поправками — PDF, 507 стр.](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/04-noether-isv-Cyrl-emendations.pdf) ·
[Все фајлы издања од 27 октобра 2026](https://github.com/KokunoYumeto/emmy-noether-isv/releases/tag/noether-isv-2026-11-15)

## Како јест створјено издање

Прєклад јест створјены AI, моделами OpenAI Codex; кторы модел прєложил текст, не јест записано. Поправкы и типографија створјене AI: OpenAI Codex — GPT-6 Astra, усилије Ultra, 23–24 октобра 2026; Claude Opus 5.5 (Anthropic), 26–27 октобра 2026, вкључајучи формулы сровнане с нємецкым текстом, читаным из печатных страниц Noether. Кирилска форма прєдставјаје тај сам прєклад в кирилском писму; она не јест другы прєклад. Програм за сеставјење створјены AI: OpenAI Codex — GPT-6 Astra, Ultra, 24 октобра 2026.

## Статус

Издање содрживаје все назване дєла, але статја 43 јест скраћена приближно на третину полного текста, а статје 41 и 42 приближно на четыри петины. Статје 23, 24, 30, 31, 32, 34, 37 и 41–43, такоже чести статиј 35 и 40, слєдујут ранєјшему англијскому прєкладу, кторого формулы на нєкторых мєстах разликујут се од нємецкого текста. В статји 2 три примєткы нємецкого текста (примєтка о Σ₃ и цитације Gordan — Kerschensteiner, стр. 92 и 134) сут означене једино знаком `*` или вкључене в сосєдны текст. Фајлы PDF не имајут закладок. Прєклад не јест провєрјены чловєком, зато в њем могут остати погрєшкы; на нєкторых мєстах формулы могут јешче слєдовати ранєјшеј нємецкој транскрипцији. Поправкы се пријимајут прєз [страницу issues](https://github.com/KokunoYumeto/emmy-noether-isv/issues); наведите дєло, страницу или одсек, спорну фразу и източник предложене поправкы.

## Содржање и читање

Издање имаје основны текст и текст с редакцијными поправками; за оба јест PDF, једин фајл LaTeX и архив източников:

| Текст | PDF | LaTeX | Източники |
|---|---|---|---|
| Основны текст: охрањаје читања првых публикациј; редакцијне примєткы објасњајут спорне читања | [PDF, 502 стр.](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/01-noether-isv-Cyrl-base.pdf) | [LaTeX](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/02-noether-isv-Cyrl-base.tex) | [ZIP](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/03-noether-isv-Cyrl-base-sources.zip) |
| Текст с редакцијными поправками: поправкы сут внесены в текст, кажда јест објасњена в редакцијној примєткє | [PDF, 507 стр.](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/04-noether-isv-Cyrl-emendations.pdf) | [LaTeX](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/05-noether-isv-Cyrl-emendations.tex) | [ZIP](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/06-noether-isv-Cyrl-emendations-sources.zip) |

[Контролне сумы SHA-256](https://github.com/KokunoYumeto/emmy-noether-isv/releases/download/noether-isv-2026-11-15/07-noether-isv-Cyrl-SHA256SUMS.txt). Те саме фајлы сут в [`editions/2026-10-24-r2/isv-Cyrl/`](editions/2026-10-24-r2/isv-Cyrl/).

Фајл LaTeX содржива все тексты и преамбулы в редаговатељној формє. Програм Python [`build.py`](editions/2026-10-24-r2/isv-Cyrl/build.py) извлачује източне фајлы, компилује јих с XeLaTeX и сједињаје PDF чести в порєдку читања; потрєбни сут Python 3, pypdf, пакеты TeX и фонты указане в преамбулах. ZIP охрањаје източну структуру, тај сам фајл LaTeX и програм.

Издање августа 2026 (v021) јест в [`source_latin/`](source_latin/) и [`source_cyrillic/`](source_cyrillic/) (LaTeX) и в [онлајновом читатељнику](https://kokunoyumeto.github.io/emmy-noether-isv/) (повезаны PDF, 1 159 страниц, латиница и кирилица). [Математичны меджусловјанскы — словник и метода](https://kokunoyumeto.github.io/emmy-noether-isv/04_NOETHER_INTERSLAVIC_DICTIONARY.pdf) (такоже в [HTML](https://kokunoyumeto.github.io/emmy-noether-isv/dictionary/book.html) и како [словник с искањем](https://kokunoyumeto.github.io/emmy-noether-isv/dictionary/)) јест AI-створјена студија терминологије прєклада: 2016 източно-меджусловјанскых паров, 168 подробных језычных и редакцијных изборов и дванадсет граматичных или правописных конвенциј. Методолошко изложење и синтеза словника сут изработане с OpenAI Codex — GPT-5.6 Sol, Ultra; реконструкција терминологичных записов и даљње двојезычне образложења с OpenAI Codex — GPT-6 Astra, Ultra. [Програм за математичне означења](methods/source-identifiers-2026-10-24/README.cyrl.md) · [Прєвод писма в краткых примєтках](methods/note-script-conversion-2026-10-24/README.cyrl.md). Нємецкы текст, издања на другых језыках и знане разликы меджу издањами сут на [централној страници](https://kokunoyumeto.github.io/emmy-noether/).

## Автори и източники

- Математичне дєла написали Emmy Noether и соавтори, названи в њих: Werner Schmeidler (статја 17), R. Brauer (статја 32), R. Brauer и H. Hasse (статја 38). Лекције 1929/30 обработал M. Deuring. Статја 45 јест дєло H. Kapferera с додатком, написаным совместно с E. Noether. Подробности о првых публикацијах, подписы и цитације сут в самых текстах.
- Издање августа 2026 (v021) сровнало прєклад с нємецкым пројектным корпусом NOETH-DE-ED-0015 ([авторство оригиналов](LICENSES/ORIGINAL_WORK_ATTRIBUTION.md)). Формулы издања од 27 октобра 2026 сут сровнане с нємецкым текстом, кторы јест страница по страници сровнаны с првыми публикацијами ([издање noether-de-2026-10-26](https://github.com/KokunoYumeto/modern-latex-manuscripts/releases/tag/noether-de-2026-10-26)).

## Права

Дєла Emmy Noether сут в јавном добру. В тој мєрє, в какој издатељ имаје права на прєклад, поправкы и типографију створјене AI, он јих дарује в јавно добро по [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). Лекције записане M. Deuringom, работа H. Kapferera и принос названых соавторов охрањајут свој правны статус.
