from collections import OrderedDict
import xml.etree.ElementTree as ET

from .config import GVALUER_GLOBAL_PART, GVALUER_GROUP_BEGIN, GVALUER_TESTS, GVALUER_SCORE, GVALUER_REQUIRES, \
    GVALUER_SET_MARKED, GVALUER_OFFLINE, GVALUER_GROUP_END, FEEDBACK_POLICY

from .common import Config


def get_group_desc(group_id, l, r, score, requires, test_score, sets_marked, offline):
    res = []
    res.append(GVALUER_GROUP_BEGIN.format(group_id))
    res.append(GVALUER_TESTS.format(l, r))
    res.append(GVALUER_SCORE.format(test_score, score))
    if len(requires) > 0:
        res.append(GVALUER_REQUIRES.format(', '.join(map(str, requires))))
    if sets_marked != "":
        res.append(GVALUER_SET_MARKED.format(sets_marked))
    if offline:
        res.append(GVALUER_OFFLINE)
    res.append(GVALUER_GROUP_END)
    return '\n'.join(res)


def generate_valuer(tree: ET.ElementTree, has_groups=True) -> OrderedDict:
    test_points = []
    test_group = []

    group_name = dict()

    for test in tree.find('judging').find('testset').find('tests'):
        test_data = test.attrib
        if 'group' not in test_data:
            has_groups = False
        if has_groups:
            test_points.append(int(float(test_data['points'])))
            if test_data['group'] not in group_name:
                c = len(group_name)
                group_name[test_data['group']] = c
            test_group.append(group_name[test_data['group']])
        else:
            test_points.append(0)

    if not has_groups:
        group_name = {None: 0}
        test_group = [0] * len(test_points)
        test_points = [0] * len(test_group)
        test_points[-1] = 100

    tests = len(test_points)
    groups = len(group_name)
    group_dependencies = [[] for i in range(groups)]
    each_test = [False] * groups
    feedback = ["brief"] * groups

    if has_groups:
        for group in tree.find('judging').find('testset').find('groups'):
            group_id = group_name[group.attrib['name']]
            dependencies = group.find('dependencies')
            points_policy = group.attrib['points-policy']
            feedback_policy = group.attrib['feedback-policy']

            if dependencies is not None:
                for dep in dependencies:
                    dep_id = group_name[dep.attrib['group']]
                    group_dependencies[group_id].append(dep_id)
            group_dependencies[group_id].sort()
            if points_policy == "each-test":
                each_test[group_id] = True
            feedback[group_id] = FEEDBACK_POLICY[feedback_policy]

    min_test = [None] * groups
    max_test = [None] * groups
    group_score = [0] * groups

    for test_id in range(tests):
        if min_test[test_group[test_id]] is None:
            min_test[test_group[test_id]] = test_id + 1
        max_test[test_group[test_id]] = test_id + 1
        group_score[test_group[test_id]] = group_score[test_group[test_id]] + test_points[test_id]

    valuer = open('valuer.cfg', 'w')
    print(GVALUER_GLOBAL_PART, file=valuer)
    full_score = 0
    full_user_score = 0
    open_tests = []
    final_open_tests = []
    test_score_list = []
    online_groups = []
    for group_id in range(groups):
        if feedback[group_id] != "hidden":
            online_groups.append(str(group_id))
    for group_id in range(groups):
        group_points = ''
        if each_test[group_id]:
            group_points = 'test_'
        sets_marked = ''
        if feedback[group_id] != "hidden" and str(group_id) == online_groups[-1]:
            sets_marked = ', '.join(online_groups)
        print(get_group_desc(
            group_id,
            min_test[group_id],
            max_test[group_id],
            group_score[group_id],
            group_dependencies[group_id],
            group_points,
            sets_marked,
            feedback[group_id] == "hidden",
        ), file=valuer)

        open_tests.append('{}-{}:{}'.format(
            min_test[group_id],
            max_test[group_id],
            feedback[group_id],
        ))

        final_open_tests.append('{}-{}:{}'.format(
            min_test[group_id],
            max_test[group_id],
            "full",
        ))

        curr_group_score = group_score[group_id]

        if each_test[group_id]:
            curr_group_score *= max_test[group_id] - min_test[group_id] + 1

        full_score += curr_group_score
        if feedback[group_id] != "hidden":
            full_user_score += curr_group_score

        group_score_list = []
        if each_test[group_id]:
            for i in range(min_test[group_id], max_test[group_id] + 1):
                group_score_list.append(str(group_score[group_id]))
        else:
            for i in range(min_test[group_id], max_test[group_id]):
                group_score_list.append('0')
            group_score_list.append(str(group_score[group_id]))
        test_score_list.append(' '.join(group_score_list))

    config = OrderedDict()
    config['full_score'] = full_score
    config['full_user_score'] = full_user_score
    config['open_tests'] = ', '.join(open_tests)
    config['final_open_tests'] = ', '.join(final_open_tests)
    config['test_score_list'] = '  '.join(test_score_list)
    config['valuer_cmd'] = "../gvaluer"
    config['interactive_valuer'] = True
    config['valuer_sets_marked'] = True
    config['olympiad_mode'] = True
    config['run_penalty'] = 0

    Config.print_config(config, valuer, '# ')

    valuer.close()

    return config
