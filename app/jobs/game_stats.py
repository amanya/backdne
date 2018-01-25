import json
from tempfile import NamedTemporaryFile
import csv
import boto3
from .. import db
from rq import get_current_job
from collections import defaultdict

def _get_lessons():
    return [
            'lesson_danger',
            'lesson_labtools',
            'lesson_atom_rutherford',
            'lesson_atom_atomic_number',
            'lesson_atom_isotops',
            'lesson_matter1_levels',
            'lesson_matter1_table',
            'lesson_matter1_connection',
            'lesson_matter2_mol',
            'lesson_matter2_mass',
            'lesson_matter2_stoichiometry',
            'lesson_change_reaction',
            'lesson_change_adjustment',
            ]

def _get_games():
    return [
        'game_danger',
        'game_labtools',
        'game_atom_rutherford',
        'game_atom_atomic_number',
        'game_atom_isotops',
        'game_matter1_levels',
        'game_matter1_table',
        'game_matter1_connection',
        'game_matter2_mol',
        'game_matter2_mass',
        'game_matter2_stoichiometry',
        'game_change_reaction',
        'game_change_adjustment',
    ]

def _get_quizes():
    return [
        'quiz_danger',
        'quiz_labtools',
        'quiz_atom_rutherford',
        'quiz_atom_atomic_number',
        'quiz_atom_isotops',
        'quiz_matter1_levels',
        'quiz_matter1_table',
        'quiz_matter1_connection',
        'quiz_matter2_mol',
        'quiz_matter2_mass',
        'quiz_matter2_stoichiometry',
        'quiz_change_reaction',
        'quiz_change_adjustment',
    ]

def _get_screens():
    return [
        'PanelTabOrganigram',
        'PanelTabQuiz',
        'DressingRoom',
    ]


def _get_user_ids():
    sql = '''
    SELECT id
    FROM users
    '''
    result = db.engine.execute(sql)
    return list(map(lambda x: x[0], result))

def _get_first_game_score(user_id, game):
    sql = '''
    SELECT score
    FROM scores
    WHERE user_id = {} AND game = '{}'
    ORDER BY created ASC
    LIMIT 1
    '''.format(user_id, game)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_last_game_score(user_id, game):
    sql = '''
    SELECT score
    FROM scores
    WHERE user_id = {} AND game = '{}'
    ORDER BY created DESC
    LIMIT 1
    '''.format(user_id, game)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_avg_game_score(user_id, game):
    sql = '''
    SELECT ROUND(AVG(score))
    FROM (
        SELECT score
        FROM scores
        WHERE user_id = {} AND game = '{}'
        ORDER BY created ASC
        LIMIT 3
    ) as scores;
    '''.format(user_id, game)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return int(ret[0]) if ret[0] else 0

def _get_num_accesses(user_id, game):
    sql = '''
    SELECT COUNT(score)
    FROM scores
    WHERE user_id = {} AND game = '{}'
    '''.format(user_id, game)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_lesson_num_accesses(user_id, lesson):
    sql = '''
    SELECT COUNT(*)
    FROM lessons
    WHERE user_id = {} AND lesson = '{}'
    '''.format(user_id, lesson)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_duration(user_id, game):
    sql = '''
    SELECT COALESCE(SUM(duration), 0)
    FROM scores
    WHERE user_id = {} AND game = '{}'
    '''.format(user_id, game)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_lesson_duration(user_id, game):
    sql = '''
    SELECT COALESCE(SUM(duration), 0)
    FROM lessons
    WHERE user_id = {} AND lesson = '{}'
    '''.format(user_id, game)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_quiz_perc_score(user_id, quiz):
    sql = '''
    SELECT score
    FROM scores
    WHERE user_id = {} AND game = '{}'
    ORDER BY created DESC
    LIMIT 1
    '''.format(user_id, quiz)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_quiz_duration(user_id, quiz):
    sql = '''
    SELECT duration
    FROM scores
    WHERE user_id = {} AND game = '{}'
    ORDER BY created DESC
    LIMIT 1
    '''.format(user_id, quiz)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_screen_num_accesses(user_id, screen):
    sql = '''
    SELECT COUNT(*)
    FROM screens
    WHERE user_id = {} AND name = '{}'
    '''.format(user_id, screen)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_screen_duration(user_id, screen):
    sql = '''
    SELECT COALESCE(SUM(duration), 0)
    FROM screens
    WHERE user_id = {} AND name = '{}'
    '''.format(user_id, screen)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_total_lessons_num_accesses(user_id):
    sql = '''
    SELECT COALESCE(SUM(total_pages_viewed), 0)
    FROM lessons
    WHERE user_id = {}
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_total_lessons_duration(user_id):
    sql = '''
    SELECT COALESCE(SUM(duration), 0)
    FROM lessons
    WHERE user_id = {}
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_total_games_num_accesses(user_id):
    sql = '''
    SELECT COUNT(*)
    FROM scores
    WHERE user_id = {} AND is_exam = false
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else 0

def _get_total_games_duration(user_id):
    sql = '''
    SELECT COALESCE(SUM(duration), 0)
    FROM scores
    WHERE user_id = {} AND is_exam = false
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_total_games_avg_game_score(user_id):
    sql = '''
    SELECT ROUND(AVG(score))
    FROM (
        SELECT score
        FROM scores
        WHERE user_id = {} AND is_exam = false
    ) as data
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return int(ret[0]) if ret[0] else 0

def _get_total_quizes_duration(user_id):
    sql = '''
    SELECT COALESCE(SUM(duration), 0)
    FROM scores
    WHERE user_id = {} AND is_exam = true
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_total_quizes_avg_quiz_score(user_id):
    sql = '''
    SELECT ROUND(AVG(score))
    FROM (
        SELECT score
        FROM scores
        WHERE user_id = {} AND is_exam = true
    ) as data
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return int(ret[0]) if ret[0] else 0

def _get_total_app_duration(user_id):
    sql = '''
    SELECT COALESCE(SUM(duration), 0)
    FROM screens
    WHERE user_id = {}
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_total_app_num_accesses(user_id):
    sql = '''
    SELECT COUNT(*)
    FROM screens
    WHERE user_id = {} AND name = 'Login'
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else 0

def _get_school_name(user_id):
    sql = '''
    SELECT s.name
    FROM schools s
        JOIN users_schools us ON s.id = us.school_id
        JOIN users u ON u.id = us.user_id
    WHERE user_id = {}
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else ""

