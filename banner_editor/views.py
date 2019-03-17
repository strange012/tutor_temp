from pyramid.response import Response
from pyramid.view import view_config

from exceptions import IOError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_

from functools import partial, wraps

from jsonschema import validate, exceptions

from pyramid.view import forbidden_view_config
from pyramid.security import (
    remember,
    forget,
    Allow,
    unauthenticated_userid
)

from .models import (
    DBSession,
    Course,
    CourseCategory,
    Lesson,
    Teacher,
    course_category_course,
    Comment
)

from security import (
    User,
    Consumer,
    Provider,
    consumer_interests,
    check_password,
    hash_password
)

from lib.util import delete_contents

from decimal import Decimal
import os
import shutil
import logging

MESSAGES = {
    'db': 'Database operation error',
    'ok': 'You have done well, comrade',
    'login': 'Failed to login',
    'request': 'Invalid request structure',
    'arguments': 'Invalid arguments',
    'id': 'Invalid ID',
    'access' : 'No access',
    'email' : 'Email already exists',
    'fav_course' : 'Inacceptable favourite course',
    'bookmark' : 'Inacceptable favourite course',
    'course_id' : 'Invalid course ID',
    'course_category_id' : 'Invalid course category ID',
    'lesson_id' : 'Invalid lesson ID',
    'teacher_id' : 'Invalid teacher ID'
}

LANGUAGES = ['Russian', 'English', 'German', 'Spanish', 'French']
LOG = logging.getLogger(__name__)


consumer_schema = {
    'type' : 'object',
    'properties' : {
        'email' : {'type' : 'string'},
        'password' : {'type' : 'string', 'default' : ''},
        'first_name' : {'type' : 'string'},
        'second_name' : {'type' : 'string'},
        'gender' : {'type' : 'string', 'enum' : ['male', 'female', 'other']},
        'interests' : {'type' : 'array'},
        'languages' : {
            'type' : 'array',
            'items' : {
                'type' : 'string',
                'enum' : LANGUAGES
            }
        }
    },
    'required' : ['email', 'password', 'first_name', 'second_name', 'gender']
}

provider_schema = {
    'type' : 'object',
    'properties' : {
        'email' : {'type' : 'string'},
        'password' : {'type' : 'string', 'default' : ''},
        'name' : {'type' : 'string'},
        'website' : {'type' : 'string'},
        'about' : {'type' : 'string'},
    },
    'required' : ['email', 'password', 'name', 'website', 'about']
}
login_schema = {
    'type' : 'object',
    'properties' : {
        'email' : {'type' : 'string'},
        'password' : {'type' : 'string'}
    },
    'required' : ['email', 'password']
}

course_schema = {
    'type' : 'object',
    'properties' : {
        'name' : {'type' : 'string'},
        'author' : {'type' : 'string'},
        'link' : {'type' : 'string'},
        'description' : {'type' : 'string'},
        'language' : {'type' : 'string', 'enum' : LANGUAGES},
        'complexity' : {'type' : 'number'},
        'course_categories' : {'type' : 'array'}
    },
    'required' : ['name', 'author', 'link', 'description', 'complexity', 'course_categories']
}

course_filter_schema = {
    'type' : 'object',
    'properties' : {
        'search_string' : {'type' : 'string'}
    },
    'required' : ['search_string']
}

course_category_schema = {
    'type' : 'object',
    'properties' : {
        'name' : {'type' : 'string'},
        'description' : {'type' : 'string'}
    },
    'required' : ['name', 'description']
}

teacher_schema = {
    'type' : 'object',
    'properties' : {
        'first_name' : {'type' : 'string'},
        'second_name' : {'type' : 'string'}
    },
    'required' : ['first_name', 'second_name']
}

lesson_schema = {
    'type' : 'object',
    'properties' : {
        'name' : {'type' : 'string'},
        'teacher_id' : {'type' : 'number'},
        'course_id' : {'type' : 'number'}
    },
    'required' : ['name', 'teacher_id', 'course_id']
}

