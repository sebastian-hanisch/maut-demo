"""Vehikel "Torwahl" aus nash-demo (Erzeugung wortgleich) mit Maut: Tor g hat die Wartezeit a_g + b_g * Last, Lkw i hat Größe w_i, das Gütemaß ist die Summe der
Wartezeiten aller Lkw (jeder Lkw zählt einmal, wie in nash-demo).

Grenzkosten-Maut: ein Lkw i am Tor g zahlt lam * b_g * w_i * (Zahl der anderen Lkw an diesem Tor) - die Mehrwartezeit, die er den anderen aufbürdet.
Bei lam = 1 ist die Summe der Wartezeiten ein exaktes Potenzial des Spiels mit Maut: jeder Alleingang ändert (Wartezeit + Maut) des Wechslers um genau die Änderung der Summe."""

from dataclasses import dataclass

import numpy as np

import maut_constants as C


@dataclass(frozen=True)
class Instance:
    a: np.ndarray      # (m,) Grundwartezeit
    b: np.ndarray      # (m,) Zuschlag je Ladungseinheit
    w: np.ndarray      # (n,) Lkw-Größe
    seed: int

    @property
    def n(self):
        return len(self.w)

    @property
    def m(self):
        return len(self.a)


def generate(n, m, size_mode="mixed", seed=0):
    rng = np.random.default_rng(seed)
    a = rng.uniform(C.A_MIN, C.A_MAX, size=m)
    b = rng.uniform(C.B_MIN, C.B_MAX, size=m)
    if size_mode == "mixed":
        w = rng.choice(C.SIZES, size=n, p=C.SIZE_PROBS).astype(float)
    elif size_mode == "uniform":
        rng.choice(C.SIZES, size=n, p=C.SIZE_PROBS)      # Ziehung verbrauchen: gleiche Tore wie im gemischten Modus
        w = np.ones(n)
    else:
        raise ValueError(size_mode)
    return Instance(a, b, w, int(seed))


def _all_states(inst):
    N = inst.m ** inst.n
    if N > C.ENUM_MAX_ASSIGNMENTS:
        raise ValueError("zu viele Zuordnungen für die Vollaufzählung")
    idx = np.arange(N, dtype=np.int64)
    A = np.empty((N, inst.n), dtype=np.int64)
    for i in range(inst.n):
        A[:, i] = idx % inst.m
        idx //= inst.m
    return A


def analyse(inst, lam=1.0):
    """Vollaufzählung: reine Gleichgewichte ohne Maut und mit Grenzkosten-Maut (Faktor lam), Optimum, Maut je Lkw im Gleichgewicht.
    Ein Gleichgewicht: kein Lkw verbessert (Wartezeit + Maut) strikt durch einen Alleingang - direkt aus der Definition."""
    A = _all_states(inst)
    N, n, m = len(A), inst.n, inst.m
    rows = np.arange(N)
    L = np.zeros((N, m))
    K = np.zeros((N, m))
    for i in range(n):
        L[rows, A[:, i]] += inst.w[i]
        K[rows, A[:, i]] += 1.0
    wait = inst.a[None, :] + inst.b[None, :] * L
    social = (K * wait).sum(axis=1)
    own = np.take_along_axis(wait, A, axis=1)
    toll_now = lam * inst.b[A] * inst.w[None, :] * (np.take_along_axis(K, A, axis=1) - 1.0)
    free = np.ones(N, dtype=bool)
    tolled = np.ones(N, dtype=bool)
    for i in range(n):
        Li, Ki = L.copy(), K.copy()
        Li[rows, A[:, i]] -= inst.w[i]
        Ki[rows, A[:, i]] -= 1.0
        dev_wait = inst.a[None, :] + inst.b[None, :] * (Li + inst.w[i])
        dev_toll = lam * inst.b[None, :] * inst.w[i] * Ki
        free &= own[:, i] <= dev_wait.min(axis=1) + C.EPS
        tolled &= own[:, i] + toll_now[:, i] <= (dev_wait + dev_toll).min(axis=1) + C.EPS
    ne_free, ne_toll = np.flatnonzero(free), np.flatnonzero(tolled)
    opt = float(social.min())
    toll_pt = toll_now.sum(axis=1) / n
    worst_toll_state = ne_toll[np.argmax(social[ne_toll])]
    return {
        "opt_cost": opt,
        "n_ne": int(len(ne_free)), "ne_cost_min": float(social[ne_free].min()), "ne_cost_max": float(social[ne_free].max()),
        "n_tne": int(len(ne_toll)), "tne_cost_min": float(social[ne_toll].min()), "tne_cost_max": float(social[ne_toll].max()),
        "opt_is_tne": bool(np.any(np.isclose(social[ne_toll], opt, atol=1e-9))),
        "toll_per_truck_worst": float(toll_pt[worst_toll_state]),
    }


def poa_free(inst):
    r = analyse(inst, 0.0)
    return r["ne_cost_max"] / r["opt_cost"]


def poa_tolled(inst, lam=1.0):
    """Schlechtestes Gleichgewicht mit Grenzkosten-Maut geteilt durch das Optimum (>= 1)."""
    r = analyse(inst, lam)
    return r["tne_cost_max"] / r["opt_cost"]