def _get_teacher_username(user_id):
    sql = '''
    SELECT username
    FROM users
    WHERE id = (
        SELECT teacher_id
        FROM users
        WHERE id = {}
    )
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret else ""

def _get_username(user_id):
    sql = '''
    SELECT username
    FROM users
    WHERE id = {}
    '''.format(user_id)
    result = db.engine.execute(sql)
    ret = result.fetchone()
    return ret[0] if ret[0] else ""

def game_stats(aws_region, s3_bucket):
    users = _get_user_ids()

    games_data = defaultdict(dict)

    for user_id in users:
        games_data[user_id]['user_id'] = user_id
        games_data[user_id]['school'] = _get_school_name(user_id)
        games_data[user_id]['teacher'] = _get_teacher_username(user_id)
        games_data[user_id]['username'] = _get_username(user_id)
        for lesson in _get_lessons():
            games_data[user_id]['lessons-{}-{}'.format(lesson, 'num_accesses')] = _get_lesson_num_accesses(user_id, lesson)
            games_data[user_id]['lessons-{}-{}'.format(lesson, 'total_duration')] = _get_lesson_duration(user_id, lesson)
        for game in _get_games():
            games_data[user_id]['games-{}-{}'.format(game, 'first_game_score')] = _get_first_game_score(user_id, game)
            games_data[user_id]['games-{}-{}'.format(game, 'last_game_score')] = _get_last_game_score(user_id, game)
            games_data[user_id]['games-{}-{}'.format(game, 'avg_game_score')] = _get_avg_game_score(user_id, game)
            games_data[user_id]['games-{}-{}'.format(game, 'num_accesses')] = _get_num_accesses(user_id, game)
            games_data[user_id]['games-{}-{}'.format(game, 'total_duration')] = _get_duration(user_id, game)
        for quiz in _get_quizes():
            games_data[user_id]['quizes-{}-{}'.format(quiz, 'perc_score')] = _get_quiz_perc_score(user_id, quiz)
            games_data[user_id]['quizes-{}-{}'.format(quiz, 'total_duration')] = _get_quiz_duration(user_id, quiz)
        for screen in _get_screens():
            games_data[user_id]['screens-{}-{}'.format(screen, 'perc_score')] = _get_screen_num_accesses(user_id, screen)
            games_data[user_id]['screens-{}-{}'.format(screen, 'total_duration')] = _get_screen_duration(user_id, screen)
        games_data[user_id]['total_lessons-num_accesses'] = _get_total_lessons_num_accesses(user_id)
        games_data[user_id]['total_lessons-total_duration'] = _get_total_lessons_duration(user_id)
        games_data[user_id]['total_games-num_accesses'] = _get_total_games_num_accesses(user_id)
        games_data[user_id]['total_games-total_duration'] = _get_total_games_duration(user_id)
        games_data[user_id]['total_games-avg_game_score'] = _get_total_games_avg_game_score(user_id)
        games_data[user_id]['total_quizes-total_duration'] = _get_total_quizes_duration(user_id)
        games_data[user_id]['total_quizes-avg_quiz_score'] = _get_total_quizes_avg_quiz_score(user_id)
        games_data[user_id]['total_app-total_duration'] = _get_total_app_duration(user_id)
        games_data[user_id]['total_app-num_accesses'] = _get_total_app_num_accesses(user_id)

    tempfile = NamedTemporaryFile()

    fieldnames = next(iter(games_data.values()))

    with open(tempfile.name, 'w') as csvfile:
        csvwrite = csv.DictWriter(csvfile, delimiter='\t', fieldnames=fieldnames)
        users = games_data.keys()
        csvwrite.writeheader()
        for user in users:
            csvwrite.writerow(games_data[user])

    tempfile.seek(0)

    job_id = get_current_job().id

    s3 = boto3.resource('s3', aws_region)
    s3_object = s3.Object(s3_bucket, 'jobs/{}.csv'.format(job_id))
    s3_object.put(Body=tempfile.read(), ContentType='text/csv')

    tempfile.close()