comment_schema = {
    'type' : 'object',
    'properties' : {
        'message' : {'type' : 'string'}
    },
    'required' : ['name', 'teacher_id', 'course_id']
}
def user_id_match(f=None):
    if f is None:
        return partial(user_id_match)

    @wraps(f)
    def decorated_function(request):
        try:
            user = DBSession.query(User).get(request.matchdict['id'])
        except SQLAlchemyError as e:
            request.response.status = 400
            return {'msg' :  MESSAGES['id']}
        if not user:
            request.response.status = 400
            return {'msg' :  MESSAGES['id']}
        if (user.group != 'admin') and (user.email != unauthenticated_userid(request)):
            request.response.status = 403
            return {'msg' :  MESSAGES['access']}
        return f(request)
    return decorated_function

def obj_id_match(f=None, oid='', Obj=None):
    if f is None:
        return partial(obj_id_match, oid=oid, Obj=Obj)

    @wraps(f)
    def decorated_function(request):
        try:
            obj = DBSession.query(Obj).get(request.matchdict[oid])
        except SQLAlchemyError as e:
            request.response.status = 400
            return {'msg' :  MESSAGES[oid]}
        if not obj:
            request.response.status = 400
            return {'msg' :  MESSAGES[oid]}
        return f(request)
    return decorated_function

def json_match(f=None, schema={}):
    if f is None:
        return partial(json_match, schema=schema)

    @wraps(f)
    def decorated_function(request):
        try: 
            validate(instance=request.json, schema=schema)
            try:
                return f(request)
            except SQLAlchemyError as e:
                LOG.exception(e.message)
                request.response.status = 500
                return {'msg' :  MESSAGES['db']}
        except exceptions.ValidationError as e:
            request.response.status = 400
            return {'msg' :  MESSAGES['request'], 'err' : e.message}
    return decorated_function

@view_config(route_name='get_id', permission='view', renderer='json')
def get_id(request):
    try:
        user = DBSession.query(User).filter(User.email == unauthenticated_userid(request)).first()
        request.response.status = 200
        return {'id' : user.id}
    except SQLAlchemyError as e:
        LOG.exception(e.message)
        request.response.status = 500
        return {'msg' :  MESSAGES['db']}

@view_config(route_name='login', renderer='json')
def login(request):
    try: 
        validate(instance=request.json, schema=login_schema)
        user = DBSession.query(User).filter(User.email == request.json['email']).first()
        if user:
            if check_password(user.password, request.json['password']):
                headers = remember(request, request.json['email'])
                request.response.headerlist.extend(headers)
                request.response.status = 200
                return {'id' : user.id}
    except:
        request.response.status = 400
        return {'msg' : MESSAGES['request']}
    request.response.status = 403
    return {'msg' :  MESSAGES['login']}

@view_config(route_name='logout', permission='view', renderer='json')
def logout(request):
    headers = forget(request)
    request.response.headerlist.extend(headers)
    request.response.status = 200
    return {'msg' :  MESSAGES['ok']}

