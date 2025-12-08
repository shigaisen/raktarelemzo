# Készletfeldolgozó Streamlit Alkalmazás

Ez az adattár egy kicsi, Streamlit alapú alkalmazás, amely Excel fájlban érkező raktárkészletet dolgoz fel, kiszámítja a **töltendő** mennyiséget, és formázott Excel, valamint nyomtatható PDF formátumban exportálja az eredményt. Az utasítások rövidek és cselekvésorientáltak; a kódpéldákat az alábbiakban találod.

---

## 🖼️ Áttekintés

* **Egyetlen webes felület:** Az `app/app.py` tartalmazza az egész alkalmazást – ez egy Streamlit app, amely kezeli a feltöltést, a feldolgozást és a letöltéseket (nincs különálló háttérszolgáltatás).
* **Adatfolyam:** Excel feltöltése $\rightarrow$ fejléc sor azonosítása (első 15 sor) $\rightarrow$ numerikus oszlopok normalizálása $\rightarrow$ `tölteni = Maximum készlet - Raktár készlet` számítás $\rightarrow$ csoportosítás a `Raktár szám` + `Terméknév` alapján $\rightarrow$ szűrt, pozitív `Tölteni` sorok kiadása $\rightarrow$ Excel és PDF letöltések biztosítása.

---

## 🗃️ Kulcsfontosságú Fájlok

* `app/app.py` — A **fő alkalmazás**, tartalmazza az összes üzleti logikát és be-/kimeneti (I/O) műveletet. Itt keresd a fejléc-azonosítás, oszlopnevek és formázási részleteket.
* `app/requirements.txt` — Futtatási függőségek (Streamlit, pandas, reportlab, xlsxwriter, openpyxl, xlrd).

---

## 🛠️ Projektspecifikus Konvenciók és Fontos Minták

* Az **oszlopnevek magyarok** és pontosan egyezniük kell. Kötelező oszlopok: `Raktár szám`, `Terméknév`, `Maximum készlet`, `Raktár készlet`.
    * A fejléc azonosítása az első 15 sort olvassa fejléc nélkül, és a fejléc sort keresi: lásd: `df_elonezet = pd.read_excel(uploaded_file, header=None, nrows=15)`.
* **Numerikus konverzió:** A numerikus oszlopok a számítás előtt `pd.to_numeric(..., errors='coerce').fillna(0)` paranccsal vannak konvertálva – ezt ne távolítsd el, hacsak nem kezeled explicit módon a NaN (Nem szám) értékeket.
* **Negatív utántöltés nullázása:** A negatív utántöltési mennyiségek nullára korlátozódnak: `df['tölteni'] = df['tölteni'].apply(lambda x: max(0, x))`.
* **Aggregáció (Összesítés):** A konszolidáció a `df.groupby(['Raktár szám', 'Terméknév'], as_index=False)['tölteni'].sum()` parancsot használja, és a végső exportált oszlopot átnevezi `Tölteni`-re.
* **Kimeneti séma:** Az exportált DataFrame oszlopai: `['Raktár szám', 'Terméknév', 'Tölteni', 'Kiírni']` (a `Kiírni` oszlop egy üres segédoszlop a nyomtatáshoz/ellenőrzéshez).

---

## 🎨 PDF és Excel Formázási Megjegyzések (Fontos a vizuális konzisztencia miatt)

* **Excel:** Az `xlsxwriter`-t használja, és alkalmazza a zebracsíkozást, meghatározott oszlopszélességeket és fejléc színt. Lásd az `app/app.py` fájlban található `with pd.ExcelWriter(..., engine='xlsxwriter')` blokkot.
* **PDF:** A `reportlab`-et használja ismételhető fejléc sorokkal és zebracsíkos háttérrel rendelkező táblázat felépítéséhez. A PDF generálás megpróbálja regisztrálni a **`DejaVuSans.ttf`** fájlt a magyar ékezetek támogatásához; ha ez nincs meg, visszavált a `Helvetica` betűtípusra (az ékezetek ekkor elvesznek). A kódban hivatkozott betűtípus fájlnév: **`DejaVuSans.ttf`**.

---

## ▶️ Futtatás / Fejlesztési Munkafolyamat

* Telepítsd a függőségeket az `app` mappából, vagy hozz létre egy venv környezetet, majd futtasd a `pip install -r app/requirements.txt` parancsot.
* Futtasd az alkalmazást helyben Streamlit segítségével az adattár gyökérkönyvtárából:

```powershell
cd app; streamlit run app.py
* Az alkalmazás elvárja, hogy a **`DejaVuSans.ttf`** betűtípus fájl elérhető legyen a munkakönyvtárban az ékezetes PDF exportáláshoz. Ha hiányzik, a PDF akkor is létrejön, de magyar ékezetek nélkül.

---

## 🔍 Mire figyelj a Szerkesztésnél

* Őrizd meg a **pontos magyar oszlopneveket**, vagy frissítsd a fejléc-azonosítási logikát, és jegyezd fel a változást ebben a fájlban.
* Az exportálási formátumok módosításakor frissítsd mind az Excel `xlsxwriter` formázási blokkját, mind a ReportLab táblázatstílusait, hogy az XLSX és a PDF **vizuálisan konzisztensek** maradjanak.
* Tartsd a be-/kimenetet memóriában (`BytesIO`) – az `st.download_button` attól függ, hogy puffereket kap.
## ❓ Mikor kérdezd az Adattár Tulajdonosát

* Ha **oszlopneveket** akarsz változtatni, erősítsd meg a kanonikus magyar neveket és azt, hogy léteznek-e feltöltött Excel variánsok.
* Ha **automatizált teszteket** vagy **CI-t** (Folyamatos Integrációt) adsz hozzá, erősítsd meg az elvárt mintabemeneti fájlokat és az elfogadható PDF betűtípus viselkedést.

Ha valami nem világos, vagy több példát szeretnél (egységtesztek, CI lépések, minta bemeneti fájlok), mondd meg, melyik részt bontsam ki, és segítek.