import csv
import operator
import os
from Patient import Patient, epic_medicine_categories, custom_medicine_categories, default_diagnoses_list, date_to_datetime
from CareEpisode import encounter_diagnoses_list
from datetime import timedelta
from statistics import median
from os import path
from progress.bar import Bar

def make_source_filepath(filename):
    return path.join('source_data', filename)

patients = {}

# Load from charges.
with open(make_source_filepath('Charges_12.20.csv'), 'r', encoding='iso-8859-1') as charges_file:
    reader = csv.DictReader(charges_file)

    for row in reader:
        patient_id = row['STUDY_ID'].strip()
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_episode_from_charges(row)

print('Charges done')

# Load from Readmission.
with open(make_source_filepath('Readmission.csv'), 'r', encoding='iso-8859-1') as readmission_file:
    reader = csv.DictReader(readmission_file)

    for row in reader:
        patient_id = row['STUDY_ID'].strip()
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_episode_from_readmissions(row)

print('Readmission done')

# Load from Demographics.
with open(make_source_filepath('Demographics.csv'), 'r', encoding='iso-8859-1') as demographics_file:
    reader = csv.DictReader(demographics_file)

    for row in reader:
        patient_id = row['ï»¿DEID_PATIENT_NUM']
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_demographics(row)

print('Demographics done')

# Load from epic medication categories.
with open(make_source_filepath('Medications_1.21.18_TS.csv'), 'r', encoding='iso-8859-1') as medications_file:
    reader = csv.DictReader(medications_file)

    for row in reader:
        patient_id = row['DEID_PATIENT_NUM']
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_epic_medication_categories(row)

print('Epic medication categories done')

# Load from Medications.
with open(make_source_filepath('Medications.csv'), 'r', encoding='iso-8859-1') as medications_file:
    reader = csv.DictReader(medications_file)

    for row in reader:
        patient_id = row['ï»¿DEID_PATIENT_NUM']
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_medications(row)

print('Medications done')

# Load from Pain Score.
with open(make_source_filepath('Pain_Score.csv'), 'r', encoding='iso-8859-1') as pain_score_file:
    reader = csv.DictReader(pain_score_file)

    for row in reader:
        patient_id = row['STUDY_ID'].strip()
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_pain_score(row)

print('Pain Score done')

# Load from Chief Complaint.
with open(make_source_filepath('Chief_Complaints.csv'), 'r', encoding='iso-8859-1') as chief_complaints_file:
    reader = csv.DictReader(chief_complaints_file)

    for row in reader:
        patient_id = row['STUDY_ID'].strip()
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_chief_complaints(row)

print('Chief Complaint done')

# Load from Diagnoses.
with open(make_source_filepath('Diagnoses.csv'), 'r', encoding='iso-8859-1') as diagnoses_file:
    reader = csv.DictReader(diagnoses_file)

    for row in reader:
        patient_id = row['ï»¿DEID_PATIENT_NUM'].strip()
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)

        patients[patient_id].add_diagnoses_by_code(row['ICD_CODE'].replace('.', ''))

print('Diagnoses done')

# Load from visits.
with open(make_source_filepath('Visit_Breakdown_Per_Year.csv'), 'r', encoding='iso-8859-1') as visits_file:
    reader = csv.DictReader(visits_file)

    for row in reader:
        patient_id = row['STUDY_ID'].strip()
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)

        patients[patient_id].add_visit(row)
print('Visits done')

# Load from ZIP code demographics.
with open(make_source_filepath('Patient_Demographics_5.2018.csv'), 'r', encoding='iso-8859-1') as zip_demographics_file:
    reader = csv.DictReader(zip_demographics_file)

    for row in reader:
        patient_id = row['STUDY_ID']
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_zip_demographics(row)
print('ZIP demographics done')

# Load from Encounter diagnoses.
with open(make_source_filepath('Encounter_Diagnoses_5.2018.csv'), 'r', encoding='iso-8859-1') as encounter_diagnoses_file:
    reader = csv.DictReader(encounter_diagnoses_file)

    for row in reader:
        patient_id = row['STUDY_ID']
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_encounter_diagnosis(row)
print('Encounter diagnoses done')

