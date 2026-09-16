import os

# Имя итогового файла
OUTPUT_FILE = "all_project_code.txt"

# Папки, которые скрипт будет полностью игнорировать
EXCLUDE_DIRS = {
    'venv', '.venv', '.git', '__pycache__', 
    '.idea', '.vscode', 'backups', 'garbage', '.json' # Добавил garbage и backups из твоего архива
}

# Расширения файлов, которые нам нужны
ALLOWED_EXTENSIONS = {'.py', '.json'}

def gather_code():
    project_root = os.path.abspath(os.path.dirname(__file__))
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(project_root):
            # Убираем ненужные папки, чтобы os.walk даже не заходил в них
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                
                # Игнорируем сам этот скрипт и итоговый файл
                if file == "gather_code.py" or file == OUTPUT_FILE:
                    continue
                    
                if ext in ALLOWED_EXTENSIONS:
                    filepath = os.path.join(root, file)
                    # Делаем красивый относительный путь (например: ui/input/input_tab.py)
                    rel_path = os.path.relpath(filepath, project_root)
                    
                    # Пишем красивый заголовок с путем к файлу
                    outfile.write("=" * 80 + "\n")
                    outfile.write(f"FILE PATH: {rel_path}\n")
                    outfile.write("=" * 80 + "\n")
                    
                    # Читаем код и записываем
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as infile:
                            outfile.write(infile.read() + "\n\n")
                    except Exception as e:
                        outfile.write(f"// ОШИБКА ЧТЕНИЯ ФАЙЛА: {e}\n\n")

if __name__ == '__main__':
    print("Начинаю сборку кода...")
    gather_code()
    print(f"Готово! Весь код собран в файл: {OUTPUT_FILE}")