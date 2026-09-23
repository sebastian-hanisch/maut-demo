"""Auswertung: Analyse eines Laufs und die Experimente - schnelle Parameter über Funktionsargumente."""

import numpy as np

import maut_constants as C
import maut_evaluation as E
import maut_network as N


def test_analyse_default_is_consistent():
    a = E.analyse(E.Settings())
    assert N.counts_of(a.run.final) in set(a.eq_toll)
    assert len(a.time_history()) == len(a.run.states) == len(a.run.moves) + 1
    assert a.opt[1] / a.n <= a.worst(a.eq_toll)[1] + 1e-9 <= a.worst(a.eq_free)[1] + 1e-9


def test_toll_from_settings_scales_the_shortcut_toll_with_b_and_n():
    s = E.Settings(n=20, mode="shortcut", tau_rel=0.4)
    assert s.toll() == N.Toll("shortcut", 1.0, 0.4 * C.CLASSIC_B * 20)


def test_no_toll_analysis_has_identical_equilibrium_sets_and_zero_revenue():
    a = E.analyse(E.Settings(mode="none"))
    assert a.eq_toll == a.eq_free and a.toll_per_truck(N.counts_of(a.run.final)) == 0.0


def test_winners_experiment_shape_and_invariants():
    rows = E.winners_experiment(n=8, c_rels=(0.5, 1.0, 2.0))
    assert [r["c_rel"] for r in rows] == [0.5, 1.0, 2.0]
    for r in rows:
        assert r["toll_time"] <= r["free_time"] + 1e-9 and r["toll_time"] >= r["opt_time"] - 1e-9 and r["toll_paid"] >= 0


def test_level_experiments_shape():
    rows = E.lambda_experiment(n=8, lams=(0.0, 1.0, 2.0))
    assert [r["lam"] for r in rows] == [0.0, 1.0, 2.0] and rows[0]["toll_paid"] == 0.0 and rows[1]["toll_paid"] <= rows[2]["toll_paid"]
    rows = E.shortcut_toll_experiment(n=8, tau_rels=(0.0, 0.5))
    assert rows[0]["toll_paid"] == 0.0 and rows[1]["time"] <= rows[0]["time"] + 1e-9


def test_gates_experiment_shapes_and_invariants():
    r = E.gates_toll_experiment("mixed", seeds=range(10))
    assert len(r["free"]) == len(r["tolled"]) == 10 and r["opt_is_toll_ne"] == 1.0 and np.all(r["tolled"] >= 1 - 1e-12)
    u = E.gates_toll_experiment("uniform", seeds=range(10))
    assert u["share_exact"] == 1.0 and u["tolled_max"] == 1.0


def test_gates_search_shape_and_determinism():
    s = E.gates_toll_search(True, starts=10, steps=15)
    assert len(s["history"]) == 25 and all(y >= x - 1e-12 for x, y in zip(s["history"], s["history"][1:]))
    assert s["best"] == s["history"][-1] >= s["random_best"]
    assert s["history"] == E.gates_toll_search(True, starts=10, steps=15)["history"]
    assert E.gates_toll_search(False, starts=10, steps=10)["best"] == 1.0
