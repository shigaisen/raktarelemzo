import streamlit as st
import pandas as pd
import io
from datetime import date

# --- PDF generáláshoz szükséges importok ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# --- Oldal beállítása ---
st.set_page_config(page_title="Svájci automata napi készlet feldolgozó", page_icon="📦")

st.title("📦 Svájci automata napi készlet feldolgozó")
st.write("""
Töltsd fel az Excel fájlt, és a rendszer kiszámolja a 'Tölteni' szükséges mennyiséget.
A végeredményt letöltheted **Excelben** (formázva) vagy **PDF-ben** (nyomtatáshoz, zebracsíkos elrendezéssel).
""")

# --- FÜGGVÉNY: Betűtípus kezelése (Magyar karakterekhez) ---
# Fontos: A 'DejaVuSans.ttf' fájlnak a Streamlit alkalmazás könyvtárában kell lennie, 
# hogy ez a rész megfelelően működjön a PDF generáláshoz!
def setup_fonts():
    # A Streamlit környezetben a fájlnév elérése. 
    # Mivel a Streamlit Cloud-ban nehézkes a fontfájl automatikus letöltése/elérése, 
    # feltételezzük, hogy a felhasználó feltöltötte/elérhetővé tette a 'DejaVuSans.ttf' fájlt.
    font_filename = "DejaVuSans.ttf"
    
    try:
        if 'DejaVuSans' not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont('DejaVuSans', font_filename))
        return True
    except Exception as e:
        # Hibaüzenet, ha a fájl (DejaVuSans.ttf) nem található a könyvtárban
        st.error(f"❌ HIBA: Nem találom a DejaVuSans.ttf fájlt a magyar karakterekhez! Hiba: {e}. A PDF Helvetica betűtípust fog használni (magyar ékezetek nélkül).")
        return False

# --- 1. Fájl feltöltése ---
uploaded_file = st.file_uploader("Húzd ide vagy válaszd ki az Excel fájlt", type=['xlsx', 'xls'])

