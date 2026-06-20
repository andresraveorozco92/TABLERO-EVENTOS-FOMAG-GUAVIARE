import pandas as pd
import sqlite3
import os
import glob
import re

DATA_DIR = r"C:\Users\FOMAG\OneDrive - fomag.gov.co (1)\ANALISTA DE DATOS\Antigravity Entornos Programación\VARIOS PERSONAL\EVENTOS SEMANA EPIDEMIOLOGICA"
DB_PATH = "eventos.db"

def extract_year_from_filename(filename):
    match = re.search(r'(\d{4})', filename)
    if match:
        return int(match.group(1))
    return None

def update_database():
    print(f"Buscando archivos Excel en: {DATA_DIR}")
    excel_files = glob.glob(os.path.join(DATA_DIR, "REPORTE DE EVENTOS - *.xlsx"))
    
    if not excel_files:
        print("Error: No se encontraron archivos Excel.")
        return

    all_data = []
    
    for file in excel_files:
        year = extract_year_from_filename(os.path.basename(file))
        if year is None:
            print(f"Advertencia: No se pudo extraer el año de {file}. Se omitirá.")
            continue
            
        print(f"Procesando {os.path.basename(file)} para el año {year}...")
        try:
            df = pd.read_excel(file)
            
            # Limpieza básica
            if 'Responsable' in df.columns:
                df = df.drop(columns=['Responsable'])
                
            # Limpiar nombres de columnas
            df.columns = [col.strip() for col in df.columns]
            
            # Agregar columna de Año
            df['Año'] = year
            
            all_data.append(df)
        except Exception as e:
            print(f"Error procesando {file}: {e}")

    if not all_data:
        print("No hay datos para actualizar.")
        return

    # Combinar todos los años
    final_df = pd.concat(all_data, ignore_index=True)
    
    try:
        # Conectar a SQLite
        print(f"Conectando a base de datos SQLite en: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        
        # Guardar en la base de datos (reemplazamos todo)
        final_df.to_sql('eventos', conn, if_exists='replace', index=False)
        
        print("Base de datos actualizada correctamente.")
        
        # Verificar
        count = pd.read_sql("SELECT COUNT(*) as total FROM eventos", conn).iloc[0]['total']
        print(f"Total de registros en la base de datos: {count}")
        
        conn.close()
    except Exception as e:
        print(f"Error al actualizar la base de datos: {e}")

if __name__ == "__main__":
    update_database()
