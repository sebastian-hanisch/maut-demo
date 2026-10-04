# 💶 Maut & Grenzkosten-Preise – wie man Eigennutz auf das Optimum lenkt

**[→ Demo live ausprobieren](https://sebastianhanisch-maut-demo.streamlit.app/)**

Drittes Stück der **Spieltheorie-&-Mechanism-Design-Linie** der "Konzepte"-Reihe im Portfolio von
[Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning. Nachfolger von
[poa-braess-demo](https://sebastianhanisch-poa-braess-demo.streamlit.app/): dort ging es darum, wie schlecht das Gleichgewicht sein kann – hier darum,
**wie ein Preis es verbessert**, was das kostet und wo es nicht reicht. Die Maut ist ein Eingriff von außen; Eigennutz und volle Information der Lkw bleiben Modellannahmen.

## Warum dieses Problem

Im Braess-Netz wählen alle Lkw die Abkürzung – und alle brauchen länger. Eine **Maut** kann das ändern: Sie rechnet jedem Lkw die Kosten ein, die er anderen aufbürdet
(die **Externalität**, Pigou 1920). Wer eine volle Kante nutzt, verlängert die Fahrzeit aller anderen dort. Zahlt er genau diese Mehrzeit als **Grenzkosten-Maut**, deckt sich sein Eigennutz
mit dem Gesamtnutzen (für Netzwerke: Beckmann/McGuire/Winsten 1956).

## Modell

**Braess-Netz** (`maut_network.py`): wortgleich zu poa-braess-demo (vier Knoten, fünf Kanten mit affiner Fahrzeit, drei Wege, Einheitslkw, Zähltupel, exakte Aufzählung bis 40 Lkw),
dazu eine Maut. Jeder Lkw wählt den Weg mit der kleinsten Summe aus **Fahrzeit und Maut** (Maut in Minuten gerechnet); Gütemaß bleibt die Summe der **Fahrzeiten** – die Maut ist eine Überweisung.

- **Grenzkosten-Maut:** auf jeder Kante zahlt ein Lkw $\lambda\, b_e\,(x_e - 1)$, also $\lambda$ mal die Mehrfahrzeit, die er den $x_e - 1$ anderen Lkw aufbürdet. Regler: Faktor $\lambda$ (1 = genau die Externalität).
- **Feste Maut auf der Abkürzung:** $\tau$ Minuten für jeden Lkw, der sie nutzt.
- **Keine Maut** als Referenz.

**Torwahl-Vehikel** (`maut_gates.py`): aus nash-demo (Tore mit Wartezeit $a_g + b_g \cdot$ Last, Lkw mit Größe 1, 2 oder 3), samt Vollaufzählung aller reinen Gleichgewichte, jetzt auch mit Grenzkosten-Maut:
ein Lkw $i$ am Tor $g$ zahlt $\lambda\, b_g\, w_i\,(n_g - 1)$.

## Methodik

- **Exaktes Potenzial (bei $\lambda = 1$):** wechselt ein Lkw den Weg oder das Tor, ändert sich (Fahrzeit + Maut) des Wechslers um genau die Änderung der Summe der Fahrzeiten. Damit ist die Summe ein Potenzial des
  Spiels mit Maut, das Optimum immer ein Gleichgewicht und Best-Response endet in einem lokalen Minimum der Summe. Die Identität wird im Netz und im Torwahl-Spiel (auch mit verschieden großen Lkw) numerisch über je 300 Zufallszüge geprüft.
- **Gleichgewichte** werden aus der Definition aufgezählt (nicht aus der Dynamik); ein Test prüft die Zähltupel-Fassung gegen die Einzel-Lkw-Fassung über alle $3^5$ Zuordnungen, mit und ohne Maut.
- **Gezielte Suche** nach schlechten Torwahl-Instanzen wie in poa-braess-demo (200 Zufallsinstanzen, dann 3000 Hill-Climbing-Schritte), hier auch für das Spiel mit Maut.
- **Literatur** (per Recherche geprüft, hier nicht nachgebaut): für Spiele mit endlich vielen, verschieden großen Spielern gibt es weiterführende Arbeiten, etwa Fotakis/Spirakis 2007 (Cost-Balancing-Tolls).

## Befunde (gemessen, keine Behauptungen)

| Frage | Befund | Test |
|---|---|---|
| Stellt die Grenzkosten-Maut das Optimum her? | Im Braess-Netz ja, für jede der 36 gerechneten Umweg-Längen (20 Lkw, $c/(b\,n)$ von 0,25 bis 2,0): das schlechteste Gleichgewicht mit Maut ist ein Optimum. Standardfall (12 Lkw): 9,0 statt 12,0 min. Die Fahrzeit sinkt für $c/(b\,n)$ von 0,55 bis 1,90; bei sehr langen Umwegen ist die Abkürzung schon ohne Maut optimal. | `test_marginal_toll_reaches_the_optimum_for_every_umweg_time_but_seldom_pays_off`, `test_standardfall_numbers` |
| Was kostet das die Lkw? | Fahrzeit plus gezahlte Maut liegt nur bei einer der 36 Umweg-Längen unter dem Wert ohne Maut ($c = b\,n$: 19,5 statt 20 min je Lkw). Sonst zahlen die Lkw mindestens so viel, wie sie an Zeit sparen (bei $c = 0{,}95\,b\,n$ genau so viel) – solange die Einnahmen nicht zurückverteilt werden (Standardfall: 2,5 min Maut je Lkw; bei $c = 2\,b\,n$ ändert die Maut die Fahrzeit nicht und kostet 19 min je Lkw). | dito, `test_ohne_nutzen_numbers` |
| Wie hoch muss die Maut sein? | Der Faktor 1 reicht (15,0 statt 20,0 min bei 20 Lkw); der halbe Faktor lässt 3 % liegen. Ein zu hoher Faktor schadet der Fahrzeit hier nicht, kostet aber: 13,5 statt 4,5 min je Lkw beim Faktor 3. | `test_marginal_toll_level_sweep`, `test_zu_niedrig_numbers` |
| Reicht eine feste Maut nur auf der Abkürzung? | Ja, ab $\tau = 0{,}5\,b\,n$ ist die Fahrzeit optimal – und dann nutzt niemand die Abkürzung, die Einnahmen sind null. Die höchsten Einnahmen (1,25 min je Lkw) gibt es bei $\tau = 0{,}25\,b\,n$, wo die Fahrzeit noch 8,3 % über dem Optimum liegt: die wirksamste Maut bringt kein Geld ein. Im Standardfall (12 Lkw, $\tau = 0{,}4\,b\,n$): 9,1 min bei 0,4 min Maut je Lkw. | `test_shortcut_toll_sweep_and_the_revenue_hump`, `test_feste_maut_numbers` |
| Reicht die Grenzkosten-Maut im Torwahl-Spiel? | Bei einheitlichen Lkw-Größen ja: in allen 200 Instanzen ist jedes Gleichgewicht ein Optimum (ohne Maut: Preis der Anarchie im Mittel 1,027, Maximum 1,172). Bei gemischten Größen nur begrenzt: im Mittel 1,048 statt 1,059, Maximum 1,125 statt 1,177, und nur 3,5 % der Instanzen werden exakt optimal. Das Optimum ist zwar immer ein Gleichgewicht mit Maut, aber nicht das einzige – die Summe der Wartezeiten hat bei verschieden großen Lkw lokale Minima. | `test_uniform_sizes_toll_makes_every_equilibrium_optimal`, `test_mixed_sizes_toll_helps_only_a_little` |
| Und im schlimmsten Fall? | Die gezielte Suche findet mit Maut 1,36 statt 1,62 ohne Maut (gemischte Größen); bei einheitlichen Größen 1,00. Das sind Ergebnisse dieser Suche, keine bewiesenen Grenzen. | `test_targeted_search_with_toll_stays_below_the_search_without_toll` |

## Ehrliche Grenzen

| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Alle Lkw sind gleich groß und gleich zeitempfindlich** | Bei verschieden großen Lkw reicht die Grenzkosten-Maut nicht für das Optimum (siehe oben). Verschieden zeitempfindliche Fahrer sind nicht abgebildet; dafür braucht es andere Maut-Konzepte. | – |
| **Die Maut wird von der Zentrale gesetzt** | Wer die Maut setzt, muss Last und Kosten der anderen kennen. Eine Behörde mit vollständiger Information ist eine Modellannahme. | Kostenteilung (Shapley) |
| **Einnahmen sind ein Nullsummen-Transfer** | Ohne Rückverteilung verlieren die Lkw im Mittel; ob und wie zurückverteilt wird, ist eine politische, keine algorithmische Frage. | – |
| **Jeder kennt Fahrzeiten und Maut und reagiert perfekt** | Ohne dieses Wissen bleibt nur Lernen aus der eigenen Erfahrung. | No-Regret-Lernen |
| **Alle entscheiden gleichzeitig, keiner legt sich fest** | Ein Anführer, der sich zuerst festlegt, lenkt das Ergebnis auch ohne Maut. | Stackelberg |

Nur **reine** Gleichgewichte. Bei Gleichstand bleibt ein Lkw, deshalb gibt es im Netz oft mehrere fast gleich gute Gleichgewichte. Die Suche nach schlechten Torwahl-Instanzen ist ein einfacher Hill Climber mit
festem Seed; ein stärkerer Suchalgorithmus könnte höhere Werte finden.

Verwandt: [frank-wolfe-demo](https://github.com/sebastian-hanisch/frank-wolfe-demo) (Netzwerkfluss-Linie: dieselbe Idee mit stetigem Verkehr auf einem Stadtgitter, Systemoptimum = Gleichgewicht auf Grenzkosten, Löser und Endspurt), [poa-braess-demo](https://sebastianhanisch-poa-braess-demo.streamlit.app/) (Vorgänger), [nash-demo](https://sebastianhanisch-nash-demo.streamlit.app/) (Best-Response im Torwahl-Spiel),
[auction-demo](https://sebastianhanisch-auction-demo.streamlit.app/) (Zahlungsregeln in Auktionen, VCG).

## Tests

Pytest-Suite (`pytest tests/ -v`): Maut und Einnahmen per Handrechnung (4 Lkw, $b=1$, $c=4$), exaktes Potenzial im Netz und im Torwahl-Spiel (300 Zufallszüge je), Schwelle der festen Maut per Handrechnung,
Zähltupel gegen Einzel-Lkw-Definition (mit und ohne Maut), Best-Response endet in einem aufgezählten Gleichgewicht, Torwahl-Vehikel gegen die Zahlen aus nash-demo und gegen eine skalare Definition der Gleichgewichte,
einheitliche Lkw → jedes Gleichgewicht optimal, AppTest-Rauchtests (jedes Preset, Zug-Slider inkl. Abspielen, Permalink-Grenzen, modusabhängige Regler, drei Experimente auf Abruf) und `test_claims.py`
(jede Zahl aus diesem README; Mehr-Instanzen-Zahlen mit großzügigen Bändern).

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Einstiegspunkt |
| `maut_constants.py` | Regler-Grenzen, Netz- und Vehikel-Konstanten, Experiment-Seeds, Presets |
| `maut_presets.py` | Permalink/Presets-Mechanik |
| `maut_network.py` | Braess-Netz, Maut, Zähltupel, Gleichgewichte, Optimum, Best-Response |
| `maut_gates.py` | Torwahl-Vehikel (aus nash-demo) mit Grenzkosten-Maut, Vollaufzählung |
| `maut_evaluation.py` | Analyse eines Laufs, drei Experimente (Wer gewinnt, Mauthöhe, Torwahl) |
| `maut_visualization.py` | Plotly-Abbildungen |

## Bewusst nicht umgesetzt

- Beliebige Netze und nicht-affine Fahrzeiten (wie poa-braess-demo).
- Verschieden zeitempfindliche Fahrer und darauf zugeschnittene Maut-Konzepte.
- Optimale Maut für gewichtete Spiele (Cost-Balancing-Tolls und Nachfolger).
- Kostenteilung als Mechanism-Design-Zwilling der Maut (späteres Stück der Linie).
- Ein PDF-Export – wie bei den anderen Konzepte-Demos dieses Portfolios nicht Teil der Linie.

## Lokal ausführen

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements-dev.txt
streamlit run app.py
```

Gebaut mit Streamlit, Plotly und numpy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Spieltheorie: von Nash bis Myerson-Satterthwaite](https://sebastianhanisch.net/konzepte-spieltheorie.html).