if uploaded_file is not None:
    st.info(f"📄 Fájl feltöltve: **{uploaded_file.name}**. Elemzés indítása...")

    # --- Dinamikus fejlécsor keresése ---
    szukseges_oszlopok = ['Maximum készlet', 'Raktár készlet', 'Raktár szám', 'Terméknév']
    fejlec_sor = None
    
    try:
        uploaded_file.seek(0) 
        df_elonezet = pd.read_excel(uploaded_file, header=None, nrows=15)
        
        for i, sor in df_elonezet.iterrows():
            # Csak azokat az értékeket nézzük, amelyek nem NaN (üres cella)
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
            st.error("❌ HIBA: Nem sikerült megtalálni a kötelező oszlopokat ('Raktár szám' és 'Terméknév') az első 15 sorban. Kérjük, ellenőrizd a fájlt.")
            st.stop()

        # --- Adatok beolvasása és feldolgozása ---
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file, header=fejlec_sor)
        
        hianyzo_oszlopok = [col for col in szukseges_oszlopok if col not in df.columns]
        if hianyzo_oszlopok:
            st.error(f"❌ HIBA: Hiányzó kötelező oszlopok a megtalált fejlécben: {', '.join(hianyzo_oszlopok)}")
            st.stop()

        # Számítások
        df['Maximum készlet'] = pd.to_numeric(df['Maximum készlet'], errors='coerce').fillna(0)
        df['Raktár készlet'] = pd.to_numeric(df['Raktár készlet'], errors='coerce').fillna(0)
        df['tölteni'] = df['Maximum készlet'] - df['Raktár készlet']
        
        # Negatív 'tölteni' értékeket nullázzuk (nem tölthetünk negatív mennyiséget)
        df['tölteni'] = df['tölteni'].apply(lambda x: max(0, x))

        # Konszolidáció (Összesítés)
        df_konszolidalt = df.groupby(['Raktár szám', 'Terméknév'], as_index=False)['tölteni'].sum()
        df_konszolidalt = df_konszolidalt.rename(columns={'tölteni': 'Tölteni'})
        
        df_vegeredmeny = df_konszolidalt.sort_values(by='Terméknév', ascending=True)
        
        final_oszlopok = ['Raktár szám', 'Terméknév', 'Tölteni']
        df_final = df_vegeredmeny[final_oszlopok].copy()
        
        # Csak a pozitív töltendő mennyiségeket tartjuk meg
        df_final = df_final[df_final['Tölteni'] > 0]
        
        df_final['Kiírni'] = "" # Üres oszlop a nyomtatáshoz/ellenőrzéshez

        st.success(f"✅ Sikeres feldolgozás! **{len(df_final)}** tétel szükséges feltöltésre.")
        st.dataframe(df_final) 
        
        col1, col2 = st.columns(2)

        # ----------------------------------------------------------------------
        # --- GOMB 1: EXCEL (Zebracsíkos formázással) ---
        # ----------------------------------------------------------------------
        with col1:
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='xlsxwriter') as writer:
                sheet_name = 'Készlet'
                df_final.to_excel(writer, index=False, sheet_name=sheet_name)
                workbook = writer.book
                worksheet = writer.sheets[sheet_name]

                # Formátumok definíciója
                header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center', 'fg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
                
                # Zebracsíkos háttérformátumok (Világosszürke: #F2F2F2)
                striped_format_even = workbook.add_format({'border': 1, 'valign': 'vcenter', 'bg_color': '#F2F2F2'})
                striped_format_odd = workbook.add_format({'border': 1, 'valign': 'vcenter', 'bg_color': '#FFFFFF'})
                striped_number_format_even = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center', 'num_format': '0', 'bg_color': '#F2F2F2'})
                striped_number_format_odd = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center', 'num_format': '0', 'bg_color': '#FFFFFF'})

                # Oszlopszélességek beállítása
                worksheet.set_column('A:A', 15)
                worksheet.set_column('B:B', 57) 
                worksheet.set_column('C:C', 8)  
                worksheet.set_column('D:D', 15)

                # Fejléc kiírása
                for col_num, value in enumerate(df_final.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Zebracsíkos sorok kiírása
                for row_num, row_data in enumerate(df_final.values):
                    excel_row = row_num + 1
                    
                    # Formátum kiválasztása a sor indexe alapján (páros/páratlan)
                    if excel_row % 2 == 0:
                        bg_format = striped_format_even
                        num_bg_format = striped_number_format_even
                    else:
                        bg_format = striped_format_odd
                        num_bg_format = striped_number_format_odd

                    # Cellaadatok kiírása az új formátumokkal
                    worksheet.write(excel_row, 0, row_data[0], bg_format)
                    worksheet.write(excel_row, 1, row_data[1], bg_format)
                    worksheet.write(excel_row, 2, row_data[2], num_bg_format)
                    worksheet.write(excel_row, 3, row_data[3], bg_format)

            buffer_excel.seek(0)
            st.download_button(
                label="📥 Excel Letöltése (Formázott)",
                data=buffer_excel,
                file_name=f"napi_keszlet_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # ----------------------------------------------------------------------
        # --- GOMB 2: PDF (Zebracsíkos formázással) ---
        # ----------------------------------------------------------------------
        with col2:
            def create_pdf(dataframe):
                font_ok = setup_fonts()
                used_font = 'DejaVuSans' if font_ok else 'Helvetica'
                
                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                        leftMargin=15*mm, rightMargin=15*mm, 
                                        topMargin=20*mm, bottomMargin=15*mm)
                elements = []

                styles = getSampleStyleSheet()
                custom_title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Title'],
                    fontName=used_font, 
                    fontSize=14,
                    alignment=1, # Középre
                    spaceAfter=15
                )
                elements.append(Paragraph(f"Napi Készlet Feltöltési Lista - {date.today()}", custom_title_style))

                table_data = [dataframe.columns.to_list()] 
                table_data.extend(dataframe.values.tolist())

                # PDF oszlopszélességek (A4: kb. 180mm használható)
                # 35 + 115 + 15 + 15 = 180 mm
                col_widths = [35*mm, 115*mm, 15*mm, 15*mm]
                
                t = Table(table_data, colWidths=col_widths, repeatRows=1)

                # Zebracsíkos színek a PDF-hez
                background_color_odd = colors.white
                background_color_even = colors.Color(red=(240/255), green=(240/255), blue=(240/255)) 

                table_style_list = [
                    # Fejléc stílusok
                    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.31, 0.50, 0.74)),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTSIZE', (0, 0), (-1, 0), 10), 
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    
                    # Sorok stílusai
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ALIGN', (2, 0), (2, -1), 'CENTER'), # Tölteni oszlop középen
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    
                    # Zebracsíkos háttér (a 1. sortól, azaz a 2. elemtől indul)
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [background_color_odd, background_color_even]),
                    
                    # Körvonalak
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    
                    # Betűtípus (a magyar ékezetek miatt fontos)
                    ('FONTNAME', (0, 0), (-1, -1), used_font)
                ]
                
                t.setStyle(TableStyle(table_style_list))
                elements.append(t)

                doc.build(elements)
                buffer.seek(0)
                return buffer

            try:
                pdf_buffer = create_pdf(df_final)
                
                st.download_button(
                    label="📄 PDF Letöltése (Nyomtatáshoz)",
                    data=pdf_buffer,
                    file_name=f"napi_keszlet_{date.today()}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Hiba a PDF generálásnál: {e}")

    except Exception as e:
        st.error(f"Váratlan hiba történt a feldolgozás során: {e}")