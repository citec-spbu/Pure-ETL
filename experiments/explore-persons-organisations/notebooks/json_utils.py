import json

def load_from_json(path: str) -> list:
    with open(path, 'r') as f:
        data = json.load(f)
    
    return data['items']

def find_top_level_keys(items: list) -> dict:
    # Find all top-level keys with their types
    
    top_level_keys = set()
    top_level_keys_typed = dict()

    for item in items:
        for key in item.keys():
            if key not in top_level_keys:
                top_level_keys.add(key)
                if key not in top_level_keys_typed:
                    top_level_keys_typed[key] = set()
                top_level_keys_typed[key].add(type(item[key]))
    
    return top_level_keys_typed

def describe_entity_from_json(path: str) -> dict:
    data = load_from_json(path)
    return find_top_level_keys(data)