"""Torwahl-Vehikel mit Maut: Vehikel wortgleich zu nash-demo, Aufzählung gegen eine skalare Definition, exaktes Potenzial, einheitliche Lkw -> Optimum."""

import itertools

import numpy as np
import pytest

import maut_gates as Gt


def state_arrays(inst, assign):
    loads = np.bincount(assign, weights=inst.w, minlength=inst.m)
    counts = np.bincount(assign, minlength=inst.m).astype(float)
    return loads, counts


def social(inst, assign):
    loads, counts = state_arrays(inst, assign)
    return float((counts * (inst.a + inst.b * loads)).sum())


def perceived(inst, assign, i, lam):
    loads, counts = state_arrays(inst, assign)
    g = assign[i]
    return inst.a[g] + inst.b[g] * loads[g] + lam * inst.b[g] * inst.w[i] * (counts[g] - 1.0)


def is_ne(inst, assign, lam):
    for i in range(inst.n):
        cur = perceived(inst, assign, i, lam)
        for g in range(inst.m):
            if g == assign[i]:
                continue
            moved = assign.copy()
            moved[i] = g
            if perceived(inst, moved, i, lam) < cur - 1e-9:
                return False
    return True


def test_matches_nash_demo_on_the_default_instance_without_toll():
    """Zahlen aus nash-demo (Seed 35, 12 Lkw, 3 Tore, gemischt): Optimum 156,2; Gleichgewichte 164,9 bis 166,6 min."""
    r = Gt.analyse(Gt.generate(12, 3, "mixed", 35), 0.0)
    assert r["n_ne"] == 2915 and abs(r["opt_cost"] - 156.2) < 0.05
    assert abs(r["ne_cost_min"] - 164.9) < 0.05 and abs(r["ne_cost_max"] - 166.6) < 0.05
    assert r["n_tne"] == r["n_ne"] and r["tne_cost_max"] == r["ne_cost_max"]


def test_uniform_mode_has_the_same_gates_as_mixed_and_errors():
    mixed, uniform = Gt.generate(12, 3, "mixed", 9), Gt.generate(12, 3, "uniform", 9)
    assert np.array_equal(mixed.a, uniform.a) and np.array_equal(mixed.b, uniform.b) and np.all(uniform.w == 1.0)
    with pytest.raises(ValueError):
        Gt.generate(4, 2, "bogus", 0)
    with pytest.raises(ValueError):
        Gt.analyse(Gt.generate(40, 6, "mixed", 0))


@pytest.mark.parametrize("lam", [0.0, 0.5, 1.0, 2.0])
@pytest.mark.parametrize("seed", range(4))
def test_enumeration_agrees_with_the_scalar_definition(seed, lam):
    inst = Gt.generate(5, 3, "mixed", seed)
    res = Gt.analyse(inst, lam)
    states = [np.array(a) for a in itertools.product(range(3), repeat=5)]
    costs = [social(inst, a) for a in states]
    tolled = [c for a, c in zip(states, costs) if is_ne(inst, a, lam)]
    free = [c for a, c in zip(states, costs) if is_ne(inst, a, 0.0)]
    assert res["n_tne"] == len(tolled) and res["n_ne"] == len(free)
    assert res["opt_cost"] == pytest.approx(min(costs)) and res["tne_cost_max"] == pytest.approx(max(tolled)) and res["tne_cost_min"] == pytest.approx(min(tolled))
    assert res["ne_cost_max"] == pytest.approx(max(free))


def test_marginal_toll_makes_social_cost_an_exact_potential():
    """Wechselt ein Lkw das Tor, ändern sich (Wartezeit + Maut) des Wechslers um genau die Änderung der Summe der Wartezeiten - auch bei verschieden großen Lkw."""
    rng = np.random.default_rng(2)
    for _ in range(300):
        inst = Gt.generate(int(rng.integers(3, 9)), int(rng.integers(2, 5)), "mixed", int(rng.integers(0, 10 ** 6)))
        assign = rng.integers(0, inst.m, size=inst.n)
        i, g = int(rng.integers(inst.n)), int(rng.integers(inst.m))
        moved = assign.copy()
        moved[i] = g
        d_own = perceived(inst, moved, i, 1.0) - perceived(inst, assign, i, 1.0)
        assert d_own == pytest.approx(social(inst, moved) - social(inst, assign), abs=1e-9)


@pytest.mark.parametrize("seed", range(10))
def test_uniform_sizes_every_toll_equilibrium_is_optimal(seed):
    r = Gt.analyse(Gt.generate(6, 3, "uniform", seed), 1.0)
    assert r["tne_cost_max"] == pytest.approx(r["opt_cost"]) and r["tne_cost_min"] == pytest.approx(r["opt_cost"])


@pytest.mark.parametrize("seed", range(15))
def test_the_optimum_is_always_a_toll_equilibrium_and_poa_is_at_least_one(seed):
    inst = Gt.generate(6, 3, "mixed", seed)
    r = Gt.analyse(inst, 1.0)
    assert r["opt_is_tne"] and Gt.poa_tolled(inst) >= 1.0 - 1e-12 and Gt.poa_free(inst) >= 1.0 - 1e-12


def test_toll_never_makes_the_worst_equilibrium_worse_in_a_uniform_instance():
    for seed in range(20):
        inst = Gt.generate(6, 3, "uniform", seed)
        assert Gt.poa_tolled(inst) <= Gt.poa_free(inst) + 1e-12
