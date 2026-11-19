# Knižnica Tomáša Akvinského

Pracovné vydanie jednej responzívnej knižnice pre GitHub Pages, počítač, Android a iOS. V priečinku `docs/` sú *Slovo vychádzajúce z výsosti*, *O večnosti sveta* a *Teologická suma I*. Oba kratšie spisy sú dostupné po latinsky, česky a slovensky. Vyhľadávanie nájde pasáž aj pri písaní bez diakritiky a otvorí ju v príslušnom jazyku.

## Čítanie na mobile

- [citacka.html](citacka.html) je samostatná offline ukážka s hymnom a traktátom vrátane exportov. Otvor ju v prehliadači. Úplný katalóg vrátane Sumy otvor cez `docs/index.html` alebo cez sieťový variant.
- Vo Windows spusti `spustit-na-mobile.cmd`. V telefóne na rovnakej Wi-Fi otvor adresu uvedenú v konzole pri texte „Na mobile“. Okno s konzolou nechaj otvorené, kým čítačku používaš. Skratka Ctrl+C server zastaví. Server sprístupňuje iba priečinok `docs/`.

V nastaveniach čítačky si môžeš vybrať motív, farebný odtieň a písmo. Listovanie ťuknutím posúva text približne o výšku čitateľskej plochy s malým prekrytím. Môžeš zvoliť vodorovné zóny, zvislé zóny alebo funkciu vypnúť. Pri čítaní smerom nadol zmizne spodná lišta a na úzkom displeji aj horná. Lišty sa vrátia po súvislom posune približne o 80 px nahor. Hlbšie v texte sa spolu s lištami zobrazí vpravo dole tlačidlo „Na začiatok“. Pri porovnávaní jazykov sa preklady párujú po strofách, oddieloch alebo článkoch. Na úzkom displeji sú pod sebou.

Latinským východiskom traktátu *O večnosti sveta* je parmenské vydanie z roku 1864, zväzok XVI, s. 318–320. V prepise boli opravené preklepy a podľa kritického vydania boli upravené tri významové čítania v oddieloch 5, 7 a 9 (*potest*, *umquam* a *ex futuro*). Desať nadpisov je redakčných. České a slovenské znenie sú pracovné preklady z latinčiny. [Parmenské vydanie](https://archive.org/details/sanctithomaeaqui16thom) · [Kritické vydanie](https://www.corpusthomisticum.org/ocm.html)

## Teologická suma I

Latinská *Prima pars* obsahuje všetkých 119 otázok a 584 článkov. Web, EPUB a PDF používajú rovnaké členenie. Slovenský pracovný preklad z latinčiny obsahuje všeobecný predhovor a otázky 1–11 spolu s ich 54 článkami. Český pracovný preklad obsahuje všeobecnú predmluvu a I, ot. 2, čl. 3 o piatich cestách. Dostupné pasáže sa dajú porovnať s latinčinou a stiahnuť do EPUB alebo PDF. Úplný historický český preklad je v dvojjazyčnom PDF na Libri nostri. [Corpus Thomisticum](https://www.corpusthomisticum.org/iopera.html) · [Libri nostri](https://librinostri.catholica.cz/download/SvTomasThSumma1-textdve.pdf)

Každý text v `texty/` má stabilné identifikátory oddielov spoločné pre všetky jazyky. V Sume napríklad `q002-a03` označuje 3. článok 2. otázky. Import latinčiny overuje sled všetkých 5 173 zdrojových odsekov. Existujúce české a slovenské preklady zostávajú pri opakovanom importe priradené k tým istým článkom.

Výstupy znova vytvorí `python build.py` s nainštalovaným balíkom `reportlab`. Prepínač `--web-only` obnoví web aj offline čítačku zo zdrojových textov a použije existujúce PDF a EPUB. Predvolený font exportovaných PDF je Georgia zo systému Windows. Prepínač `--font-dir` umožňuje zvoliť iný priečinok s rovnakými súbormi fontu.

Pre GitHub Pages použite vetvu `main` a priečinok `/docs` ako zdroj publikovania. Tento priečinok obsahuje hotový statický web a exporty, takže na GitHube netreba spúšťať Python. Referenčné vydania a zdrojová rešerš sú uložené v lokálnom archíve projektu.
