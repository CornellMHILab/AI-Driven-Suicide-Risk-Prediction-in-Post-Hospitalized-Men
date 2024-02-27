from math import log
from icd_code_to_category import make_diagnosis_categories, add_icd_code_to_dictionary

planned_psychiatric_transfer_strings = [
    'Psychiatric Hospital UCLA RNPH with planned Acute IP readmission',
    'Psychiatric Hospital (not UCLA, not VA) with planned Acute IP readmission'
]
psychiatric_transfer_out_string = 'Psychiatric Hospital (not UCLA, not VA)'
psychiatric_transfer_in_string = 'Psychiatric Hospital UCLA RNPH'
psychiatric_transfer_strings = planned_psychiatric_transfer_strings[:]
psychiatric_transfer_strings.append(psychiatric_transfer_out_string)
psychiatric_transfer_strings.append(psychiatric_transfer_in_string)

disposition_names = [
    'home', 'home_health', 'psychiatry', 'acute_care', 'operating_room', 'hospice', 'skilled_nursing_facility',
    'planned_readmit', 'awol', 'died', 'rehab', 'long_term_care'
]

home_strings = [ 'Home or Self Care' ]
home_health_strings = [ 'Home Health Svc not related to IP stay', 'Home Health Service' ]
psychiatry_strings = [ 'Psychiatric Hospital (not UCLA, not VA)', 'Psychiatric Hospital UCLA RNPH', 'Psychiatric Hospital UCLA RNPH with planned Acute IP readmission', 'Psychiatric Hospital (not UCLA, not VA) with planned Acute IP readmission' ]
acute_care_strings = [ 'Acute Care Hosp UCLA SMHOH', 'Acute Care Hosp (not Childrens/Cancer/VA)', 'Admitted as an Inpatient', 'Acute Care Hosp UCLA RRUMC' ]
operating_room_strings = [ 'Discharge to OR' ]
hospice_strings = [ 'Hospice Inpatient Care Facility', 'Hospice Care at Home' ]
skilled_nursing_facility_strings = [ 'Federal Healthcare facility (VA Hosp/SNF)', 'SNF Skilled Nursing Bed', 'SNF or Intermediate Care Facility', 'Skilled Nursing Facility - Medi-Cal Certified (not Medicare)', 'SNF/ICF Custodial Care Bed', 'SNF Skilled Nursing Bed with planned Acute IP readmission' ]
planned_readmit_strings = [ 'Home Health Service with planned Acute IP readmission', 'Long Term Care Hospital (LTCH) with planned Acute IP readmission', 'Inpatient Rehab Facility or Unit (not UCLA) w/ planned Acute IP readmission', 'Acute Care Hosp UCLA SMHOH with planned Acute IP readmission', 'Residential Care Facility with planned Acute IP readmission', 'Acute Care Hosp UCLA RRUMC with planned Acute IP readmission', 'Acute Care Hosp (not Childrens/Cancer/VA) w/ planned Acute IP readmission' ]
awol_strings = [ 'Eloped from ED', 'Left Against Medical Advice (AMA)' ]
died_strings = [ 'Expired' ]
rehab_strings = [ 'Inpatient Rehab Facility or Unit (not UCLA)', 'Inpatient Rehab Unit UCLA 1West' ]
long_term_care_strings = [ 'Residential Care Facility', 'Long Term Care Hospital (LTCH)', 'Long Term Acute Facility' ]

default_encounter_diagnoses_list = make_diagnosis_categories()
default_diagnoses = {}
for item in default_encounter_diagnoses_list:
    default_diagnoses[item] = -9999

class Encounter:
    def __init__(self, id):
        self.id = id
        self.discharge_date = None
        self.charge = None
        self.pain_scores = []
        self.chief_complaint_medical = None
        self.chief_complaint_psychiatric = None
        self.chief_complaint_suicidal = None
        self.chief_complaint_substance_use = None
        self.primary_icd_codes = []
        self.primary_icd_descriptions = []
        self.is_transfer_psychiatric = None
        self.is_transfer_planned = None
        self.is_transfer_out = None
        self.length_of_stay = None
        self.start_day = None
        self.discharge_day = None
        self.diagnoses = default_diagnoses.copy()

        self.dispositions = {}
        for disposition_name in disposition_names:
            self.dispositions[disposition_name] = None

    def add_charge(self, charge):
        if self.charge is None:
            self.charge = 0

        charge_float = float(charge)
        if charge_float > 0:
            self.charge = self.charge + log(charge_float)

    def add_pain_score(self, pain_score):
        if 0 <= pain_score <= 11:
            self.pain_scores.append(pain_score)

    def add_chief_complaints(self, medical, psychiatric, suicidal, substance_use):
        self.chief_complaint_medical = True if self.chief_complaint_medical else medical
        self.chief_complaint_psychiatric = True if self.chief_complaint_psychiatric else psychiatric
        self.chief_complaint_suicidal = True if self.chief_complaint_suicidal else suicidal
        self.chief_complaint_substance_use = True if self.chief_complaint_substance_use else substance_use

        if self.chief_complaint_suicidal:
            self.diagnoses['suicidal_ideation'] = 1

    def add_diagnosis(self, icd_code, icd_description, is_primary_diagnosis):
        if is_primary_diagnosis:
            self.primary_icd_codes.append(icd_code)
            self.primary_icd_descriptions.append(icd_description)
        add_icd_code_to_dictionary(icd_code, self.diagnoses)

    def add_discharge_disposition(self, discharge_disposition):
        self.is_transfer_psychiatric = discharge_disposition in psychiatric_transfer_strings
        self.is_transfer_planned = discharge_disposition in planned_psychiatric_transfer_strings
        self.is_transfer_out = discharge_disposition == psychiatric_transfer_out_string

        self.dispositions = {
            'home': discharge_disposition in home_strings,
            'home_health': discharge_disposition in home_health_strings,
            'psychiatry': discharge_disposition in psychiatry_strings,
            'acute_care': discharge_disposition in acute_care_strings,
            'operating_room': discharge_disposition in operating_room_strings,
            'hospice': discharge_disposition in hospice_strings,
            'skilled_nursing_facility': discharge_disposition in skilled_nursing_facility_strings,
            'planned_readmit': discharge_disposition in planned_readmit_strings,
            'awol': discharge_disposition in awol_strings,
            'died': discharge_disposition in died_strings,
            'rehab': discharge_disposition in rehab_strings,
            'long_term_care': discharge_disposition in long_term_care_strings,
        }

    def add_length_of_stay(self, length_of_stay):
        self.length_of_stay = None if length_of_stay == '' else int(length_of_stay)

    def add_date_ranges(self, start_day, discharge_day):
        self.start_day = None if start_day == '' else int(start_day)
        self.discharge_day = None if discharge_day == '' else int(discharge_day)
