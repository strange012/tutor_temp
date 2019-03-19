from pyramid.config import Configurator
from sqlalchemy import engine_from_config

from pyramid.session import SignedCookieSessionFactory
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

import os

from .models import (
    DBSession,
    Base,
)

from .security import (
    groupfinder,
    Root,
    ContentTypePredicate
)

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    session_factory = SignedCookieSessionFactory('tutor_secret')
    authn_policy = AuthTktAuthenticationPolicy(
        'tutor_secret', callback=groupfinder, hashalg='sha512')
    authz_policy = ACLAuthorizationPolicy()

    if os.environ.get('DATABASE_URL', ''):
        settings["sqlalchemy.url"] = os.environ["DATABASE_URL"]

    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    Base.metadata.bind = engine
    with Configurator(settings=settings) as config:

        config.add_static_view('static', 'static', cache_max_age=3600)
        config.add_view_predicate('content_type', ContentTypePredicate)
        
        config.add_route('get_id', '/')

        config.add_route('login', '/login')
        config.add_route('logout', '/logout')

        config.add_route('consumer_add', '/consumer/add')
        config.add_route('consumer_edit', '/consumer/{id}/edit')
        config.add_route('consumer_remove', '/consumer/{id}/remove')
        config.add_route('consumer_view', '/consumer/{id}/view')

        config.add_route('consumer_favs_view', '/consumer/{id}/fav/view')
        config.add_route('consumer_fav_add', '/consumer/{id}/fav/{course_id}/add')
        config.add_route('consumer_fav_remove', '/consumer/{id}/fav/{course_id}/remove')

        config.add_route('consumer_bookmarks_view', '/consumer/{id}/bookmark/view')
        config.add_route('consumer_bookmark_add', '/consumer/{id}/bookmark/{course_id}/add')
        config.add_route('consumer_bookmark_remove', '/consumer/{id}/bookmark/{course_id}/remove')

        config.add_route('provider_add', '/provider/add')
        config.add_route('provider_edit', '/provider/{id}/edit')
        config.add_route('provider_remove', '/provider/{id}/remove')
        config.add_route('provider_view', '/provider/{id}/view')

        config.add_route('course_add', 'provider/{id}/course/add')
        config.add_route('course_image_add', 'provider/{id}/course/{course_id}/image/add')
        config.add_route('course_image_remove', 'provider/{id}/course/{course_id}/image/remove')
        config.add_route('course_edit', 'provider/{id}/course/{course_id}/edit')
        config.add_route('course_remove', 'provider/{id}/course/{course_id}/remove')
        config.add_route('course_view', 'course/{course_id}/view')
        config.add_route('course_filter', 'course/view')
        config.add_route('course_comments_view', 'course/{course_id}/comment/view')

        config.add_route('lesson_add', 'provider/{id}/lesson/add')
        config.add_route('lesson_edit', 'provider/{id}/lesson/{lesson_id}/edit')
        config.add_route('lesson_remove', 'provider/{id}/lesson/{lesson_id}/remove')
        config.add_route('lesson_view', 'lesson/{lesson_id}/view')

        config.add_route('course_category_add', '/course_category/add')
        config.add_route('course_category_edit', '/course_category/{course_category_id}/edit')
        config.add_route('course_category_remove', '/course_category/{course_category_id}/remove')
        config.add_route('course_category_view', '/course_category/{course_category_id}/view')
        config.add_route('course_category_courses_view', '/course_category/{course_category_id}/courses/view')
        config.add_route('course_categories_view', '/course_category/view')

        config.add_route('teacher_add', 'provider/{id}/teacher/add')
        config.add_route('teacher_edit', 'provider/{id}/teacher/{teacher_id}/edit')
        config.add_route('teacher_remove', 'provider/{id}/teacher/{teacher_id}/remove')
        config.add_route('teacher_view', 'teacher/{teacher_id}/view')

        config.add_route('comment_add', 'course/{course_id}/comment/add')
        config.add_route('comment_edit', 'comment/{comment_id}/edit')
        config.add_route('comment_remove', 'comment/{comment_id}/remove')
        config.add_route('comment_view', 'comment/{comment_id}/view')


        config.set_root_factory(Root)
        config.set_session_factory(session_factory)
        config.set_authentication_policy(authn_policy)
        config.set_authorization_policy(authz_policy)

        config.scan()
        return config.make_wsgi_app()
