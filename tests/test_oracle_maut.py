"""Unabhängige Orakel (anderer Rechenweg als der Demo-Code): Gleichgewichte des Braess-Netzes und der Torwahl in exakter Bruchrechnung bzw. reinen Schleifen über ALLE Zuordnungen je Lkw
(keine Zähltupel, keine Vektorisierung), Optimum und Einnahmen aus der Definition, Zähltupel-Rechnung mit Brüchen für den Wer-gewinnt-Lauf, exaktes Potenzial je Alleingang, erneute
Bewertung der von der gezielten Suche gefundenen Instanz."""

import itertools
from fractions import Fraction as Fr

import numpy as np
import pytest

import maut_constants as C
import maut_evaluation as ev
import maut_gates as gt
import maut_network as net_

PATHS = ((0, 1), (2, 3), (0, 4, 3))


def _loads(assign):
    loads = [0] * 5
    for p in assign:
        for e in PATHS[p]:
            loads[e] += 1
    return loads


def _cost(a, b, assign, i, p, mode, lam, tau):
    moved = list(assign)
    moved[i] = p
    loads = _loads(moved)
    c = sum(a[e] + b[e] * loads[e] for e in PATHS[p])
    if mode == "marginal":
        c += lam * sum(b[e] * (loads[e] - 1) for e in PATHS[p])
    elif mode == "shortcut" and p == 2:
        c += tau
    return c


@pytest.mark.parametrize("seed", range(18))
def test_braess_equilibria_equal_exact_per_truck_enumeration(seed):
    rng = np.random.default_rng(seed)
    n, mode = int(rng.integers(2, 7)), ("none", "marginal", "shortcut")[seed % 3]
    c_rel, e_rel, lam, tau_rel = Fr(int(rng.integers(5, 41)), 20), Fr(int(rng.integers(0, 11)), 20), Fr(int(rng.integers(0, 7)), 2), Fr(int(rng.integers(0, 13)), 20)
    shortcut = seed % 5 != 4
    net = net_.classic(n, float(c_rel), float(e_rel))
    b = Fr(1, 2)
    exact_a, exact_b = (Fr(0), c_rel * b * n, c_rel * b * n, Fr(0), e_rel * b * n), (b, Fr(0), Fr(0), b, Fr(0))
    tau = tau_rel * b * n
    ref = set()
    for assign in itertools.product(range(3 if shortcut else 2), repeat=n):
        stable = all(_cost(exact_a, exact_b, assign, i, p, mode, lam, tau) <= min(_cost(exact_a, exact_b, assign, i, q, mode, lam, tau) for q in range(3 if shortcut else 2)) for i, p in enumerate(assign))
        if stable:
            ref.add(tuple(int(x) for x in np.bincount(assign, minlength=3)))
    toll = net_.Toll(mode, float(lam), float(tau))
    assert set(net_.equilibria(net, toll, shortcut)) == ref
    social = {s: sum(_cost(exact_a, exact_b, [p for p in range(3) for _ in range(s[p])], i, p, "none", 0, 0) for i, p in enumerate([p for p in range(3) for _ in range(s[p])])) for s in net_.all_states(n, shortcut)}
    assert net_.optimum(net, shortcut)[1] == pytest.approx(float(min(social.values())))
    for s, val in social.items():
        assert net_.social(net, s) == pytest.approx(float(val))
        assign = [p for p in range(3) for _ in range(s[p])]
        assert net_.revenue(net, s, toll) == pytest.approx(float(sum(_cost(exact_a, exact_b, assign, i, p, mode, lam, tau) - _cost(exact_a, exact_b, assign, i, p, "none", 0, 0) for i, p in enumerate(assign))))


def _counts_equilibria(n, c_rel, mode, lam=Fr(1), tau=Fr(0)):
    b, c = Fr(1, 2), c_rel * Fr(1, 2) * n
    a, bb = [Fr(0), c, c, Fr(0), Fr(0)], [b, 0, 0, b, 0]

    def times(cnt):
        loads = [sum(cnt[p] for p in range(3) if e in PATHS[p]) for e in range(5)]
        t = [sum(a[e] + bb[e] * loads[e] for e in PATHS[p]) for p in range(3)]
        tl = [sum(lam * bb[e] * (loads[e] - 1) for e in PATHS[p]) for p in range(3)] if mode == "marginal" else [Fr(0), Fr(0), tau if mode == "shortcut" else Fr(0)]
        return t, tl

    out = []
    for n1 in range(n + 1):
        for n2 in range(n + 1 - n1):
            cnt = [n1, n2, n - n1 - n2]
            t, tl = times(cnt)
            if all(not (times([cnt[r] + (r == q) - (r == p) for r in range(3)])[0][q] + times([cnt[r] + (r == q) - (r == p) for r in range(3)])[1][q] < t[p] + tl[p]) for p in range(3) if cnt[p] for q in range(3) if q != p):
                out.append((t, tl, cnt))
    return out


