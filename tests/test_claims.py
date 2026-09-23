"""Jede im README/PRESET_HELP/App genannte Zahl wird hier nachgerechnet - keine Behauptung ohne Test.

Netz-Läufe sind diskret (ganzzahlige Züge, Gleichstände mit Toleranz), also robust gegen Fließkomma-Rundung. Mehr-Instanzen-Zahlen (Torwahl-Instanzen, Suche)
bekommen großzügige Bänder (feedback_ci_platform_robust_tests / feedback_ci_unpinned_numeric_asserts)."""

import pytest

import maut_constants as C
import maut_evaluation as E
import maut_gates as Gt
import maut_network as N


def _preset(name):
    return E.analyse(E.Settings(**C.PRESETS[name]))


def _final(a):
    return N.counts_of(a.run.final)


# --- PRESET_HELP: Einzelläufe mit ganzzahligen Zügen -----------------------------------------------------------------------------------------


def test_standardfall_numbers():
    a = _preset("Standardfall (Grenzkosten-Maut)")
    assert len(a.run.moves) == 6 and _final(a) == (6, 6, 0) and a.eq_toll == [(6, 6, 0)]
    assert a.time_history()[-1] == pytest.approx(9.0) and a.toll_per_truck(_final(a)) == pytest.approx(2.5)
    assert a.worst(a.eq_free)[1] == pytest.approx(12.0) and a.opt[1] / a.n == pytest.approx(9.0)
    assert a.worst(a.eq_toll)[1] + a.toll_per_truck(a.worst(a.eq_toll)[0]) == pytest.approx(11.5)


def test_keine_maut_numbers():
    a = _preset("Keine Maut")
    assert len(a.run.moves) == 4 and _final(a) == (1, 1, 10) and a.time_history()[-1] == pytest.approx(11.08, abs=0.005)
    assert a.worst(a.eq_free)[1] == pytest.approx(12.0) and a.worst(a.eq_free)[0] == (0, 0, 12)


def test_feste_maut_numbers():
    a = _preset("Feste Maut nur auf der Abkürzung")
    assert len(a.run.moves) == 4 and _final(a) == (5, 5, 2) and a.time_history()[-1] == pytest.approx(9.08, abs=0.005)
    assert a.toll_per_truck(_final(a)) == pytest.approx(0.4) and a.toll.tau == pytest.approx(2.4)


def test_zu_niedrig_numbers():
    a = _preset("Maut zu niedrig (Faktor 0,5)")
    assert _final(a) == (4, 4, 4) and a.time_history()[-1] == pytest.approx(9.33, abs=0.005) and a.toll_per_truck(_final(a)) == pytest.approx(2.33, abs=0.005)


def test_ohne_nutzen_numbers():
    a = _preset("Maut ohne Nutzen (c = 2,0)")
    assert _final(a) == (0, 0, 12) and a.time_history()[-1] == pytest.approx(12.0) and a.toll_per_truck(_final(a)) == pytest.approx(11.0)
    assert a.worst(a.eq_free)[1] == pytest.approx(12.0) and a.opt[1] / a.n == pytest.approx(12.0)


def test_grosse_instanz_numbers():
    a = _preset("Große Instanz (40 Lkw)")
    assert len(a.run.moves) == 18 and _final(a) == (20, 20, 0) and a.time_history()[-1] == pytest.approx(30.0)
    assert a.toll_per_truck(_final(a)) == pytest.approx(9.5) and a.worst(a.eq_free)[1] == pytest.approx(40.0)


# --- Experiment 1: wer gewinnt? (exakt aufgezählt) -----------------------------------------------------------------------------------------


