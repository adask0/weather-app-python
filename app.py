"""
Pogoda w polskich miastach — dashboard analityczny.

Dane: Open-Meteo Archive API (darmowe, bez klucza / rejestracji).
Uruchomienie lokalne:  streamlit run app.py

app.py jest orkiestratorem: buduje layout, spina filtry z danymi i rysuje
wykresy. Cała logika pobierania/czyszczenia danych siedzi w data.py.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.express as px
import streamlit as st

from data import CITIES, MONTHS_PL, load_weather

st.set_page_config(
    page_title="Pogoda w polskich miastach",
    page_icon="🌤️",
    layout="wide",
)

METRIC_LABELS = {
    "temperature_2m_mean": "Temperatura średnia (°C)",
    "temperature_2m_max": "Temperatura maksymalna (°C)",
    "temperature_2m_min": "Temperatura minimalna (°C)",
    "precipitation_sum": "Suma opadów (mm)",
    "wind_speed_10m_max": "Maksymalny wiatr (km/h)",
}


def fmt(x: float, unit: str = "") -> str:
    """Liczba w polskiej konwencji: 1 234,5 (spacja jako separator tysięcy)."""
    return f"{x:,.1f}".replace(",", " ").replace(".", ",") + unit


def fmt_int(x: float) -> str:
    """Liczba całkowita w polskiej konwencji: 1 234."""
    return f"{int(round(x)):,}".replace(",", " ")


#SIDEBAR
st.sidebar.title("🌤️ Filtry")

sel_cities = st.sidebar.multiselect(
    "Miasta",
    list(CITIES.keys()),
    default=["Warszawa", "Gdańsk", "Kraków", "Zakopane"],
)

default_end = dt.date.today() - dt.timedelta(days=7)
default_start = dt.date(default_end.year - 1, 1, 1)
date_range = st.sidebar.date_input(
    "Zakres dat",
    value=(default_start, default_end),
    min_value=dt.date(1980, 1, 1),
    max_value=default_end,
)

metric = st.sidebar.selectbox(
    "Metryka główna",
    options=list(METRIC_LABELS.keys()),
    format_func=lambda k: METRIC_LABELS[k],
)

hot_threshold = st.sidebar.slider(
    "Próg dnia gorącego (°C)", 20, 35, 25,
)

st.sidebar.caption("Źródło: Open-Meteo Archive API — bez klucza API.")

#HEAD
st.title("Pogoda w polskich miastach")
st.caption(
    "Analiza historycznych danych pogodowych. Zmień filtry po lewej — "
    "KPI, wykresy i tabela przeliczą się na żywo."
)

#WALIDACJA WEJŚCIA
if not sel_cities:
    st.warning("Wybierz przynajmniej jedno miasto w panelu po lewej.")
    st.stop()
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Wybierz pełny **zakres** dat (początek i koniec).")
    st.stop()

start, end = date_range
df = load_weather(tuple(sorted(sel_cities)), start.isoformat(), end.isoformat())
if df.empty:
    st.error("Brak danych dla wybranych parametrów. Spróbuj innego zakresu dat.")
    st.stop()

df["is_hot"] = df["temperature_2m_max"] >= hot_threshold
label = METRIC_LABELS[metric]

#KPI
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Śr. temperatura", fmt(df["temperature_2m_mean"].mean(), " °C"))
k2.metric("Rekord ciepła", fmt(df["temperature_2m_max"].max(), " °C"))
k3.metric("Rekord zimna", fmt(df["temperature_2m_min"].min(), " °C"))
k4.metric(f"Dni ≥ {hot_threshold}°C", fmt_int(df["is_hot"].sum()))
k5.metric("Suma opadów", fmt(df["precipitation_sum"].sum(), " mm"))

st.caption(
    f"Wczytano **{fmt_int(len(df))}** obserwacji dziennych dla "
    f"**{df['city'].nunique()}** miast. Uzupełniono "
    f"**{fmt_int(df.attrs.get('missing_filled', 0))}** brakujących wartości."
)

#ZAKŁADKI
tab_trend, tab_city, tab_map, tab_rel = st.tabs(
    ["📈 Trendy w czasie", "🏙️ Porównanie miast", "🗺️ Mapa", "🔬 Zależności"]
)

#1. TRENDY: wykres liniowy + heatmapa
with tab_trend:
    monthly = (
        df.groupby(["city", pd.Grouper(key="date", freq="MS")])[metric]
        .mean().reset_index()
    )
    fig_line = px.line(
        monthly, x="date", y=metric, color="city",
        labels={"date": "Miesiąc", metric: label, "city": "Miasto"},
        title=f"{label} — średnia miesięczna",
    )
    fig_line.update_layout(height=440, hovermode="x unified",
                           legend_title_text="")
    st.plotly_chart(fig_line, use_container_width=True)
    st.markdown(
        "**Co widać:** sezonowość jest wyraźna — lato/zima tworzą regularną "
        "sinusoidę, a miasta górskie (np. Zakopane) leżą niżej przez cały rok."
    )

    heat = df.groupby(["city", "month"])[metric].mean().reset_index()
    pivot = heat.pivot(index="city", columns="month", values=metric)
    pivot.columns = [MONTHS_PL[m] for m in pivot.columns]
    fig_heat = px.imshow(
        pivot, aspect="auto", color_continuous_scale="RdBu_r",
        labels={"x": "Miesiąc", "y": "Miasto", "color": label},
        title=f"{label} — mapa ciepła miasto × miesiąc",
        text_auto=".1f",
    )
    fig_heat.update_layout(height=380)
    st.plotly_chart(fig_heat, use_container_width=True)

#2. MIASTA: ranking słupkowy + boxplot
with tab_city:
    col_a, col_b = st.columns(2)

    with col_a:
        rank = (
            df.groupby("city")[metric].mean()
            .sort_values().reset_index()
        )
        fig_bar = px.bar(
            rank, x=metric, y="city", orientation="h",
            color=metric, color_continuous_scale="RdBu_r",
            labels={metric: label, "city": "Miasto"},
            title=f"Ranking miast — {label}",
        )
        fig_bar.update_layout(height=460, coloraxis_showscale=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_b:
        fig_box = px.box(
            df, x="city", y="temperature_2m_mean", color="city",
            labels={"city": "Miasto",
                    "temperature_2m_mean": "Temperatura średnia (°C)"},
            title="Rozrzut temperatur dziennych w miastach",
        )
        fig_box.update_layout(height=460, showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown(
        "**Co widać:** ranking porządkuje miasta wg wybranej metryki, a "
        "boxplot pokazuje nie tylko średnią, ale i rozstęp — miasta o dużym "
        "pudełku mają bardziej zmienny klimat."
    )

#3. MAPA: rozmieszczenie geograficzne
with tab_map:
    geo = (
        df.groupby(["city", "lat", "lon"])[metric]
        .mean().reset_index()
    )
    geo["marker"] = 14
    fig_map = px.scatter_map(
        geo, lat="lat", lon="lon", color=metric, size="marker",
        size_max=22, hover_name="city",
        color_continuous_scale="RdBu_r",
        map_style="open-street-map", zoom=4.7,
        center={"lat": 52.0, "lon": 19.2},
        labels={metric: label},
        title=f"Mapa: {label} (średnia w okresie)",
    )
    fig_map.update_layout(height=560, margin=dict(l=0, r=0, t=48, b=0))
    st.plotly_chart(fig_map, use_container_width=True)
    st.markdown(
        "**Co widać:** gradient północ–południe i wpływ gór na dole mapy. "
        "Kliknij i przybliż, żeby porównać sąsiednie miasta."
    )

#4. ZALEŻNOŚCI: scatter + histogram
with tab_rel:
    col_c, col_d = st.columns(2)

    with col_c:
        fig_sc = px.scatter(
            df, x="temperature_2m_mean", y="precipitation_sum",
            color="season", hover_name="city", opacity=0.45,
            category_orders={"season": ["Zima", "Wiosna", "Lato", "Jesień"]},
            labels={"temperature_2m_mean": "Temperatura średnia (°C)",
                    "precipitation_sum": "Opady (mm)", "season": "Pora roku"},
            title="Temperatura a opady wg pory roku",
        )
        fig_sc.update_layout(height=440, legend_title_text="")
        st.plotly_chart(fig_sc, use_container_width=True)

    with col_d:
        fig_hist = px.histogram(
            df, x="temperature_2m_mean", color="city", nbins=40,
            barmode="overlay", opacity=0.6,
            labels={"temperature_2m_mean": "Temperatura średnia (°C)",
                    "count": "Liczba dni", "city": "Miasto"},
            title="Rozkład temperatur dziennych",
        )
        fig_hist.update_layout(height=440, legend_title_text="")
        st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown(
        "**Co widać:** najintensywniejsze opady zdarzają się latem (ciepłe "
        "punkty wysoko na osi Y), a histogram ujawnia dwumodalność — osobne "
        "skupiska dni zimowych i letnich."
    )

#TABELA + EKSPORT
with st.expander("🔎 Podgląd i eksport danych"):
    st.dataframe(
        df.sort_values(["city", "date"]).reset_index(drop=True),
        use_container_width=True, height=320,
    )
    st.download_button(
        "Pobierz przefiltrowane dane (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="pogoda_polska.csv",
        mime="text/csv",
    )
