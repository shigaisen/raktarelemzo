import streamlit as st
import pandas as pd
import io

# --- Oldal beállítása ---
st.set_page_config(page_title="Raktárkészlet Elemző", page_icon="📦")

st.title("📦 Raktárkészlet Elemző")
st.write("""
Töltsd fel az Excel fájlt (.xlsx vagy .xls), és a rendszer kiszámolja a 'tölteni' mennyiséget,
majd konszolidálja az adatokat.
""")

# --- 1. Fájl feltöltése (Ez helyettesíti a glob keresést) ---
uploaded_file = st.file_uploader("Húzd ide vagy válaszd ki az Excel fájlt", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.info(f"📄 Fájl feltöltve: {uploaded_file.name}. Elemzés indítása...")

    # --- Dinamikus fejlécsor keresése ---
    szukseges_oszlopok = ['Maximum készlet', 'Raktár készlet', 'Raktár szám', 'Terméknév']
    fejlec_sor = None
    
    try:
        # Mivel ez egy stream (memóriában lévő fájl), az olvasás után vissza kell tekerni az elejére
        # 1. lépés: Fejléc keresése az első 15 sorban
        uploaded_file.seek(0) 
        df_elonezet = pd.read_excel(uploaded_file, header=None, nrows=15)
        
        for i, sor in df_elonezet.iterrows():
            sor_ertekei = [str(x) for x in sor.dropna().tolist()]
            oszlop_talalt = True
            for oszlop in ['Raktár szám', 'Terméknév']:
                if oszlop not in sor_ertekei:
                    oszlop_talalt = False
                    break
            
            if oszlop_talalt:
                fejlec_sor = i
                break
        
        if fejlec_sor is None:
            st.error("❌ HIBA: Nem sikerült megtalálni a kötelező oszlopokat az első 15 sorban.")
            st.stop() # Megállítjuk a futást

        # 2. lépés: A teljes fájl beolvasása a megtalált fejléccel
        uploaded_file.seek(0) # FONTOS: Visszatekerjük a fájlt az elejére
        df = pd.read_excel(uploaded_file, header=fejlec_sor)
        
        # --- Eredeti logika folytatása ---
        
        # Oszlop ellenőrzés
        hianyzo_oszlopok = [col for col in szukseges_oszlopok if col not in df.columns]
        if hianyzo_oszlopok:
            st.error(f"❌ HIBA: Hiányzó oszlopok: {', '.join(hianyzo_oszlopok)}")
            st.stop()

        # Számítások
        df['Maximum készlet'] = pd.to_numeric(df['Maximum készlet'], errors='coerce').fillna(0)
        df['Raktár készlet'] = pd.to_numeric(df['Raktár készlet'], errors='coerce').fillna(0)
        df['tölteni'] = df['Maximum készlet'] - df['Raktár készlet']

        # Konszolidáció
        df_konszolidalt = df.groupby(['Raktár szám', 'Terméknév'], as_index=False)['tölteni'].sum()
        df_konszolidalt = df_konszolidalt.rename(columns={'tölteni': 'Összes Tölteni'})
        
        # Rendezés
        df_vegeredmeny = df_konszolidalt.sort_values(by='Terméknév', ascending=True)
        
        # Szűrés
        final_oszlopok = ['Raktár szám', 'Terméknév', 'Összes Tölteni']
        df_final = df_vegeredmeny[final_oszlopok]

        # --- Eredmény megjelenítése ---
        st.success(f"✅ Siker! {len(df_final)} tétel feldolgozva.")
        
        # Előnézet a képernyőn
        st.dataframe(df_final.head(10)) # Csak az első 10 sort mutatjuk előnézetnek

        # --- Letöltés gomb készítése ---
        # Excel fájl létrehozása a memóriában (nem a lemezen)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False)
            
            # Formázás (opcionális, de szép)
            workbook  = writer.book
            worksheet = writer.sheets['Sheet1']
            format1 = workbook.add_format({'num_format': '0'})
            worksheet.set_column('C:C', None, format1)

        buffer.seek(0)
        
        st.download_button(
            label="📥 Eredmény letöltése (output.xlsx)",
            data=buffer,
            file_name="output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Váratlan hiba történt: {e}")