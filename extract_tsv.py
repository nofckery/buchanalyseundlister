import pandas as pd
import os

# Excel-Datei einlesen
excel_file = 'booklooker_vorlage_neu.xls'
xls = pd.ExcelFile(excel_file)

# Für jedes Sheet eine TSV-Datei erstellen
for sheet_name in xls.sheet_names:
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    output_file = f"{sheet_name}.tsv"
    df.to_csv(output_file, sep='\t', index=False, encoding='utf-8')
    print(f"Erstellt: {output_file}")