# Load from Encounters with length of stay and hospital discharge disposition.
with open(make_source_filepath('Encounters_5.2018.csv'), 'r', encoding='iso-8859-1') as encounter_file:
    reader = csv.DictReader(encounter_file)

    for row in reader:
        patient_id = row['STUDY_ID']
        if patient_id not in patients:
            patients[patient_id] = Patient(patient_id)
        patients[patient_id].add_encounters(row)
print('Encounter done')


def merge_two_care_episodes(episode_1, episode_2):

    # Merge date via choosing the earliest date.
    episode_1.date = min(episode_1.date, episode_2.date)

    # Merge does_include_hospitalization via OR
    episode_1.does_include_hospitalization = episode_1.does_include_hospitalization or episode_2.does_include_hospitalization

    # Combine all encounters into one.
    episode_1.encounters.update(episode_2.encounters)

    # Combine previous calendar year via using the largest value.
    episode_1.previous_calendar_year_ambulatory_visits = max(episode_1.previous_calendar_year_ambulatory_visits, episode_2.previous_calendar_year_ambulatory_visits)
    episode_1.previous_calendar_year_emergency_visits = max(episode_1.previous_calendar_year_emergency_visits, episode_2.previous_calendar_year_emergency_visits)
    episode_1.previous_calendar_year_hospital_visits = max(episode_1.previous_calendar_year_hospital_visits, episode_2.previous_calendar_year_hospital_visits)


def date_ranges_had_overlap(start_day1, discharge_day1, start_day2, discharge_day2):
    first_starts_before_second_ends = start_day1 > discharge_day2
    second_starts_before_first_ends = start_day2 > discharge_day1
    return not(first_starts_before_second_ends or second_starts_before_first_ends or discharge_day2 == -9999)


def try_to_merge(care_episodes):
    first_episode = care_episodes[0]
    first_episode_start_day = first_episode.get_start_day()
    first_episode_discharge_day = first_episode.get_discharge_day()

    first_episode_start_day = first_episode_start_day if first_episode_start_day >= 0 else first_episode_discharge_day
    first_episode_discharge_day = first_episode_discharge_day if first_episode_discharge_day >= 0 else first_episode_start_day

    first_episode_start_day_2 = date_to_datetime(first_episode.date)
    first_episode_length_of_stay_2 = max(first_episode.get_length_of_stay(), 0)
    first_episode_discharge_day_2 = first_episode_start_day_2 + timedelta(days=first_episode_length_of_stay_2)

    care_episode_to_merge = None
    for care_episode in care_episodes[1:]:
        care_episode_start_day = care_episode.get_start_day()
        care_episode_discharge_day = care_episode.get_discharge_day()

        # Sometimes start_day or discharge_day are unknown, so assign the value from one to the other.
        care_episode_start_day = care_episode_start_day if care_episode_start_day >= 0 else care_episode_discharge_day
        care_episode_discharge_day = care_episode_discharge_day if care_episode_discharge_day >= 0 else care_episode_start_day
        had_overlap_check_1 = date_ranges_had_overlap(first_episode_start_day, first_episode_discharge_day, care_episode_start_day, care_episode_discharge_day)

        # Do the same check as above, but use the start_date as the care_episode.date and discharge_date as care_episode.get_length_of_stay()
        care_episode_start_day_2 = date_to_datetime(care_episode.date)
        care_episode_length_of_stay_2 = max(care_episode.get_length_of_stay(), 0)
        care_episode_discharge_day_2 = care_episode_start_day_2 + timedelta(days=care_episode_length_of_stay_2)
        had_overlap_check_2 = date_ranges_had_overlap(first_episode_start_day_2, first_episode_discharge_day_2, care_episode_start_day_2, care_episode_discharge_day_2)

        if had_overlap_check_1 or had_overlap_check_2:
            care_episode_to_merge = care_episode
            break

    # Merge values from care_episode_to_merge into first_episode, then throw out care_episode_to_merge.
    if care_episode_to_merge:
        merge_two_care_episodes(first_episode, care_episode_to_merge)

        # Remove care_episode_to_merge from care_episodes.
        care_episodes.remove(care_episode_to_merge)
        return True
    return False

