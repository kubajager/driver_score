# grid.online Driver Scorecard

Interní nástroj pro zákaznickou podporu: rychlé vyhledání kurýra podle jména nebo `driver_id`, zobrazení segmentu, pořadí, skóre, metrik vůči benchmarkům a doporučení (silné stránky + na co se zaměřit).

## Spuštění

```bash
pip install -r requirements.txt
streamlit run app.py
```

Prohlížeč se otevře na `http://localhost:8501`.

## Data

Aplikace načítá Excel ze souboru:

**`data/Priority Booking 02-26 results.xlsx`**

Před prvním spuštěním zkopírujte tento soubor do složky `data/`. Očekávané listy: **OOH**, **HD Praha**, **HD Brno**, **HD Ostrava**, **HD Olomouc**, **HD HK**, **HD Plzen**.

### Aktualizace dat (měsíční)

1. Nahraďte soubor **`data/Priority Booking 02-26 results.xlsx`** novým exportem (stejná struktura).
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
