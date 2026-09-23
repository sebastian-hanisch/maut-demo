"""Plotly-Abbildungen der Maut-Demo. Achsen sind gesperrt (fixedrange)."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import maut_constants as C
import maut_network as N

LINE_COLOR = "#4c78a8"
REF_COLOR = "#7f7f7f"
GOOD = "#54a24b"
BAD = "#e45756"
WARN = "#f58518"
NODE_XY = {"s": (0.0, 0.5), "A": (1.0, 1.0), "B": (1.0, 0.0), "t": (2.0, 0.5)}
EDGE_NODES = (("s", "A"), ("A", "t"), ("s", "B"), ("B", "t"), ("A", "B"))


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.2), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _de(x, digits=1):
    return f"{x:.{digits}f}".replace(".", ",")


def build_network(net, counts, toll):
    """Das Netz mit Last, Fahrzeit und Maut je Kante; Linienstärke = Last. Bei fester Maut trägt die Abkürzung das Preisschild."""
    loads = N.edge_loads(net, counts)
    costs = N.edge_costs(net, counts)
    fig = go.Figure()
    top = max(1.0, float(max(loads)))
    for e, (u, v) in enumerate(EDGE_NODES):
        (x0, y0), (x1, y1) = NODE_XY[u], NODE_XY[v]
        width = 2 + 10 * loads[e] / top
        fig.add_trace(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", line=dict(color=LINE_COLOR, width=width), hoverinfo="skip", showlegend=False))
        label = f"{loads[e]:g} Lkw · {costs[e]:.1f} min"
        if toll.mode == "marginal" and net.b[e] > 0:
            label += f"<br>Maut {_de(toll.lam * net.b[e] * max(loads[e] - 1.0, 0.0))} min je Lkw"
        if toll.mode == "shortcut" and e == 4:
            label += f"<br>Maut {_de(toll.tau)} min je Lkw"
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = {0: (-0.27, 0.17), 1: (0.27, 0.17), 2: (-0.27, -0.17), 3: (0.27, -0.17), 4: (0.27, 0.0)}[e]
        fig.add_annotation(x=mx + dx, y=my + dy, text=f"<b>{N.EDGES[e]}</b><br>{label}", showarrow=False, font=dict(size=11))
    for name, (x, y) in NODE_XY.items():
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", text=[name], textposition="middle center", marker=dict(size=34, color="white", line=dict(color="#14233B", width=2)),
                                 hoverinfo="skip", showlegend=False))
    fig.update_xaxes(visible=False, range=[-0.7, 2.7])
    fig.update_yaxes(visible=False, range=[-0.3, 1.3])
    return _base(fig, 330)


def build_time_curve(history, upto=None, reference=None, reference_label="Optimum"):
    xs = list(range(len(history)))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=history, mode="lines+markers", line=dict(color=BAD, width=2.5), name="Mittlere Fahrzeit"))
    if reference is not None:
        fig.add_hline(y=reference, line=dict(color=REF_COLOR, dash="dot"), annotation_text=reference_label, annotation_position="bottom right")
    if upto is not None:
        fig.add_vline(x=upto, line=dict(color=REF_COLOR, dash="dot"))
    fig.update_xaxes(title_text="Zug (0 = Start)", dtick=1 if len(xs) < 16 else None)
    fig.update_yaxes(title_text="Mittlere Fahrzeit je Lkw (min)")
    fig.update_layout(showlegend=False)
    return _base(fig, 300)


def build_winners(rows):
    """Fahrzeit je Lkw im schlechtesten Gleichgewicht ohne Maut, mit Maut, und mit Maut plus gezahlter Maut; dazu das Optimum."""
    xs = [r["c_rel"] for r in rows]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=[r["free_time"] for r in rows], mode="lines", name="Fahrzeit ohne Maut", line=dict(color=BAD, width=2.5)))
    fig.add_trace(go.Scatter(x=xs, y=[r["toll_time"] for r in rows], mode="lines", name="Fahrzeit mit Maut (= Optimum)", line=dict(color=GOOD, width=2.5)))
    fig.add_trace(go.Scatter(x=xs, y=[r["toll_time"] + r["toll_paid"] for r in rows], mode="lines", name="Fahrzeit + gezahlte Maut", line=dict(color=WARN, width=2.5, dash="dash")))
    fig.update_xaxes(title_text="Umweg-Fahrzeit c / (b · n)")
    fig.update_yaxes(title_text="min je Lkw")
    return _base(fig, 340).update_layout(legend=dict(orientation="h", y=-0.3))


def build_toll_sweep(rows, x_key, x_title, reference_x=None):
    """Links: Fahrzeit im schlechtesten Gleichgewicht über der Mauthöhe (gepunktet: Optimum); rechts: gezahlte Maut je Lkw."""
    xs = [r[x_key] for r in rows]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Fahrzeit je Lkw", "Gezahlte Maut je Lkw"), horizontal_spacing=0.12)
    fig.add_trace(go.Scatter(x=xs, y=[r["time"] for r in rows], mode="lines+markers", line=dict(color=BAD, width=2.5), name="schlechtestes Gleichgewicht"), row=1, col=1)
    fig.add_trace(go.Scatter(x=xs, y=[r["opt_time"] for r in rows], mode="lines", line=dict(color=REF_COLOR, dash="dot", width=2), name="Optimum"), row=1, col=1)
    fig.add_trace(go.Scatter(x=xs, y=[r["toll_paid"] for r in rows], mode="lines+markers", line=dict(color=WARN, width=2.5), name="Maut je Lkw", showlegend=False), row=1, col=2)
    if reference_x is not None:
        fig.add_vline(x=reference_x, line=dict(color=GOOD, dash="dash"), row=1, col=1)
        fig.add_vline(x=reference_x, line=dict(color=GOOD, dash="dash"), row=1, col=2)
    fig.update_xaxes(title_text=x_title)
    fig.update_yaxes(title_text="min", row=1, col=1)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.3), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_gates_toll(res_mixed, res_uniform):
    """Verteilung des Preises der Anarchie über Zufallsinstanzen, ohne und mit Grenzkosten-Maut; links gemischte, rechts einheitliche Lkw-Größen."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Gemischte Größen", "Einheitliche Größen"), horizontal_spacing=0.1, shared_yaxes=True)
    bins = dict(start=1.0, end=1.3, size=0.01)
    for col, res in ((1, res_mixed), (2, res_uniform)):
        fig.add_trace(go.Histogram(x=res["free"], xbins=bins, name="ohne Maut", marker_color=BAD, opacity=0.7, showlegend=col == 1), row=1, col=col)
        fig.add_trace(go.Histogram(x=res["tolled"], xbins=bins, name="mit Grenzkosten-Maut", marker_color=GOOD, opacity=0.7, showlegend=col == 1), row=1, col=col)
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(title_text="Preis der Anarchie", range=[0.995, 1.2])
    fig.update_yaxes(title_text="Instanzen", row=1, col=1)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.3), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def build_search_pair(free, tolled):
    """Gezielte Suche nach der schlechtesten Torwahl-Instanz mit gemischten Größen: ohne Maut gegen mit Grenzkosten-Maut."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=free["history"], mode="lines", name="ohne Maut", line=dict(color=BAD, width=2.5)))
    fig.add_trace(go.Scatter(y=tolled["history"], mode="lines", name="mit Grenzkosten-Maut", line=dict(color=GOOD, width=2.5)))
    fig.add_trace(go.Scatter(x=[C.SEARCH_RANDOM_STARTS] * 2, y=[1.0, max(free["best"], tolled["best"]) * 1.03], mode="lines", name="ab hier gezielte Suche", line=dict(color="#b0b0b0", dash="dash", width=1.5)))
    fig.update_xaxes(title_text="Bewertete Instanzen", range=[0, len(free["history"])])
    fig.update_yaxes(title_text="Bester bisheriger Preis der Anarchie")
    return _base(fig, 340).update_layout(legend=dict(orientation="h", y=-0.3))