# Merge care episodes that have the same date ranges.
bar = Bar('Merging care episodes', max=len(patients))
for patient_id, patient in patients.items():
    care_episodes = list(patient.care_episodes.values())

    iterations_without_merging = 0
    while iterations_without_merging < len(care_episodes):
        had_merge = try_to_merge(care_episodes)

        # Move first episode to become the last episode.
        first_episode = care_episodes.pop(0)
        care_episodes.append(first_episode)

        if had_merge:
            iterations_without_merging = -1
        iterations_without_merging += 1

    # Rebuild the care episodes for the patient based on the remaining care episodes.
    patient.care_episodes = {}
    for care_episode in care_episodes:
        patient.care_episodes[care_episode.date] = care_episode
    bar.next()
bar.finish()

def compute_chief_complaint(complaints):
    had_complaints = [ complaint for complaint in complaints if complaint >= 0 ]
    return max(had_complaints) if len(had_complaints) else -9999

def make_care_episode_file(number_of_days_back):

    # Print analyzable encounters.
    with open('analyzable_care_episodes_%ddays.csv' % number_of_days_back, 'w') as analyzable_encounters_file:
        column_names = [
            'PatientID', 'CareEpisodeDate', 'does_include_hospitalization',
            'previous_calendar_year_ambulatory_visits', 'previous_calendar_year_emergency_visits', 'previous_calendar_year_hospital_visits',
            'previous_year_hospital_cares', 'previous_year_non_hospital_cares', 'previous_year_total_cares',
            'is_transfer_psychiatric',
            'is_primary_diagnosis_psychiatric', 'is_primary_diagnosis_medical',
            'primary_diagnosis_icd_codes', 'primary_diagnosis_descriptions',
            'chief_complaint_medical', 'chief_complaint_psychiatric', 'chief_complaint_suicidal', 'chief_complaint_substance_use',
            'episode_chief_complaint_medical', 'episode_chief_complaint_psychiatric', 'episode_chief_complaint_suicidal', 'episode_chief_complaint_substance_use',

            # Demographics
            'AGE_AS_OF_1ST_ADMIT', 'gender', 'race', 'ethnicity', 'zip_code',
            'Charges', 'pain_score',

            'elixhauser_walraven_score',
        ]
        column_names.extend(default_diagnoses_list)
        column_names.extend(encounter_diagnoses_list)
        column_names.extend(epic_medicine_categories)
        column_names.extend(custom_medicine_categories)
        column_names.extend([

            # Dispositions.
            'home', 'home_health', 'psychiatry', 'acute_care', 'operating_room', 'hospice', 'skilled_nursing_facility', 'planned_readmit', 'awol', 'died', 'rehab', 'long_term_care',

            'start_day', 'discharge_day', 'length_of_stay',
            'is_psychiatric_hospitalization', 'days_until_psychiatric_rehospitalization', 'is_30_day_psychiatric_rehospitalization',
            'days_until_rehospitalization', 'is_30_day_rehospitalization',
            'is_rehospitalized_for_suicide_attempt', 'is_rehospitalized_for_suicidal_ideation',
            'is_rehospitalized_for_suicidal_attempt_broad', 'is_rehospitalized_for_cdc_suicide_self_injury'
        ])

        writer = csv.DictWriter(analyzable_encounters_file, fieldnames=column_names)
        writer.writeheader()

        bar = Bar('Building csv file for %d days' % number_of_days_back, max=len(patients))

        for patient_id, patient in patients.items():
            bar.next()

            # Only 18+ year olds.
            if patient.age_of_first_admit >= 18:

                # Sort care episodes from earliest to latest date.
                care_episodes = patient.care_episodes.values()
                sorted_care_episodes = sorted(care_episodes, key=operator.attrgetter('date'))

                for care_episode in sorted_care_episodes:

                    # Don't print before 2007.
                    care_episode_datetime = date_to_datetime(care_episode.date)
                    if care_episode_datetime.year >= 2007:

                        # Only print if there was an encounter and one of those encounters was a hospitalization.
                        if len(care_episode.encounters) and care_episode.does_include_hospitalization:
                            previous_year_hospital_cares, previous_year_non_hospital_cares, previous_year_total_cares = patient.count_previous_year_cares(care_episode)

                            start_datetime = care_episode_datetime
                            end_datetime = care_episode_datetime - timedelta(days=number_of_days_back)

                            # Find care episodes going back |number_of_days_back| days.
                            care_episodes_in_range = [
                                care_episode for care_episode in patient.care_episodes.values()
                                if (end_datetime <= date_to_datetime(care_episode.date) <= start_datetime)
                            ]

                            charges_list = [ episodes.get_charges() for episodes in care_episodes_in_range if episodes.get_charges() >= 0 ]
                            charges = sum(charges_list) if len(charges_list) else -9999

                            pain_scores = [ episodes.get_pain_score() for episodes in care_episodes_in_range if episodes.get_pain_score() >= 0 ]
                            pain_score = median(pain_scores) if len(pain_scores) else -9999

                            is_transfer_psychiatric = care_episode.is_transfer_psychiatric()

                            # Compute primary diagnosis.
                            (is_primary_diagnosis_psychiatric, is_primary_diagnosis_medical,
                            primary_diagnosis_icd_codes, primary_diagnosis_descriptions) = care_episode.get_primary_diagnosis()

                            # Compute chief complaints.
                            chief_complaint_medical = compute_chief_complaint(
                                [ episodes.get_chief_complaint_medical() for episodes in care_episodes_in_range ]
                            )
                            chief_complaint_psychiatric = compute_chief_complaint(
                                [ episodes.get_chief_complaint_psychiatric() for episodes in care_episodes_in_range ]
                            )
                            chief_complaint_suicidal = compute_chief_complaint(
                                [ episodes.get_chief_complaint_suicidal() for episodes in care_episodes_in_range ]
                            )
                            chief_complaint_substance_use = compute_chief_complaint(
                                [ episodes.get_chief_complaint_substance_use() for episodes in care_episodes_in_range ]
                            )

                            is_psychiatric_hospitalization = care_episode.is_psychiatric_hospitalization()

                            start_day = care_episode.get_start_day()
                            discharge_day = care_episode.get_discharge_day()
                            length_of_stay = care_episode.get_length_of_stay()

                            days_until_psychiatric_rehospitalization = patient.get_days_until_psychiatric_rehospitalization(care_episode)
                            is_30_day_psychiatric_rehospitalization = 1 if 1 <= days_until_psychiatric_rehospitalization <= 30 else 0

                            days_until_rehospitalization = patient.get_days_until_rehospitalization(care_episode)
                            is_30_day_rehospitalization = 1 if 1 <= days_until_rehospitalization <= 30 else 0

                            is_rehospitalized_for_suicide_attempt = patient.get_whether_rehospitalized_for_diagnosis(care_episode, 'episode_suicide_attempt')
                            is_rehospitalized_for_suicide_attempt_likely = patient.get_whether_rehospitalized_for_diagnosis(care_episode, 'episode_suicide_attempt_likely')
                            is_rehospitalized_for_cdc_suicide_self_injury = patient.get_whether_rehospitalized_for_diagnosis(care_episode, 'episode_cdc_suicide_self_injury')

                            # suicidal_attempt_broad is suicide_attempt or suicide_attempt_likely.
                            is_rehospitalized_for_suicidal_attempt_broad = -9999
                            if (is_rehospitalized_for_suicide_attempt == 1) or (is_rehospitalized_for_suicide_attempt_likely == 1):
                                is_rehospitalized_for_suicidal_attempt_broad = 1
                            elif (is_rehospitalized_for_suicide_attempt != -9999) or (is_rehospitalized_for_suicide_attempt_likely != -9999):
                                is_rehospitalized_for_suicidal_attempt_broad = 0

                            row = {
                                'PatientID': patient_id,
                                'CareEpisodeDate': care_episode.date,
                                'Charges': charges,
                                'does_include_hospitalization': 1 if care_episode.does_include_hospitalization else 0,
                                'previous_calendar_year_ambulatory_visits': care_episode.previous_calendar_year_ambulatory_visits,
                                'previous_calendar_year_emergency_visits': care_episode.previous_calendar_year_emergency_visits,
                                'previous_calendar_year_hospital_visits': care_episode.previous_calendar_year_hospital_visits,
                                'previous_year_hospital_cares': previous_year_hospital_cares,
                                'previous_year_non_hospital_cares': previous_year_non_hospital_cares,
                                'previous_year_total_cares': previous_year_total_cares,
                                'start_day': start_day,
                                'discharge_day': discharge_day,
                                'length_of_stay': length_of_stay,
                                'days_until_psychiatric_rehospitalization': days_until_psychiatric_rehospitalization,
                                'is_psychiatric_hospitalization': is_psychiatric_hospitalization,
                                'is_30_day_psychiatric_rehospitalization': is_30_day_psychiatric_rehospitalization,
                                'days_until_rehospitalization': days_until_rehospitalization,
                                'is_30_day_rehospitalization': is_30_day_rehospitalization,
                                'is_rehospitalized_for_suicide_attempt': is_rehospitalized_for_suicide_attempt,
                                'is_rehospitalized_for_suicidal_ideation': patient.get_whether_rehospitalized_for_diagnosis(care_episode, 'episode_suicidal_ideation'),
                                'is_rehospitalized_for_suicidal_attempt_broad': is_rehospitalized_for_suicidal_attempt_broad,
                                'is_rehospitalized_for_cdc_suicide_self_injury': is_rehospitalized_for_cdc_suicide_self_injury,
                                'AGE_AS_OF_1ST_ADMIT': patient.age_of_first_admit,
                                'gender': patient.gender,
                                'race': patient.race,
                                'ethnicity': patient.ethnicity,
                                'zip_code': patient.zip_code,
                                'pain_score': pain_score,
                                'is_transfer_psychiatric': is_transfer_psychiatric,
                                'is_primary_diagnosis_psychiatric': is_primary_diagnosis_psychiatric,
                                'is_primary_diagnosis_medical': is_primary_diagnosis_medical,
                                'primary_diagnosis_icd_codes': primary_diagnosis_icd_codes,
                                'primary_diagnosis_descriptions': primary_diagnosis_descriptions,
                                'chief_complaint_medical': chief_complaint_medical,
                                'chief_complaint_psychiatric': chief_complaint_psychiatric,
                                'chief_complaint_suicidal': chief_complaint_suicidal,
                                'chief_complaint_substance_use': chief_complaint_substance_use,
                                'elixhauser_walraven_score': patient.get_elixhauser_walraven_score(),
                                'episode_chief_complaint_medical': care_episode.get_chief_complaint_medical(),
                                'episode_chief_complaint_psychiatric': care_episode.get_chief_complaint_psychiatric(),
                                'episode_chief_complaint_suicidal': care_episode.get_chief_complaint_suicidal(),
                                'episode_chief_complaint_substance_use': care_episode.get_chief_complaint_substance_use(),
                            }

                            # Add dispositions.
                            for disposition, disposition_value in care_episode.get_dispositions().items():
                                row[disposition] = disposition_value

                            # Add each diagnoses category to the row.
                            for diagnosis in default_diagnoses_list:
                                row[diagnosis] = patient.had_prior_diagnosis(care_episode, diagnosis)

                            episode_diagnoses = care_episode.get_episode_diagnoses()
                            for diagnosis, value in episode_diagnoses.items():
                                row[diagnosis] = value

                            # Add each medicine category to the row.
                            for category in epic_medicine_categories:
                                row[category] = patient.epic_medicines[category]
                            for category in custom_medicine_categories:
                                row[category] = patient.custom_medicines[category]

                            writer.writerow(row)
        bar.finish()

