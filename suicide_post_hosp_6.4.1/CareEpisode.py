from Encounter import Encounter, disposition_names, default_encounter_diagnoses_list
from icd_code_to_category import compute_suicide_attempt_likely
import uuid
from statistics import median

def compute_whether_had_complaint(encounters, complaints):
    if any(complaints):
        return 1
    elif (len(encounters) == 0) or all([ complaint == None for complaint in complaints ]):
        return -9999
    return 0

diagnosis_to_episode_diagnosis = {}
for diagnosis in default_encounter_diagnoses_list:
    diagnosis_to_episode_diagnosis[diagnosis] = 'episode_%s' % diagnosis
encounter_diagnoses_list = diagnosis_to_episode_diagnosis.values()

class CareEpisode:
    def __init__(self, date):
        self.date = date
        self.encounters = {}
        self.does_include_hospitalization = False
        self.previous_calendar_year_ambulatory_visits = -9999
        self.previous_calendar_year_emergency_visits = -9999
        self.previous_calendar_year_hospital_visits = -9999

        # Used to cache a commonly accessed set of data during CSV generation. This data has non-trivial computation costs, so caching saves non-trivial time.
        self.encounter_diagnoses = None

    def add_visit_type(self, encounter_year, visit_type, number_of_visits):
        self.previous_calendar_year_ambulatory_visits = max(self.previous_calendar_year_ambulatory_visits, 0)
        self.previous_calendar_year_emergency_visits = max(self.previous_calendar_year_emergency_visits, 0)
        self.previous_calendar_year_hospital_visits = max(self.previous_calendar_year_hospital_visits, 0)

        if visit_type == 'Ambulatory Visit':
            self.previous_calendar_year_ambulatory_visits = self.previous_calendar_year_ambulatory_visits + number_of_visits
        elif visit_type == 'ED':
            self.previous_calendar_year_emergency_visits = self.previous_calendar_year_emergency_visits + number_of_visits
        elif visit_type == 'Hospitalization':
            self.previous_calendar_year_hospital_visits = self.previous_calendar_year_hospital_visits + number_of_visits

    def add_encounter_from_charges(self, row):
        encounter_id = row['STUDY_CSN']

        # Ignore encounters that don't have an id.
        if encounter_id:
            if encounter_id not in self.encounters:
                self.encounters[encounter_id] = Encounter(encounter_id)

            self.encounters[encounter_id].add_charge(row['AMOUNT'])

    def add_encounter_by_encounter_id(self, encounter_id = None):
        encounter_id = encounter_id if encounter_id else 'phantom%s' % str(uuid.uuid4())

        if encounter_id not in self.encounters:
            self.encounters[encounter_id] = Encounter(encounter_id)

    def add_pain_score_to_encounter(self, encounter_id, pain_score):
        self.encounters[encounter_id].add_pain_score(int(pain_score))

    def get_pain_score(self):

        # Combine all pain scores for each encounter.
        pain_scores = []
        for encounter in self.encounters.values():
            pain_scores.extend(encounter.pain_scores)

        # Take the median pain score across all encounters.
        pain_score = -9999
        if len(pain_scores):
            pain_score = median(pain_scores)
        return pain_score

    def get_charges(self):
        episode_charges = [ encounter.charge for encounter in self.encounters.values() if encounter.charge is not None ]

        return sum(episode_charges) if len(episode_charges) > 0 else -9999

    def get_chief_complaint_medical(self):
        return compute_whether_had_complaint(
            self.encounters,
            [ encounter.chief_complaint_medical for encounter in self.encounters.values() ]
        )

    def get_chief_complaint_psychiatric(self):
        return compute_whether_had_complaint(
            self.encounters,
            [ encounter.chief_complaint_psychiatric for encounter in self.encounters.values() ]
        )

    def get_chief_complaint_suicidal(self):
        return compute_whether_had_complaint(
            self.encounters,
            [ encounter.chief_complaint_suicidal for encounter in self.encounters.values() ]
        )

    def get_chief_complaint_substance_use(self):
        return compute_whether_had_complaint(
            self.encounters,
            [ encounter.chief_complaint_substance_use for encounter in self.encounters.values() ]
        )

    def get_primary_diagnosis(self):
        is_primary_diagnosis_psychiatric = -9999
        is_primary_diagnosis_medical = -9999
        primary_diagnosis_icd_codes = ''
        primary_diagnosis_descriptions = ''
        is_psychiatric = False

        for encounter in self.encounters.values():
            if len(encounter.primary_icd_codes):

                for index, icd_code in enumerate(encounter.primary_icd_codes):
                    primary_diagnosis_icd_codes = primary_diagnosis_icd_codes + ',' + icd_code
                    primary_diagnosis_descriptions = primary_diagnosis_descriptions + ',' + encounter.primary_icd_descriptions[index]
                    try:

                        # ICD 9: 290.* - 319.* are psychiatric.
                        icd_9_code = float(icd_code)
                        if (icd_9_code >= 290) and (icd_9_code < 320):
                            is_psychiatric = True
                    except:

                        # ICD 10: Anything starting with F is psychiatric.
                        if icd_code[0] == 'F':
                            is_psychiatric = True

                    if is_psychiatric:
                        is_primary_diagnosis_psychiatric = 1
                        if is_primary_diagnosis_medical == -9999:
                            is_primary_diagnosis_medical = 0
                    else:
                        is_primary_diagnosis_medical = 1
                        if is_primary_diagnosis_psychiatric == -9999:
                            is_primary_diagnosis_psychiatric = 0

        return (is_primary_diagnosis_psychiatric, is_primary_diagnosis_medical,
                primary_diagnosis_icd_codes, primary_diagnosis_descriptions)

    def is_psychiatric_hospitalization(self):
        (is_primary_diagnosis_psychiatric, is_primary_diagnosis_medical,
        primary_diagnosis_icd_codes, primary_diagnosis_descriptions) = self.get_primary_diagnosis()
        is_transfer_psychiatric = self.is_transfer_psychiatric()

        if self.does_include_hospitalization:
            if ((is_primary_diagnosis_psychiatric == 1) or (is_transfer_psychiatric == 1)):
                return 1
            elif is_primary_diagnosis_psychiatric == -9999 and is_transfer_psychiatric == -9999:
                return -9999
        return 0

    def is_transfer_psychiatric(self):
        is_transfer_psychiatric = any([encounter.is_transfer_psychiatric for encounter in self.encounters.values()])

        if is_transfer_psychiatric:
            return 1
        elif all([encounter.is_transfer_psychiatric == None for encounter in self.encounters.values()]):
            return -9999
        return 0

    def get_start_day(self):
        start_days = [ encounter.start_day for encounter in self.encounters.values() if encounter.start_day != None ]

        if len(start_days) > 0:
            return min(start_days)
        return -9999

    def get_discharge_day(self):
        discharge_days = [ encounter.discharge_day for encounter in self.encounters.values() if encounter.discharge_day != None ]

        if len(discharge_days) > 0:
            return max(discharge_days)
        return -9999

    def get_length_of_stay(self):
        start_day = self.get_start_day()
        discharge_day = self.get_discharge_day()

        if (start_day == -9999) or (discharge_day == -9999):
            return -9999
        return discharge_day - start_day

    def get_dispositions(self):
        dispositions = {}
        for name in disposition_names:
            disposition_values = [ encounter.dispositions[name] for encounter in self.encounters.values() if encounter.dispositions[name] != None ]
            value = -9999
            if len(disposition_values):
                value = 1 if any(disposition_values) else 0
            dispositions[name] = value
        return dispositions

    def get_episode_diagnoses(self):
        if not self.encounter_diagnoses:

            # Initialize to each diagnosis to -9999.
            diagnoses = {}
            for diagnosis in default_encounter_diagnoses_list:
                diagnoses[diagnosis] = -9999

            # Combine diagnoses across encounters. If any diagnosis is 1, then 1. Else if any 0, then 0. Else, -9999.
            for encounter in self.encounters.values():
                for diagnosis in diagnoses:
                    diagnoses[diagnosis] = max(diagnoses[diagnosis], encounter.diagnoses[diagnosis])

            compute_suicide_attempt_likely(diagnoses)

            self.encounter_diagnoses = {}
            for diagnosis, value in diagnoses.items():
                self.encounter_diagnoses[diagnosis_to_episode_diagnosis[diagnosis]] = value

        return self.encounter_diagnoses