@view_config(route_name='consumer_add', renderer='json')
@json_match(schema=consumer_schema)
def consumer_add(request):
    if DBSession.query(User).filter(User.email == request.json['email']).one_or_none():
        request.response.status = 403
        return {'msg' :  MESSAGES['email']}
    consumer = Consumer()
    consumer.email = request.json['email']
    consumer.password = hash_password(request.json['password'])
    consumer.first_name = request.json['first_name']
    consumer.second_name = request.json['second_name']
    consumer.languages = request.json['languages']
    consumer.gender = request.json['gender']
    consumer.group = 'consumer'
    DBSession.add(consumer)
    DBSession.flush()
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  
 
   
@view_config(route_name='consumer_edit', permission='view', renderer='json')
@user_id_match
@json_match(schema=consumer_schema)
def consumer_edit(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    if DBSession.query(User).filter(User.email == request.json['email']).filter(User.id != consumer.id).one_or_none():
        request.response.status = 403
        return {'msg' :  MESSAGES['email']}
    consumer.email = request.json['email']
    consumer.password = hash_password(request.json['password'])
    consumer.first_name = request.json['first_name']
    consumer.second_name = request.json['second_name']
    consumer.languages = request.json['languages']
    consumer.gender = request.json['gender']
    if 'interests' in request.json.keys():
        old_interests = set(map(lambda x: x.id, consumer.interests))
        new_interests = set(request.json['interests'])
        to_remove = old_interests.difference(new_interests)
        to_add = new_interests.difference(old_interests)
        try:
            if len(to_remove):
                DBSession.execute(consumer_interests.delete()
                        .where(and_(consumer_interests.c.consumer_id == consumer.id, consumer_interests.c.course_category_id.in_(to_remove))))
            if len(to_add):
                DBSession.execute(consumer_interests.insert(), [
                    {'consumer_id': consumer.id, 'course_category_id': x} for x in to_add
                ])
        except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db'], 'err' : e.message}
    DBSession.flush()
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}   
        
   
@view_config(route_name='consumer_remove', permission='view', renderer='json')
@user_id_match
def consumer_remove(request):   
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    try:
        DBSession.delete(consumer)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db']}
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  

