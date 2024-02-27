from datetime import datetime, timedelta
from CareEpisode import CareEpisode, diagnosis_to_episode_diagnosis
import re
from icd_code_to_category import add_icd_code_to_dictionary, make_diagnosis_categories, elixhauser_to_icd9

psychiatric_regular_expression = re.compile('(anxi|depress|psych|suicid|homicid|aggress|panic|agitat|hallucin|addict|manic|mania|bipola|paranoi|behavior|schizo|stress|adhd)', re.IGNORECASE)
suicidal_regular_expression = re.compile('suicid', re.IGNORECASE)
substance_use_regular_expression = re.compile('(intoxication|withdrawal|delirium tremens|alcohol problem|dependence)', re.IGNORECASE)

# Epic medicine categories.
epic_medicine_categories = [ 'Aminoglycosides', 'Analgesics-Narcotic', 'Analgesics-Nonnarcotic', 'Androgen-Anabolic', 'Anorectal', 'Antacids', 'Anthelmintic', 'Anti-Rheumatic', 'Antianginal Agents', 'Antianxiety Agents', 'Antiarrhythmic', 'Antiasthmatic', 'Anticoagulants', 'Anticonvulsant', 'Antidepressants', 'Antidiabetic', 'Antidiarrheals', 'Antidotes', 'Antiemetics', 'Antifungals', 'Antihistamines', 'Antihyperlipidemic', 'Antihypertensive', 'Antimalarial', 'Antimyasthenic Agents', 'Antimycobacterial Agents', 'Antineoplastics', 'Antiparkinsonian', 'Antipsychotics', 'Antiseptics and Disinfectants', 'Antisera', 'Antiviral', 'Assorted Classes', 'Beta Blockers', 'Calcium Blockers', 'Cardiotonics', 'Cardiovascular', 'Cephalosporins', 'Chemicals', 'Contraceptives', 'Corticosteroids', 'Cough/Cold', 'Decongestants', 'Dermatological', 'Diagnostic Products', 'Dietary Products', 'Digestive Aids', 'Diuretics', 'Estrogens', 'Fluoroquinolones', 'General Anesthetics', 'Gout', 'Hematopoietic Agents', 'Hemostatics', 'Hypnotics', 'Laxatives', 'Local Anesthetics-Parenteral', 'Macrolide Antibiotics', 'Medi-Span Reserved Or Unknown(95)', 'Medical Devices', 'Migraine Products', 'Minerals and Electrolytes', 'Misc. Antiinfectives', 'Misc. Endocrine', 'Misc. Genitourinary Products', 'Misc. Gi', 'Misc. Hematological', 'Misc. Psychotherapeutic', 'Misc. Respiratory', 'Mouth and Throat (Local)', 'Multivitamins', 'Neuromuscular Blockers', 'Nutrients', 'Ophthalmic', 'Otic', 'Oxytocics', 'Penicillins', 'Pharmaceutical Adjuvants', 'Pressors', 'Progestins', 'Skeletal Muscle Relaxants', 'Stimulants', 'Sulfonamides', 'Tetracyclines', 'Thyroid', 'Toxoids', 'Ulcer Drugs', 'Urinary Antiinfectives', 'Urinary Antispasmodics', 'Vaccines', 'Vaginal Products', 'Vitamins', 'NA' ]
default_epic_medicine_category_values = {}
for category in epic_medicine_categories:
    default_epic_medicine_category_values[category] = -9999

# Custom medicine categories.
custom_medicine_category_to_regular_expression = {
    'MoodStabilizer_custom': re.compile('(Lithium|Valpro|Lamotrigine|Carbamazepine)', re.IGNORECASE),
    'Antipsychotic_custom': re.compile('(Aripiprazole|Risperidone|Olanzapine|Quetiapine|Asenapine|Paliperidone|Ziprasidone|Lurasidone|Haloperidol|Chlorpromazine|Amisulpride)', re.IGNORECASE),
    'Anxiolytics_custom': re.compile('(Alprazolam|Bromazepam|Chlordiazepoxide|Clonazepam|Clorazepate|Diazepam|Flurazepam|Lorazepam|Oxazepam|Temazepam|Triazolam)', re.IGNORECASE),
    'Antidepressants_custom': re.compile('(Citalopram|Escitalopram|Paroxetine|Fluoxetine|Fluvoxamine|Sertraline|Desvenlafaxine|Duloxetine|Levomilnacipran|Milnacipran|Venlafaxine|Vilazodone|Vortioxetine|Nefazodone|Trazodone|Reboxetine|Teniloxazine|Viloxazine|Bupropion|Amitriptyline|Amitriptylinoxide|Clomipramine|Desipramine|Dibenzepin|Dimetacrine|Dosulepin|Doxepin|Imipramine|Lofepramine|Melitracen|Nitroxazepine|Nortriptyline|Noxiptiline|Opipramol|Pipofezine|Protriptyline|Trimipramine|Amoxapine|Maprotiline|Mianserin|Mirtazapine|Setiptiline|Isocarboxazid|Phenelzine|Tranylcypromine|Selegiline)', re.IGNORECASE),
}
custom_medicine_categories = custom_medicine_category_to_regular_expression.keys()
default_custom_medicine_category_values = {}
for category in custom_medicine_categories:
    default_custom_medicine_category_values[category] = -9999

