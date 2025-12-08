import streamlit as st
import pandas as pd
import io

# --- PDF generáláshoz szükséges importok ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Oldal beállítása ---
st.set_page_config(page_title="Svájci automata napi készlet feldolgozó", page_icon="📦")

st.title("📦 Svájci automata napi készlet feldolgozó")
st.write("""
Töltsd fel az Excel fájlt, és a rendszer kiszámolja a 'tölteni' szükséges mennyiséget.
Letöltheted Excelben vagy PDF-ben (nyomtatáshoz).
""")

# --- 1. Fájl feltöltése ---
uploaded_file = st.file_uploader("Húzd ide vagy válaszd ki az Excel fájlt", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.info(f"📄 Fájl feltöltve: {uploaded_file.name}. Elemzés indítása...")

    # --- Dinamikus fejlécsor keresése ---
    szukseges_oszlopok = ['Maximum készlet', 'Raktár készlet', 'Raktár szám', 'Terméknév']
    fejlec_sor = None
    
    try:
        # Fejléc keresése
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
            st.error("❌ HIBA: Nem sikerült megtalálni a kötelező oszlopokat.")
            st.stop()

        # Adatok beolvasása
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
        
        # Szűrés és "Kiírni" oszlop
        final_oszlopok = ['Raktár szám', 'Terméknév', 'Összes Tölteni']
        df_final = df_vegeredmeny[final_oszlopok].copy()
        df_final['Kiírni'] = "" 

        # --- Eredmény megjelenítése ---
        st.success(f"✅ Siker! {len(df_final)} tétel feldolgozva.")
        st.dataframe(df_final.head(10)) 
        
        # Két oszlop létrehozása a gomboknak, hogy egymás mellett legyenek
        col1, col2 = st.columns(2)

        # ---------------------------------------------------------
        # 1. GOMB: EXCEL LETÖLTÉS
        # ---------------------------------------------------------
        with col1:
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
                sheet_name = 'Készlet'
                df_final.to_excel(writer, index=False, sheet_name=sheet_name)
                
                workbook  = writer.book
                worksheet = writer.sheets[sheet_name]

                # Formátumok
                header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'fg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
                border_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
                number_format = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center', 'num_format': '0'})

                # Szélességek
                worksheet.set_column('A:A', 15)
                worksheet.set_column('B:B', 40)
                worksheet.set_column('C:C', 15)
                worksheet.set_column('D:D', 15)

                # Fejléc írás
                for col_num, value in enumerate(df_final.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Adat írás
                for row_num, row_data in enumerate(df_final.values):
                    excel_row = row_num + 1
                    worksheet.write(excel_row, 0, row_data[0], border_format)
                    worksheet.write(excel_row, 1, row_data[1], border_format)
                    worksheet.write(excel_row, 2, row_data[2], number_format)
                    worksheet.write(excel_row, 3, row_data[3], border_format)

            buffer_excel.seek(0)
            st.download_button(
                label="📥 Excel Letöltése",
                data=buffer_excel,
                file_name="napi_keszlet.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # ---------------------------------------------------------
        # 2. GOMB: PDF LETÖLTÉS
        # ---------------------------------------------------------
        with col2:
            def create_pdf(dataframe):
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4)
                elements = []

                # Stílusok
                styles = getSampleStyleSheet()
                title_style = styles['Title']
                title_style.alignment = 1 # Center
                
                # Cím
                elements.append(Paragraph("Napi Készlet Feltöltési Lista", title_style))
                elements.append(Paragraph("<br/><br/>", styles['Normal'])) # Sortörés

                # Adatok előkészítése a táblázathoz (Fejléc + Adatok)
                # A fejlécet listává alakítjuk
                table_data = [dataframe.columns.to_list()] 
                # Az adatokat hozzáadjuk
                table_data.extend(dataframe.values.tolist())

                # Táblázat létrehozása
                # Oszlopszélességek mm-ben: [Raktár szám, Terméknév, Összes Tölteni, Kiírni]
                col_widths = [35*mm, 85*mm, 30*mm, 30*mm]
                t = Table(table_data, colWidths=col_widths, repeatRows=1)

                # Táblázat stílusa (Keretezés és Színezés)
                style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.31, 0.50, 0.74)), # Kék fejléc
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), # Fehér betű a fejlécben
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'), # Általános balra igazítás
                    ('ALIGN', (2, 0), (2, -1), 'CENTER'), # Számok (C oszlop) középre
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), # Fejléc félkövér
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black), # Fekete rács mindenhol
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ])
                t.setStyle(style)
                elements.append(t)

                # PDF generálása a memóriába
                doc.build(elements)
                buffer.seek(0)
                return buffer

            try:
                # PDF generálás hívása
                pdf_buffer = create_pdf(df_final)
                
                st.download_button(
                    label="📄 PDF Letöltése",
                    data=pdf_buffer,
                    file_name="napi_keszlet.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Hiba a PDF generálásnál: {e}")

    except Exception as e:
        st.error(f"Váratlan hiba történt: {e}")