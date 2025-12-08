import streamlit as st
import pandas as pd
import io

# --- Oldal beállítása ---
st.set_page_config(page_title="Svájci automata napi készlet feldolgozó", page_icon="📦")

st.title("📦 Svájci automata napi készlet feldolgozó")
st.write("""
Töltsd fel az Excel fájlt (.xlsx vagy .xls), és a rendszer kiszámolja a 'tölteni' szükséges mennyiséget,
majd konszolidálja az adatokat.
""")

# --- 1. Fájl feltöltése ---
uploaded_file = st.file_uploader("Húzd ide vagy válaszd ki az Excel fájlt", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.info(f"📄 Fájl feltöltve: {uploaded_file.name}. Elemzés indítása...")

    # --- Dinamikus fejlécsor keresése ---
    szukseges_oszlopok = ['Maximum készlet', 'Raktár készlet', 'Raktár szám', 'Terméknév']
    fejlec_sor = None
    
    try:
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
            st.stop()

        # 2. lépés: A teljes fájl beolvasása a megtalált fejléccel
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, header=fejlec_sor)
        
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
        
        # Szűrés és ÚJ Oszlop hozzáadása
        final_oszlopok = ['Raktár szám', 'Terméknév', 'Összes Tölteni']
        df_final = df_vegeredmeny[final_oszlopok].copy()
        
        # Itt adjuk hozzá az üres oszlopot
        df_final['Kiírni'] = "" 

        # --- Eredmény megjelenítése ---
        st.success(f"✅ Siker! {len(df_final)} tétel feldolgozva.")
        st.dataframe(df_final.head(10)) 

        # --- Letöltés gomb és Excel FORMÁZÁS ---
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            sheet_name = 'Készlet'
            df_final.to_excel(writer, index=False, sheet_name=sheet_name)
            
            workbook  = writer.book
            worksheet = writer.sheets[sheet_name]

            # --- Formátumok ---
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'vcenter',
                'align': 'center',
                'fg_color': '#4F81BD',
                'font_color': 'white',
                'border': 1
            })

            border_format = workbook.add_format({
                'border': 1,
                'valign': 'vcenter'
            })
            
            number_format = workbook.add_format({
                'border': 1,
                'valign': 'vcenter',
                'align': 'center',
                'num_format': '0'
            })

            # --- Formázás alkalmazása ---

            # Oszlop szélességek (Most már a D oszlop is kap szélességet)
            worksheet.set_column('A:A', 15) # Raktár szám
            worksheet.set_column('B:B', 40) # Terméknév
            worksheet.set_column('C:C', 15) # Összes tölteni
            worksheet.set_column('D:D', 15) # Kiírni (ÚJ)

            # Fejléc formázása
            for col_num, value in enumerate(df_final.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Adatok formázása
            for row_num, row_data in enumerate(df_final.values):
                excel_row = row_num + 1
                
                # A: Raktár szám
                worksheet.write(excel_row, 0, row_data[0], border_format)
                
                # B: Terméknév
                worksheet.write(excel_row, 1, row_data[1], border_format)
                
                # C: Összes Tölteni (Szám)
                worksheet.write(excel_row, 2, row_data[2], number_format)
                
                # D: Kiírni (ÚJ - Üres, de keretezett)
                worksheet.write(excel_row, 3, row_data[3], border_format)

        buffer.seek(0)
        
        st.download_button(
            label="📥 Letöltés formázva (napi_keszlet.xlsx)",
            data=buffer,
            file_name="napi_keszlet.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Váratlan hiba történt: {e}")