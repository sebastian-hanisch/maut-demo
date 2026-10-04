"""Maut & Grenzkosten-Preise - wie man Eigennutz auf das Optimum lenkt - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Drittes Stück der Linie "Spieltheorie & Mechanism Design" der "Konzepte"-Reihe (Nachfolger von poa-braess-demo): wenn das Gleichgewicht schlecht ist,
kann ein Preis es verbessern - was bewirkt eine Maut, was kostet sie, und wo reicht sie nicht?

Lauffähig mit: streamlit run app.py
"""

import time

import numpy as np
import streamlit as st

import maut_constants as C
import maut_network as N
from maut_evaluation import Settings, analyse, gates_toll_experiment, gates_toll_search, lambda_experiment, shortcut_toll_experiment, winners_experiment
from maut_presets import apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, sync_query_params, seed_widget
from maut_visualization import build_gates_toll, build_network, build_search_pair, build_time_curve, build_toll_sweep, build_winners

st.set_page_config(page_title="Maut & Grenzkosten-Preise – Sebastian Hanisch", layout="wide")


def de(x, digits=1):
    """Deutsche Zahlenschreibweise: Punkt als Tausendertrenner, Komma als Dezimalzeichen."""
    return f"{x:,.{digits}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def pct(x, digits=0):
    return f"{de(100 * x, digits)} %"


@st.cache_data(show_spinner=False)
def _winners():
    return winners_experiment()


@st.cache_data(show_spinner=False)
def _levels():
    return lambda_experiment(), shortcut_toll_experiment()


@st.cache_data(show_spinner=False)
def _gates():
    return gates_toll_experiment("mixed"), gates_toll_experiment("uniform"), gates_toll_search(True, lam=0.0), gates_toll_search(True, lam=1.0)


st.title("💶 Maut & Grenzkosten-Preise – wie man Eigennutz auf das Optimum lenkt")
st.markdown(
    """
Im Braess-Netz der Vorgänger-Demo wählen alle Lkw die Abkürzung - und alle brauchen länger. Eine **Maut** kann das ändern: Sie rechnet jedem Lkw die Kosten ein, die er anderen Lkw
aufbürdet (die **Externalität**). Wer eine volle Kante nutzt, verlängert die Fahrzeit aller anderen dort - zahlt er genau diese Mehrzeit als **Grenzkosten-Maut**, deckt sich sein Eigennutz mit
dem Gesamtnutzen. Die Demo zeigt, was das im Braess-Netz und im Torwahl-Spiel bewirkt, was es kostet und wo es nicht reicht.
"""
)
st.caption(
    "Drittes Stück der Linie \"Spieltheorie & Mechanism Design\" der \"Konzepte\"-Reihe, Nachfolger von **poa-braess-demo**: dort ging es darum, wie schlecht das Gleichgewicht sein kann - hier darum, "
    "wie ein Preis es verbessert. Die Maut ist ein Eingriff von außen; Eigennutz und volle Information der Lkw bleiben Modellannahmen."
)