@view_config(route_name='consumer_view', permission='view', renderer='json')
@user_id_match
def consumer_view(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    request.response.status = 200
    return consumer.to_json()

@view_config(route_name='consumer_favs_view', permission='view', renderer='json')
@user_id_match
def consumer_favs_view(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    request.response.status = 200
    return [fav.to_json() for fav in consumer.fav_courses]

@view_config(route_name='consumer_fav_add', permission='view', renderer='json')
@user_id_match
@obj_id_match(oid='course_id', Obj=Course)
def consumer_fav_add(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    if course in consumer.fav_courses:
        request.response.status = 403
        return {'msg' :  MESSAGES['fav_course']}
    try:
        consumer.fav_courses.append(course)
        DBSession.flush()
        request.response.status = 200
        return {'msg' : MESSAGES['ok']} 
    except SQLAlchemyError as e:
        request.response.status = 500
        return {'msg' : MESSAGES['db']} 



@view_config(route_name='consumer_fav_remove', permission='view', renderer='json')
@user_id_match
@obj_id_match(oid='course_id', Obj=Course)
def consumer_fav_remove(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    if course not in consumer.fav_courses:
        request.response.status = 403
        return {'msg' :  MESSAGES['fav_course']}
    try:
        consumer.fav_courses.remove(course)
        DBSession.flush()
        request.response.status = 200
        return {'msg' : MESSAGES['ok']}  
    except SQLAlchemyError as e:
        request.response.status = 500
        return {'msg' : MESSAGES['db']} 

@view_config(route_name='consumer_bookmarks_view', permission='view', renderer='json')
@user_id_match
def consumer_bookmarks_view(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    request.response.status = 200
    return [bookmark.to_json() for bookmark in consumer.bookmarks]

@view_config(route_name='consumer_bookmark_add', permission='view', renderer='json')
@user_id_match
@obj_id_match(oid='course_id', Obj=Course)
def consumer_bookmark_add(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    if course in consumer.bookmarks:
        request.response.status = 403
        return {'msg' :  MESSAGES['bookmark']}
    try:
        consumer.bookmarks.append(course)
        DBSession.flush()
        request.response.status = 200
        return {'msg' : MESSAGES['ok']} 
    except SQLAlchemyError as e:
        request.response.status = 500
        return {'msg' : MESSAGES['db']} 

@view_config(route_name='consumer_bookmark_remove', permission='view', renderer='json')
@user_id_match
@obj_id_match(oid='course_id', Obj=Course)
def consumer_bookmark_remove(request):
    consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    if course not in consumer.bookmarks:
        request.response.status = 403
        return {'msg' :  MESSAGES['bookmark']}
    try:
        consumer.bookmarks.remove(course)
        DBSession.flush()
        request.response.status = 200
        return {'msg' : MESSAGES['ok']}  
    except SQLAlchemyError as e:
        request.response.status = 500
        return {'msg' : MESSAGES['db']} 

@view_config(route_name='provider_add', renderer='json')
@json_match(schema=provider_schema)
def provider_add(request):
    if DBSession.query(User).filter(User.email == request.json['email']).one_or_none():
        request.response.status = 403
        return {'msg' :  MESSAGES['email']}
    provider = Provider()
    provider.email = request.json['email']
    provider.password = hash_password(request.json['password'])
    provider.name = request.json['name']
    provider.website = request.json['website']
    provider.about = request.json['about']
    provider.group = 'provider'
    DBSession.add(provider)
    DBSession.flush()
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  
        
@view_config(route_name='provider_edit', permission='add', renderer='json')
@user_id_match
@json_match(schema=provider_schema)
def provider_edit(request):
    provider = DBSession.query(Provider).get(request.matchdict['id'])
    if DBSession.query(User).filter(User.email == request.json['email']).filter(User.id != provider.id).one_or_none():
        request.response.status = 403
        return {'msg' :  MESSAGES['email']}
    provider.email = request.json['email']
    provider.password = hash_password(request.json['password'])
    provider.name = request.json['name']
    provider.website = request.json['website']
    provider.about = request.json['about']
    DBSession.flush()
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 

@view_config(route_name='provider_remove', permission='add', renderer='json')
@user_id_match
def provider_remove(request):   
    provider = DBSession.query(Provider).get(request.matchdict['id'])
    try:
        DBSession.delete(provider)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db']}
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  

@view_config(route_name='provider_view', permission='view', renderer='json')
def provider_view(request): 
    try:
        provider = DBSession.query(Provider).get(request.matchdict['id'])
    except SQLAlchemyError as e:
        request.response.status = 400
        return {'msg' :  MESSAGES['id']}
    if not provider:
        request.response.status = 400
        return {'msg' :  MESSAGES['id']}
    request.response.status = 200
    return provider.to_json()
  
@view_config(route_name='course_add', permission='add', renderer='json')
@user_id_match
@json_match(schema=course_schema)
def course_add(request):
    course = Course()
    course.name = request.json['name']
    course.description = request.json['description']
    course.complexity = request.json['complexity']
    course.author = request.json['author']
    course.language = request.json['language']
    course.link = request.json['link']
    DBSession.add(course)
    DBSession.flush()

    DBSession.execute(course_category_course.insert(), [
        {'course_category_id': x, 'course_id': course.id} for x in request.json['course_categories']
    ])
            
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  

@view_config(route_name='course_edit', permission='add', renderer='json')
@user_id_match
@json_match(schema=course_schema)
@obj_id_match(oid='course_id', Obj=Course)
def course_edit(request):
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    if course.provider_id is not request.matchdict['id']:
        request.response.status = 403
        return {'msg' :  MESSAGES['access']}
    course.name = request.json['name']
    course.description = request.json['description']
    course.complexity = request.json['complexity']
    course.author = request.json['author']
    course.language = request.json['language']
    course.link = request.json['link']
    DBSession.flush()

    old_categories = set(map(lambda x: x.id, course.course_categories))
    new_categories = set(request.json['course_categories'])
    to_remove = old_categories.difference(new_categories)
    to_add = new_categories.difference(old_categories)
    try:
        if len(to_remove):
            DBSession.execute(course_category_course.delete()
                .where(and_(course_category_course.c.course_id == course.id, course_category_course.c.course_category_id.in_(to_remove))))
        if len(to_add):
            DBSession.execute(course_category_course.insert(), [
                {'course_category_id': x, 'course_id': course.id} for x in request.json['course_categories']
            ])
    
    except SQLAlchemyError as e:
        LOG.exception(e.message)
        request.response.status = 500
        return {'msg' :  MESSAGES['db'], 'err' : e.message}
        
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 

@view_config(route_name='course_remove', permission='add', renderer='json')
@user_id_match
@obj_id_match(oid='course_id', Obj=Course)
def course_remove(request):
    provider = DBSession.query(Provider).get(request.matchdict['id'])
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    if course.provider_id is not request.matchdict['id']:
        request.response.status = 403
        return {'msg' :  MESSAGES['access']}
    try:
        DBSession.delete(course)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db']}
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 

@view_config(route_name='course_view', permission='view', renderer='json')
@obj_id_match(oid='course_id', Obj=Course)
def course_view(request):
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    request.response.status = 200
    return course.to_json()

@view_config(route_name='course_filter', permission='view', renderer='json')
@json_match(schema=course_filter_schema)
def course_filter(request):
    courses = DBSession.query(Course).filter(func.lower(Course.name).contains(request.json['search_string'].lower())).all()
    request.response.status = 200
    return [course.to_json() for course in courses]

@view_config(route_name='course_category_add', permission='edit', renderer='json')
@json_match(schema=course_category_schema)
def course_category_add(request):
    course_category = CourseCategory()
    course_category.name = request.json['name']
    course_category.description = request.json['description']
    DBSession.add(course_category)
    DBSession.flush()          
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 

@view_config(route_name='course_category_edit', permission='edit', renderer='json')
@json_match(schema=course_category_schema)
@obj_id_match(oid='course_category_id', Obj=CourseCategory)
def course_category_edit(request):
    course_category = DBSession.query(CourseCategory).get(request.matchdict['course_category_id'])
    course_category.name = request.json['name']
    course_category.description = request.json['description']
    DBSession.flush()          
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}

@view_config(route_name='course_category_remove', permission='edit', renderer='json')
@obj_id_match(oid='course_category_id', Obj=Course)
def course_category_remove(request):
    course_category = DBSession.query(CourseCategory).get(request.matchdict['course_category_id'])
    try:
        DBSession.delete(course_category)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db']}
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 


@view_config(route_name='course_category_view', permission='view', renderer='json')
@obj_id_match(oid='course_category_id', Obj=CourseCategory)
def course_category_view(request):
    course_category = DBSession.query(CourseCategory).get(request.matchdict['course_category_id'])
    request.response.status = 200
    return course_category.to_json()


@view_config(route_name='course_category_courses_view', permission='view', renderer='json')
@obj_id_match(oid='course_category_id', Obj=CourseCategory)
def course_category_courses_view(request):
    course_category = DBSession.query(CourseCategory).get(request.matchdict['course_category_id'])
    request.response.status = 200
    return [course.to_json() for course in course_category.courses]

@view_config(route_name='course_categories_view', permission='view', renderer='json')
def course_categories_view(request):
    course_categories = DBSession.query(CourseCategory).all()
    request.response.status = 200
    return [cat.to_json() for cat in course_categories]


@view_config(route_name='teacher_add', permission='add', renderer='json')
@user_id_match
@json_match(schema=teacher_schema)
def teacher_add(request):
    teacher = Teacher()
    teacher.first_name = request.json['first_name']
    teacher.second_name = request.json['second_name'] 

    DBSession.add(teacher)
    DBSession.flush()    
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  

@view_config(route_name='teacher_edit', permission='add', renderer='json')
@user_id_match
@json_match(schema=teacher_schema)
@obj_id_match(oid='teacher_id', Obj=Teacher)
def teacher_edit(request):
    teacher = DBSession.query(Teacher).get(request.matchdict['teacher_id'])
    teacher.first_name = request.json['first_name']
    teacher.second_name = request.json['second_name'] 

    DBSession.flush()    
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}

@view_config(route_name='teacher_remove', permission='add', renderer='json')
@user_id_match
@obj_id_match(oid='teacher_id', Obj=Teacher)
def teacher_remove(request):
    teacher = DBSession.query(Teacher).get(request.matchdict['teacher_id'])
    try:
        DBSession.delete(teacher)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db']}
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 

@view_config(route_name='teacher_view', permission='view', renderer='json')
@obj_id_match(oid='teacher_id', Obj=Teacher)
def teacher_view(request):
    teacher = DBSession.query(Teacher).get(request.matchdict['teacher_id'])
    request.response.status = 200
    return teacher.to_json()

@view_config(route_name='lesson_add', permission='add', renderer='json')
@user_id_match
@json_match(schema=lesson_schema)
def lesson_add(request):
    lesson = Lesson()
    lesson.name = request.json['name']
    lesson.teacher_id = request.json['teacher_id'] 
    lesson.course_id = request.json['course_id'] 

    DBSession.add(lesson)
    DBSession.flush()    
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  

@view_config(route_name='lesson_edit', permission='add', renderer='json')
@user_id_match
@json_match(schema=lesson_schema)
@obj_id_match(oid='lesson_id', Obj=Lesson)
def lesson_edit(request):
    lesson = DBSession.query(Lesson).get(request.matchdict['lesson_id'])
    lesson.name = request.json['name']

    DBSession.flush()    
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}

@view_config(route_name='lesson_remove', permission='add', renderer='json')
@user_id_match
@obj_id_match(oid='lesson_id', Obj=Lesson)
def lesson_remove(request):
    lesson = DBSession.query(Lesson).get(request.matchdict['lesson_id'])
    try:
        DBSession.delete(lesson)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db']}
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 

@view_config(route_name='lesson_view', permission='view', renderer='json')
@obj_id_match(oid='lesson_id', Obj=Lesson)
def lesson_view(request):
    lesson = DBSession.query(Lesson).get(request.matchdict['lesson_id'])
    request.response.status = 200
    return lesson.to_json()

@view_config(route_name='comment_add', permission='view', renderer='json')
@json_match(schema=comment_schema)
@obj_id_match(oid='course_id', Obj=Course)
def comment_add(request):
    comment = Comment()
    comment.message = request.json['message']
    comment.course_id = request.matchdict['course_id']
    comment.consumer_id = DBSession.query(Consumer).filter(Consumer.email == unauthenticated_userid(request)).first().id

    DBSession.add(comment)
    DBSession.flush()    
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}  

@view_config(route_name='comment_edit', permission='view', renderer='json')
@json_match(schema=comment_schema)
@obj_id_match(oid='comment_id', Obj=Comment)
def comment_edit(request):
    comment = DBSession.query(Comment).get(request.matchdict['comment_id'])
    user = unauthenticated_userid(request)
    if (comment.consumer.email != user) and (comment.course.provider.email != user):
        request.response.status = 403
        return {'msg' :  MESSAGES['access']}

    comment.message = request.json['message']
    DBSession.flush()    
    request.response.status = 200
    return {'msg' : MESSAGES['ok']}

@view_config(route_name='comment_remove', permission='view', renderer='json')
@obj_id_match(oid='comment_id', Obj=Comment)
def comment_remove(request):
    comment = DBSession.query(Comment).get(request.matchdict['comment_id'])
    user = unauthenticated_userid(request)
    if (comment.consumer.email != user) and (comment.course.provider.email != user):
        request.response.status = 403
        return {'msg' :  MESSAGES['access']}
    try:
        DBSession.delete(comment)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            request.response.status = 500
            return {'msg' :  MESSAGES['db']}
    request.response.status = 200
    return {'msg' : MESSAGES['ok']} 

@view_config(route_name='comment_view', permission='view', renderer='json')
@obj_id_match(oid='comment_id', Obj=Comment)
def comment_view(request):
    comment = DBSession.query(Comment).get(request.matchdict['comment_id'])
    request.response.status = 200
    return comment.to_json()

@view_config(route_name='course_comments_view', permission='view', renderer='json')
@obj_id_match(oid='course_id', Obj=Course)
def course_comments_view(request):
    course = DBSession.query(Course).get(request.matchdict['course_id'])
    request.response.status = 200
    return {
        'count' : len(course.comments),
        'comments' : [comment.to_json() for comment in course.comments]
    }