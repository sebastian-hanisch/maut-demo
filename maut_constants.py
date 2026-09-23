"""Konstanten der Maut-Demo: Braess-Netz (Einheitslkw) mit Maut, Vehikel "Torwahl" aus nash-demo, Regler, Experimente (Presets nach den Messungen)."""

EPS = 1e-9                         # ein Wechsel zählt nur bei echter Verbesserung
SEED_MAX = 999999

# --- Braess-Netz (wortgleich zu poa-braess-demo) ---------------------------------------------------------------------------------------------

CLASSIC_B = 0.5                    # Zuschlag je Lkw auf den lastabhängigen Kanten s→A und B→t (Minuten)
N_MIN, N_MAX, DEFAULT_N, N_STEP = 4, 40, 12, 2
CREL_MIN, CREL_MAX, DEFAULT_CREL, CREL_STEP = 0.25, 2.0, 1.0, 0.05      # c = c_rel * b * n: feste Fahrzeit der Umwege A→t und s→B
EREL_MIN, EREL_MAX, DEFAULT_EREL, EREL_STEP = 0.0, 0.5, 0.0, 0.05       # e = e_rel * b * n: Fahrzeit der Abkürzung A→B
DEFAULT_SEED = 7                   # Seed der Startzuordnung

# --- Maut ------------------------------------------------------------------------------------------------------------------------------------

TOLL_MODES = ("none", "marginal", "shortcut")
TOLL_LABELS = {"none": "Keine Maut", "marginal": "Grenzkosten-Maut auf allen Kanten", "shortcut": "Feste Maut nur auf der Abkürzung"}
LAM_MIN, LAM_MAX, DEFAULT_LAM, LAM_STEP = 0.0, 3.0, 1.0, 0.25           # Faktor auf die Grenzkosten-Maut (1 = genau die Kosten, die der Lkw anderen aufbürdet)
TAU_MIN, TAU_MAX, DEFAULT_TAU, TAU_STEP = 0.0, 0.6, 0.4, 0.05           # tau = tau_rel * b * n: feste Maut auf der Abkürzung A→B

# --- Vehikel "Torwahl" (wortgleich zu nash-demo) ----------------------------------------------------------------------------------------------

A_MIN, A_MAX = 2.0, 10.0
B_MIN, B_MAX = 0.5, 3.0
SIZES = (1, 2, 3)
SIZE_PROBS = (0.5, 0.3, 0.2)
ENUM_MAX_ASSIGNMENTS = 2_000_000

# --- Experimente (feste Seeds) ----------------------------------------------------------------------------------------------------------------

WINNERS_N = 20
WINNERS_CRELS = tuple(round(0.25 + 0.05 * k, 2) for k in range(36))       # 0,25 bis 2,0
LAMBDAS = tuple(round(0.25 * k, 2) for k in range(13))                     # 0 bis 3
TAU_RELS = tuple(round(0.05 * k, 2) for k in range(13))                    # 0 bis 0,6
GATES_N, GATES_M = 6, 3
GATES_SEEDS = tuple(range(600000, 600200))
SEARCH_RANDOM_STARTS = 200
SEARCH_STEPS = 3000
SEARCH_SEED = 11
SEARCH_A_MAX, SEARCH_B_MIN, SEARCH_B_MAX = 50.0, 0.01, 20.0

# --- Presets (Werte nach den Messungen; PRESET_HELP aus dem Netz mit Startzuordnungs-Seed 7) ----------------------------------------------------


def _preset(n=DEFAULT_N, c_rel=DEFAULT_CREL, e_rel=DEFAULT_EREL, mode="marginal", lam=DEFAULT_LAM, tau_rel=DEFAULT_TAU, seed=DEFAULT_SEED):
    return {"n": n, "c_rel": c_rel, "e_rel": e_rel, "mode": mode, "lam": lam, "tau_rel": tau_rel, "seed": seed}


PRESETS = {
    "Standardfall (Grenzkosten-Maut)": _preset(),
    "Keine Maut": _preset(mode="none"),
    "Feste Maut nur auf der Abkürzung": _preset(mode="shortcut"),
    "Maut zu niedrig (Faktor 0,5)": _preset(lam=0.5),
    "Maut ohne Nutzen (c = 2,0)": _preset(c_rel=2.0),
    "Große Instanz (40 Lkw)": _preset(n=40),
}
PRESET_HELP = {
    "Standardfall (Grenzkosten-Maut)": "12 Lkw, Braess-Netz: mit der Grenzkosten-Maut steht das Gleichgewicht nach 6 Wechseln bei 6/6/0 Lkw und 9,0 min - dem Optimum. Ohne Maut wären es im schlechtesten Gleichgewicht 12,0 min. Dafür zahlt jeder Lkw 2,5 min Maut.",
    "Keine Maut": "Dasselbe Netz ohne Maut: 4 Wechsel bis 11,1 min je Lkw, im schlechtesten Gleichgewicht 12,0 min (alle auf der Abkürzung) - Braess-Paradox aus poa-braess-demo.",
    "Feste Maut nur auf der Abkürzung": "Nur die Abkürzung kostet 2,4 min Maut (0,4 · b · n): 4 Wechsel, 5/5/2 Lkw, 9,1 min - fast das Optimum bei nur 0,4 min Maut je Lkw im Schnitt.",
    "Maut zu niedrig (Faktor 0,5)": "Halbe Grenzkosten-Maut: 4/4/4 Lkw, 9,3 min. Ein Teil des Gewinns geht verloren (Optimum 9,0), dafür zahlt jeder Lkw 2,3 statt 2,5 min.",
    "Maut ohne Nutzen (c = 2,0)": "Sind die Umwege sehr lang, ist die Abkürzung schon ohne Maut optimal (12,0 min). Die Maut ändert die Fahrzeit nicht und kostet 11,0 min je Lkw - reine Umverteilung.",
    "Große Instanz (40 Lkw)": "40 Lkw: 18 Wechsel bis 30,0 min (Optimum) statt 40,0 im schlechtesten Gleichgewicht ohne Maut; Maut 9,5 min je Lkw.",
}
