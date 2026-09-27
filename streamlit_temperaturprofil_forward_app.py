"""Vorwärtssimulation eines räumlich einheitlich temperierten Körpers."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import colorsys
import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from matplotlib.figure import Figure

REPO = "https://github.com/dubbehendrik/temperaturprofil_forward"
DEFAULTS = dict(alpha=10.0, cp=900.0, A=0.1, m=1.0, T0=20.0, T_inf=100.0,
                t_end=600.0, dt=1.0, keep=False, unit="Sekunden", height=600,
                full_width=False, manual_axes=False, x_min=0.0, x_max=600.0,
                y_min=0.0, y_max=120.0)
PARAMS = ("alpha", "cp", "A", "m", "T0", "T_inf", "t_end", "dt")
MAX_POINTS = 20001
PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#8C6D00", "#6A3D9A"]


def validate(p):
    if not all(math.isfinite(p[k]) for k in PARAMS):
        raise ValueError("Bitte ausschließlich endliche Zahlen eingeben.")
    for k in ("cp", "A", "m", "t_end", "dt"):
        if p[k] <= 0:
            raise ValueError("cₚ, A, m, Endzeit und Zeitschritt müssen größer als null sein.")
    if p["alpha"] < 0:
        raise ValueError("α darf nicht negativ sein.")
    if min(p["T0"], p["T_inf"]) < -273.15:
        raise ValueError("Temperaturen dürfen nicht unter −273,15 °C liegen.")
    if p["t_end"] / p["dt"] > MAX_POINTS - 1:
        raise ValueError("Maximal 20.001 Stützstellen: Bitte den Zeitschritt erhöhen oder die Endzeit verkürzen.")


def simulate(p):
    validate(p)
    t = np.arange(math.ceil(p["t_end"] / p["dt"]), dtype=float) * p["dt"]
    t = np.append(t[t < p["t_end"]], p["t_end"])
    # Analytische Lösung; dt bestimmt nur die Abtastung, nicht die Lösungsgüte.
    rate = p["alpha"] * p["A"] / (p["m"] * p["cp"])
    temperature = p["T0"] + (p["T_inf"] - p["T0"]) * (-np.expm1(-rate * t))
    if not np.all(np.isfinite(temperature)):
        raise ValueError("Die Parameter führen zu einem numerischen Überlauf.")
    return t, temperature


def curve_color(index):
    if index < len(PALETTE):
        return PALETTE[index]
    rgb = colorsys.hsv_to_rgb((index * 0.61803398875) % 1, 0.72, 0.65)
    return "#" + "".join(f"{round(v * 255):02x}" for v in rgb)


def parameter_text(p):
    return (f"α = {p['alpha']:g} W/(m² K)\nA = {p['A']:g} m² · m = {p['m']:g} kg\n"
            f"cₚ = {p['cp']:g} J/(kg K)\n"
            f"T₀ = {p['T0']:g} °C · T∞ = {p['T_inf']:g} °C\n"
            f"t_end = {p['t_end']:g} s · Δt = {p['dt']:g} s")


def build_figure(curves, preview, unit, height, ranges=None, revision=0):
    fig = go.Figure()
    factor, label = (60.0, "min") if unit == "Minuten" else (1.0, "s")
    entries = [(c, False) for c in curves]
    if preview is not None:
        entries.append((dict(params=preview, name="Vorschau", color="#666666"), True))
    actual_height = max(height, 160 * len(entries) + 120)
    for i, (curve, is_preview) in enumerate(entries):
        t, temp = simulate(curve["params"])
        fig.add_trace(go.Scatter(x=t / factor, y=temp, mode="lines", name=curve["name"],
                                line=dict(color=curve["color"], width=2 if is_preview else 3,
                                          dash="dash" if is_preview else "solid"),
                                hovertemplate=f"%{{x:.3f}} {label}<br>%{{y:.3f}} °C<extra>{curve['name']}</extra>"))
        fig.add_annotation(x=0.68, y=1 - i * 150 / (actual_height - 120),
                           xref="paper", yref="paper", xanchor="left", yanchor="top",
                           text=f"<b>{curve['name']}</b><br>" + parameter_text(curve["params"]).replace("\n", "<br>"),
                           showarrow=False, align="left", font=dict(size=11, color=curve["color"]),
                           bordercolor=curve["color"], borderwidth=1, borderpad=7, bgcolor="white")
    fig.update_layout(template="plotly_white", title="Temperaturverlauf", height=actual_height,
                      margin=dict(l=55, r=20, t=60, b=60), showlegend=False,
                      xaxis=dict(title=f"Zeit [{label}]", domain=[0, 0.63], zeroline=False),
                      yaxis=dict(title="Temperatur [°C]", zeroline=False), dragmode="zoom",
                      uirevision=str((revision, unit, ranges)), font=dict(size=14))
    if ranges:
        fig.update_xaxes(range=ranges[0])
        fig.update_yaxes(range=ranges[1])
    return fig


def data_frames(curves):
    data, parameters = [], []
    for c in curves:
        t, temp = simulate(c["params"])
        # Long format supports comparison curves with different time grids.
        frame = pd.DataFrame({"Kurve": c["name"], "Zeit_s": t, "Temperatur_C": temp})
        for k, v in c["params"].items():
            frame[k] = v
        data.append(frame)
        parameters.append({"Kurve": c["name"], "Farbe": c["color"], **c["params"]})
    return pd.concat(data, ignore_index=True), pd.DataFrame(parameters)


@st.cache_data(show_spinner=False, max_entries=12)
def export_data(curves):
    data, params = data_frames(curves)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        data.to_excel(writer, sheet_name="Temperaturverläufe", index=False)
        params.to_excel(writer, sheet_name="Parameter", index=False)
        pd.DataFrame({"Größe": list(PARAMS), "Einheit": ["W/(m² K)", "J/(kg K)", "m²", "kg", "°C", "°C", "s", "s"]}).to_excel(writer, sheet_name="Einheiten", index=False)
    return data.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"), output.getvalue()


@st.cache_data(show_spinner=False, max_entries=12)
def export_images(curves, unit, height, ranges):
    # Matplotlib keeps PNG export independent of a Chrome/Kaleido installation.
    factor, label = (60.0, "min") if unit == "Minuten" else (1.0, "s")
    inches = max(height / 100, len(curves) * 1.45 + 1.5)
    fig = Figure(figsize=(13, inches))
    ax = fig.add_axes([0.08, 0.12, 0.55, 0.78])
    for i, c in enumerate(curves):
        t, temp = simulate(c["params"])
        ax.plot(t / factor, temp, color=c["color"], linewidth=2)
        fig.text(0.67, 0.91 - i * 1.4 / inches,
                 c["name"] + "\n" + parameter_text(c["params"]), va="top", fontsize=10,
                 color=c["color"], bbox=dict(facecolor="white", edgecolor=c["color"], boxstyle="round,pad=0.5"))
    ax.set(xlabel=f"Zeit [{label}]", ylabel="Temperatur [°C]", title="Temperaturverlauf")
    ax.grid(alpha=0.25)
    if ranges:
        ax.set_xlim(ranges[0])
        ax.set_ylim(ranges[1])
    png, svg = BytesIO(), BytesIO()
    fig.savefig(png, format="png", dpi=160)
    fig.savefig(svg, format="svg")
    return png.getvalue(), svg.getvalue()


def reset():
    revision = st.session_state.get("revision", 0) + 1
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state.curves = []
    st.session_state.revision = revision


def reset_view():
    st.session_state.manual_axes = False
    st.session_state.revision += 1


def main():
    st.set_page_config(page_title="Temperaturprofil – Vorwärtssimulation", layout="wide")
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("curves", [])
    st.session_state.setdefault("revision", 0)
    _, logo_col = st.columns([4, 1])
    with logo_col:
        st.image(str(Path(__file__).with_name("HSE-Logo.jpg")), width="stretch")
    st.title("Vorwärtssimulation des Temperaturverlaufs")
    with st.expander("ℹ️ Hinweise zur Verwendung"):
        st.markdown("Aus dem vorgegebenen Wärmeübergangskoeffizienten **α** wird die Erwärmung oder Abkühlung eines Körpers berechnet.")
        st.latex(r"T(t)=T_\infty-(T_\infty-T_0)\,e^{-\frac{\alpha A}{m c_p}t}")
        st.markdown("""**Modellannahmen:** räumlich einheitliche Bauteiltemperatur; konstante Werte für α, A, m, cₚ und T∞.
