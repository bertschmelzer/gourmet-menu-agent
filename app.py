import json
import requests
import streamlit as st
from openai import OpenAI
from streamlit_local_storage import LocalStorage

# App-Konfiguration für mobile Ansicht
st.set_page_config(page_title="Gourmet Menu Agent", page_icon="👨‍🍳", layout="centered")

st.title("🍳 Schweizer Gourmet-Agent")
st.write("Deine Präferenzen sind sicher gespeichert. Bereit für Coop Schweiz.")

# Lokaler Speicher für das Handy-Gedächtnis initialisieren
local_storage = LocalStorage()

# API Keys in der Seitenleiste
OPENAI_API_KEY = st.sidebar.text_input("OpenAI API Key", type="password")
PEPESTO_API_KEY = st.sidebar.text_input("Pepesto API Key", type="password")

# --- ERWEITERTE SPEZIAL-KÖCHE ---
verfuegbare_koeche = [
    "Betty Bossi (Klassisch Schweizerisch & Geling-Garantie)",
    "Jamie Oliver (Schnell, Unkompliziert, '5-Ingredients' Stil)",
    "Yotam Ottolenghi (Sehr Gemüse-fokussiert, Levantinische Gewürze)",
    "Gordon Ramsay (Präzise, Französisch-Britische Spitzenküche)",
    "Tanja Grandits (Schweizer Sterne-Köchin, Monochrome & Aroma-Küche)",
    "Andreas Caminada (Bündner Spitzenküche, Regional & Edel)",
    "Nadia Damaso (Eat Better Not Less, Gesund & Superfoods)"
]

st.subheader("⚙️ Deine gespeicherten Einstellungen")

# Lade alte Einstellungen vom Handy, falls vorhanden
saved_koeche = local_storage.getItem("saved_koeche")
saved_praferenzen = local_storage.getItem("saved_praferenzen")

# Fallback, wenn die App das erste Mal geöffnet wird
default_koeche = json.loads(saved_koeche) if saved_koeche else [verfuegbare_koeche[0]]
default_praf = saved_praferenzen if saved_praferenzen else "gesund, saisonal, keine Fertigprodukte"

# 1. Multi-Select für Köche (lädt automatisch die gespeicherte Auswahl)
ausgewaehlte_koeche = st.multiselect(
    "Deine Lieblings-Köche:",
    verfuegbare_koeche,
    default=default_koeche,
    key="koeche_select"
)

# 2. Textfeld für Allergien/No-Gos (lädt automatisch deine Vorlieben)
praferenzen = st.text_area(
    "Deine dauerhaften Vorlieben & Allergien:",
    value=default_praf,
    key="praferenzen_text"
)

# --- SPEICHER-LOGIK ---
if st.button("💾 Einstellungen auf dem Handy sichern", use_container_width=True):
    local_storage.setItem("saved_koeche", json.dumps(ausgewaehlte_koeche))
    local_storage.setItem("saved_praferenzen", praferenzen)
    st.success("Erfolgreich gemerkt! Die App weiss das auch beim nächsten Mal noch.")

st.divider()

# --- HAUPTTEIL: AGENTEN-LOGIK ---
if not OPENAI_API_KEY or not PEPESTO_API_KEY:
    st.warning("Bitte gib deine API-Keys in der Seitenleiste ein, um die App zu nutzen.")
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

    tages_wunsch = st.text_input(
        "Spezielle Wünsche für dieses Menü? (Optional)",
        placeholder="z.B. 'Heute Lust auf Pasta' oder 'Etwas für kalte Tage'"
    )

    if st.button("Mein Gourmet-Menü planen ✨", use_container_width=True):
        with st.spinner("Dein persönlicher Chefkoch kreiert die Rezepte..."):
            
            prompt = f"""
            Du bist ein Schweizer Starkoch-Sterne-Agent. Erstelle einen Menüplan auf Deutsch.
            
            STRENGE VORGABEN FÜR DIE GERICHTE:
            - Inspiriert vom spezifischen Kochstil dieser Köche: {', '.join(ausgewaehlte_koeche)}.
            - Beachte diese Benutzer-Präferenzen/Allergien konsequent: {praferenzen}.
            - Berücksichtige diesen aktuellen Wunsch: {tages_wunsch if tages_wunsch else 'Keine Sonderwünsche'}.
            
            Einkaufsliste-Regeln für die Schweiz:
            - Übersetze alle Zutaten in exakte, bei Coop Schweiz erhältliche Produkte.
            - Verwende Schweizer Begriffe (z.B. Poulet, Rüebli, Halbrahm, Peperoni, Gschwellti).
            
            GIB DIE ANTWORT STRIKT ALS JSON-OBJEKT IN FOLGENDEM FORMAT ZURÜCK:
            {{
                "menu_text": "Hier steht das Menü. Erwähne im Text elegant, wie du die Stile von z.B. Ottolenghi, Caminada oder Betty Bossi kombiniert hast.",
                "shopping_list": [
                    {{"name": "Produktname", "quantity": 1, "unit": "Stück"}}
                ]
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices.message.content)
            st.session_state["menu_text"] = result["menu_text"]
            st.session_state["shopping_list"] = result["shopping_list"]

    # Menü-Anzeige & Coop-Export
    if "menu_text" in st.session_state:
        st.subheader("👨‍🍳 Dein Menüvorschlag:")
        st.info(st.session_state["menu_text"])

        if st.button("🛒 Zutaten in den Coop-Warenkorb legen", type="primary", use_container_width=True):
            with st.spinner("Warenkorb wird bei Coop befüllt..."):
                coop_url = "https://pepesto.com"
                payload = {
                    "items": st.session_state["shopping_list"],
                    "options": {"prefer_budget": True},
                }
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {PEPESTO_API_KEY}",
                }

                res = requests.post(coop_url, json=payload, headers=headers)

                if res.status_code == 200:
                    redirect_url = res.json().get("redirect_url")
                    st.success("Warenkorb ist bereit!")
                    st.link_button("👉 Jetzt zu Coop wechseln & bestellen", redirect_url, use_container_width=True)
                else:
                    st.error("Fehler bei der Coop-Übermittlung.")
