"""Braess-Netz mit Maut: Handrechnung, exaktes Potenzial der Grenzkosten-Maut, Gleichgewichte gegen eine unabhängige Prüfung auf Einzel-Lkw-Ebene."""

import itertools

import numpy as np
import pytest

import maut_network as N

MARGINAL = N.Toll("marginal", 1.0, 0.0)


def hand_net():
    """4 Lkw, b = 1 auf s→A und B→t, Umwege c = 4, Abkürzung kostenlos."""
    return N.Net((0.0, 4.0, 4.0, 0.0, 0.0), (1.0, 0.0, 0.0, 1.0, 0.0), 4)


def test_hand_calculation_of_tolls_and_revenue():
    net = hand_net()
    assert list(N.path_tolls(net, (2, 2, 0), MARGINAL)) == [1.0, 1.0, 1.0 + 1.0]     # (Last - 1) je lastabhängiger Kante; Weg 3 bei Last 2 und 2 ohne den Wechsler
    assert N.revenue(net, (2, 2, 0), MARGINAL) == 4.0
    assert list(N.path_tolls(net, (0, 0, 4), MARGINAL)) == [3.0, 3.0, 6.0]
    assert N.revenue(net, (0, 0, 4), MARGINAL) == 24.0
    assert list(N.path_tolls(net, (2, 2, 0), N.Toll("shortcut", 1.0, 2.5))) == [0.0, 0.0, 2.5]
    assert list(N.path_tolls(net, (2, 2, 0), N.NO_TOLL)) == [0.0, 0.0, 0.0]


def test_hand_calculation_of_equilibria():
    net = hand_net()
    assert set(N.equilibria(net, N.NO_TOLL)) == {(0, 0, 4), (0, 1, 3), (1, 0, 3), (1, 1, 2)}
    assert N.equilibria(net, MARGINAL) == [(2, 2, 0)]
    assert N.social(net, (2, 2, 0)) == N.optimum(net)[1] == 24.0


def test_marginal_toll_makes_social_cost_an_exact_potential():
    """Wechselt ein Lkw von Weg p auf q, ändern sich (Fahrzeit + Maut) des Wechslers um genau die Änderung der Summe der Fahrzeiten."""
    rng = np.random.default_rng(1)
    for _ in range(300):
        n = int(rng.integers(4, 15))
        net = N.classic(n, float(rng.uniform(0.3, 2.0)), float(rng.uniform(0.0, 0.5)))
        counts = list(np.bincount(rng.integers(0, 3, size=n), minlength=3))
        p = int(rng.choice([q for q in range(3) if counts[q] > 0]))
        q = int(rng.choice([x for x in range(3) if x != p]))
        after = counts.copy()
        after[p] -= 1
        after[q] += 1
        d_own = (N.path_costs(net, after)[q] + N.path_toll(net, after, q, MARGINAL)) - (N.path_costs(net, counts)[p] + N.path_toll(net, counts, p, MARGINAL))
        assert d_own == pytest.approx(N.social(net, after) - N.social(net, counts), abs=1e-9)


def test_optimum_is_always_a_marginal_toll_equilibrium_and_all_equilibria_are_local_minima():
    for c in (0.25, 0.75, 1.0, 1.25, 1.5, 2.0):
        net = N.classic(12, c, 0.1)
        opt_state, opt_cost = N.optimum(net)
        eq = N.equilibria(net, MARGINAL)
        assert any(N.social(net, s) == pytest.approx(opt_cost) for s in eq)
        assert all(N.social(net, s) >= opt_cost - 1e-9 for s in eq)


def test_zero_factor_marginal_toll_equals_no_toll():
    net = N.classic(10, 1.0, 0.0)
    assert N.equilibria(net, N.Toll("marginal", 0.0, 0.0)) == N.equilibria(net, N.NO_TOLL)


def test_shortcut_toll_threshold_for_the_all_on_shortcut_equilibrium():
    """Alle auf der Abkürzung ist Gleichgewicht genau dann, wenn tau <= c - b*n - e (Handrechnung, Einheitslkw)."""
    n, b = 10, 0.5
    for c_rel, e_rel in ((1.4, 0.0), (1.4, 0.2), (1.0, 0.0), (1.2, 0.1)):
        net = N.classic(n, c_rel, e_rel)
        limit = c_rel * b * n - b * n - e_rel * b * n
        for tau in (limit - 0.5, limit, limit + 0.01, limit + 0.5):
            if tau < 0:
                continue
            assert N.is_equilibrium(net, (0, 0, n), N.Toll("shortcut", 1.0, tau)) == (tau <= limit + 1e-9)


@pytest.mark.parametrize("toll", [N.NO_TOLL, MARGINAL, N.Toll("marginal", 0.5, 0.0), N.Toll("shortcut", 1.0, 1.5)])
def test_counting_states_agree_with_per_truck_definition(toll):
    """Ein Zähltupel ist genau dann Gleichgewicht, wenn kein Lkw einer der 3^n erzeugenden Einzelzuordnungen einen strikt besseren Weg hat."""
    net = N.classic(5, 1.0, 0.0)
    eq = set(N.equilibria(net, toll))
    for assign in itertools.product(range(3), repeat=net.n):
        counts = N.counts_of(np.array(assign))
        stable = all(N.best_move(net, np.array(assign), i, toll) == assign[i] for i in range(net.n))
        assert stable == (counts in eq)


@pytest.mark.parametrize("toll", [N.NO_TOLL, MARGINAL, N.Toll("marginal", 2.0, 0.0), N.Toll("shortcut", 1.0, 2.0)])
@pytest.mark.parametrize("seed", range(6))
def test_best_response_ends_in_an_enumerated_equilibrium(seed, toll):
    net = N.classic(12, 0.6 + 0.2 * seed, 0.05 * (seed % 3))
    run = N.run_sequential(net, N.random_assignment(net.n, True, seed), toll, True, "random", seed)
    assert N.counts_of(run.final) in set(N.equilibria(net, toll))


def test_unknown_toll_mode_raises():
    with pytest.raises(ValueError):
        N.path_toll(hand_net(), (1, 1, 2), 0, N.Toll("bogus"))
