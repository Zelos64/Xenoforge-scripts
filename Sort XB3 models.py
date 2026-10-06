import pandas
import os
import shutil
import pathlib


print(pandas.__version__)
quit()

CONFIGURATIONS = [
    # Configuration for "Main Six (Chx1)"
    {
        'sheet': 'Main Six (Chx1)',
        'usecols': 'A:L',
        'skiprows': [0],
        'tasks':
        [
            {'new_folder': r'chr\ch\Main Six (Chx1)\Noah',     'cols': [0, 1], 'format': '{0} ({1})'},
            {'new_folder': r'chr\ch\Main Six (Chx1)\Mio',      'cols': [2, 3], 'format': '{0} ({1})'},
            {'new_folder': r'chr\ch\Main Six (Chx1)\Eunie',    'cols': [4, 5], 'format': '{0} ({1})'},
            {'new_folder': r'chr\ch\Main Six (Chx1)\Taion',    'cols': [6, 7], 'format': '{0} ({1})'},
            {'new_folder': r'chr\ch\Main Six (Chx1)\Lanz',     'cols': [8, 9], 'format': '{0} ({1})'},
            {'new_folder': r'chr\ch\Main Six (Chx1)\Sena',   'cols': [10, 11], 'format': '{0} ({1})'}
        ]
    },
                 
    # Configuration for "ch02/03/04 (Forms, Heros, Story)"
    {
        'sheet': 'ch020304 (Forms, Heros, Story)',
        'usecols': 'A:F',
        'skiprows': [0],
        'tasks':
        [
            {'new_folder': r'chr\ch\Forms',    'cols': [0, 1], 'format': '{0} ({1})'},
            {'new_folder': r'chr\ch\Heroes',   'cols': [2, 3], 'format': '{0} ({1})'},
            {'new_folder': r'chr\ch\Story',    'cols': [4, 5], 'format': '{0} ({1})'}
        ]
    },

    # Configuration for "Base Game - wp, en, oj, Maps"
    {
        'sheet': 'Base Game - wp, en, oj, Maps',
        'usecols': 'A:K',
        'skiprows': [0, 1],
        'tasks':
        [
            {'new_folder': r'chr\en', 'cols': [0, 1],    'format': '{0} ({1})'},
            {'new_folder': r'chr\wp', 'cols': [4, 5, 6], 'format': '{0} ({1} - {2})'},
            {'new_folder': r'chr\oj', 'cols': [8, 9],    'format': '{0} ({1})'}
        ]
    },

    # Configuration for "ch05/06 (NPC Parts)"
    {
        'sheet': 'ch0506 (NPC Parts)',
        'usecols': 'A:D',
        'skiprows': [0],
        'tasks':
        [
            {'new_folder': r'chr\ch\NPC Parts', 'cols': [0, 1, 2, 3], 'format': '{0} ({1} - {2} - {3})'}
        ]
    },
]

def sanitize_name(name):
    # Clean folder's name of special characters and replace by "§"
    replace_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in replace_chars:
        name = name.replace(char, '§')
    return name

def process(config, excel_path, game_path):
    try:
        df = pandas.read_excel(
            excel_path,
            sheet_name=config['sheet'],
            usecols=config['usecols'],
            skiprows=config['skiprows'],
            header=0 if config['skiprows'] is None else None)
        print(f"\nProcessing sheet: {config['sheet']}")
        print(df.head(5)) # Show first 5 rows for preview
        
        for task in config['tasks']:
            for _, row in df.iterrows():
                # Take files ID (only from the first column of task['cols'])
                file_id = str(row.iloc[task['cols'][0]]).strip()
                if not file_id or file_id == 'nan': continue
                
                # Take the description (from other columns of task['cols'])
                descriptions = [
                    str(row.iloc[col]).strip() 
                    for col in task['cols'][1:]
                    if not pandas.isna(row.iloc[col])
                ]
                
                # Create folders name
                dest_folder = os.path.join(game_path, task['new_folder'])
                folder_name = f"{file_id} ({' - '.join(descriptions)})" if descriptions else file_id
                folder_path = os.path.join(dest_folder, sanitize_name(folder_name))
                os.makedirs(folder_path, exist_ok=True)
                
                # Search and move files
                for root, _, files in os.walk(game_path):
                    for file in files:
                        if file.split('.')[0] == file_id:
                            src_file = os.path.join(root, file)
                            shutil.move(src_file, os.path.join(folder_path, file))
                            print(f"✓ {file} → {folder_name}")

    except Exception as e:
        print(f"Error processing {config['sheet']}: {str(e)}")

def main():
    game_chosen = input("Which game did you want to sort ? (XB1, XB1:DE, XBX, XBX:DE, XB2, XB3) : ")
    print("Download the following excel-format file wherever you want.")
    print("https://docs.google.com/spreadsheets/d/12wgzG4gIgd8iY6GyYw_ObsUTDjE0ZvE2CMNtX5WrWzs")

    print("By exemple : C:\\Users\\Geo\\Downloads\\Xenoblade 3 Models - Spoilers.xlsx")
    excel_path = input("Excel file path : ")
    if not pathlib.Path(excel_path).exists():
        print("Error: Excel file not found!")
        return
    
    print("By exemple : C:\\Users\\Geo\\Downloads\\Xenoblade 3 extracted")
    game_path = input(f"Extracted game files path for {game_chosen} : ")
    if not pathlib.Path(game_path).exists():
        print("Error: Game folder not found!")
        return
    
    for config in CONFIGURATIONS:
        process(config, excel_path, game_path)
    
    print("\nFile organization completed!")

if __name__ == "__main__":
    main()