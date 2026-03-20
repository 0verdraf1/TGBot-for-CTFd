import pandas as pd
from docx import Document
from docx2pdf import convert
import os
import time

# Тут у нас все ФИО участниц (определялись нейронкой) -> поменять на актуальные
female_names = [
    'Малакей Валерия Геннадьевна',
    'Бобылева Оксана Александровна',
    'Белорыбкина Влада Михайловна',
    'Ушакова Милена Юрьевна',
    'Белова Ксения Александровна',
    'Мальцева Арина Артемовна',
    'Королёва Алина Александровна',
    'Уарова Сардаана Николаевна',
    'Ханаева Анна Романовна',
    'Десятникова Маргарита Сергеевна',
    'Зайцева Глафира Сергеевна',
    'Бухарева Анастасия Руслановна',
    'Черных Ирина Александровна',
    'Потемкина Юлия Евгеньевна',
    'Початкина Софья Сергеевна',
    'Командирова Алёна Владимировна',
    'Кускова Карина Павловна',
    'Давыдова Полина Артемовна',
    'Иванова Эвелина Игоревна',
    'Кадура Елена Вячеславовна',
    'Белоусова Анастасия Алексеевна',
    'Болтрушевич Мирослава Станиславна',
    'Бутырева Виктория Дмитриевна',
    'Волкова Виктория Александровна',
    'Дербина Ксения Александровна',
    'Иванова Александрина Валериановна',
    'Коц Галина Родионовна',
    'Лопуха Кира',
    'Масина Алина Александровна',
    'Машкина Софья Денисовна',
    'Медведева Татьяна Романовна',
    'Наседкина Анна Сергеевна',
    'Парилова Кира Артуровна',
    'Перминова Юлия Александровна',
    'Плотникова Виолетта Евгеньевна',
    'Родченко Анфиса Сергеевна',
    'Саннинова Мария Константиновна',
    'Симко Вероника Андреевна',
    'Сыроватская Майя Витальевна',
    'Таурьянина Анастасия Николаевна',
    'Телюта Елизавета Владимировна',
    'Турьева Мария Андреевна',
    'Федоренко Анна Максимовна',
    'Фисенко Анна Владимировна',
    'Чепчигашева Алиса Сергеевна',
    'Чичкова Диана Тимофеевна',
    'Шаповалова Мария Владимировна',
    'Шершнева Алина Юрьевна',
    'Янова Мария Максимовна'
]

female_names_set = {name.strip() for name in female_names}


def create_certificates():
    """
    Функция создания сертификатов участников по шаблону.
    - В usecols буквы столбцов, в которых tg_id (телеграм_id для подписи
    pdf-ки) и fio (ФИО для заполнения сертификата).
    ! изменение шаблона Sertificate.docx (количества абзацей и тп влечет за
    собой изменение этого кода, например, параметра target_paragraph_index).
    """
    excel_file = 'table.xlsx'           # эксель-таблица, получаемая по кнопке "Выгрузить результаты"
    template_file = 'Sertificate.docx'  # шаблон сертифика (актуализировать его)

    try:
        df = pd.read_excel(excel_file, usecols="B,D", header=None, names=['tg_id', 'fio'])
    except Exception as e:
        print(f"Ошибка при чтении Excel: {e}")
        return

    print(f"Всего записей: {len(df)}")

    for index, row in df.iterrows():
        tg_id = str(row['tg_id']).strip()
        raw_fio = str(row['fio']).strip()

        if pd.isna(row['fio']) or pd.isna(tg_id) or tg_id == 'nan':
            continue

        fio_clean = raw_fio.upper()

        print(f"Обработка: {raw_fio}")

        try:
            doc = Document(template_file)
        except FileNotFoundError:
            print("Файл шаблона не найден!")
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

        verb_paragraph_index = 12
        if raw_fio in female_names_set:
            if len(doc.paragraphs) > verb_paragraph_index:
                p_verb = doc.paragraphs[verb_paragraph_index]
                for run in p_verb.runs:
                    if "принимал" in run.text:
                        run.text = run.text.replace("принимал", "принимала")
                        break
            else:
                print(f"Внимание: строки {verb_paragraph_index+1} нет в документе")

        temp_docx = f"{tg_id}.docx"
        final_pdf = f"{tg_id}.pdf"

        doc.save(temp_docx)

        try:
            convert(temp_docx, final_pdf)
        except Exception as e:
            print(f"Ошибка конвертации PDF: {e}")
        finally:
            time.sleep(1)
            if os.path.exists(temp_docx):
                try:
                    os.remove(temp_docx)
                except PermissionError:
                    print(f"Файл {temp_docx} занят, удалите вручную.")

    print("Готово!")


if __name__ == "__main__":
    create_certificates()
