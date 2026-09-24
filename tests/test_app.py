"""AppTest-Rauchtests: Voreinstellung, jedes Preset, Zug-Slider, Abspielen ohne doppelte Schlüssel, Würfel-Knopf, Permalink-Grenzen, modusabhängige Regler,
Extremwerte, drei Experimente auf Abruf, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import maut_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=300)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def test_default_run_has_no_exception_and_shows_the_optimum_result():
    at = _run()
    _ok(at)
    assert at.metric and any("jedes Gleichgewicht ein Optimum" in s.value for s in at.success)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_button_runs(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert at.session_state["n_slider"] == p["n"] and at.session_state["mode_select"] == p["mode"]
    assert at.metric


def test_step_slider_runs_at_various_positions():
    at = _run()
    step = next(s for s in at.slider if s.key == "maut_step")
    step.set_value(0).run()
    _ok(at)
    step = next(s for s in at.slider if s.key == "maut_step")
    step.set_value(step.max).run()
    _ok(at)
    assert at.get("plotly_chart")


def test_play_runs_without_duplicate_keys():
    at = _run()
    next(b for b in at.button if b.label == "▶️ Abspielen").click().run()
    _ok(at)


def test_mode_dependent_controls_are_never_dead():
    at = _run()
    assert any(s.key == "lam_slider" for s in at.slider) and not any(s.key == "tau_slider" for s in at.slider)
    at = _run(mode_select="shortcut")
    assert any(s.key == "tau_slider" for s in at.slider) and not any(s.key == "lam_slider" for s in at.slider)
    at = _run(mode_select="none")
    assert not any(s.key in ("lam_slider", "tau_slider") for s in at.slider)


def test_verdict_switches_with_the_toll_and_the_umweg_time():
    assert any("jedes Gleichgewicht ein Optimum" in s.value for s in _run().success)
    assert any("Ohne Maut liegt" in i.value for i in _run(mode_select="none").info)
    assert any("nützt hier nichts" in w.value for w in _run(crel_slider=2.0).warning)
    assert any("nur teilweise" in w.value for w in _run(lam_slider=0.5).warning)


def test_dice_button_changes_the_seed():
    at = _run()
    old = at.session_state["seed_input"]
    next(b for b in at.button if b.label == "🎲 Neue Startzuordnung würfeln").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old


def test_permalink_values_are_clamped_and_snapped():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["n"] = "9999"
    at.query_params["lam"] = "9999"
    at.query_params["tau"] = "0.33"
    at.query_params["toll"] = "shortcut"
    at.run()
    _ok(at)
    assert at.session_state["n_slider"] == C.N_MAX and at.session_state["_kept_lam_slider"] == C.LAM_MAX      # lam ist im Modus "shortcut" ausgeblendet: der Wert liegt nur in KEPT
    assert abs(at.session_state["tau_slider"] - 0.35) < 1e-9 and at.session_state["mode_select"] == "shortcut"


@pytest.mark.parametrize("kw", [dict(n_slider=C.N_MIN), dict(n_slider=C.N_MAX), dict(crel_slider=C.CREL_MIN), dict(crel_slider=C.CREL_MAX), dict(erel_slider=C.EREL_MAX),
                                dict(lam_slider=C.LAM_MIN), dict(lam_slider=C.LAM_MAX), dict(mode_select="shortcut", tau_slider=C.TAU_MIN), dict(mode_select="shortcut", tau_slider=C.TAU_MAX)])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))


def test_winners_experiment_runs_on_demand(monkeypatch):
    monkeypatch.setattr(C, "WINNERS_N", 8)
    monkeypatch.setattr(C, "WINNERS_CRELS", (0.5, 1.0, 1.6))
    at = _run()
    next(b for b in at.button if b.key == "winners_start").click().run()
    _ok(at)
    assert at.session_state["winners_on"] and at.get("plotly_chart")


def test_levels_experiment_runs_on_demand(monkeypatch):
    monkeypatch.setattr(C, "WINNERS_N", 8)
    monkeypatch.setattr(C, "LAMBDAS", (0.0, 0.5, 1.0, 2.0))
    monkeypatch.setattr(C, "TAU_RELS", (0.0, 0.25, 0.5))
    at = _run()
    next(b for b in at.button if b.key == "levels_start").click().run()
    _ok(at)
    assert at.session_state["levels_on"]


def test_gates_experiment_runs_on_demand(monkeypatch):
    monkeypatch.setattr(C, "GATES_SEEDS", (1, 2, 3, 4))
    monkeypatch.setattr(C, "SEARCH_RANDOM_STARTS", 5)
    monkeypatch.setattr(C, "SEARCH_STEPS", 5)
    at = _run()
    next(b for b in at.button if b.key == "gates_start").click().run()
    _ok(at)
    assert at.session_state["gates_on"]


def test_footer_and_grenzen_are_present():
    at = _run()
    assert any("Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in c.value for c in at.caption)
    assert any("Wo die Annahmen enden" in s.value for s in at.subheader)
