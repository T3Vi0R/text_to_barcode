import csv
import os
import barcode # Główna biblioteka do kodów kreskowych
from barcode.writer import ImageWriter # Do zapisu jako obrazy (PNG, JPG itp.)
import logging # Do logowania błędów i informacji

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Konfiguracja ---
csv_file_path = 'kody.csv'  # Ścieżka do Twojego pliku CSV
output_dir = 'wygenerowane_kody_kreskowe' # Nazwa folderu na wygenerowane kody
# Ważne: Wybierz odpowiedni format kodu kreskowego!
# 'ean13' - Typowy dla produktów sklepowych (wymaga 12 cyfr!)
# 'code128' - Dobry dla kodów alfanumerycznych o zmiennej długości
# Inne dostępne: 'upca', 'isbn13', 'code39', etc.
barcode_format = 'ean13'
# Format pliku wyjściowego: 'PNG', 'SVG', 'JPEG' itp. (zależne od ImageWriter)
# SVG jest formatem wektorowym (dobra skalowalność), PNG jest rastrowy.
image_format = 'PNG'
# Opcje dla zapisu obrazu (np. cicha strefa, rozmiar modułu)
# Zobacz dokumentację python-barcode dla pełnej listy
writer_options = {
    'module_height': 15.0, # Wysokość kodu w mm
    'font_size': 10,       # Rozmiar czcionki tekstu pod kodem
    'text_distance': 5.0,  # Odległość tekstu od kodu w mm
    'quiet_zone': 6.5,     # Szerokość cichej strefy (marginesu) w mm
    'format': image_format.upper() # Format pliku wyjściowego dla ImageWriter
}
# Zakłada, że kody są w pierwszej kolumnie (indeks 0). Zmień w razie potrzeby.
csv_column_index = 0
# Czy plik CSV ma nagłówek, który należy pominąć?
has_header = True # Ustaw na False, jeśli plik nie ma nagłówka

# --- Główna logika skryptu ---