def test_marginal_toll_reaches_the_optimum_for_every_umweg_time_but_seldom_pays_off():
    rows = E.winners_experiment()
    assert all(r["toll_time"] == pytest.approx(r["opt_time"]) for r in rows)
    faster = [r["c_rel"] for r in rows if r["toll_time"] < r["free_time"] - 1e-9]
    assert min(faster) == pytest.approx(0.55) and max(faster) == pytest.approx(1.9)
    net_better = [r["c_rel"] for r in rows if r["toll_time"] + r["toll_paid"] < r["free_time"] - 1e-9]
    assert net_better == [pytest.approx(1.0)] and len(rows) == 36
    at_1 = next(r for r in rows if r["c_rel"] == pytest.approx(1.0))
    assert (at_1["free_time"], at_1["toll_time"], at_1["toll_paid"]) == (pytest.approx(20.0), pytest.approx(15.0), pytest.approx(4.5))
    at_2 = next(r for r in rows if r["c_rel"] == pytest.approx(2.0))
    assert at_2["free_time"] == pytest.approx(at_2["toll_time"]) and at_2["toll_paid"] == pytest.approx(19.0)


# --- Experiment 2: Mauthöhe --------------------------------------------------------------------------------------------------------------------


def test_marginal_toll_level_sweep():
    rows = {r["lam"]: r for r in E.lambda_experiment()}
    assert rows[0.0]["time"] == pytest.approx(20.0) and rows[0.0]["opt_time"] == pytest.approx(15.0)
    assert rows[0.5]["time"] / rows[0.5]["opt_time"] - 1 == pytest.approx(0.03, abs=0.001)
    assert all(rows[l]["time"] == pytest.approx(15.0) for l in (1.0, 1.5, 2.0, 3.0))
    assert rows[0.75]["time"] > 15.0 + 1e-9
    assert rows[1.0]["toll_paid"] == pytest.approx(4.5) and rows[3.0]["toll_paid"] == pytest.approx(13.5)


def test_shortcut_toll_sweep_and_the_revenue_hump():
    rows = {r["tau_rel"]: r for r in E.shortcut_toll_experiment()}
    assert rows[0.0]["time"] == pytest.approx(20.0)
    assert rows[0.45]["time"] > 15.0 + 1e-9 and rows[0.5]["time"] == pytest.approx(15.0) and rows[0.5]["toll_paid"] == pytest.approx(0.0)
    top = max(rows.values(), key=lambda r: r["toll_paid"])
    assert top["tau_rel"] == pytest.approx(0.25) and top["toll_paid"] == pytest.approx(1.25) and top["time"] / top["opt_time"] - 1 == pytest.approx(0.083, abs=0.001)
    times = [rows[t]["time"] for t in sorted(rows)]
    assert all(y <= x + 1e-9 for x, y in zip(times, times[1:]))          # mehr Maut auf der Abkürzung verschlechtert die Fahrzeit nie


# --- Experiment 3: Torwahl (Bänder) ------------------------------------------------------------------------------------------------------------


def test_uniform_sizes_toll_makes_every_equilibrium_optimal():
    r = E.gates_toll_experiment("uniform")
    assert r["share_exact"] == 1.0 and r["tolled_max"] == pytest.approx(1.0) and r["opt_is_toll_ne"] == 1.0
    assert 1.01 < r["free_mean"] < 1.05 and r["free_max"] < 1.3


def test_mixed_sizes_toll_helps_only_a_little():
    r = E.gates_toll_experiment("mixed")
    assert r["opt_is_toll_ne"] == 1.0 and 1.03 < r["free_mean"] < 1.09 and 1.02 < r["tolled_mean"] < r["free_mean"] - 0.003
    assert r["tolled_max"] < r["free_max"] and r["share_exact"] < 0.15 and 1.5 < r["toll_per_truck_mean"] < 4.5


def test_targeted_search_with_toll_stays_below_the_search_without_toll():
    free, tolled = E.gates_toll_search(True, lam=0.0), E.gates_toll_search(True, lam=1.0)
    assert 1.45 < free["best"] < 1.9 and 1.15 < tolled["best"] < free["best"] - 0.1
    assert E.gates_toll_search(False, lam=1.0)["best"] == pytest.approx(1.0)


def test_default_torwahl_instance_matches_nash_demo():
    r = Gt.analyse(Gt.generate(12, 3, "mixed", 35), 0.0)
    assert r["n_ne"] == 2915
