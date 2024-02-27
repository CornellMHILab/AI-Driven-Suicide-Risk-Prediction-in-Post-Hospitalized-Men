import os, pydotplus
from sklearn.model_selection import LeaveOneOut
from sklearn.model_selection import KFold
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, roc_curve, auc
from sklearn.externals.six import StringIO
from sklearn.tree import export_graphviz
from progress.bar import Bar
from multiprocessing.dummy import Pool as ThreadPool
from HospitalizationEpisode import get_bipolar_episodes
from sklearn.preprocessing import Imputer
import matplotlib.pyplot as plt
import argparse

predictors_labeled = predictors = outcomes = care_episode_index_results = None

class IndexResult:
    def __init__(self, index):
        self.index = index
        self.result = None

def make_decision_tree_classifier(balancing, seed, max_leaf_nodes):
    return DecisionTreeClassifier(

        # Many suggest 'gini'. 'entropy' is the other option, which is effectively the same thing but is slower to compute.
        criterion='gini',

        # Set random number
        random_state = seed,

        # Ensures balance in training between N-day rehospitalization and non-N-day rehospitalization.
        class_weight=balancing,

        max_leaf_nodes=max_leaf_nodes
    )

true_positives = []
false_positives = []
true_negatives = []
false_negatives = []
outcome_values = []
probabilities = []
def compute_metrics(run):
    predictors_train, predictors_test = predictors[run['train_index']], predictors[run['test_index']]
    outcomes_train, outcomes_test = outcomes[run['train_index']], outcomes[run['test_index']]
    if care_episode_index_results:
        index_results = [ care_episode_index_results[index] for index in run['test_index'] ]

    decision_tree = make_decision_tree_classifier(run['balancing'], run['seed'], run['max_leaf_nodes'])
    decision_tree.fit(predictors_train, outcomes_train)
    predictions = decision_tree.predict(predictors_test)

    # Compute accuracy.
    for index, outcome in enumerate(outcomes_test):
        if outcome == 1:
            if predictions[index] == 1:
                true_positives.append(True)
                result = 'true positive'
            else:
                false_negatives.append(True)
                result = 'false negative'
        else:
            if predictions[index] == 1:
                false_positives.append(True)
                result = 'false positive'
            else:
                true_negatives.append(True)
                result = 'true negative'

        if index_results:
            index_results[index].result = result

    outcome_values.extend(outcomes_test)
    probabilities.extend(decision_tree.predict_proba(predictors_test)[:,1].tolist())

# generalizing to x fold CV
def run_cross_validation(command_args, tree_filename):
    print('Initializing ', command_args['cv_fold'], ' fold cross validation')
    loo = KFold(n_splits=command_args['cv_fold'], shuffle=True, random_state=command_args['random_seed']) # n_splits equal to data dimension is equivalent to LOO, command_args['random_seed']
    runs = []
    for train_index, test_index in loo.split(predictors):
        runs.append({
            'train_index': train_index,
            'test_index': test_index,
            'max_leaf_nodes': command_args['max_leaf_nodes'],
            'balancing': command_args['balancing'],
            'seed': command_args['random_seed']
        })

    # Multi-thread computation of classifier metrics.
    pool = ThreadPool(10)
    bar = Bar('Computing metrics', max=command_args['cv_fold'])
    for i in pool.imap(compute_metrics, runs):
        bar.next()
    bar.finish()

    # Compute metrics.
    sensitivity = 100.0 * len(true_positives) / (len(true_positives) + len(false_negatives))
    specificity = 100.0 * len(true_negatives) / (len(true_negatives) + len(false_positives))
    positive_predictive_value = 100.0 * len(true_positives) / (len(true_positives) + len(false_positives))
    negative_predictive_value = 100.0 * len(true_negatives) / (len(true_negatives) + len(false_negatives))
    accuracy = float(len(true_positives) + len(true_negatives)) / (len(true_positives) + len(true_negatives) + len(false_positives) + len(false_negatives))
    print('true_positives:', len(true_positives))
    print('false_negatives:', len(false_negatives))
    print('true_negatives:', len(true_negatives))
    print('false_positives:', len(false_positives))
    print('sensitivity:', sensitivity)
    print('specificity:', specificity)
    print('ppv:', positive_predictive_value)
    print('npv:', negative_predictive_value)
    print('accuracy:', accuracy)

    # Make AUC.
    false_positive_rate, true_positive_rate, _ = roc_curve(outcome_values, probabilities)
    roc_auc = auc(false_positive_rate, true_positive_rate)
    f = plt.figure()
    lw = 2
    plt.plot(false_positive_rate, true_positive_rate, color='darkorange',
             lw=lw, label='ROC curve (area = %0.2f)' % roc_auc)
    plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver operating characteristic example')
    plt.legend(loc="lower right")
    f.savefig(tree_filename + '.pdf', bbox_inches='tight')

def make_decision_tree_picture(command_args, tree_filename):
    decision_tree = make_decision_tree_classifier(command_args['balancing'], command_args['random_seed'], command_args['max_leaf_nodes'])
    decision_tree.fit(predictors, outcomes)
    dot_data = StringIO()
    export_graphviz(decision_tree, out_file=dot_data,
                    filled=True, rounded=True,
                    special_characters=True,
                    feature_names=list(predictors_labeled[0].keys()),
                    class_names=['no', 'yes'],
                    impurity=False,
                    proportion=True)
    graph = pydotplus.graph_from_dot_data(dot_data.getvalue())
    graph.write_png(tree_filename + '.png')

def make_decision_tree_fit_statistics_and_picture(file_prefix, _predictors_labeled, _predictors, _outcomes, care_episode_indices=None):
    global predictors_labeled
    global predictors
    global outcomes
    global care_episode_index_results

    predictors_labeled = _predictors_labeled
    predictors = _predictors
    outcomes = _outcomes

    if care_episode_indices:
        care_episode_index_results = [ IndexResult(index) for index in care_episode_indices ]

    parser = argparse.ArgumentParser(description='Compute rehospitalization classification')
    parser.add_argument('--cv_fold', default = 10, type=int, help='specifies fold number for cross-validation')
    parser.add_argument('--balancing', default = "balanced", help='specifies the tree class_weight')
    parser.add_argument('--random_seed', default = 314, type=int, help='randomization seed')
    parser.add_argument('--max_leaf_nodes', default = 16, type=int, help='max # of leaf nodes')

    # Fill missing data with median of that type of data.
    imputer = Imputer(strategy='median')
    predictors = imputer.fit_transform(predictors)

    command_args = vars(parser.parse_args())

    tree_filename = 'tree_%s_seed_%d_max_leaf_nodes_%d_balancing_%s' % (file_prefix, command_args['random_seed'], command_args['max_leaf_nodes'], command_args['balancing'])
    make_decision_tree_picture(command_args, tree_filename)
    run_cross_validation(command_args, tree_filename)

    return care_episode_index_results