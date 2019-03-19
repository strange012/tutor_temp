import os
import sys
import transaction
import string
import json

from sqlalchemy import engine_from_config

from pyramid.paster import (
    get_appsettings,
    setup_logging,
)

from pyramid.scripts.common import parse_vars
from ..lib.util import delete_contents
from ..security import hash_password

from ..models import (
    DBSession,
    Base,
    Course,
    Lesson,
    Teacher,
    CourseCategory,
    course_category_course
)

from ..security import (
    User,
    Provider,
    Consumer,
    consumer_interests
)


def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)


def create_subdirectories(folder):
    symbs = string.ascii_letters + string.digits + '?'
    for symb in symbs:
        os.mkdir(os.path.join(folder, symb))


def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    print("BIBA")
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)


    if os.environ.get('DATABASE_URL', ''):
        settings["sqlalchemy.url"] = os.environ["DATABASE_URL"]
        
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)    
    Base.metadata.drop_all(engine)
    static_folder = os.path.join(
        os.getcwd(), "banner_editor", "static")
    if not os.path.isdir(static_folder):
        os.makedirs(static_folder) 
    delete_contents(static_folder)
    Base.metadata.create_all(engine)
    with transaction.manager:
        admin = Provider(
            email='admin@host.mail',
            password=hash_password('lol'),
            group='admin',
            name='coursera',
            website='www.coursera.com',
            about='Coursera'
        )
        provider = Provider(
            email='provider@host.mail',
            password=hash_password('lol'),
            group='provider',
            name='dummy lessons',
            website='www.dummy-lessons.com',
            about='Coursera'
        )
        consumer = Consumer(
            email='consumer@host.mail',
            password=hash_password('lol'),
            group='consumer',
            first_name='Ivan',
            second_name='Fighter',
            gender='male',
            languages=['English']
        )

        DBSession.add(admin)


        DBSession.add(provider)
        DBSession.add(consumer)
        DBSession.flush()

        with open('data.json') as f:
            json_data = f.read()
        data = json.loads(json_data)
        DBSession.execute(CourseCategory.__table__.insert(), data['categories'])

        DBSession.execute(Course.__table__.insert(), data['courses'])

        cat_course = []
        for idx, course in enumerate(data['courses']):
            for cat in course['course_categories']:
                cat_course.append((idx + 1, cat))

        DBSession.execute(course_category_course.insert(), [
            {'course_category_id': y, 'course_id': x} for x, y in cat_course
        ])
        
        DBSession.execute(consumer_interests.insert(), [
            {'consumer_id': 3, 'course_category_id': 1},
            {'consumer_id': 3, 'course_category_id': 2},
            {'consumer_id': 3, 'course_category_id': 5},
            {'consumer_id': 3, 'course_category_id': 6}
        ])


        course = Course(
            name='Naturalistic fighting',
            provider_id=provider.id,
            description='We will teach you how to fight with nature',
            complexity=4,
            language='English'
        )

        teacher = Teacher(
            first_name='Gayorgy',
            second_name='Leatherman'
        )

        DBSession.add(course)
        DBSession.add(teacher)
        DBSession.flush()

        lesson1 = Lesson(
            name='Know your enemy: basic biology',
            teacher_id=teacher.id,
            course_id=course.id
        )
        lesson2 = Lesson(
            name='How to reflect a potato projectile',
            teacher_id=teacher.id,
            course_id=course.id
        )

        DBSession.add(lesson1)
        DBSession.add(lesson2)

        cat1 = CourseCategory(
            name='Biology',
            description='A science about growing creatures'
        )
        cat2 = CourseCategory(
            name='Physics',
            description='A science about matter and its motion'
        )

        course.course_categories.append(cat1)
        course.course_categories.append(cat2)
        DBSession.flush()

        consumer.interests.append(cat1)
        consumer.fav_courses.append(course)
        DBSession.flush()

