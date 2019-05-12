import requests
import json
import shutil
import os
import transaction

from urlparse import urljoin
import datetime
from PIL import (
    Image
)
from ..models import (
    DBSession,
    Course,
    CourseCategory,
    Comment
)

from ..security import (
    Provider
)

from util import (
    PictureSize
)
class UdemyAPI():
    def __init__(self, settings):
        self.settings = settings
        self.provider_id = DBSession.query(Provider).filter(Provider.email == 'udemy@gmail.com').first().id

    def get_course_ids(self, search):
        params = {
            'page' : 1,
            'page_size' : 2,
            'language' : 'en',
            'search' : search
        }
        r = requests.get(self.settings['udemy.api.url'], auth=(self.settings['udemy.id'], self.settings['udemy.secret']), params=params)
        ids = [x['id'] for x in r.json()['results']]
        return ids

    def get_parsed_course(self, iid):
        params = {
                'fields[course]' : 'image_480x270,locale,title,headline,created,id,context_info,url,visible_instructors,primary_subcategory',
                'fields[user]' : 'title,url',
                'fields[locale]' : 'simple_english_title'
        }
        r = requests.get(self.settings['udemy.api.url'] + str(iid), auth=(self.settings['udemy.id'], self.settings['udemy.secret']), params=params)
        res = r.json()
        # print(json.dumps(r.json(), indent=2))
        course = Course()
        course.provider_id = self.provider_id
        course.name = res['title']
        course.description = res['headline']
        course.language = res['locale']['simple_english_title']
        course.link = urljoin(self.settings['udemy.url'], res['url'])   
        course.date_created = datetime.datetime.strptime(res['created'],'%Y-%m-%dT%H:%M:%SZ')
        course.author = ', '.join([x['title'] for x in res['visible_instructors']])   

        cats = [
            CourseCategory(name=res['context_info']['category']['title']),
            CourseCategory(name=res['context_info']['label']['title']),
            CourseCategory(name=res['primary_subcategory']['title'])
        ]
        

        with transaction.manager:          
            DBSession.add(course)
            DBSession.flush()
            for cat in cats:
                newcat = DBSession.query(CourseCategory).filter(CourseCategory.name == cat.name).first()
                if newcat:
                    course.course_categories.append(newcat)
                else:
                    course.course_categories.append(cat)
            r = requests.get(res['image_480x270'], stream=True)
            filename = 'original.jpg'
            file_path = os.path.join(course.full_path(), filename)
            with open(file_path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)

            course.image = filename
            DBSession.flush()
            

            size = PictureSize.course_icon

            image = Image.open(file_path)
            w = image.width
            h = image.height
            image = image.crop(((w-h)/2, 0, (w+h)/2, image.height))
            image = image.resize(size.value, Image.NEAREST)
            image.save(os.path.join(course.full_path(), size.name + '.jpg'))
            return course.id
        return None

    def get_parsed_course_comments(self, iid):
        params = {
            'page' : 1,
            'page_size' : 10,
            'is_text_review' : True,
            'fields[course_review]' : 'content,created,user'
        }
        url = urljoin(self.settings['udemy.api.url'], str(iid) + '/reviews')
        res = requests.get(url, auth=(self.settings['udemy.id'], self.settings['udemy.secret']), params=params).json()
        # print(json.dumps(res, indent=2))

        comments = []
        for res_comment in res['results']:
            comment = Comment()
            comment.name = res_comment['user']['title']
            comment.message = res_comment['content']
            comment.date_created = res_comment['created']
            comments.append(comment)
        return comments