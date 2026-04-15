import json
import pandas as pd
import requests

def fetch_api_swagger_json(url, save_to_filepath=None) -> object:
    """
    Attempts to fetch json from the provided endpoint.

    Arguments:
    url: url to the remote swagger.json file
    save_to_filepath (optional): Relative path (where to save json file)

    Returns: Response object (if successful)
    """

    response = requests.get(url)

    data = response.json()

    if (save_to_filepath):
        with open(save_to_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("JSON saved successfully")
        
    print("Fetched successfully!")
    return data

def load_from_json(path_to_pec) -> object:
    with open(path_to_pec, 'r') as f:
        return json.load(f)

def fetch_schema(spec, schema_name):
    """
    Finds schema by its name in a dedicated spec object.

    Arguments:
    spec: Object representing swagger specification
    schema_name: schema name of iterest

    Returns: Pandas DataFrame representing found field name and its type
    """

    schema_object = spec['definitions'][schema_name]['properties']
    parsed_schema = parse_schema(schema_object)

    return pd.DataFrame(parsed_schema).sort_values(by='field')

def parse_schema(schema):
    """
    Parses schema based on my heuristics.

    NOTE:
    Since this is just a heuristic, these are the rules I developed for it:
    - if `type` is `string` or `boolean`, this is sufficient
    - if `string` has `format`, append it to the resulting type
    - if `type` is `integer`, it has `format`, add it to the resulting type
    - if `type` is `number`, it has `format`, add it to the resulting type (it is likely double)
    - if `type` is `array`, it must have `items`; then search for its type according to previous rules

    Arguments:
    schema: Object representing schema of interest

    Returns: List of found keys with their types
    """

    references = []
    
    for key, value in schema.items():
        row = { 'field': key }

        match value:
            case {'$ref': ref}:
                # just ref, i.e. link to another entity
                entity = ref.split('/')[-1]
                row['type'] = entity
            case {'type': 'array', 'items': { 'type': field_type }}:
                # likely this is a string then
                row['type'] = f'Array <Primitive<{field_type}>>'
            case {'type': 'array', 'items': { '$ref': ref }}:
                entity = ref.split('/')[-1]
                row['type'] = f'Array <{entity}>'
            case {'type': 'integer', 'format': int_format}:
                row['type'] = f'Primitive <{int_format}>'
            case {'type': 'number', 'format': number_format}:
                row['type'] = f'Primitive <{number_format}>'
            case {'type': 'string', 'format': string_format}:
                row['type'] = f'Primitive <string ({string_format})>'
            case {'type': 'string'}:
                row['type'] = f'Primitive <string>'
            case {'type': simple_type}:
                row['type'] = f'Primitive <{simple_type}>'
            case _:
                row['type'] = 'UNKNOWN'
        
        references.append(row)
    
    return references

def count_field_frequences(items, keys):
    """
    Calculates field frequency in the sample.

    Arguments:
    items: List of objects to analyze
    keys: List of keys that should be searched

    Returns: tuple of `key_frequences`, `unknown_key_frequences`.
    Each of those is a dictionary, key - field name, value - number of occurences in the sample.
    `key_frequences` - number of occurences specified in the `keys` list.
    `unknown_key_frequences` - number of occurences for fields that were not provided in the inital `keys` list, yet present in the sample.

    """

    key_frequences = dict.fromkeys(keys, 0)
    unknown_key_frequences = dict()

    for item in items:
        for key in item.keys():
            if key in key_frequences.keys():
                key_frequences[key] += 1
            else:
                if key in unknown_key_frequences.keys():
                    unknown_key_frequences[key] += 1
                else:
                    unknown_key_frequences[key] = 1

    return key_frequences, unknown_key_frequences

