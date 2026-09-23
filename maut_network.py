"""Braess-Netz mit Maut. Vier Knoten s, A, B, t, fünf Kanten mit affiner Fahrzeit a_e + b_e * Last; drei Wege für die Lkw (Einheitsgröße):
Weg 1 = s-A-t, Weg 2 = s-B-t, Weg 3 = s-A-B-t (die Abkürzung). Zustände sind Zähltupel (n1, n2, n3).

Maut (Geld, in Minuten gerechnet): jeder Lkw entscheidet nach Fahrzeit + Maut seines Weges.
- keine: 0
- Grenzkosten-Maut: auf jeder Kante zahlt ein Lkw lam * b_e * (Last - 1), also lam mal die Mehrfahrzeit, die er den anderen Lkw auf der Kante aufbürdet.
- feste Maut: tau Minuten für die Nutzung der Abkürzung.
Die Fahrzeit (ohne Maut) ist das Gütemaß; die Maut ist eine Überweisung und zählt nicht zur Summe der Fahrzeiten."""

from dataclasses import dataclass, field

import numpy as np

import maut_constants as C

EDGES = ("s→A", "A→t", "s→B", "B→t", "A→B")
PATHS = ((0, 1), (2, 3), (0, 4, 3))
PATH_LABELS = ("s→A→t", "s→B→t", "s→A→B→t (Abk.)")


@dataclass(frozen=True)
class Net:
    a: tuple          # (5,) Grundfahrzeit je Kante
    b: tuple          # (5,) Zuschlag je Lkw auf der Kante
    n: int


@dataclass(frozen=True)
class Toll:
    mode: str = "none"
    lam: float = 1.0      # Faktor der Grenzkosten-Maut
    tau: float = 0.0      # feste Maut auf der Abkürzung in Minuten


NO_TOLL = Toll()


def classic(n, c_rel=1.0, e_rel=0.0, b=C.CLASSIC_B):
    """Klassisches Braess-Netz: s→A und B→t lastabhängig (b je Lkw), A→t und s→B konstant c = c_rel * b * n, Abkürzung A→B konstant e = e_rel * b * n."""
    c, e = c_rel * b * n, e_rel * b * n
    return Net((0.0, c, c, 0.0, e), (b, 0.0, 0.0, b, 0.0), n)


def edge_loads(net, counts):
    counts = np.asarray(counts, dtype=float)
    loads = np.zeros(5)
    for p, path in enumerate(PATHS):
        for e in path:
            loads[e] += counts[p]
    return loads


def edge_costs(net, counts):
    return np.asarray(net.a) + np.asarray(net.b) * edge_loads(net, counts)


def path_costs(net, counts):
    ec = edge_costs(net, counts)
    return np.array([sum(ec[e] for e in path) for path in PATHS])


def path_toll(net, counts, q, toll):
    """Maut, die ein Lkw auf Weg q bei den Lasten `counts` zahlt (der Lkw selbst ist in `counts` enthalten)."""
    if toll.mode == "none":
        return 0.0
    if toll.mode == "marginal":
        loads = edge_loads(net, counts)
        return float(toll.lam * sum(net.b[e] * (loads[e] - 1.0) for e in PATHS[q]))
    if toll.mode == "shortcut":
        return float(toll.tau) if q == 2 else 0.0
    raise ValueError(toll.mode)


def path_tolls(net, counts, toll):
    return np.array([path_toll(net, counts, q, toll) for q in range(3)])


def social(net, counts):
    """Summe der Fahrzeiten aller Lkw (ohne Maut)."""
    return float(np.dot(counts, path_costs(net, counts)))


def revenue(net, counts, toll):
    """Summe der gezahlten Maut."""
    return float(sum(counts[q] * path_toll(net, counts, q, toll) for q in range(3) if counts[q] > 0))


def n_paths(shortcut):
    return 3 if shortcut else 2


def all_states(n, shortcut=True):
    if shortcut:
        return [(n1, n2, n - n1 - n2) for n1 in range(n + 1) for n2 in range(n + 1 - n1)]
    return [(n1, n - n1, 0) for n1 in range(n + 1)]


def is_equilibrium(net, counts, toll=NO_TOLL, shortcut=True):
    """Kein Lkw verbessert seine wahrgenommenen Kosten (Fahrzeit + Maut) strikt durch einen Alleingang auf einen anderen erlaubten Weg (direkt aus der Definition)."""
    counts = list(counts)
    cur = path_costs(net, counts)
    for p in range(3):
        if counts[p] == 0:
            continue
        cur_cost = cur[p] + path_toll(net, counts, p, toll)
        for q in range(n_paths(shortcut)):
            if q == p:
                continue
            moved = counts.copy()
            moved[p] -= 1
            moved[q] += 1
            if path_costs(net, moved)[q] + path_toll(net, moved, q, toll) < cur_cost - C.EPS:
                return False
    return True


def equilibria(net, toll=NO_TOLL, shortcut=True):
    return [s for s in all_states(net.n, shortcut) if is_equilibrium(net, s, toll, shortcut)]


def optimum(net, shortcut=True):
    states = all_states(net.n, shortcut)
    costs = [social(net, s) for s in states]
    k = int(np.argmin(costs))
    return states[k], costs[k]


def random_assignment(n, shortcut, seed):
    return np.random.default_rng(seed).integers(0, n_paths(shortcut), size=n)


def counts_of(assign):
    return tuple(int(x) for x in np.bincount(assign, minlength=3))


@dataclass
class Run:
    states: list = field(default_factory=list)     # Zuordnung (Weg je Lkw) nach jedem Zug, 0 = Start
    moves: list = field(default_factory=list)      # (Lkw, von, nach)

    @property
    def final(self):
        return self.states[-1]


def best_move(net, assign, i, toll=NO_TOLL, shortcut=True):
    """Bester Weg für Lkw i (Fahrzeit + Maut) bei unveränderten anderen; bei Gleichstand bleibt er, sonst kleinster Index."""
    counts = list(counts_of(assign))
    p = int(assign[i])
    best, best_cost = p, path_costs(net, counts)[p] + path_toll(net, counts, p, toll)
    for q in range(n_paths(shortcut)):
        if q == p:
            continue
        moved = counts.copy()
        moved[p] -= 1
        moved[q] += 1
        c = path_costs(net, moved)[q] + path_toll(net, moved, q, toll)
        if c < best_cost - C.EPS:
            best, best_cost = q, c
    return best


def run_sequential(net, start, toll=NO_TOLL, shortcut=True, order="index", seed=0):
    rng = np.random.default_rng(seed)
    cur = np.array(start, dtype=np.int64)
    run = Run([cur.copy()])
    while True:
        moved = False
        idx = list(range(net.n)) if order == "index" else [int(x) for x in rng.permutation(net.n)]
        for i in idx:
            q = best_move(net, cur, i, toll, shortcut)
            if q != cur[i]:
                run.moves.append((i, int(cur[i]), q))
                cur[i] = q
                run.states.append(cur.copy())
                moved = True
        if not moved:
            return run
