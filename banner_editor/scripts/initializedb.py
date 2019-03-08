import os
import sys
import transaction
import string

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
    CourseCategory
)

from ..security import (
    User,
    Provider,
    Consumer
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
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)    
    Base.metadata.drop_all(engine)
    static_folder = os.path.join(
        os.getcwd(), "banner_editor", "static", "banners")
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
            gender='male'
        )


        DBSession.add(admin)
        DBSession.add(provider)
        DBSession.add(consumer)

        DBSession.flush()
        
        course = Course(
            name='Naturalistic fighting',
            provider_id=provider.id,
            description='We will teach you how to fight with nature',
            complexity=4
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

