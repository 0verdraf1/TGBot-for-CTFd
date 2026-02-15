import pandas as pd
from docx import Document
from docx2pdf import convert
import os
import time


def create_certificates():
    excel_file = 'table.xlsx'  # таблица из выгрузки резултатов
    template_file = 'Sertificate.docx'  # шаблон сретификата

    try:
        df = pd.read_excel(excel_file, usecols="B,D", header=None, names=['tg_id', 'fio'])
    except Exception as e:
        print(f"Ошибка при чтении Excel: {e}")
        return

    print(f"Найдено строк: {len(df)}")

    for index, row in df.iterrows():
        tg_id = str(row['tg_id']).strip()
        fio = row['fio']

        if pd.isna(fio) or pd.isna(tg_id) or tg_id == 'nan':
            continue

        fio_clean = str(fio).strip().upper()

        print(f"Обработка: {fio_clean} -> {tg_id}.pdf")

        try:
            doc = Document(template_file)
        except FileNotFoundError:
            print(f"Не найден файл шаблона: {template_file}")
            return

        target_paragraph_index = 11

        if len(doc.paragraphs) > target_paragraph_index:
            p = doc.paragraphs[target_paragraph_index]

            if p.runs:
                p.runs[0].text = fio_clean

                for run in p.runs[1:]:
                    run.text = ''
            else:
                p.add_run(fio_clean)
        else:
            print(f"Ошибка: В документе меньше 12 строк. Пропуск {tg_id}")
            continue

        temp_docx = f"{tg_id}.docx"
        final_pdf = f"{tg_id}.pdf"

        doc.save(temp_docx)

        try:
            convert(temp_docx, final_pdf)
        except Exception as e:
            print(f"Ошибка конвертации PDF для {tg_id}: {e}")
        finally:
            if os.path.exists(temp_docx):
                time.sleep(1)
                os.remove(temp_docx)

    print("Готово.")


if __name__ == "__main__":
    create_certificates()
