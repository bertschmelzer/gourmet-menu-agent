import json
import requests
import streamlit as st
from openai import OpenAI
from streamlit_local_storage import LocalStorage

# App-Konfiguration für mobile Ansicht
st.set_page_config(page_title="Family Gourmet Menu Agent", page_icon="👨‍🍳", layout="centered")

st.title("🍳 Schweizer Familien-Wochenplaner")
st.write("Massgeschneiderte Menüs für die ganze Familie – Unabhängig & Kostenlos.")

# Lokaler Speicher initialisieren
local_storage = LocalStorage()

# --- SIDEBAR: OPENAI SCHLÜSSEL ---
st.sidebar.subheader("🔑 API-Schlüssel")
OPENAI_API_KEY = st.sidebar.text_input("OpenAI API Key", type="password")

# --- KÖCHE & STAMM-PRÄFERENZEN ---
verfuegbare_koeche = [
    "Betty Bossi (Klassisch Schweizerisch & Geling-Garantie)",
    "Jamie Oliver (Schnell, Unkompliziert, '5-Ingredients' Stil)",
    "Yotam Ottolenghi (Sehr Gemüse-fokussiert, Levantinische Gewürze)",
    "Gordon Ramsay (Präzise, Französisch-Britische Spitzenküche)",
    "Tanja Grandits (Schweizer Sterne-Köchin, Monochrome & Aroma-Küche)",
    "Andreas Caminada (Bündner Spitzenküche, Regional & Edel)",
    "Nadia Damaso (Eat Better Not Less, Gesund & Superfoods)"
]

st.subheader("⚙️ Grundeinstellungen (Dauerhaft)")

saved_koeche = local_storage.getItem("saved_koeche")
saved_praferenzen = local_storage.getItem("saved_praferenzen")
saved_openai_key = local_storage.getItem("saved_openai_key")

if saved_openai_key and not OPENAI_API_KEY:
    OPENAI_API_KEY = saved_openai_key

default_koeche = json.loads(saved_koeche) if saved_koeche else [verfuegbare_koeche]
default_praf = saved_praferenzen if saved_praferenzen else "gesund, saisonal, keine Fertigprodukte"

ausgewaehlte_koeche = st.multiselect("Deine Lieblings-Köche:", verfuegbare_koeche, default=default_koeche, key="koeche_select")
praferenzen = st.text_area("Allgemeine Allergien / No-Gos (WG/Familie):", value=default_praf, key="praferenzen_text")

if st.button("💾 Grundeinstellungen sichern", use_container_width=True):
    local_storage.setItem("saved_koeche", json.dumps(ausgewaehlte_koeche), key="save_k")
    local_storage.setItem("saved_praferenzen", praferenzen, key="save_p")
    if OPENAI_API_KEY:
        local_storage.setItem("saved_openai_key", OPENAI_API_KEY, key="save_o")
    st.success("Grundeinstellungen gesichert!")

st.divider()

# --- DYNAMISCHE WOCHENPLANUNG PRO TAG ---
st.subheader("📅 Dein Wochenfahrplan (Montag - Sonntag)")

tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
wochen_konfiguration = {}

for tag in tage:
    with st.expander(f"📌 {tag} konfigurieren", expanded=(tag == "Montag")):
        st.write(f"**Personenanzahl für {tag}:**")
        col1, col2 = st.columns(2)
        with col1:
            erwachsene = st.number_input(f"Erwachsene ({tag})", min_value=0, max_value=10, value=2, step=1, key=f"erw_{tag}")
        with col2:
            kinder = st.number_input(f"Kinder ({tag})", min_value=0, max_value=10, value=2, step=1, key=f"kind_{tag}")
            
        st.write(f"**Mahlzeiten & Wünsche für {tag}:**")
        
        fruehstueck = st.checkbox(f"Frühstück einplanen (+ extra Zutaten)", value=False, key=f"frueh_{tag}")
        extra_fruehstueck = ""
        if fruehstueck:
            extra_fruehstueck = st.text_input(f"Extra Frühstücks-Wünsche ({tag})", placeholder="z.B. Munder-Zopf, Hafermilch, Konfitüre", key=f"frueh_text_{tag}")
            
        fleisch_option = st.selectbox(
            f"Abendessen Fleisch-Regel ({tag})",
            ["Egal (KI entscheidet)", "Strikt OHNE rotes Fleisch (Geflügel/Fisch erlaubt)", "Komplett Vegetarisch / Vegie-Tag", "Mit rotem Fleisch (Rind/Schwein)"],
            key=f"fleisch_{tag}"
        )
        
        spezialwunsch = st.text_input(f"Spezialwunsch für {tag} (Optional)", placeholder="z.B. 'Schnelles Gericht unter 20 Min' oder 'Pasta'", key=f"wunsch_{tag}")
        
        wochen_konfiguration[tag] = {
            "erwachsene": erwachsene,
            "kinder": kinder,
            "fruehstueck_aktiv": fruehstueck,
            "fruehstueck_zutaten": extra_fruehstueck,
            "fleisch_regel": fleisch_option,
            "spezialwunsch": spezialwunsch
        }