Strahlung, Phasenwechsel und innere Wärmequellen werden nicht separat modelliert.
Die Annahme einer einheitlichen Temperatur muss für den konkreten Körper geprüft werden.

**Bedienung:** Parameter ändern → gestrichelte Live-Vorschau → **Plot** übernimmt die Kurve.
Mit **Graph behalten** bleiben frühere Kurven einschließlich ihrer Parameter erhalten.
Ohne Häkchen ersetzt der nächste Klick auf **Plot** die bisherigen Kurven.
**Reset** stellt alle Standardwerte wieder her und löscht übernommene Kurven.

**Zeit:** Die Simulation beginnt bei 0 s und enthält immer die Endzeit.
Δt steuert die Abtastung der analytischen Lösung; der letzte Zeitschritt kann kürzer sein.
Für schnelle Vorgänge einen ausreichend kleinen Zeitschritt wählen.

**Diagramm:** Mit der Maus einen Ausschnitt aufziehen, per Werkzeugleiste verschieben oder zoomen.
Die Streamlit-Vollbildfunktion vergrößert die Ansicht. „Ansicht zurücksetzen“ stellt automatische Achsen wieder her.
Parameterboxen stehen rechts innerhalb der Diagrammfläche, damit sie die Kurven nicht verdecken.
Exporte enthalten ausschließlich übernommene Kurven. Kurven werden nur in dieser Sitzung gespeichert.
""")

    plot_col, input_col = st.columns([0.65, 0.35], gap="large")
    with input_col:
        st.subheader("Parameter")
        for key, label, step, fmt in [
            ("alpha", "Wärmeübergangskoeffizient α [W/(m² K)]", 1.0, "%.3f"),
            ("cp", "Spezifische Wärmekapazität cₚ [J/(kg K)]", 10.0, "%.3f"),
            ("A", "Oberfläche A [m²]", 0.01, "%.6f"),
            ("m", "Masse m [kg]", 0.1, "%.6f"),
            ("T0", "Anfangstemperatur T₀ [°C]", 1.0, "%.2f"),
            ("T_inf", "Umgebungstemperatur T∞ [°C]", 1.0, "%.2f"),
            ("t_end", "Endzeit t_end [s]", 60.0, "%.3f"),
            ("dt", "Zeitschritt Δt [s]", 0.1, "%.4f"),
        ]:
            st.number_input(label, key=key, step=step, format=fmt)
        p = {k: st.session_state[k] for k in PARAMS}
        problem = None
        try:
            t, temp = simulate(p)
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            problem = str(exc)
            st.error(problem)
        buttons = st.columns([1, 1.7, 1])
        with buttons[0]:
            plot_clicked = st.button("Plot", key="plot_action", type="primary", disabled=problem is not None)
        with buttons[1]:
            st.checkbox("Graph behalten", key="keep")
        with buttons[2]:
            st.button("Reset", key="reset_action", on_click=reset)
        if plot_clicked:
            old = st.session_state.curves if st.session_state.keep else []
            index = len(old)
            st.session_state.curves = old + [dict(name=f"Kurve {index + 1}", color=curve_color(index), params=deepcopy(p))]
        if problem is None:
            st.metric("Vorschau: Temperatur bei t_end", f"{temp[-1]:.2f} °C")
            if p["alpha"] > 0:
                tau = p["m"] * p["cp"] / (p["alpha"] * p["A"])
                st.caption(f"Zeitkonstante τ = {tau:.2f} s. Nach τ sind 63,2 % der Temperaturänderung erreicht.")
                if p["dt"] > tau / 5:
                    st.info("Δt ist im Verhältnis zur Zeitkonstante groß. Ein kleinerer Zeitschritt zeigt den frühen Verlauf genauer.")
            else:
                st.caption("α = 0: kein Wärmeaustausch; T(t) = T₀.")

    with plot_col:
        st.subheader("Temperaturverlauf")
        with st.expander("Diagramm einstellen"):
            st.selectbox("Zeiteinheit im Diagramm", ["Sekunden", "Minuten"], key="unit", on_change=reset_view)
            st.slider("Diagrammhöhe [px]", 450, 1200, step=50, key="height")
            st.checkbox("Diagramm über gesamte Breite", key="full_width")
            st.checkbox("Achsengrenzen manuell festlegen", key="manual_axes")
            label = "min" if st.session_state.unit == "Minuten" else "s"
            c1, c2 = st.columns(2)
            with c1:
                st.number_input(f"Zeitachse von [{label}]", key="x_min", disabled=not st.session_state.manual_axes)
                st.number_input("Temperaturachse von [°C]", key="y_min", disabled=not st.session_state.manual_axes)
            with c2:
                st.number_input(f"Zeitachse bis [{label}]", key="x_max", disabled=not st.session_state.manual_axes)
                st.number_input("Temperaturachse bis [°C]", key="y_max", disabled=not st.session_state.manual_axes)
            st.button("Ansicht zurücksetzen", on_click=reset_view)
        ranges = None
        if st.session_state.manual_axes:
            limits = [st.session_state[k] for k in ("x_min", "x_max", "y_min", "y_max")]
            if not all(math.isfinite(v) for v in limits) or limits[0] >= limits[1] or limits[2] >= limits[3]:
                st.warning("Achsenminimum muss kleiner als Maximum sein. Es werden automatische Achsen verwendet.")
            else:
                ranges = [limits[:2], limits[2:]]
        st.caption("Gestrichelt: Vorschau · Durchgezogen: übernommen. Gleiche Vorschau und letzte Kurve werden nur einmal dargestellt.")

    curves = st.session_state.curves
    preview = p if problem is None and (not curves or curves[-1]["params"] != p) else None
    fig = build_figure(curves, preview, st.session_state.unit, st.session_state.height, ranges, st.session_state.revision)
    chart_container = st.container() if st.session_state.full_width else plot_col
    with chart_container:
        st.plotly_chart(fig, width="stretch", theme=None, key=f"temperature_chart_{st.session_state.revision}",
                        config=dict(scrollZoom=True, displaylogo=False, displayModeBar=True,
                                    modeBarButtonsToRemove=["toImage", "select2d", "lasso2d"]))

    st.subheader("Ergebnisse exportieren")
    if not curves:
        st.info("Zuerst mit „Plot“ mindestens eine Kurve übernehmen. Die Vorschau wird nicht exportiert.")
    else:
        st.caption(f"{len(curves)} übernommene Kurve(n). CSV/Excel enthalten alle Stützstellen und Parameter in SI-bezogenen Einheiten. "
                   "Bildexporte verwenden die numerisch eingestellten Achsengrenzen; ein Maus-Zoom wird nicht übernommen.")
        csv, excel = export_data(curves)
        png, svg = export_images(curves, st.session_state.unit, st.session_state.height, ranges)
        cols = st.columns(4)
        for col, name, data, filename, mime in [
            (cols[0], "CSV herunterladen", csv, "temperaturverlaeufe.csv", "text/csv"),
            (cols[1], "Excel herunterladen", excel, "temperaturverlaeufe.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            (cols[2], "PNG herunterladen", png, "temperaturverlaeufe.png", "image/png"),
            (cols[3], "SVG herunterladen", svg, "temperaturverlaeufe.svg", "image/svg+xml"),
        ]:
            with col:
                st.download_button(name, data, filename, mime, on_click="ignore")

    st.divider()
    st.subheader("🛠️ Feedback & Support")
    fb1, fb2 = st.columns(2)
    fb1.link_button("🐞 Bug melden", REPO + "/issues/new?template=bug_report.yml")
    fb2.link_button("✨ Feature anfragen", REPO + "/issues/new?template=feature_request.yml")
    st.divider()
    st.caption("Diese Anwendung dient ausschließlich zu Demonstrations- und Lehrzwecken. "
               "Es wird keine Gewähr für die Richtigkeit, Vollständigkeit oder Aktualität übernommen. "
               "Die Nutzung erfolgt auf eigene Verantwortung. Eine kommerzielle Verwendung ist ausdrücklich nicht gestattet.")
    st.markdown("[Prof. Dr.-Ing. Hendrik Dubbe](mailto:hendrik.dubbe@hs-esslingen.de?subject=Temperaturprofil-Forward-App)")


if __name__ == "__main__":
    main()