def generate_barcodes_from_csv(input_csv, output_folder, code_format, img_format, options, col_index, skip_header):
    """
    Generuje kody kreskowe z pliku CSV i zapisuje je jako obrazy.

    Args:
        input_csv (str): Ścieżka do pliku wejściowego CSV.
        output_folder (str): Ścieżka do folderu wyjściowego.
        code_format (str): Nazwa formatu kodu kreskowego (np. 'ean13', 'code128').
        img_format (str): Format pliku obrazu (np. 'PNG', 'SVG').
        options (dict): Opcje dla ImageWriter.
        col_index (int): Indeks kolumny z kodami w pliku CSV.
        skip_header (bool): Czy pominąć pierwszy wiersz (nagłówek).
    """
    logging.info(f"Rozpoczynam generowanie kodów kreskowych w formacie: {code_format}")
    logging.info(f"Plik wejściowy CSV: {input_csv}")
    logging.info(f"Folder wyjściowy: {output_folder}")

    # Sprawdzenie i utworzenie folderu wyjściowego, jeśli nie istnieje
    try:
        os.makedirs(output_folder, exist_ok=True)
        logging.info(f"Folder wyjściowy '{output_folder}' gotowy.")
    except OSError as e:
        logging.error(f"Nie można utworzyć folderu wyjściowego: {e}")
        return # Zakończ, jeśli nie można utworzyć folderu

    # Uzyskanie klasy kodu kreskowego na podstawie nazwy formatu
    try:
        barcode_class = barcode.get_barcode_class(code_format)
        logging.info(f"Używam klasy kodu kreskowego: {barcode_class.__name__}")
    except barcode.errors.BarcodeNotFoundError:
        logging.error(f"Nie znaleziono formatu kodu kreskowego: '{code_format}'. Sprawdź dostępne formaty.")
        return

    # Sprawdzenie poprawności formatu obrazu dla ImageWriter
    valid_image_formats = ['PNG', 'JPEG', 'BMP', 'GIF', 'TIFF', 'SVG'] # SVG jest obsługiwane inaczej
    if img_format.upper() not in valid_image_formats and img_format.lower() != 'svg':
         logging.warning(f"Format obrazu '{img_format}' może nie być w pełni wspierany przez domyślny ImageWriter (Pillow). Używam mimo to.")
         # ImageWriter spróbuje użyć Pillow; może zadziałać dla innych formatów wspieranych przez Pillow.

    processed_count = 0
    skipped_count = 0

    # Otwarcie i odczytanie pliku CSV
    try:
        with open(input_csv, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)

            # Pomiń nagłówek, jeśli ustawiono
            if skip_header:
                try:
                    header = next(reader)
                    logging.info(f"Pominięto nagłówek: {header}")
                except StopIteration:
                    logging.warning("Plik CSV jest pusty.")
                    return

            # Przetwarzanie każdego wiersza
            for i, row in enumerate(reader):
                row_number = i + (2 if skip_header else 1) # Numer wiersza w oryginalnym pliku
                try:
                    if len(row) > col_index:
                        code_data = row[col_index].strip() # Pobierz kod i usuń białe znaki

                        if not code_data:
                            logging.warning(f"Pominięto pusty wpis w wierszu {row_number}.")
                            skipped_count += 1
                            continue

                        # --- Walidacja specyficzna dla EAN-13 ---
                        if code_format.lower() == 'ean13':
                            if not code_data.isdigit() or len(code_data) != 12:
                                logging.warning(f"Pominięto wiersz {row_number}: Kod '{code_data}' nie jest poprawnym 12-cyfrowym numerem wymaganym dla EAN-13.")
                                skipped_count += 1
                                continue
                        # --- Można dodać walidację dla innych formatów tutaj ---

                        # Wygenerowanie kodu kreskowego
                        try:
                            # Utwórz instancję kodu kreskowego (cyfra kontrolna np. dla EAN13 jest dodawana automatycznie)
                            generated_barcode = barcode_class(code_data, writer=ImageWriter())

                            # Przygotowanie nazwy pliku wyjściowego (bezpieczna nazwa)
                            safe_filename = "".join(c for c in code_data if c.isalnum() or c in ('-', '_')).rstrip()
                            if not safe_filename: # Jeśli kod zawierał tylko niebezpieczne znaki
                                safe_filename = f"kod_wiersz_{row_number}"
                            output_filename = f"{safe_filename}.{img_format.lower()}"
                            output_path = os.path.join(output_folder, output_filename)

                            # Zapisz kod kreskowy jako obraz, przekazując opcje
                            # Ważne: 'save' zwraca faktyczną nazwę pliku (czasem może się różnić)
                            actual_filename = generated_barcode.save(output_path.replace(f'.{img_format.lower()}', ''), options=options) # Przekazujemy bez rozszerzenia, writer doda sam
                            logging.info(f"Wygenerowano kod kreskowy dla '{code_data}' i zapisano jako: {actual_filename}")
                            processed_count += 1

                        except Exception as e: # Złap błędy podczas generowania/zapisu pojedynczego kodu
                            logging.error(f"Błąd podczas przetwarzania kodu '{code_data}' z wiersza {row_number}: {e}")
                            skipped_count += 1

                    else:
                        logging.warning(f"Pominięto wiersz {row_number}: Wiersz ma za mało kolumn (wymagany indeks {col_index}).")
                        skipped_count += 1

                except Exception as e: # Ogólny błąd przetwarzania wiersza
                    logging.error(f"Nieoczekiwany błąd podczas przetwarzania wiersza {row_number}: {e}")
                    skipped_count += 1

    except FileNotFoundError:
        logging.error(f"Błąd: Nie znaleziono pliku CSV: {input_csv}")
    except Exception as e:
        logging.error(f"Wystąpił nieoczekiwany błąd podczas odczytu pliku CSV: {e}")

    logging.info(f"Zakończono przetwarzanie. Wygenerowano: {processed_count} kodów kreskowych. Pominięto: {skipped_count} wpisów.")

# --- Uruchomienie skryptu ---
if __name__ == "__main__":
    generate_barcodes_from_csv(
        input_csv=csv_file_path,
        output_folder=output_dir,
        code_format=barcode_format,
        img_format=image_format,
        options=writer_options,
        col_index=csv_column_index,
        skip_header=has_header
    )