@pytest.mark.parametrize("c_rel", [Fr(1, 2), Fr(19, 20), Fr(1), Fr(3, 2), Fr(2)])
def test_winners_row_equals_exact_count_enumeration_and_marginal_toll_reaches_the_optimum(c_rel):
    n = 20
    row = ev.winners_experiment(n, (float(c_rel),))[0]
    free, toll = _counts_equilibria(n, c_rel, "none"), _counts_equilibria(n, c_rel, "marginal")
    social = lambda t, cnt: sum(cnt[p] * t[p] for p in range(3))
    assert row["free_time"] == pytest.approx(float(max(social(t, c) for t, _tl, c in free) / n))
    assert row["toll_time"] == pytest.approx(float(max(social(t, c) for t, _tl, c in toll) / n))
    worst = max(toll, key=lambda r: social(r[0], r[2]))
    assert row["toll_paid"] == pytest.approx(float(sum(worst[2][p] * worst[1][p] for p in range(3)) / n))
    assert row["toll_time"] == pytest.approx(row["opt_time"])


def _wait(inst, s, i, h=None):
    h = s[i] if h is None else h
    return inst.a[h] + inst.b[h] * (inst.w[i] + sum(inst.w[j] for j in range(inst.n) if j != i and s[j] == h))


def _toll(inst, s, i, lam, h=None):
    h = s[i] if h is None else h
    return lam * inst.b[h] * inst.w[i] * sum(1 for j in range(inst.n) if j != i and s[j] == h)


def _gate_reference(inst, lam):
    soc, free, tolled = {}, [], []
    for s in itertools.product(range(inst.m), repeat=inst.n):
        soc[s] = sum(_wait(inst, s, i) for i in range(inst.n))
        ok_f = ok_t = True
        for i in range(inst.n):
            for h in range(inst.m):
                if h == s[i]:
                    continue
                s2 = list(s)
                s2[i] = h
                ok_f &= not (_wait(inst, s2, i) < _wait(inst, s, i) - 1e-9)
                ok_t &= not (_wait(inst, s2, i) + _toll(inst, s2, i, lam) < _wait(inst, s, i) + _toll(inst, s, i, lam) - 1e-9)
        if ok_f:
            free.append(s)
        if ok_t:
            tolled.append(s)
    return min(soc.values()), free, tolled, soc


@pytest.mark.parametrize("seed", range(16))
def test_gate_enumeration_and_potential_equal_loop_definitions(seed):
    rng = np.random.default_rng(seed)
    inst = gt.generate(int(rng.integers(2, 6)), int(rng.integers(2, 4)), ("mixed", "uniform")[seed % 2], seed + 3000)
    lam = (0.0, 1.0, 0.5, 2.0)[seed % 4]
    r = gt.analyse(inst, lam)
    opt, free, tolled, soc = _gate_reference(inst, lam)
    assert r["opt_cost"] == pytest.approx(opt)
    assert (r["n_ne"], r["n_tne"]) == (len(free), len(tolled))
    assert r["ne_cost_max"] == pytest.approx(max(soc[s] for s in free)) and r["tne_cost_max"] == pytest.approx(max(soc[s] for s in tolled))
    if lam == 1.0:
        assert r["opt_is_tne"] and any(abs(soc[s] - opt) < 1e-9 for s in tolled)
        for _ in range(15):
            s, h, i = tuple(int(x) for x in rng.integers(0, inst.m, inst.n)), int(rng.integers(0, inst.m)), int(rng.integers(0, inst.n))
            s2 = list(s)
            s2[i] = h
            mover = _wait(inst, s2, i) + _toll(inst, s2, i, 1.0) - _wait(inst, s, i) - _toll(inst, s, i, 1.0)
            assert mover == pytest.approx(sum(_wait(inst, s2, j) for j in range(inst.n)) - sum(_wait(inst, s, j) for j in range(inst.n)))


def test_targeted_search_best_value_is_reproduced_by_loop_evaluation():
    s = ev.gates_toll_search(True, starts=15, steps=60, lam=1.0)
    opt, _free, tolled, soc = _gate_reference(s["instance"], 1.0)
    assert max(soc[x] for x in tolled) / opt == pytest.approx(s["best"])
    assert all(x <= y + 1e-12 for x, y in zip(s["history"], s["history"][1:]))
