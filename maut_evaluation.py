"""Auswertung: ein Lauf im Braess-Netz mit Maut, Wer-gewinnt-Experiment, Mauthöhe, feste Maut auf der Abkürzung, Torwahl mit Maut."""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

import maut_constants as C
import maut_gates as Gt
import maut_network as N


@dataclass(frozen=True)
class Settings:
    n: int = C.DEFAULT_N
    c_rel: float = C.DEFAULT_CREL
    e_rel: float = C.DEFAULT_EREL
    mode: str = "marginal"
    lam: float = C.DEFAULT_LAM
    tau_rel: float = C.DEFAULT_TAU
    seed: int = C.DEFAULT_SEED

    def toll(self):
        b = C.CLASSIC_B
        return N.Toll(self.mode, self.lam, self.tau_rel * b * self.n)


@dataclass
class Analysis:
    settings: Settings
    net: object
    toll: object
    run: object
    eq_toll: list          # alle Gleichgewichte mit dieser Maut
    eq_free: list          # alle Gleichgewichte ohne Maut
    opt: tuple             # (Zustand, Fahrzeit-Summe)

    @property
    def n(self):
        return self.net.n

    def time_history(self):
        return [N.social(self.net, N.counts_of(s)) / self.n for s in self.run.states]

    def worst(self, eq):
        """Schlechtestes Gleichgewicht der Liste nach Fahrzeit: (Zustand, Fahrzeit je Lkw)."""
        s = max(eq, key=lambda t: N.social(self.net, t))
        return s, N.social(self.net, s) / self.n

    def toll_per_truck(self, counts):
        return N.revenue(self.net, counts, self.toll) / self.n


@lru_cache(maxsize=64)
def analyse(settings):
    net = N.classic(settings.n, settings.c_rel, settings.e_rel)
    toll = settings.toll()
    start = N.random_assignment(net.n, True, settings.seed)
    run = N.run_sequential(net, start, toll, True, "index", settings.seed)
    return Analysis(settings, net, toll, run, N.equilibria(net, toll), N.equilibria(net, N.NO_TOLL), N.optimum(net))


# --- Experiment 1: wer gewinnt? ---------------------------------------------------------------------------------------------------------------


def winners_experiment(n=None, c_rels=None, e_rel=0.0):
    """Je Umweg-Fahrzeit: schlechtestes Gleichgewicht ohne Maut gegen schlechtestes mit Grenzkosten-Maut (Faktor 1), dazu die gezahlte Maut je Lkw."""
    n = C.WINNERS_N if n is None else n
    c_rels = C.WINNERS_CRELS if c_rels is None else c_rels
    toll = N.Toll("marginal", 1.0, 0.0)
    rows = []
    for c in c_rels:
        net = N.classic(n, c, e_rel)
        eq_free, eq_toll = N.equilibria(net, N.NO_TOLL), N.equilibria(net, toll)
        s_free = max(eq_free, key=lambda t: N.social(net, t))
        s_toll = max(eq_toll, key=lambda t: N.social(net, t))
        rows.append({"c_rel": c, "free_time": N.social(net, s_free) / n, "toll_time": N.social(net, s_toll) / n, "toll_paid": N.revenue(net, s_toll, toll) / n,
                     "opt_time": N.optimum(net)[1] / n})
    return rows


# --- Experiment 2: Mauthöhe --------------------------------------------------------------------------------------------------------------------


def lambda_experiment(n=None, c_rel=None, lams=None, e_rel=0.0):
    n = C.WINNERS_N if n is None else n
    c_rel = C.DEFAULT_CREL if c_rel is None else c_rel
    lams = C.LAMBDAS if lams is None else lams
    net = N.classic(n, c_rel, e_rel)
    rows = []
    for lam in lams:
        toll = N.Toll("marginal", lam, 0.0)
        eq = N.equilibria(net, toll)
        s = max(eq, key=lambda t: N.social(net, t))
        rows.append({"lam": lam, "time": N.social(net, s) / n, "toll_paid": N.revenue(net, s, toll) / n, "opt_time": N.optimum(net)[1] / n})
    return rows


