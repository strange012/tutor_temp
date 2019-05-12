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
    CourseCategory
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

    req_params = {
        'page' : 1,
        'page_size' : 3,
        'language' : 'en',
        'search' : 'cook'
    }
    udemy_settings = {
        'api' : settings['udemy.api.url'],
        'id' : settings['udemy.id'],
        'secret' : settings['udemy.secret'],
        'url' : settings['udemy.url']
    }
    udemy = UdemyAPI(udemy_settings)

    ids = udemy.get_course_ids(req_params)
    
    for iid in ids:
        with transaction.manager:
            course, cats = udemy.get_parsed_course(iid)
            DBSession.add(course)
            DBSession.flush()
            for cat in cats:
                newcat = DBSession.query(CourseCategory).filter(CourseCategory.name == cat.name).first()
                if newcat:
                    course.course_categories.append(newcat)
                else:
                    course.course_categories.append(cat)



if __name__ == "__main__":
    main(sys.argv)