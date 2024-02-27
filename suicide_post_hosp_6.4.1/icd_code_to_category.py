import json
from os import path

def build_map(filename):
    filepath = path.join('icd_code_maps', filename)
    category_to_codes = json.load(open(filepath))
    code_to_category = {}
    for category, codes in category_to_codes.items():
        for code in codes:
            if code not in code_to_category:
                code_to_category[code] = []
            code_to_category[code].append(category)
    return code_to_category, category_to_codes


# Build Elixhauser mappings.
icd_code_to_elixhauser_categories_mapping, elixhauser_to_icd9 = build_map('elixhauser_icd9.json')
tmp, elixhauser_to_icd10 = build_map('elixhauser_icd10.json')
icd_code_to_elixhauser_categories_mapping.update(tmp)

# Build custom mappings.
icd_code_to_custom_categories_mapping, custom_icd9 = build_map('custom_icd9.json')
tmp, custom_icd10 = build_map('custom_icd10.json')
icd_code_to_custom_categories_mapping.update(tmp)

def make_diagnosis_categories():
    return list(elixhauser_to_icd9.keys()) + list(custom_icd9.keys()) + ['suicide_attempt_likely']


def compute_suicide_attempt_likely(diagnoses):
    if diagnoses['suicide_attempt'] == 1:
        diagnoses['suicide_attempt_likely'] = 1
    elif diagnoses['suicide_attempt'] == 0:
        diagnoses['suicide_attempt_likely'] = max(diagnoses['suicide_attempt_likely'], 0)

    if diagnoses['injury_of_unknown_intent'] == 1:
        diagnoses['suicide_attempt_likely'] = 1
    elif diagnoses['injury_of_unknown_intent'] == 0:
        diagnoses['suicide_attempt_likely'] = max(diagnoses['suicide_attempt_likely'], 0)

    if (diagnoses['suicidal_ideation'] != -9999) and (diagnoses['injury'] != -9999):
        if (diagnoses['suicidal_ideation'] == 1) and (diagnoses['injury'] == 1):
            diagnoses['suicide_attempt_likely'] = 1
        else:
            diagnoses['suicide_attempt_likely'] = max(diagnoses['suicide_attempt_likely'], 0)


def add_icd_code_to_dictionary(icd_code, diagnoses_dict):
    elixhauser_categories = None
    try:
        elixhauser_categories = icd_code_to_elixhauser_categories_mapping[icd_code]
    except Exception:
        pass
    if elixhauser_categories is not None:
        for category in elixhauser_categories:
            add_diagnoses_by_category(category, diagnoses_dict)

    bipolar_categories = None
    try:
        bipolar_categories = icd_code_to_custom_categories_mapping[icd_code]
    except Exception:
        pass
    if bipolar_categories is not None:
        for category in bipolar_categories:
            add_diagnoses_by_category(category, diagnoses_dict)

    compute_suicide_attempt_likely(diagnoses_dict)


def add_diagnoses_by_category(category, diagnoses_dict):
    diagnoses_dict[category] = 1
    for diagnosis in diagnoses_dict:
        diagnoses_dict[diagnosis] = max(diagnoses_dict[diagnosis], 0)