def shortcut_toll_experiment(n=None, c_rel=None, tau_rels=None, e_rel=0.0):
    n = C.WINNERS_N if n is None else n
    c_rel = C.DEFAULT_CREL if c_rel is None else c_rel
    tau_rels = C.TAU_RELS if tau_rels is None else tau_rels
    net = N.classic(n, c_rel, e_rel)
    rows = []
    for tr in tau_rels:
        toll = N.Toll("shortcut", 1.0, tr * C.CLASSIC_B * n)
        eq = N.equilibria(net, toll)
        s = max(eq, key=lambda t: N.social(net, t))
        rows.append({"tau_rel": tr, "time": N.social(net, s) / n, "toll_paid": N.revenue(net, s, toll) / n, "opt_time": N.optimum(net)[1] / n})
    return rows


# --- Experiment 3: Torwahl mit Maut -----------------------------------------------------------------------------------------------------------


def gates_toll_experiment(size_mode, n=None, m=None, seeds=None, lam=1.0):
    n = C.GATES_N if n is None else n
    m = C.GATES_M if m is None else m
    seeds = C.GATES_SEEDS if seeds is None else seeds
    free, tolled, opt_is_ne, toll_pt = [], [], [], []
    for s in seeds:
        r = Gt.analyse(Gt.generate(n, m, size_mode, s), lam)
        free.append(r["ne_cost_max"] / r["opt_cost"])
        tolled.append(r["tne_cost_max"] / r["opt_cost"])
        opt_is_ne.append(r["opt_is_tne"])
        toll_pt.append(r["toll_per_truck_worst"])
    free, tolled = np.array(free), np.array(tolled)
    return {"free": free, "tolled": tolled, "free_mean": float(free.mean()), "tolled_mean": float(tolled.mean()), "free_max": float(free.max()), "tolled_max": float(tolled.max()),
            "share_exact": float(np.mean(tolled <= 1 + 1e-9)), "opt_is_toll_ne": float(np.mean(opt_is_ne)), "toll_per_truck_mean": float(np.mean(toll_pt))}


def _random_instance(rng, n, m, weighted):
    a = rng.uniform(0.0, 10.0, m)
    b = rng.uniform(0.1, 3.0, m)
    w = rng.choice(C.SIZES, size=n).astype(float) if weighted else np.ones(n)
    return Gt.Instance(a, b, w, 0)


def gates_toll_search(weighted, n=None, m=None, starts=None, steps=None, seed=None, lam=1.0):
    """Gezielte Suche nach einer Instanz mit möglichst schlechtem Gleichgewicht trotz Maut: beste von `starts` Zufallsinstanzen, dann Hill Climbing
    über beliebige Tor-Parameter (nicht auf die Vehikel-Bereiche beschränkt). Verlauf = bester bisheriger Preis der Anarchie mit Maut je Bewertung."""
    n = C.GATES_N if n is None else n
    m = C.GATES_M if m is None else m
    starts = C.SEARCH_RANDOM_STARTS if starts is None else starts
    steps = C.SEARCH_STEPS if steps is None else steps
    seed = C.SEARCH_SEED if seed is None else seed
    rng = np.random.default_rng(seed)
    history, best, best_v = [], None, 0.0
    for _ in range(starts):
        inst = _random_instance(rng, n, m, weighted)
        v = Gt.poa_tolled(inst, lam)
        if v > best_v:
            best, best_v = inst, v
        history.append(best_v)
    random_best = best_v
    for _ in range(steps):
        a = np.clip(best.a * np.exp(rng.normal(0, 0.2, m)), 0.0, C.SEARCH_A_MAX)
        b = np.clip(best.b * np.exp(rng.normal(0, 0.2, m)), C.SEARCH_B_MIN, C.SEARCH_B_MAX)
        w = best.w.copy()
        if weighted and rng.random() < 0.3:
            w[rng.integers(n)] = rng.choice(C.SIZES)
        cand = Gt.Instance(a, b, w, 0)
        v = Gt.poa_tolled(cand, lam)
        if v >= best_v:
            best, best_v = cand, v
        history.append(best_v)
    return {"history": history, "random_best": random_best, "best": best_v, "instance": best}