date_format = '%Y-%m-%d'

default_diagnoses_list = make_diagnosis_categories()
default_diagnoses = {}
for item in default_diagnoses_list:
    default_diagnoses[item] = -9999

def date_to_string(date):
    global date_format
    return date.strftime(date_format)


def timestamp_to_date(timestamp):
    return date_to_string(datetime.strptime(timestamp, '%m/%d/%y %H:%M'))


def date_to_datetime(date):
    return datetime.strptime(date, date_format)


class Patient:
    def __init__(self, id):
        self.id = id
        self.care_episodes = {}
        self.age_of_first_admit = -9999
        self.gender = -9999
        self.race = -9999
        self.ethnicity = -9999
        self.epic_medicines = default_epic_medicine_category_values.copy()
        self.custom_medicines = default_custom_medicine_category_values.copy()
        self.diagnoses = default_diagnoses.copy()
        self.zip_code = -9999

        # Used to cache a common accessed list of information during CSV generation.
        self.episodes_and_days = None

    def get_elixhauser_walraven_score(self):

        '''
            Scoring from paper:
            A Modification of the Elixhauser Comorbidity Measures Into a Point System for Hospital Death Using Administrative Data
            Carl van Walraven, Peter C. Austin, Alison Jennings, Hude Quan, and Alan J. Forster
        '''
        category_to_points = {
            'congestive_heart_failure': 7,
            'cardiac_arrhythmia': 5,
            'valvular_disease': -1,
            'pulmonary_circulation_disorder': 4,
            'peripheral_vascular_disorder': 2,
            'hypertension_uncomplicated': 0,
            'hypertension_complicated': 0,
            'paralysis': 7,
            'other_neurological_disorder': 6,
            'chronic_pulmonary_disease': 3,
            'diabetes_uncomplicated': 0,
            'diabetes_complicated': 0,
            'hypothyroidism': 0,
            'renal_failure': 5,
            'liver_disease': 11,
            'peptic_ulcer_disease_excluding_bleeding': 0,
            'aids_hiv': 0,
            'lymphoma': 9,
            'metastatic_cancer': 12,
            'solid_tumor_wo_metastasis': 4,
            'rheumatoid_arhritis': 0,
            'coagulopathy': 3,
            'obesity': -4,
            'weight_loss': 6,
            'fluid_and_electrolyte_disorders': 5,
            'blood_loss_anemia': -2,
            'deficiency_anemia': -2,
            'alcohol_abuse': 0,
            'drug_abuse': -7,
            'psychoses': 0,
            'depression': -3,
        }

        elixhauser_walraven_score = sum(
            [ self.diagnoses[category] * category_to_points[category] for category in elixhauser_to_icd9.keys() ]
        )

        return elixhauser_walraven_score if elixhauser_walraven_score >= 0 else -9999

    def add_episode_from_charges(self, row):
        encounter_id = row['STUDY_CSN']
        encounter = self.find_encounter_by_id(encounter_id)

        # Ensure this encounter doesn't exist already.
        if encounter:
            encounter.add_charge(row['AMOUNT'])
        else:
            date = timestamp_to_date(row['SERVICE_DATE'])
            if date not in self.care_episodes:
                self.care_episodes[date] = CareEpisode(date)
            self.care_episodes[date].add_encounter_from_charges(row)


    def add_episode_from_readmissions(self, row):
        global date_format
        date = timestamp_to_date(row['EFFECTIVE_DATE_DT'])

        # Flag this date as a hospitalization.
        if date not in self.care_episodes:
            self.care_episodes[date] = CareEpisode(date)
        self.care_episodes[date].does_include_hospitalization = True
        self.care_episodes[date].add_encounter_by_encounter_id(row['STUDY_CSN'])

        # Flag the previous date as a hospitalization.
        previous_date_object = datetime.strptime(date, date_format) - timedelta(days=int(row['DIFF_IN_DAYS']))
        previous_date = date_to_string(previous_date_object)
        if previous_date not in self.care_episodes:
            self.care_episodes[previous_date] = CareEpisode(previous_date)
        self.care_episodes[previous_date].does_include_hospitalization = True
        self.care_episodes[date].add_encounter_by_encounter_id()

    def add_demographics(self, row):
        self.age_of_first_admit = int(row['AGE_AS_OF_1ST_ADMIT'])
        self.gender = row['gender']
        self.race = row['race']
        self.ethnicity = row['ethnicity']

    def add_zip_demographics(self, row):
        self.zip_code = row['ZIP_1ST_3']

    def add_epic_medication_categories(self, row):
        medicines = dict(row)
        del medicines['']
        del medicines['DEID_PATIENT_NUM']
        del medicines['MED_START_DATE']

        # If medicine is being taken (i.e, >0), then medicine should stay as taken (i.e., 1). Otherwise, set medicine to 0.
        for category in epic_medicine_categories:
            medicine_value = 1 if int(medicines[category]) > 0 else 0

            if medicine_value == 1:
                self.epic_medicines[category] = 1
            elif self.epic_medicines[category] != 1:
                self.epic_medicines[category] = 0

    def add_medications(self, row):
        for category in custom_medicine_categories:
            regular_expression = custom_medicine_category_to_regular_expression[category]
            medicine_value = 1 if regular_expression.match(row['MEDICATION_NAME']) else 0

            if medicine_value == 1:
                self.custom_medicines[category] = 1
            elif self.custom_medicines[category] != 1:
                self.custom_medicines[category] = 0

    def add_pain_score(self, row):
        encounter_id = row['STUDY_CSN']
        encounter = self.find_encounter_by_id(encounter_id)

        # Ensure this encounter doesn't exist already.
        if encounter:
            encounter.add_pain_score(int(row['VITAL_SIGN_VALUE']))
        else:
            date = timestamp_to_date(row['VITAL_SIGN_TAKEN_TIME'])
            if date not in self.care_episodes:
                self.care_episodes[date] = CareEpisode(date)
            self.care_episodes[date].add_encounter_by_encounter_id(encounter_id)
            self.care_episodes[date].add_pain_score_to_encounter(encounter_id, row['VITAL_SIGN_VALUE'])

    def find_encounter_by_id(self, encounter_id):
        for episode in self.care_episodes.values():
            for encounter in episode.encounters.values():
                if encounter.id == encounter_id:
                    return encounter
        return None

    def add_encounter_diagnosis(self, row):
        encounter_id = row['STUDY_CSN']
        encounter = self.find_encounter_by_id(encounter_id)
        is_primary_diagnosis = (row['PRIMARY_DIAGNOSIS_FLAG'] == 'P') or (row['ADMISSION_DIAGNOSIS_FLAG'] == 'Y')
        if encounter:
            icd_code = row['ICD_CODE'].replace('.', '')
            encounter.add_diagnosis(icd_code, row['ICD_DESCRIPTION'], is_primary_diagnosis)

    def add_visit(self, row):
        encounter_year = int(row['ENCOUNTER_YEAR'])

        # Outside this range is probably a typo.
        if 2006 <= encounter_year <= 2017:
            for date, care_episode in self.care_episodes.items():
                care_datetime = date_to_datetime(date)
                if encounter_year == (care_datetime.year - 1):
                    care_episode.add_visit_type(encounter_year, row['VISIT_TYPE'], int(row['TOTAL (Visits per Year)']))

    def add_chief_complaints(self, row):
        encounter_id = row['STUDY_CSN']
        encounter = self.find_encounter_by_id(encounter_id)

        if encounter:
            complaints = row['CHIEF_COMPLAINT_LIST'].split('|')
            medical = False
            psychiatric = False
            suicidal = False
            substance_use = False
            for complaint in complaints:
                if psychiatric_regular_expression.match(complaint):
                    psychiatric = True
                else:
                    medical = True

                if suicidal_regular_expression.match(complaint):
                    suicidal = True

                if substance_use_regular_expression.match(complaint):
                    substance_use = True

            encounter.add_chief_complaints(medical, psychiatric, suicidal, substance_use)

    def build_episodes_and_days(self, current_care_episode):
        if not self.episodes_and_days:
            care_episodes = [ care_episode for care_episode in self.care_episodes.values() if len(care_episode.encounters) ]
            self.episodes_and_days = [ { 'episode': care_episode, 'days': date_to_datetime(care_episode.date) } for care_episode in care_episodes ]

        # Day 0 is the day that the patient was discharged.
        admit_day = date_to_datetime(current_care_episode.date)
        length_of_stay = max(current_care_episode.get_length_of_stay(), 0)
        day0 = admit_day + timedelta(days=length_of_stay)

        return [
            { 'episode': episode_and_day['episode'], 'days': (episode_and_day['days'] - day0).days }
            for episode_and_day in self.episodes_and_days
        ]

    def get_days_until_psychiatric_rehospitalization(self, current_care_episode):
        if current_care_episode.is_psychiatric_hospitalization() == 1:
            episodes_and_days = self.build_episodes_and_days(current_care_episode)
            hospitalizations_and_days = [ episode_and_day for episode_and_day in episodes_and_days if episode_and_day['episode'].does_include_hospitalization == 1 ]
            days = [ hospitalization_and_day['days'] for hospitalization_and_day in hospitalizations_and_days ]
            days_since_hospitalization = [ day for day in days if day > 0 ]

            if days_since_hospitalization:
                return min(days_since_hospitalization)
        return -9999

    def had_prior_diagnosis(self, current_care_episode, diagnosis):
        episodes_and_days = self.build_episodes_and_days(current_care_episode)
        if episodes_and_days:

            # Filter out later hospitalizations.
            prior_episodes = [ episode_and_day['episode'] for episode_and_day in episodes_and_days if episode_and_day['days'] < 0 ]

            if prior_episodes:
                encounter_diagnosis = diagnosis_to_episode_diagnosis[diagnosis]
                had_prior_diagnosis = any([
                    prior_episode.get_episode_diagnoses()[encounter_diagnosis] == 1
                    for prior_episode in prior_episodes
                ])
                return 1 if had_prior_diagnosis else 0
        return -9999

    def get_next_hospitalizations_and_days_since(self, current_care_episode):
        episodes_and_days = self.build_episodes_and_days(current_care_episode)
        if episodes_and_days:
            hospitalizations_and_days = [ episode_and_day for episode_and_day in episodes_and_days if episode_and_day['episode'].does_include_hospitalization == 1 ]

            # Filter out prior hospitalizations.
            prior_hospitalizations_and_days = [ hospitalization_and_day for hospitalization_and_day in hospitalizations_and_days if hospitalization_and_day['days'] > 0 ]

            if prior_hospitalizations_and_days:
                return sorted(prior_hospitalizations_and_days, key=lambda k: k['days'])
        return None

    def get_days_until_rehospitalization(self, current_care_episode):
        next_hospitalizations_and_days = self.get_next_hospitalizations_and_days_since(current_care_episode)
        return next_hospitalizations_and_days[0]['days'] if next_hospitalizations_and_days else -9999

    def get_whether_rehospitalized_for_diagnosis(self, current_care_episode, diagnosis):
        next_hospitalizations_and_days = self.get_next_hospitalizations_and_days_since(current_care_episode)
        if next_hospitalizations_and_days:
            next_year_episodes = [ next_hospitalization_and_day['episode'] for next_hospitalization_and_day in next_hospitalizations_and_days if next_hospitalization_and_day['days'] <= 365 ]
            subsequent_diagnoses = [ next_year_episode.get_episode_diagnoses()[diagnosis] for next_year_episode in next_year_episodes ]
            if subsequent_diagnoses:
                return max(subsequent_diagnoses)
        return -9999

    def add_diagnoses_by_code(self, code):
        add_icd_code_to_dictionary(code, self.diagnoses)

    def count_previous_year_cares(self, care_episode_to_count_from):
        care_episode_to_count_from_datetime = date_to_datetime(care_episode_to_count_from.date)
        start_datetime = care_episode_to_count_from_datetime
        end_datetime = care_episode_to_count_from_datetime - timedelta(days=365)

        # Find care episodes going back 365 days.
        care_episodes_in_range = [
            care_episode for care_episode in self.care_episodes.values()
            if (end_datetime <= date_to_datetime(care_episode.date) < start_datetime) and len(care_episode.encounters)
        ]

        previous_year_hospital_cares = 0
        previous_year_non_hospital_cares = 0
        previous_year_total_cares = 0
        for care_episode in care_episodes_in_range:
            previous_year_total_cares = previous_year_total_cares + 1
            if care_episode.does_include_hospitalization:
                previous_year_hospital_cares = previous_year_hospital_cares + 1
            else:
                previous_year_non_hospital_cares = previous_year_non_hospital_cares + 1

        return previous_year_hospital_cares, previous_year_non_hospital_cares, previous_year_total_cares

    def add_encounters(self, row):
        encounter_id = row['STUDY_CSN']
        encounter = self.find_encounter_by_id(encounter_id)

        if encounter:
            encounter.add_discharge_disposition(row['HOSP_DISCHARGE_DISP'])
            encounter.add_length_of_stay(row['LENGTH_OF_STAY'])
            encounter.add_date_ranges(row['ENCOUNTER_DATE'], row['DISCHARGE_DATE'])
