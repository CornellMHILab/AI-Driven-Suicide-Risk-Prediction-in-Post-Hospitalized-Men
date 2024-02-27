from numpy import nan
from Patient import epic_medicine_categories, custom_medicine_categories
from CareEpisode import encounter_diagnoses_list
from icd_code_to_category import make_diagnosis_categories, elixhauser_to_icd9
import csv
from numpy import array
from math import isnan

def load_episodes(aggregated_days):
    print('Loading episodes')
    care_episodes = []
    with open('analyzable_care_episodes_%ddays.csv' % aggregated_days, 'r', encoding='iso-8859-1') as encounters_file:
        reader = csv.DictReader(encounters_file)
        for row in reader:
            care_episodes.append(HospitalizationEpisode(row))
    return care_episodes


def get_medical_hospitalization_episodes(aggregated_days, use_serious_mental_illness_only=False, use_suicidal_ideation=False, use_suicide_attempt=True, use_suicide_attempt_broad=False, use_cdc_suicide_self_injury=False):
    initial_care_episodes = load_episodes(aggregated_days)

    # Remove hospitalizations that we don't know whether the next hospitalization included a suicide attempt.
    care_episodes = [ episode for episode in initial_care_episodes if not isnan(episode.get_suicidal_outcome(use_suicidal_ideation, use_suicide_attempt, use_suicide_attempt_broad, use_cdc_suicide_self_injury)) ]

    if use_serious_mental_illness_only:
        care_episodes = [ episode for episode in care_episodes if (episode.diagnoses['bipolar'] == 1) or (episode.diagnoses['psychosis'] == 1) or (episode.diagnoses['schizoaffective'] == 1) or (episode.diagnoses['depression'] == 1) ]

    predictors_labeled = [ episode.get_predictors() for episode in care_episodes ]
    predictors = array([ list(episode.values()) for episode in predictors_labeled ])
    outcomes = array([ episode.get_suicidal_outcome(use_suicidal_ideation, use_suicide_attempt, use_suicide_attempt_broad, use_cdc_suicide_self_injury) for episode in care_episodes ])

    care_episode_indices = [ initial_care_episodes.index(care_episode) for care_episode in care_episodes ]

    return predictors_labeled, predictors, outcomes, care_episode_indices


def get_bipolar_episodes(aggregated_days, outcome_days_until_rehospitalization, predictors_to_use=None, use_psychiatric_rehospitalization_outcome=False, use_bipolar_only=False):
    care_episodes = load_episodes(aggregated_days)

    if use_bipolar_only:
        care_episodes = [ care_episode for care_episode in care_episodes if care_episode.diagnoses['bipolar'] == 1 ]

    if use_psychiatric_rehospitalization_outcome:
        care_episodes = [ care_episode for care_episode in care_episodes if care_episode.is_psychiatric_hospitalization ]

    # Juliet note: Our research group decided these are unlikely to be useful for prediction as is, so removing medicines and diagnoses.
    all_predictors_labeled = [ episode.get_predictors(exclude_medicines_and_diagnoses=True) for episode in care_episodes ]

    if predictors_to_use is None:
        predictors_labeled = all_predictors_labeled
    else:
        predictors_labeled = []
        for episode in all_predictors_labeled:
            new_episode = {}
            for label, value in episode.items():
                if label in predictors_to_use:
                    new_episode[label] = value
            predictors_labeled.append(new_episode)

    predictors = array([ list(episode.values()) for episode in predictors_labeled ])
    outcomes = array([ episode.get_days_until_rehospitalization(outcome_days_until_rehospitalization, use_psychiatric_rehospitalization_outcome) for episode in care_episodes ])

    return predictors_labeled, predictors, outcomes


def handle_missing_data_int(value):
    int_value = int(value)
    if int_value == -9999:
        return nan
    return int_value


def handle_missing_data_float(value):
    try:
        if int(value) == -9999:
            return nan
    except:
        pass
    return float(value)


# Build races.
races = [
    'American Indian or Alaska Native', 'Asian', 'Black or African American', 'Multiple Races',
    'Native Hawaiian or Other Pacific Islander', 'White or Caucasian'
]
default_races = {}
for race in races:
    default_races[race] = nan

# Build ethnicities.
ethnicities = [
    'Mexican, Mexican American, Chicano/a', 'Hispanic or Latino', 'Hispanic/Spanish origin Other', 'Not Hispanic or Latino', 'Puerto Rican'
]
default_ethnicities = {}
for ethnicity in ethnicities:
    default_ethnicities[ethnicity] = nan

gender_options = {
    '-9999': nan,
    'Male': '0',
    'Female': '1',
}

diagnoses = make_diagnosis_categories()

