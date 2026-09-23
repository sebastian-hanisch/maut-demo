"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (Standardmuster des Portfolios, vgl. nash_presets.py / poa_presets.py)."""

import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import maut_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None


def _choice(options):
    def cast(value):
        value = str(value)
        if value not in options:
            raise ValueError(value)
        return value
    return cast


SETTING_SPECS = {
    "n_slider": SettingSpec("n", int, C.DEFAULT_N, C.N_MIN, C.N_MAX),
    "crel_slider": SettingSpec("c", float, C.DEFAULT_CREL, C.CREL_MIN, C.CREL_MAX),
    "erel_slider": SettingSpec("e", float, C.DEFAULT_EREL, C.EREL_MIN, C.EREL_MAX),
    "mode_select": SettingSpec("toll", _choice(C.TOLL_MODES), "marginal"),
    "lam_slider": SettingSpec("lam", float, C.DEFAULT_LAM, C.LAM_MIN, C.LAM_MAX),
    "tau_slider": SettingSpec("tau", float, C.DEFAULT_TAU, C.TAU_MIN, C.TAU_MAX),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, 0, C.SEED_MAX),
}
PRESET_KEYS = {"n": "n_slider", "c_rel": "crel_slider", "e_rel": "erel_slider", "mode": "mode_select", "lam": "lam_slider", "tau_rel": "tau_slider", "seed": "seed_input"}
# Regler, die je nach Maut-Art ausgeblendet sind: Streamlit löscht ihren Zustand, sobald sie nicht gezeichnet werden - der letzte Wert bleibt hier erhalten
KEPT = {"lam_slider": "_kept_lam_slider", "tau_slider": "_kept_tau_slider"}
STEPS = {"n_slider": C.N_STEP, "crel_slider": C.CREL_STEP, "erel_slider": C.EREL_STEP, "lam_slider": C.LAM_STEP, "tau_slider": C.TAU_STEP}


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = st.session_state.get(KEPT[state_key], spec.default) if state_key in KEPT else spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if isinstance(value, float) and not math.isfinite(value):
                    continue
                if spec.lo is not None:
                    value = max(spec.lo, value)
                if spec.hi is not None:
                    value = min(spec.hi, value)
                st.session_state[state_key] = value
                if state_key in KEPT:
                    st.session_state[KEPT[state_key]] = value
            except (ValueError, TypeError):
                pass
    for key, step in STEPS.items():
        if key in st.session_state:
            spec = SETTING_SPECS[key]
            snapped = spec.lo + round((st.session_state[key] - spec.lo) / step) * step
            snapped = min(spec.hi, max(spec.lo, snapped))    # Rundungs-Artefakte nie über hi/unter lo lassen
            st.session_state[key] = int(snapped) if isinstance(spec.default, int) else round(snapped, 10)
            if key in KEPT:
                st.session_state[KEPT[key]] = st.session_state[key]
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][key]
        if state_key in KEPT:
            st.session_state[KEPT[state_key]] = C.PRESETS[name][key]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(0, C.SEED_MAX)
