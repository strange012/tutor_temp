import sys
import os
import json
import transaction
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from sqlalchemy import engine_from_config
from pyramid.scripts.common import parse_vars
from ..models import (
    DBSession,
    CourseCategory,
    Course
)

from ..lib.udemy_api import (
    UdemyAPI
)
import requests

def usage(argv):
    cmd = os.path.basename(argv[0])
    print('usage: %s <config_uri> [var=value]\n'
          '(example: "%s development.ini")' % (cmd, cmd))
    sys.exit(1)

def main(argv=sys.argv):
    if len(argv) < 2:
        usage(argv)
    config_uri = argv[1]
    options = parse_vars(argv[2:])
    print("PODLIVA")
    setup_logging(config_uri)
    settings = get_appsettings(config_uri, options=options)

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)    

    udemy = UdemyAPI(settings)

    ids = udemy.get_course_ids('physics')
    for index, iid in enumerate(ids):
        print("Loading course #{}...".format(index + 1))
        course_id = udemy.get_parsed_course(iid)
        comments = udemy.get_parsed_course_comments(iid)
        with transaction.manager:
            course = DBSession.query(Course).get(course_id)
            course.comments.extend(comments)
            DBSession.flush()
        print("Course #{} is loaded!".format(index + 1))



if __name__ == "__main__":
    main(sys.argv)