class HospitalizationEpisode:
    def __init__(self, row):
        self.id = row['PatientID']
        self.date = row['CareEpisodeDate']
        self.does_include_hospitalization = handle_missing_data_int(row['does_include_hospitalization'])

        # Outcomes.
        self.is_30_day_rehospitalization = handle_missing_data_int(row['is_30_day_rehospitalization'])
        self.days_until_rehospitalization = handle_missing_data_int(row['days_until_rehospitalization'])
        self.is_30_day_psychiatric_rehospitalization = handle_missing_data_int(row['is_30_day_psychiatric_rehospitalization'])
        self.days_until_psychiatric_rehospitalization = handle_missing_data_int(row['days_until_psychiatric_rehospitalization'])

        # Demographics.
        self.gender = gender_options[row['gender']]
        self.age = handle_missing_data_int(row['AGE_AS_OF_1ST_ADMIT'])
        self.races = default_races.copy()
        if row['race'] in races:
            for race in races:
                self.races[race] = 0
            self.races[row['race']] = 1
        self.ethnicities = default_ethnicities.copy()
        if row['ethnicity'] in ethnicities:
            for ethnicity in ethnicities:
                self.ethnicities[ethnicity] = 0
            self.ethnicities[row['ethnicity']] = 1

        # Dispositions.
        self.dispositions = {}
        self.dispositions['home'] = handle_missing_data_int(row['home'])
        self.dispositions['home_health'] = handle_missing_data_int(row['home_health'])
        self.dispositions['psychiatry'] = handle_missing_data_int(row['psychiatry'])
        self.dispositions['acute_care'] = handle_missing_data_int(row['acute_care'])
        self.dispositions['operating_room'] = handle_missing_data_int(row['operating_room'])
        self.dispositions['hospice'] = handle_missing_data_int(row['hospice'])
        self.dispositions['skilled_nursing_facility'] = handle_missing_data_int(row['skilled_nursing_facility'])
        self.dispositions['planned_readmit'] = handle_missing_data_int(row['planned_readmit'])
        self.dispositions['awol'] = handle_missing_data_int(row['awol'])
        self.dispositions['died'] = handle_missing_data_int(row['died'])
        self.dispositions['rehab'] = handle_missing_data_int(row['rehab'])
        self.dispositions['long_term_care'] = handle_missing_data_int(row['long_term_care'])

        # Build medicines.
        self.medicines = {}
        for category in epic_medicine_categories:
            self.medicines[category] = handle_missing_data_int(row[category])
        for category in custom_medicine_categories:
            self.medicines[category] = handle_missing_data_int(row[category])

        # Build diagnoses.
        self.elixhauser_walraven_score = handle_missing_data_int(row['elixhauser_walraven_score'])
        self.diagnoses = {}
        for diagnosis in diagnoses:
            self.diagnoses[diagnosis] = handle_missing_data_int(row[diagnosis])
        self.encounter_diagnoses = {}
        for diagnosis in encounter_diagnoses_list:
            self.encounter_diagnoses[diagnosis] = handle_missing_data_int(row[diagnosis])

        # Other predictors.
        self.pain_score = handle_missing_data_float(row['pain_score'])
        self.charges = handle_missing_data_float(row['Charges'])
        self.previous_calendar_year_ambulatory_visits = handle_missing_data_int(row['previous_calendar_year_ambulatory_visits'])
        self.previous_calendar_year_emergency_visits = handle_missing_data_int(row['previous_calendar_year_emergency_visits'])
        self.previous_calendar_year_hospital_visits = handle_missing_data_int(row['previous_calendar_year_hospital_visits'])
        self.previous_year_hospital_cares = handle_missing_data_int(row['previous_year_hospital_cares'])
        self.previous_year_non_hospital_cares = handle_missing_data_int(row['previous_year_non_hospital_cares'])
        self.previous_year_total_cares = handle_missing_data_int(row['previous_year_total_cares'])
        self.chief_complaint_medical = handle_missing_data_int(row['chief_complaint_medical'])
        self.chief_complaint_psychiatric = handle_missing_data_int(row['chief_complaint_psychiatric'])
        self.chief_complaint_suicidal = handle_missing_data_int(row['chief_complaint_suicidal'])
        self.chief_complaint_substance_use = handle_missing_data_int(row['chief_complaint_substance_use'])
        self.is_primary_diagnosis_psychiatric = handle_missing_data_int(row['is_primary_diagnosis_psychiatric'])
        self.is_primary_diagnosis_medical = handle_missing_data_int(row['is_primary_diagnosis_medical'])
        self.is_transfer_psychiatric = handle_missing_data_int(row['is_transfer_psychiatric'])
        self.length_of_stay = handle_missing_data_int(row['length_of_stay'])
        self.is_psychiatric_hospitalization = handle_missing_data_int(row['is_psychiatric_hospitalization'])
        self.is_rehospitalized_for_suicide_attempt = handle_missing_data_int(row['is_rehospitalized_for_suicide_attempt'])
        self.is_rehospitalized_for_suicidal_ideation = handle_missing_data_int(row['is_rehospitalized_for_suicidal_ideation'])
        self.is_rehospitalized_for_suicidal_attempt_broad = handle_missing_data_int(row['is_rehospitalized_for_suicidal_attempt_broad'])
        self.is_rehospitalized_for_cdc_suicide_self_injury = handle_missing_data_int(row['is_rehospitalized_for_cdc_suicide_self_injury'])

    def get_days_until_rehospitalization(self, days, use_psychiatric_rehospitalization_outcome):
        days_until_rehospitalization = self.days_until_psychiatric_rehospitalization if use_psychiatric_rehospitalization_outcome else self.days_until_rehospitalization
        return 1 if 1 <= days_until_rehospitalization <= days else 0

    def get_suicidal_outcome(self, use_suicidal_ideation, use_suicide_attempt, use_suicide_attempt_broad, use_cdc_suicide_self_injury):
        is_rehospitalized_for_suicide = False
        if use_suicidal_ideation:
            is_rehospitalized_for_suicide = self.is_rehospitalized_for_suicidal_ideation
        if use_suicide_attempt:
            is_rehospitalized_for_suicide = is_rehospitalized_for_suicide or self.is_rehospitalized_for_suicide_attempt
        if use_suicide_attempt_broad:
            is_rehospitalized_for_suicide = is_rehospitalized_for_suicide or self.is_rehospitalized_for_suicidal_attempt_broad
        if use_cdc_suicide_self_injury:
            is_rehospitalized_for_suicide = is_rehospitalized_for_suicide or self.is_rehospitalized_for_cdc_suicide_self_injury
        return is_rehospitalized_for_suicide

    def get_predictors(self, exclude_medicines_and_diagnoses=False):
        # Demographics
        predictors = {
            'age': self.age,
            'gender': self.gender,
        }
        for race in races:
            predictors[race] = self.races[race]
        for ethnicity in ethnicities:
            predictors[ethnicity] = self.ethnicities[ethnicity]

        # Other predictors
        predictors.update({
            'pain_score': self.pain_score,
            'charges': self.charges,
            'previous_calendar_year_ambulatory_visits': self.previous_calendar_year_ambulatory_visits,
            'previous_calendar_year_emergency_visits': self.previous_calendar_year_emergency_visits,
            'previous_calendar_year_hospital_visits': self.previous_calendar_year_hospital_visits,
            'previous_year_hospital_cares': self.previous_year_hospital_cares,
            'previous_year_non_hospital_cares': self.previous_year_non_hospital_cares,
            'previous_year_total_cares': self.previous_year_total_cares,
            'chief_complaint_psychiatric': self.chief_complaint_psychiatric,
            'chief_complaint_medical': self.chief_complaint_medical,
            'chief_complaint_suicidal': self.chief_complaint_suicidal,
            'chief_complaint_substance_use': self.chief_complaint_substance_use,
            'elixhauser_walraven_score': self.elixhauser_walraven_score,
            'is_primary_diagnosis_psychiatric': self.is_primary_diagnosis_psychiatric,
            'is_primary_diagnosis_medical': self.is_primary_diagnosis_medical,
            'is_transfer_psychiatric': self.is_transfer_psychiatric,
            'length_of_stay': self.length_of_stay,
            'is_psychiatric_hospitalization': self.is_psychiatric_hospitalization,
        })

        # Dispositions.
        for disposition, value in self.dispositions.items():
            predictors[disposition] = value

        if not exclude_medicines_and_diagnoses:

            # Medicines
            for category in epic_medicine_categories:
                predictors[category] = self.medicines[category]
            for category in custom_medicine_categories:
                predictors[category] = self.medicines[category]

            # Diagnoses
            for diagnosis in diagnoses:
                predictors[diagnosis] = self.diagnoses[diagnosis]
            for diagnosis in encounter_diagnoses_list:
                predictors[diagnosis] = self.encounter_diagnoses[diagnosis]

        # Number of Elixhauser diagnoses.
        elixhauser_diagnoses = sum([ 1 for category in elixhauser_to_icd9.keys() if self.diagnoses[category] == 1 ])
        predictors['elixhauser_diagnoses'] = elixhauser_diagnoses

        # Remove undesired predictors.
        undesired_predictors = [
            'suicide_attempt',
            'injury_of_unknown_intent',
            'injury',
            'suicide_attempt_likely',
            'episode_suicide_attempt',
            'episode_injury_of_unknown_intent',
            'episode_injury',
            'episode_suicide_attempt_likely',
        ]
        for undesired_predictor in undesired_predictors:
            if undesired_predictor in predictors:
                del predictors[undesired_predictor]

        return predictors
