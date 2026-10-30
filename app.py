import json
import streamlit as st
from openai import OpenAI
from streamlit_local_storage import LocalStorage

# App-Konfiguration für mobile Ansicht
st.set_page_config(page_title="Family Gourmet Menu Agent", page_icon="👨‍🍳", layout="centered")

st.title("🍳 Schweizer Familien-Wochenplaner")
st.write("Wähle aus 3 Vorschlägen pro Tag dein Lieblingsmenü – inklusive Anleitung.")

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
        spezialwunsch = st.text_input(f"Spezialwunsch für {tag} (Optional)", placeholder="z.B. 'Schnelles Gericht unter 20 Min'", key=f"wunsch_{tag}")
        
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

    # SCHRITT 1: 3 Vorschläge pro Tag generieren
    if st.button("🔍 Schritt 1: Je 3 Gerichtsvorschläge generieren", type="primary", use_container_width=True):
        # KORREKTUR: st.spinner kleingeschrieben
        with st.spinner("KI berechnet jeweils 3 Vorschläge pro Tag..."):
            konfig_text = json.dumps(wochen_konfiguration, ensure_ascii=False, indent=2)
            
            prompt_vorschlaege = f"""
            Du bist ein Schweizer Sterne-Chefkoch. Erstelle für JEDEN der 7 Wochentage exakt 3 unterschiedliche, kreative Gerichtvorschläge für das Abendessen auf Deutsch.
            Beachte die Tageskonfigurationen (Fleisch-Regel, Spezialwünsche): {konfig_text}
            Stil der Köche: {', '.join(ausgewaehlte_koeche)}.
            Allgemeine Präferenzen: {praferenzen}.
            
            GIB DIE ANTWORT STRIKT ALS JSON-OBJEKT IN FOLGENDEM FORMAT ZURÜCK:
            {{
                "Montag": ["Vorschlag A", "Vorschlag B", "Vorschlag C"],
                "Dienstag": ["Vorschlag A", "Vorschlag B", "Vorschlag C"],
                "Mittwoch": ["Vorschlag A", "Vorschlag B", "Vorschlag C"],
                "Donnerstag": ["Vorschlag A", "Vorschlag B", "Vorschlag C"],
                "Freitag": ["Vorschlag A", "Vorschlag B", "Vorschlag C"],
                "Samstag": ["Vorschlag A", "Vorschlag B", "Vorschlag C"],
                "Sonntag": ["Vorschlag A", "Vorschlag B", "Vorschlag C"]
            }}
            """
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt_vorschlaege}],
                    response_format={"type": "json_object"},
                )
                st.session_state["alle_vorschlaege"] = json.loads(response.choices[0].message.content)
                # Lösche alte finale Pläne, wenn neu gesucht wird
                if "final_anleitung" in st.session_state:
                    del st.session_state["final_anleitung"]
            except Exception as e:
                st.error(f"Fehler bei Schritt 1: {e}")

    # Wenn Vorschläge da sind, zeigen wir die Bestätigungs-Dropdowns an
    if "alle_vorschlaege" in st.session_state:
        st.subheader("👨‍🍳 Schritt 2: Wähle deine Favoriten")
        st.write("Wähle für jeden Tag einen der 3 Vorschläge aus:")
        
        ausgewaehlte_gerichte = {}
        for tag in tage:
            optionen = st.session_state["alle_vorschlaege"].get(tag, ["Konnte keine Vorschläge laden"])
            ausgewaehlte_gerichte[tag] = st.selectbox(f"Dein Menü für {tag}:", optionen, key=f"select_final_{tag}")
        
        st.divider()
        
        # SCHRITT 3: Anleitungen und Einkaufsliste generieren
        if st.button("🚀 Schritt 3: Anleitungen & Einkaufsliste erstellen", use_container_width=True):
            with st.spinner("Anleitungen werden geschrieben und Mengen kalkuliert..."):
                final_auswahl_text = json.dumps(ausgewaehlte_gerichte, ensure_ascii=False, indent=2)
                konfig_text = json.dumps(wochen_konfiguration, ensure_ascii=False, indent=2)
                
                prompt_final = f"""
                Du bist ein Schweizer Familien-Sterne-Agent. Der Benutzer hat folgende Gerichte für die Woche ausgewählt:
                {final_auswahl_text}
                
                Hier ist die Personenanzahl und Frühstückskonfiguration pro Tag:
                {konfig_text}
                
                AUFGABE:
                1. Schreibe für jedes der 7 ausgewählten Gerichte eine kurze, präzise Schritt-für-Schritt-Kochanleitung auf Deutsch.
                2. Berechne die Portionsmengen exakt für die angegebene Anzahl Erwachsener und Kinder pro Tag.
                3. Füge eventuelle Frühstücks-Zutaten ('fruehstueck_zutaten') direkt der Einkaufsliste hinzu.
                4. Addiere alle identischen Zutaten über die ganze Woche hinweg zu einer einzigen Gesamteinkaufsliste zusammen.
                5. Verwende Schweizer Begriffe (Poulet, Rüebli, Halbrahm, Peperoni).
                
                GIB DIE ANTWORT STRIKT ALS JSON-OBJEKT IN FOLGENDEM FORMAT ZURÜCK:
                {{
                    "anleitungen_text": "Hier stehen die detaillierten Kochanleitungen sortiert nach Wochentag (Montag bis Sonntag). Erwähne charmant den jeweiligen Starkoch-Stil.",
                    "shopping_list_text": "Produkt 1 (Gesamtmenge)\\nProdukt 2 (Gesamtmenge)\\n"
                }}
                """
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt_final}],
                        response_format={"type": "json_object"},
                    )
                    result_final = json.loads(response.choices[0].message.content)
                    st.session_state["final_anleitung"] = result_final["anleitungen_text"]
                    st.session_state["final_shopping"] = result_final["shopping_list_text"]
                except Exception as e:
                    st.error(f"Fehler bei Schritt 3: {e}")

    # Endergebnis anzeigen
    if "final_anleitung" in st.session_state:
        st.divider()
        st.subheader("📖 Deine Kochanleitungen für die Woche:")
        st.info(st.session_state["final_anleitung"])

        st.subheader("🛒 Deine akkumulierte Einkaufsliste:")
        st.text_area("Kopiere diese Liste für deine Supermarkt-App:", 
                     value=st.session_state["final_shopping"], 
                     height=300)
