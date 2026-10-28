import json
import requests
import streamlit as st
from openai import OpenAI
from streamlit_local_storage import LocalStorage

# App-Konfiguration für mobile Ansicht
st.set_page_config(page_title="Family Gourmet Menu Agent", page_icon="👨‍🍳", layout="centered")

st.title("🍳 Schweizer Familien-Wochenplaner")
st.write("Massgeschneiderte Menüs für die ganze Familie – direkt zu Coop.")

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

default_koeche = json.loads(saved_koeche) if saved_koeche else [verfuegbare_koeche[0]]
default_praf = saved_praferenzen if saved_praferenzen else "gesund, saisonal, keine Fertigprodukte"

ausgewaehlte_koeche = st.multiselect("Deine Lieblings-Köche:", verfuegbare_koeche, default=default_koeche, key="koeche_select")
praferenzen = st.text_area("Allgemeine Allergien / No-Gos (WG/Familie):", value=default_praf, key="praferenzen_text")

if st.button("💾 Grundeinstellungen sichern", use_container_width=True):
    local_storage.setItem("saved_koeche", json.dumps(ausgewaehlte_koeche))
    local_storage.setItem("saved_praferenzen", praferenzen)
    if OPENAI_API_KEY:
        local_storage.setItem("saved_openai_key", OPENAI_API_KEY)
    st.success("Grundeinstellungen gesichert!")

st.divider()

# --- NEU: DYNAMISCHE WOCHENPLANUNG PRO TAG ---
st.subheader("📅 Dein Wochenfahrplan (Montag - Sonntag)")

tage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
wochen_konfiguration = {}

# Wir erstellen für jeden Wochentag eine einklappbare Box (Expander)
for tag in tage:
    with st.expander(f"📌 {tag} konfigurieren", expanded=(tag == "Montag")):
        st.write(f"**Personenanzahl für {tag}:**")
        col1, col2 = st.columns(2)
        with col1:
            erwachsene = st.number_input(f"Erwachsene ({tag})", min_value=0, max_value=10, value=2, step=1, key=f"erw_{tag}")
        with col2:
            kinder = st.number_input(f"Kinder ({tag})", min_value=0, max_value=10, value=2, step=1, key=f"kind_{tag}")
            
        st.write(f"**Mahlzeiten & Wünsche für {tag}:**")
        
        # Frühstücks-Option
        fruehstueck = st.checkbox(f"Frühstück einplanen (+ extra Zutaten)", value=False, key=f"frueh_{tag}")
        extra_fruehstueck = ""
        if fruehstueck:
            extra_fruehstueck = st.text_input(f"Extra Frühstücks-Wünsche ({tag})", placeholder="z.B. Munder-Zopf, Hafermilch, Konfitüre", key=f"frueh_text_{tag}")
            
        # Abendessen-Fleischoption
        fleisch_option = st.selectbox(
            f"Abendessen Fleisch-Regel ({tag})",
            ["Egal (KI entscheidet)", "Strikt OHNE rotes Fleisch (Geflügel/Fisch erlaubt)", "Komplett Vegetarisch / Vegie-Tag", "Mit rotem Fleisch (Rind/Schwein)"],
            key=f"fleisch_{tag}"
        )
        
        spezialwunsch = st.text_input(f"spezialwunsch für {tag} (Optional)", placeholder="z.B. 'Schnelles Gericht unter 20 Min' oder 'Pasta'", key=f"wunsch_{tag}")
        
        # Daten für die KI sammeln
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
            
            # Wir wandeln die gesammelten Tages-Daten in Text für die KI um
            konfig_text = json.dumps(wochen_konfiguration, ensure_ascii=False, indent=2)
            
            prompt = f"""
            Du bist ein präziser Schweizer Familien-Sterne-Agent. Erstelle einen strukturierten Menüplan für die kommende Woche (Montag bis Sonntag) auf Deutsch.
            
            DEINE WOCHENVORGABE PRO TAG (Personen, Frühstück & Fleisch-Regeln):
            {konfig_text}
            
            ALLGEMEINE VORGABEN:
            - Stil der Köche: {', '.join(ausgewaehlte_koeche)}.
            - Stamm-Präferenzen: {praferenzen}.
            
            EINKAUFSLISTE-BERECHNUNG (SEHR WICHTIG):
            1. Berechne die Portionsmengen exakt basierend auf der angegebenen Anzahl Erwachsener und Kinder pro Tag (Kinder essen kleinere Portionen, passe Gramm-Angaben bei Fleisch/Beilagen an!).
            2. Wenn 'fruehstueck_aktiv' auf true steht, füge die unter 'fruehstueck_zutaten' genannten Extra-Produkte (z.B. Zopf, Butter, Milch) direkt der Einkaufsliste hinzu.
            3. Beachte strikt die 'fleisch_regel' des jeweiligen Tages beim Abendessen.
            4. Addiere identische Zutaten über die ganze Woche hinweg zusammen (z.B. nicht 3x separat Zwiebeln auflisten, sondern die Gesamtmenge akkumulieren).
            5. Übersetze alle Artikel in bei Coop Schweiz erhältliche Produkte unter Verwendung von Schweizer Begriffen (Poulet, Rüebli, Halbrahm, Peperoni).
            
            GIB DIE ANTWORT STRIKT ALS JSON-OBJEKT IN FOLGENDEM FORMAT ZURÜCK:
            {{
                "menu_text": "Hier steht der detaillierte Wochenplan gegliedert nach Wochentagen. Erwähne kurz, wie viele Personen am jeweiligen Tag bekocht werden, ob es Frühstück gibt und welche Fleisch-Regel gilt.",
                "shopping_list": [
                    {{"name": "Produktname", "quantity": 1, "unit": "Stück"}}
                ]
            }}
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )

                result = json.loads(response.choices.message.content)
                st.session_state["menu_text"] = result["menu_text"]
                st.session_state["shopping_list"] = result["shopping_list"]
            except Exception as e:
                st.error(f"Fehler bei der KI-Anfrage: {e}")

    # Menü-Anzeige & Kostenloser Coop-Warenkorb-Link
    if "menu_text" in st.session_state:
        st.subheader("👨‍🍳 Dein persönlicher Wochenspeiseplan:")
        st.info(st.session_state["menu_text"])

        if st.button("🛒 Gesamten Wocheneinkauf in den Coop-Warenkorb legen", type="primary", use_container_width=True):
            with st.spinner("Wocheneinkauf wird über den Gratis-Kanal übertragen..."):
                
                coop_url = "https://pepesto.com"
                payload = {"items": st.session_state["shopping_list"]}
                
                res = requests.post(coop_url, json=payload)

                if res.status_code == 200:
                    redirect_url = res.json().get("redirect_url")
                    st.success("Warenkorb für die ganze Woche ist bereit!")
                    st.link_button("👉 Jetzt zu Coop wechseln & Wocheneinkauf prüfen", redirect_url, use_container_width=True)
                else:
                    st.error("Fehler bei der Coop-Übermittlung.")
