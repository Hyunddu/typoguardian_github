import json

with open('git_package_list.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

unique_values = set()
for value_list in data.values():
    unique_values.update(value_list)

with open('values_only.json', 'w', encoding='utf-8') as file:
    json.dump(list(unique_values), file, ensure_ascii=False, indent=4)
