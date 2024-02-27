from HospitalizationEpisode import get_medical_hospitalization_episodes
from decision_tree_utilities import make_decision_tree_fit_statistics_and_picture
import csv

use_suicidal_ideation = False
use_suicide_attempt = False
use_suicide_attempt_broad = False
use_cdc_suicide_self_injury = True
use_serious_mental_illness_only = False
aggregated_days = 365

if not use_suicidal_ideation and not use_suicide_attempt and not use_suicide_attempt_broad and not use_cdc_suicide_self_injury:
    print('Must specify at least one type of suicide outcome... canceling run')
    exit()

predictors_labeled, predictors, outcomes, care_episode_indices = get_medical_hospitalization_episodes(
    aggregated_days=aggregated_days,
    use_serious_mental_illness_only=use_serious_mental_illness_only,
    use_suicidal_ideation=use_suicidal_ideation,
    use_suicide_attempt=use_suicide_attempt,
    use_suicide_attempt_broad=use_suicide_attempt_broad,
    use_cdc_suicide_self_injury=use_cdc_suicide_self_injury
)

# Build filename.
suicide_type = 'e_attempt'
if use_suicidal_ideation and use_suicide_attempt:
    suicide_type = 'e'
elif use_suicidal_ideation:
    suicide_type = 'al_ideation'
elif use_suicide_attempt_broad:
	suicide_type = 'e_attempt_broad'
elif use_cdc_suicide_self_injury:
    suicide_type = 'e_cdc_self_injury'

care_episode_index_results = make_decision_tree_fit_statistics_and_picture(
    'rehospitalization_for_suicid%s' % suicide_type, predictors_labeled, predictors, outcomes, care_episode_indices
)

with open('analyzable_care_episodes_%ddays_classifier_results.csv' % aggregated_days, 'w') as output_file:
    with open('analyzable_care_episodes_%ddays.csv' % aggregated_days, 'r', encoding='iso-8859-1') as input_file:
        reader = csv.DictReader(input_file)

        column_names = [ 'classifier_prediction_result' ] + reader.fieldnames
        writer = csv.DictWriter(output_file, fieldnames=column_names)
        writer.writeheader()

        rows = list(reader)
        results = [ '' ] * len(rows)
        for result in care_episode_index_results:
            results[result.index] = result.result

        for index, row in enumerate(rows):
            row['classifier_prediction_result'] = results[index]
            writer.writerow(row)