"""
Pobieranie i przygotowanie danych pogodowych z Open-Meteo Archive API.

API jest w pełni darmowe i NIE wymaga klucza ani rejestracji — wystarczy
zapytanie GET z parametrami w URL. Logikę danych trzymamy tutaj, żeby
`app.py` pełnił rolę orkiestratora (warstwa UI oddzielona od warstwy danych).
"""
from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

CITIES: dict[str, tuple[float, float]] = {
    "Warszawa": (52.2298, 21.0118),
    "Kraków": (50.0647, 19.9450),
    "Gdańsk": (54.3520, 18.6466),
    "Wrocław": (51.1079, 17.0385),
    "Poznań": (52.4064, 16.9252),
    "Łódź": (51.7592, 19.4560),
    "Szczecin": (53.4285, 14.5528),
    "Lublin": (51.2465, 22.5684),
    "Katowice": (50.2649, 19.0238),
    "Białystok": (53.1325, 23.1688),
    "Rzeszów": (50.0413, 21.9990),
    "Zakopane": (49.2992, 19.9496),
}

# Dzienne agregaty dostępne w archiwum Open-Meteo.
DAILY_VARS = [
    "temperature_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "wind_speed_10m_max",
    "shortwave_radiation_sum",
]

MONTHS_PL = {1: "sty", 2: "lut", 3: "mar", 4: "kwi", 5: "maj", 6: "cze",
             7: "lip", 8: "sie", 9: "wrz", 10: "paź", 11: "lis", 12: "gru"}

SEASONS = {12: "Zima", 1: "Zima", 2: "Zima",
           3: "Wiosna", 4: "Wiosna", 5: "Wiosna",
           6: "Lato", 7: "Lato", 8: "Lato",
           9: "Jesień", 10: "Jesień", 11: "Jesień"}


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_city(city: str, lat: float, lon: float,
                start: str, end: str) -> pd.DataFrame:
    """Pobiera surowe dane dzienne dla jednego miasta. Cache na 1 godzinę,
    dzięki czemu zmiana filtrów nie odpala setek zapytań od nowa."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start,
        "end_date": end,
        "daily": ",".join(DAILY_VARS),
        "timezone": "Europe/Warsaw",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=30)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    if not daily or "time" not in daily:
        return pd.DataFrame()
    df = pd.DataFrame(daily)
    df["city"] = city
    df["lat"] = lat
    df["lon"] = lon
    return df


@st.cache_data(ttl=3600, show_spinner="Pobieram dane z Open-Meteo…")
def load_weather(cities: tuple[str, ...], start: str, end: str) -> pd.DataFrame:
    """Pobiera dane dla wielu miast, łączy je i przekazuje do czyszczenia.
    Zwraca jeden „długi" DataFrame gotowy do filtrowania w aplikacji."""
    frames = [
        part
        for city in cities
        if not (part := _fetch_city(city, *CITIES[city], start, end)).empty
    ]
    if not frames:
        return pd.DataFrame()
    return _clean(pd.concat(frames, ignore_index=True))


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Czyszczenie + kolumny pochodne — właściwy krok przygotowania danych."""
    df["date"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.drop(columns=["time"])
    num_cols = [c for c in DAILY_VARS if c in df.columns]
    for col in num_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["city", "date"])
    missing_before = int(df[num_cols].isna().sum().sum())
    df[num_cols] = df.groupby("city")[num_cols].transform(
        lambda g: g.interpolate(limit_direction="both")
    )
    for col in ("precipitation_sum", "rain_sum", "snowfall_sum"):
        if col in df.columns:
            df[col] = df[col].fillna(0)
    df = df.dropna(subset=["temperature_2m_mean"])

    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["month_name"] = df["month"].map(MONTHS_PL)
    df["season"] = df["month"].map(SEASONS)
    df["temp_range"] = df["temperature_2m_max"] - df["temperature_2m_min"]
    df["is_frost"] = df["temperature_2m_min"] < 0     # dzień z przymrozkiem
    df["has_rain"] = df["precipitation_sum"] > 0.1

    df = df.reset_index(drop=True)
    df.attrs["missing_filled"] = missing_before
    return df
