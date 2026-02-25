# grid.online Driver Scorecard

Interní nástroj pro zákaznickou podporu: rychlé vyhledání kurýra podle jména nebo `driver_id`, zobrazení segmentu, pořadí, skóre, metrik vůči benchmarkům a doporučení (silné stránky + na co se zaměřit).

## Spuštění

```bash
pip install -r requirements.txt
streamlit run app.py
```

Prohlížeč se otevře na `http://localhost:8501`.

## Data

**Excel nesmí být v Gitu** (soubor je v `.gitignore`). Repozitář může zůstat veřejný – data se načtou jinak.

### Lokální spuštění

Umístěte **`Priority Booking 02-26 results.xlsx`** do složky **`data/`**. Aplikace ho načte z disku.

### Nasazení (Streamlit Cloud atd.)

Excel nikdy necommitujte. Místo toho:

1. Nahrajte Excel do **soukromého** úložiště, které umí vrátit soubor na URL:
   - **Google Drive**: soubor → „Sdílet“ → „Kdokoli s odkazem“ → získejte odkaz ke stažení (např. `https://drive.google.com/uc?export=download&id=ID_SOUBORU`).
   - **Dropbox**: „Sdílet“ → „Vytvořit odkaz“ → v URL změňte `?dl=0` na `?dl=1` pro přímé stažení.
   - **OneDrive / S3 / vlastní server**: jakékoli soukromé URL, které vrací soubor (případně s tokenem v URL).

2. V **Streamlit Cloud** u projektu: **Settings → Secrets** a přidejte (bez mezery před `=`):
   ```toml
   excel_url = "https://docs.google.com/spreadsheets/d/VAS_ID/edit?usp=sharing"
   ```
   Stačí váš běžný odkaz na Google Sheets (úpravy nebo sdílení). Aplikace ho převede na export ve formátu xlsx. Tabulka musí být nastavená tak, že **„Kdokoli s odkazem může zobrazit“** (jinak export selže).  
   Nebo nastavte proměnnou prostředí **`EXCEL_URL`** na stejnou URL.

Aplikace při startu nejdřív zkusí lokální soubor v `data/`; pokud neexistuje, stáhne data z `excel_url` / `EXCEL_URL`. Data tak zůstanou mimo Git a nikdo je v repu neuvidí.

Očekávané listy v Excelu: **OOH**, **HD Praha**, **HD Brno**, **HD Ostrava**, **HD Olomouc**, **HD HK**, **HD Plzen**.

### Aktualizace dat (měsíční)

1. **Lokálně:** nahraďte soubor v **`data/`** novým exportem. **Při nasazení:** nahrajte nový Excel do stejného úložiště (stejná URL) nebo aktualizujte soubor na téže adrese.
2. Zachovejte názvy listů a názvy sloupců:
   - `full_name`, `contact_email`, `driver_id`, `primary_ride_type`, `working_city`, `rank`, `drivers_score`
   - Metriky: `Kvalita doručení`, `Efektivita jízdy`, `Zdvojené/otočky`, `Jízdy Po, Út, Pá`, `Zpoždění v jízdě`, `Zpoždění na příjezdu`, `Delivery Quality`
3. Po uložení souboru obnovte stránku v prohlížeči (F5). Data jsou cacheována; při dalším načtení se použije nový soubor.

Žádná migrace ani konfigurace není potřeba – stačí přepsat Excel a obnovit aplikaci.

## Funkce

- **Vyhledání**: podle celého nebo částečného jména, nebo podle `driver_id` (přesná nebo částečná shoda).
- **Více výsledků**: výběr z dropdownu (jméno, ID, město, segment).
- **Karta kurýra**: segment (OOH / HD + město), pořadí, `drivers_score`, eligibility (Top 20 % / Top 50 % / Zatím bez rezervací).
- **Metriky**: hodnota kurýra + P25 / P50 / P75 pro daný segment a vizuální pruh (pás P25–P75, medián, hodnota kurýra).
- **Silné stránky a doporučení**: odvozené od rozdílu k mediánu + předpřipravené české texty pro support.

## Zabezpečení a nasazení (24/7 pro support)

Při otevření aplikace se zobrazí přihlášení heslem. Výchozí heslo je **grid.@nline** (pro nasazení lze nastavit proměnnou prostředí `SCORECARD_PASSWORD`). Po přihlášení zůstane session aktivní v rámci prohlížeče; support tak může mít aplikaci otevřenou průběžně.

## Technické

- **Stack**: Streamlit, pandas, openpyxl.
- **Lokální**: žádné externí služby, žádné síťové volání (kromě načtení fontů z Google Fonts).
- Data se načítají s cache (TTL 5 min); při změně Excelu obnovte stránku.
