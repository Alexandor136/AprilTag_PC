import os

def print_directory_structure(root_dir, indent=0):
    """
    Функция для рекурсивного вывода структуры директории.
    - root_dir: путь к корневой директории (например, '.')
    - indent: уровень отступа для дерева
    """
    try:
        # Получаем список элементов в директории
        items = os.listdir(root_dir)
    except PermissionError:
        print('  ' * indent + f"[Нет доступа к директории: {root_dir}]")
        return
    
    # Сортируем для лучшей читаемости (папки сначала)
    items.sort(key=lambda x: (not os.path.isdir(os.path.join(root_dir, x)), x.lower()))
    
    for item in items:
        item_path = os.path.join(root_dir, item)
        # Печатаем элемент с отступом
        if os.path.isdir(item_path):
            print('  ' * indent + f"📁 {item}/")  # Эмодзи для папки
            print_directory_structure(item_path, indent + 1)  # Рекурсия
        else:
            print('  ' * indent + f"📄 {item}")  # Эмодзи для файла

# Укажи путь к корневой директории ('.' для текущей папки)
root_dir = '.'
print(f"Структура проекта в директории: {os.path.abspath(root_dir)}")
print_directory_structure(root_dir)