st.divider()

# --- AGENTEN-LOGIK ---
if not OPENAI_API_KEY:
    st.warning("👈 Bitte öffne die Seitenleiste links und trage deinen OpenAI API-Schlüssel ein.")
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

    if st.button("🚀 Gesamten Gourmet-Wochenplan generieren", type="primary", use_container_width=True):
        with st.spinner("Dein Privatchef kalkuliert den Wocheneinkauf..."):
            
            konfig_text = json.dumps(wochen_konfiguration, ensure_ascii=False, indent=2)
            
            prompt = f"""
            Du bist ein präziser Schweizer Familien-Sterne-Agent. Erstelle einen strukturierten Menüplan für die kommende Woche (Montag bis Sonntag) auf Deutsch.
            
            DEINE WOCHENVORGABE PRO TAG (Personen, Frühstück & Fleisch-Regeln):
            {konfig_text}
            
            ALLGEMEINE VORGABEN:
            - Stil der Köche: {', '.join(ausgewaehlte_koeche)}.
            - Stamm-Präferenzen: {praferenzen}.
            
            EINKAUFSLISTE-BERECHNUNG (SEHR WICHTIG):
            1. Berechne die Portionsmengen exakt basierend auf der angegebenen Anzahl Erwachsener und Kinder pro Tag.
            2. Wenn 'fruehstueck_aktiv' auf true steht, füge die Frühstücks-Wünsche direkt hinzu.
            3. Beachte strikt die Fleisch-Regel des jeweiligen Tages beim Abendessen.
            4. Addiere identische Zutaten über die ganze Woche hinweg zusammen (Gesamtmenge akkumulieren).
            5. Verwende Schweizer Begriffe (Poulet, Rüebli, Halbrahm, Peperoni).
            
            GIB DIE ANTWORT STRIKT ALS JSON-OBJEKT IN FOLGENDEM FORMAT ZURÜCK:
            {{
                "menu_text": "Hier steht der detaillierte Wochenplan gegliedert nach Wochentagen.",
                "shopping_list_text": "Produkt 1 (Menge)\\nProdukt 2 (Menge)\\n"
            }}
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )

                # JETZT KORREKT: Zugriff auf das ERSTE Element der Liste über [0]
                raw_content = response.choices[0].message.content
                result = json.loads(raw_content)
                
                st.session_state["menu_text"] = result["menu_text"]
                st.session_state["shopping_list_text"] = result["shopping_list_text"]
            except Exception as e:
                st.error(f"Fehler bei der KI-Anfrage: {e}")

    # Menü-Anzeige & Einkaufsliste
    if "menu_text" in st.session_state:
        st.subheader("👨‍🍳 Dein persönlicher Wochenspeiseplan:")
        st.info(st.session_state["menu_text"])

        st.subheader("🛒 Deine akkumulierte Einkaufsliste für die Woche:")
        
        # Zeige die Liste in einer Textbox an, die man mit 1 Klick kopieren kann
        st.text_area("Kopiere diese Liste für die Coop- oder Migros-App:", 
                     value=st.session_state["shopping_list_text"], 
                     height=300)
        
        st.success("💡 Tipp: Kopiere den Text oben und füge ihn in deiner Coop- oder Migros-App unter 'Zutaten importieren' / Freitext-Suche ein, um alles sofort im Warenkorb zu haben!")