with st.expander("So funktioniert die Maut", expanded=True):
    st.markdown(
        """
1. **Wahrgenommene Kosten.** Jeder Lkw wählt den Weg mit der kleinsten Summe aus **Fahrzeit und Maut** (Maut in Minuten gerechnet). Gütemaß ist weiter die **Fahrzeit** - die Maut ist eine Überweisung.
2. **Grenzkosten-Maut.** Auf jeder lastabhängigen Kante zahlt ein Lkw *Faktor · b · (Last − 1)*: die Mehrfahrzeit, die er den anderen Lkw dort aufbürdet. Bei Faktor 1 ist die Summe der Fahrzeiten
   ein exaktes Potenzial des Spiels mit Maut - jeder Wechsel ändert (Fahrzeit + Maut) des Wechslers um genau die Änderung der Summe. Wer sich nur selbst verbessert, verbessert also das Ganze.
3. **Feste Maut auf der Abkürzung.** Eine einzige Gebühr an einer Stelle statt lastabhängiger Preise überall - einfacher, aber nur so gut wie ihre Höhe.
4. **Rückverteilung.** Die Einnahmen verschwinden nicht: Werden sie gleichmäßig zurückgegeben, bleibt netto nur die Fahrzeit. Ohne Rückgabe kommt zur Fahrzeit die Maut dazu.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_names = list(C.PRESETS.keys())
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(len(row))
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name], key=f"preset_{name}")

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_trucks = st.slider("Lkw", *bounds("n_slider"), key="n_slider", step=C.N_STEP, help="Anzahl der Lkw (alle gleich groß), die einen Weg wählen.")
    c_rel = st.slider("Umweg-Fahrzeit c / (b · n)", *bounds("crel_slider"), key="crel_slider", step=C.CREL_STEP, format="%.2f",
                      help="Feste Fahrzeit der Umwege A→t und s→B im Verhältnis zur Fahrzeit, die die lastabhängigen Kanten bei voller Auslastung hätten.")
    e_rel = st.slider("Abkürzung: eigene Fahrzeit e / (b · n)", *bounds("erel_slider"), key="erel_slider", step=C.EREL_STEP, format="%.2f",
                      help="Feste Fahrzeit der Abkürzung A→B. 0 = die Abkürzung ist kostenlos.")
    mode = st.selectbox("Maut", C.TOLL_MODES, key="mode_select", format_func=lambda k: C.TOLL_LABELS[k])
    if mode == "marginal":
        seed_widget("lam_slider")
        lam = st.slider("Faktor auf die Grenzkosten-Maut", *bounds("lam_slider"), key="lam_slider", step=C.LAM_STEP, format="%.2f",
                        help="1 = genau die Mehrfahrzeit, die der Lkw den anderen aufbürdet. Darunter: zu niedrig, darüber: zu hoch.")
        tau = float(st.session_state.get("_kept_tau_slider", C.DEFAULT_TAU))
        st.session_state["_kept_lam_slider"] = lam
    elif mode == "shortcut":
        seed_widget("tau_slider")
        tau = st.slider("Maut auf der Abkürzung τ / (b · n)", *bounds("tau_slider"), key="tau_slider", step=C.TAU_STEP, format="%.2f",
                        help="Feste Gebühr für jeden Lkw, der die Abkürzung nutzt, im Verhältnis zur Fahrzeit einer voll ausgelasteten lastabhängigen Kante.")
        lam = float(st.session_state.get("_kept_lam_slider", C.DEFAULT_LAM))
        st.session_state["_kept_tau_slider"] = tau
    else:
        lam = float(st.session_state.get("_kept_lam_slider", C.DEFAULT_LAM))
        tau = float(st.session_state.get("_kept_tau_slider", C.DEFAULT_TAU))
    seed = st.number_input("Zufalls-Seed der Startzuordnung", *bounds("seed_input"), key="seed_input", step=1, help="Legt die zufällige Anfangs-Wegwahl fest.")
    st.button("🎲 Neue Startzuordnung würfeln", width="stretch", on_click=randomize_seed)

sync_query_params({"n_slider": int(n_trucks), "crel_slider": float(c_rel), "erel_slider": float(e_rel), "mode_select": mode, "lam_slider": float(lam), "tau_slider": float(tau), "seed_input": int(seed)})

settings = Settings(int(n_trucks), float(c_rel), float(e_rel), mode, float(lam), float(tau), int(seed))
a = analyse(settings)
net, toll, run = a.net, a.toll, a.run
n = net.n
n_steps = len(run.states) - 1
history = a.time_history()
opt_time = a.opt[1] / n
worst_free_state, worst_free = a.worst(a.eq_free)
worst_toll_state, worst_toll = a.worst(a.eq_toll)

# --- Best-Response mit Maut ----------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Best-Response mit Maut")
if "maut_step" not in st.session_state or st.session_state.get("maut_step_owner") != settings:
    st.session_state["maut_step"] = n_steps
    st.session_state["maut_step_owner"] = settings
step_col, play_col = st.columns([5, 2])
with step_col:
    step = st.slider("Zug", 0, n_steps, key="maut_step", help="0 = Startzuordnung.") if n_steps > 0 else 0
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch", disabled=n_steps == 0)
if n_steps == 0:
    st.info("Die zufällige Startzuordnung ist bereits ein Gleichgewicht - kein Lkw will wechseln. Andere Startzuordnung würfeln oder eine andere Lkw-Zahl wählen.")
view_slot = st.empty()


def _render(s):
    with view_slot.container():
        c1, c2 = st.columns([5, 4])
        counts = N.counts_of(run.states[s])
        head = "Startzuordnung" if s == 0 else f"Zug {s} von {n_steps}"
        c1.markdown(f"**{head} – mittlere Fahrzeit: {de(history[s])} min, mittlere Maut: {de(a.toll_per_truck(counts))} min je Lkw**")
        c1.plotly_chart(build_network(net, counts, toll), width="stretch", key=f"maut_net_{s}")
        times, tolls = N.path_costs(net, counts), N.path_tolls(net, counts, toll)
        c2.markdown("**Lkw je Weg** (Zeit und Maut in min)")
        c2.dataframe({"Weg": list(N.PATH_LABELS), "Lkw": list(counts), "Zeit": [de(x) for x in times], "Maut": [de(x) for x in tolls]}, hide_index=True)
        c2.plotly_chart(build_time_curve(history, upto=s, reference=opt_time), width="stretch", key=f"maut_curve_{s}")
        if s > 0:
            i, p, q = run.moves[s - 1]
            c2.caption(f"Lkw {i + 1} wechselt von Weg {p + 1} zu Weg {q + 1}.")


def _frames():
    if n_steps == 0:
        return [0]
    return sorted({int(round(x)) for x in np.linspace(0, n_steps, min(n_steps + 1, 40))})


if auto_play:
    for f in _frames():
        _render(f)
        time.sleep(0.25)
else:
    _render(step)

st.markdown("---")

# --- Ergebnis -------------------------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Was die Maut bewirkt")
final = N.counts_of(run.final)
reached_toll = a.toll_per_truck(final)
worst_toll_paid = a.toll_per_truck(worst_toll_state)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Erreichtes Gleichgewicht", f"{de(history[-1])} min", delta=f"Maut {de(reached_toll)} min", delta_color="off", help=f"Mittlere Fahrzeit je Lkw nach {len(run.moves)} Wechseln, dazu die mittlere Maut.")
m2.metric("Schlechtestes Gleichgewicht mit dieser Maut", f"{de(worst_toll)} min", help=f"Unter {len(a.eq_toll)} Gleichgewichten (Vollaufzählung); Fahrzeit ohne Maut.")
m3.metric("Schlechtestes Gleichgewicht ohne Maut", f"{de(worst_free)} min", help=f"Unter {len(a.eq_free)} Gleichgewichten (Vollaufzählung).")
m4.metric("Optimum", f"{de(opt_time)} min", help="Kleinste mittlere Fahrzeit über alle Zuordnungen, von außen gesteuert.")

total_toll = worst_toll + worst_toll_paid
if mode == "none":
    st.info(f"Ohne Maut liegt das schlechteste Gleichgewicht bei {de(worst_free)} min, das Optimum bei {de(opt_time)} min (Preis der Anarchie {de(worst_free / opt_time, 3)}).")
elif worst_toll <= opt_time + 1e-9 and worst_free > opt_time + 1e-9:
    st.success(f"✅ Mit dieser Maut ist jedes Gleichgewicht ein Optimum: {de(worst_toll)} statt {de(worst_free)} min ({pct(1 - worst_toll / worst_free)} weniger). "
               f"Dafür zahlt jeder Lkw im Schnitt {de(worst_toll_paid)} min Maut - Fahrzeit plus Maut {de(total_toll)} min gegenüber {de(worst_free)} min ohne Maut.")
elif worst_toll < worst_free - 1e-9:
    st.warning(f"⚠️ Die Maut hilft nur teilweise: {de(worst_toll)} statt {de(worst_free)} min im schlechtesten Gleichgewicht, das Optimum liegt bei {de(opt_time)} min. "
               f"Jeder Lkw zahlt dafür im Schnitt {de(worst_toll_paid)} min Maut (Fahrzeit plus Maut {de(total_toll)} min).")
elif worst_free <= opt_time + 1e-9:
    st.warning(f"⚠️ Die Maut nützt hier nichts: Schon ohne Maut ist das Gleichgewicht optimal ({de(worst_free)} min). Sie kostet jeden Lkw im Schnitt {de(worst_toll_paid)} min - reine Umverteilung.")
else:
    st.warning(f"⚠️ Diese Maut ändert die Fahrzeit im schlechtesten Gleichgewicht nicht ({de(worst_toll)} min), kostet aber im Schnitt {de(worst_toll_paid)} min je Lkw.")
if mode != "none" and total_toll > worst_free + 1e-9:
    st.caption(f"Ohne Rückverteilung der Einnahmen liegen die Lkw im schlechtesten Gleichgewicht bei Fahrzeit plus Maut über dem Wert ohne Maut ({de(total_toll)} statt {de(worst_free)} min). "
               "Bei gleichmäßiger Rückgabe bleibt netto die Fahrzeit.")

st.markdown("**Alle Gleichgewichte mit dieser Maut** (Vollaufzählung der Zähltupel Lkw je Weg)")
st.dataframe(
    {"Lkw auf s→A→t": [s[0] for s in a.eq_toll], "Lkw auf s→B→t": [s[1] for s in a.eq_toll], "Lkw über die Abkürzung": [s[2] for s in a.eq_toll],
     "Mittlere Fahrzeit (min)": [de(N.social(net, s) / n, 2) for s in a.eq_toll], "Mittlere Maut (min)": [de(a.toll_per_truck(s), 2) for s in a.eq_toll]},
    hide_index=True,
)
st.caption("Bei Gleichstand bleibt ein Lkw, deshalb kann es mehrere, fast gleich gute Gleichgewichte geben.")

st.markdown("---")

# --- Experiment 1: wer gewinnt? ------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wer gewinnt, wer zahlt?")
st.caption(f"{C.WINNERS_N} Lkw, kostenlose Abkürzung, Grenzkosten-Maut mit Faktor 1; Umweg-Fahrzeit c von {de(C.WINNERS_CRELS[0], 2)} bis {de(C.WINNERS_CRELS[-1], 2)} mal b·n. "
           "Schlechtestes Gleichgewicht je Fall, exakt aufgezählt.")
if st.button("Vergleich berechnen", key="winners_start"):
    st.session_state["winners_on"] = True
if st.session_state.get("winners_on"):
    rows_w = _winners()
    st.plotly_chart(build_winners(rows_w), width="stretch", key="winners_chart")
    faster = [r["c_rel"] for r in rows_w if r["toll_time"] < r["free_time"] - 1e-9]
    net_better = [r["c_rel"] for r in rows_w if r["toll_time"] + r["toll_paid"] < r["free_time"] - 1e-9]
    at_opt = all(abs(r["toll_time"] - r["opt_time"]) < 1e-9 for r in rows_w)
    st.warning(
        f"**Befund:** Die Grenzkosten-Maut {'stellt in jedem gerechneten Fall das Optimum her' if at_opt else 'verbessert das Gleichgewicht'}; die Fahrzeit sinkt für c von {de(min(faster), 2)} bis {de(max(faster), 2)} mal b·n. "
        f"Aber die Maut kostet: Fahrzeit plus gezahlte Maut liegt nur für {len(net_better)} der {len(rows_w)} gerechneten Umweg-Längen unter dem Wert ohne Maut"
        f"{' (c = ' + ', '.join(de(x, 2) for x in net_better) + ' mal b·n)' if net_better else ''}. Überall sonst zahlen die Lkw mindestens so viel, wie sie an Zeit sparen - solange die Einnahmen nicht zurückverteilt werden. "
        "Bei sehr langen Umwegen ist die Abkürzung schon ohne Maut optimal, dort ist die Maut reine Umverteilung."
    )

st.markdown("---")

# --- Experiment 2: Mauthöhe ------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wie hoch muss die Maut sein?")
st.caption(f"{C.WINNERS_N} Lkw, Umwege c = {de(C.DEFAULT_CREL, 2)} · b·n, kostenlose Abkürzung (das Standard-Braess-Netz). Schlechtestes Gleichgewicht je Mauthöhe, exakt aufgezählt.")
if st.button("Mauthöhen vergleichen", key="levels_start"):
    st.session_state["levels_on"] = True
if st.session_state.get("levels_on"):
    rows_l, rows_s = _levels()
    st.markdown("**Grenzkosten-Maut mit Faktor**")
    st.plotly_chart(build_toll_sweep(rows_l, "lam", "Faktor auf die Grenzkosten-Maut", reference_x=1.0), width="stretch", key="levels_chart")
    st.markdown("**Feste Maut nur auf der Abkürzung**")
    st.plotly_chart(build_toll_sweep(rows_s, "tau_rel", "Maut auf der Abkürzung τ / (b · n)"), width="stretch", key="shortcut_chart")
    first_opt = next(r for r in rows_l if abs(r["time"] - r["opt_time"]) < 1e-9)
    half = next(r for r in rows_l if abs(r["lam"] - 0.5) < 1e-9)
    top = rows_l[-1]
    s_opt = next(r for r in rows_s if abs(r["time"] - r["opt_time"]) < 1e-9)
    s_rev = max(rows_s, key=lambda r: r["toll_paid"])
    st.warning(
        f"**Befund:** Bei der Grenzkosten-Maut erreicht schon der Faktor {de(first_opt['lam'], 2)} das Optimum ({de(first_opt['opt_time'])} min). Der halbe Faktor lässt {pct(half['time'] / half['opt_time'] - 1)} liegen; "
        f"ein zu hoher Faktor schadet der Fahrzeit hier nicht, kostet aber: beim Faktor {de(top['lam'], 0)} zahlt jeder Lkw {de(top['toll_paid'])} statt {de(first_opt['toll_paid'])} min. "
        f"Die feste Maut auf der Abkürzung erreicht das Optimum ab τ = {de(s_opt['tau_rel'], 2)} · b·n - und dann nutzt niemand die Abkürzung mehr, die Einnahmen sind {de(s_opt['toll_paid'])} min je Lkw. "
        f"Die höchsten Einnahmen ({de(s_rev['toll_paid'], 2)} min je Lkw) gibt es bei τ = {de(s_rev['tau_rel'], 2)} · b·n, wo die Fahrzeit noch {pct(s_rev['time'] / s_rev['opt_time'] - 1)} über dem Optimum liegt: "
        "die wirksamste Maut bringt kein Geld ein."
    )

st.markdown("---")

# --- Experiment 3: Torwahl mit Maut ----------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Torwahl-Spiel: reicht die Grenzkosten-Maut?")
st.caption(f"Das Torwahl-Spiel der Vorgänger-Demos ({C.GATES_N} Lkw, {C.GATES_M} Tore): ein Lkw am Tor g zahlt Faktor · b_g · (eigene Größe) · (Zahl der anderen Lkw am Tor), also die Mehrwartezeit, die er den anderen aufbürdet. "
           f"{len(C.GATES_SEEDS)} Vehikel-Instanzen wie in nash-demo, schlechtestes Gleichgewicht gegen Optimum, exakt aufgezählt; dazu die gezielte Suche aus poa-braess-demo "
           f"({C.SEARCH_RANDOM_STARTS} Zufallsinstanzen, dann {C.SEARCH_STEPS} Hill-Climbing-Schritte) nach der schlechtesten Instanz mit gemischten Größen.")
if st.button("Torwahl mit und ohne Maut vergleichen (dauert einige Sekunden)", key="gates_start"):
    st.session_state["gates_on"] = True
if st.session_state.get("gates_on"):
    with st.spinner("Rechne..."):
        g_mixed, g_uniform, s_free, s_toll = _gates()
    st.plotly_chart(build_gates_toll(g_mixed, g_uniform), width="stretch", key="gates_chart")
    st.plotly_chart(build_search_pair(s_free, s_toll), width="stretch", key="gates_search")
    st.warning(
        f"**Befund:** Bei einheitlichen Lkw-Größen macht die Grenzkosten-Maut jedes Gleichgewicht zum Optimum: in {pct(g_uniform['share_exact'])} der Instanzen Preis der Anarchie genau 1 "
        f"(ohne Maut im Mittel {de(g_uniform['free_mean'], 3)}, Maximum {de(g_uniform['free_max'], 3)}). Bei gemischten Größen wirkt sie nur begrenzt: im Mittel {de(g_mixed['tolled_mean'], 3)} statt {de(g_mixed['free_mean'], 3)}, "
        f"Maximum {de(g_mixed['tolled_max'], 3)} statt {de(g_mixed['free_max'], 3)}, und nur {pct(g_mixed['share_exact'])} der Instanzen werden exakt optimal. Das Optimum ist zwar immer ein Gleichgewicht mit Maut "
        f"({pct(g_mixed['opt_is_toll_ne'])} der Instanzen), aber nicht das einzige - die Summe der Wartezeiten hat bei verschieden großen Lkw lokale Minima. "
        f"Die gezielte Suche findet mit Maut {de(s_toll['best'], 2)} statt {de(s_free['best'], 2)} ohne Maut. Die Maut kostet dabei im Mittel {de(g_mixed['toll_per_truck_mean'])} min je Lkw (gemischt)."
    )

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Alle Lkw sind gleich groß und gleich zeitempfindlich** | Bei verschieden großen Lkw reicht die Grenzkosten-Maut nicht für das Optimum (Experiment oben). Verschieden zeitempfindliche Fahrer (Zeit ist ihnen verschieden viel wert) sind hier nicht abgebildet; dafür braucht es andere Maut-Konzepte. | - |
| **Die Maut wird von der Zentrale gesetzt** | Wer die Maut setzt, muss die Kosten der anderen kennen: Last und Preise je Kante. Eine Behörde mit vollständiger Information ist eine Modellannahme. | Kostenteilung (Shapley) |
| **Einnahmen sind ein Nullsummen-Transfer** | Ohne Rückverteilung verlieren die Lkw im Mittel; ob und wie zurückverteilt wird, ist eine politische, keine algorithmische Frage. | - |
| **Jeder kennt Fahrzeiten und Maut und reagiert perfekt** | Ohne dieses Wissen bleibt nur Lernen aus der eigenen Erfahrung. | **No-Regret-Lernen** |
| **Alle entscheiden gleichzeitig, keiner legt sich fest** | Ein Anführer, der sich zuerst festlegt, lenkt das Ergebnis auch ohne Maut. | **Stackelberg** |
"""
)
st.caption(
    "Verwandt: [poa-braess-demo](https://sebastianhanisch-poa-braess-demo.streamlit.app/) (Vorgänger: Preis der Anarchie und Braess-Paradox), "
    "[nash-demo](https://sebastianhanisch-nash-demo.streamlit.app/) (Best-Response im Torwahl-Spiel), [auction-demo](https://sebastianhanisch-auction-demo.streamlit.app/) (Zahlungsregeln in Auktionen, VCG)."
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Wahrgenommene Kosten.** Weg $p$ mit Fahrzeit $T_p(x)$ (Summe der Kantenzeiten $a_e + b_e x_e$) und Maut $\tau_p(x)$: Lkw wählen den Weg mit kleinster Summe $T_p(x) + \tau_p(x)$.

**Grenzkosten-Maut.** Auf Kante $e$ zahlt jeder Lkw $\tau_e = \lambda\, b_e\,(x_e - 1)$, ein Weg zahlt die Summe über seine Kanten. Dass ein weiterer Lkw auf $e$ die Fahrzeit der $x_e - 1$ anderen
um je $b_e$ verlängert, ist die Externalität; bei $\lambda = 1$ zahlt der Lkw genau sie.

**Exaktes Potenzial.** Sei $SC(x) = \sum_e x_e\,(a_e + b_e x_e)$ die Summe der Fahrzeiten. Wechselt ein Lkw von Weg $p$ auf $q$, ändert sich $SC$ um genau die Änderung seiner wahrgenommenen Kosten
(Fahrzeit + Maut) bei $\lambda = 1$: $\Delta SC = \Delta(T + \tau)$. Also ist $SC$ ein exaktes Potenzial: Best-Response endet in einem lokalen Minimum von $SC$, und das globale Minimum, das Optimum, ist
stets ein Gleichgewicht. Bei einheitlichen Lkw in der Torwahl ist $SC$ eine konvexe, trennbare Summe über die Zahl der Lkw je Tor; jedes lokale Minimum ist dann global. Bei verschieden großen Lkw
gilt das nicht.

**Torwahl-Maut.** Lkw $i$ mit Größe $w_i$ am Tor $g$ zahlt $\lambda\, b_g\, w_i\,(n_g - 1)$, $n_g$ = Zahl der Lkw am Tor.

**Feste Maut.** Auf der Abkürzung: alle Lkw auf $P_3$ sind Gleichgewicht genau dann, wenn $2bn + e + \tau \le bn + c$, also für $\tau \le c - bn - e$. Beim klassischen Netz ($c = bn$, $e = 0$) bricht schon jede Maut $\tau > 0$ dieses Gleichgewicht; wie weit die Fahrzeit sinkt, zeigt das Experiment.

Literatur: Pigou 1920 (Grenzkosten-Preise), Beckmann/McGuire/Winsten 1956 (Netzwerke); für Spiele mit endlich vielen, verschieden großen Spielern Fotakis/Spirakis 2007 (Cost-Balancing-Tolls) - hier nicht nachgebaut.

Implementiert in `maut_network.py` (Netz, Maut, Gleichgewichte, Best-Response), `maut_gates.py` (Torwahl-Vehikel mit Maut, Vollaufzählung), `maut_evaluation.py` (Experimente).
        """
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Spieltheorie: von Nash bis Myerson-Satterthwaite](https://sebastianhanisch.net/konzepte-spieltheorie.html)."
)
