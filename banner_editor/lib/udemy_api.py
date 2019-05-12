import requests
import json
from urlparse import urljoin
import datetime
from ..models import (
    DBSession,
    Course,
    CourseCategory
)

from ..security import (
    Provider
)

class UdemyAPI():
    def __init__(self, settings):
        self.settings = settings
        self.provider_id = DBSession.query(Provider).filter(Provider.email == 'udemy@gmail.com').first().id

    def get_course_ids(self, params):
        r = requests.get(self.settings['api'], auth=(self.settings['id'], self.settings['secret']), params=params)
        ids = [x['id'] for x in r.json()['results']]
        return ids

    def get_parsed_course(self, iid):
        params = {
                'fields[course]' : 'locale,title,headline,created,id,context_info,url,visible_instructors,primary_subcategory',
                'fields[user]' : 'title,url',
                'fields[locale]' : 'simple_english_title'
        }
        r = requests.get(self.settings['api'] + str(iid), auth=(self.settings['id'], self.settings['secret']), params=params)
        res = r.json()
        print(json.dumps(r.json(), indent=2))
        course = Course()
        course.provider_id = self.provider_id
        course.name = res['title']
        course.description = res['headline']
        course.language = res['locale']['simple_english_title']
        course.link = urljoin(self.settings['url'], res['url'])   
        course.date_created = datetime.datetime.strptime(res['created'],'%Y-%m-%dT%H:%M:%SZ')
        course.author = ', '.join([x['title'] for x in res['visible_instructors']])   

        cats = [
            CourseCategory(name=res['context_info']['category']['title']),
            CourseCategory(name=res['context_info']['label']['title']),
            CourseCategory(name=res['primary_subcategory']['title'])
        ]

        return course, cats