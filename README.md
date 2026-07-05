# 🌤️ Pogoda w polskich miastach

Interaktywny dashboard analityczny w Streamlit prezentujący historyczne dane
pogodowe dla wybranych miast Polski. Użytkownik wybiera miasta, zakres dat i
metrykę, a KPI, wykresy i tabela przeliczają się na żywo.

**Działająca wersja:** https://TWOJA-APP.streamlit.app  ← *(uzupełnij po deployu)*

## Co robi aplikacja

- pobiera dzienne dane pogodowe (temperatura, opady, wiatr, nasłonecznienie)
  dla 12 polskich miast z kontrastem klimatycznym (wybrzeże, centrum, góry),
- czyści dane: konwersja typów, interpolacja braków w obrębie miasta,
  wyznaczenie kolumn pochodnych (pora roku, rozstęp dobowy, dni gorące/mroźne),
- prezentuje wyniki na **7 typach wykresów**: liniowy, mapa ciepła (heatmapa),
  słupkowy, wykres pudełkowy, mapa, punktowy (scatter) i histogram,
- pozwala filtrować dane **4 widgetami**: multiselect miast, wybór zakresu dat,
  selectbox metryki i suwak progu dnia gorącego.

## Skąd są dane

[**Open-Meteo Archive API**](https://open-meteo.com/) — darmowe, otwarte źródło
historycznych danych meteorologicznych. **Nie wymaga klucza API ani
rejestracji.** Zapytania idą do `https://archive-api.open-meteo.com/v1/archive`,
strefa czasowa `Europe/Warsaw`. Odpowiedzi są cache'owane przez
`@st.cache_data`, więc zmiana filtrów nie odpala zapytań od zera.

## Uruchomienie lokalne

```bash
git clone <adres-repo>
cd <folder-repo>
pip install -r requirements.txt
streamlit run app.py
```

Aplikacja wystartuje pod `http://localhost:8501`.

## Struktura projektu

```
├── app.py            # orkiestrator: layout, filtry, wykresy
├── data.py           # pobieranie z API + czyszczenie + kolumny pochodne
├── requirements.txt  # zależności
└── README.md
```

Logika danych jest oddzielona od warstwy UI: `data.py` odpowiada za pobieranie
i przygotowanie danych, `app.py` tylko je spina i wizualizuje.

## Technologie

Python · Streamlit · pandas · Plotly · requests