def make_patient_file():

    # Print analyzable encounters.
    with open('analyzable_patients.csv', 'w') as analyzable_patients_file:
        column_names = [
            'PatientID',

            # Demographics
            'AGE_AS_OF_1ST_ADMIT', 'gender', 'race', 'ethnicity',
        ]
        column_names.extend(default_diagnoses_list)
        column_names.extend(epic_medicine_categories)

        writer = csv.DictWriter(analyzable_patients_file, fieldnames=column_names)
        writer.writeheader()

        for patient_id, patient in patients.items():

            # Only 18+ year olds.
            if patient.age_of_first_admit >= 18:
                row = {
                    'PatientID': patient_id,
                    'AGE_AS_OF_1ST_ADMIT': patient.age_of_first_admit,
                    'gender': patient.gender,
                    'race': patient.race,
                    'ethnicity': patient.ethnicity,
                }

                # Add each diagnoses category to the row.
                for diagnosis in default_diagnoses_list:
                    row[diagnosis] = patient.diagnoses[diagnosis]

                # Add each medicine category to the row.
                for medicine_category in epic_medicine_categories:
                    row[medicine_category] = patient.epic_medicines[medicine_category]

                writer.writerow(row)

# Year
make_care_episode_file(365)

os.system('say "365 done."')

# 10 Years
make_care_episode_file(3650)

# Half year
make_care_episode_file(int(365 / 2))

# 2 months
make_care_episode_file(60)

make_patient_file()

os.system('say "Script done."')