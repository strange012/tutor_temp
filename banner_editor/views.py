from pyramid.response import Response
from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPOk,
    HTTPForbidden,
    HTTPBadRequest,
    HTTPInternalServerError
)

from exceptions import IOError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from formencode import (
    Schema,
    validators,
    FancyValidator,
    Invalid
)

from pyramid_simpleform import Form
from pyramid_simpleform.renderers import FormRenderer
from pyramid.view import forbidden_view_config
from pyramid.security import (
    remember,
    forget,
    Allow,
    unauthenticated_userid
)

from .models import (
    DBSession,
    Banner
)

from security import (
    User,
    Consumer,
    Provider,
    check_password,
    hash_password
)

from lib.util import delete_contents

from decimal import Decimal
import os
import shutil
import logging

MESSAGES = {
    'db': 'Database operation is unavailable right now.',
    'file': 'Unable to save this file right now.',
    'delete': 'Unable to remove this banner right now.',
    'id': 'Invalid banner ID in URL.',
    'move': 'Unable to move this banner right now.',
    'login': 'Failed to login.'
}
LOG = logging.getLogger(__name__)

class HashedPassword(FancyValidator):
    def _to_python(self, value, state):
        return hash_password(validators.UnicodeString(if_missing='').to_python(value))


class ConsumerSchema(Schema):

    allow_extra_fields = True
    filter_extra_fields = True

    email = validators.UnicodeString(max=255)
    password = HashedPassword()
    first_name = validators.UnicodeString(max=255)
    second_name = validators.UnicodeString(max=255)
    gender = validators.UnicodeString(max=255)

# class BannerSchema(Schema):

#     allow_extra_fields = True
#     filter_extra_fields = True

#     name = validators.UnicodeString(max=255)
#     url = validators.URL()
#     pos = validators.Number(min=0, if_missing=Banner.seq_pos.next_value())
#     enabled = validators.Bool()


# class MoveSchema(Schema):

#     allow_extra_fields = True
#     filter_extra_fields = True

#     upwards = validators.StringBool()


class LoginSchema(Schema):

    allow_extra_fields = True
    filter_extra_fields = True

    email = validators.UnicodeString(max=255)
    password = validators.UnicodeString()

@view_config(route_name='login')
def login(request):
    form = Form(request, schema=LoginSchema())
    if request.POST and form.validate():
        user = DBSession.query(User).filter(User.email == form.data['email']).first()
        if user:
            if check_password(user.password, form.data['password']):
                headers = remember(request, form.data['email'])
                return HTTPOk(headers=headers)
    else:
        return HTTPBadRequest('Invalid arguments')
    return HTTPForbidden('Failed to login')

@view_config(route_name='logout', permission='view')
def logout(request):
    headers = forget(request)
    return HTTPOk(headers=headers)

@view_config(route_name='consumer_add')
def consumer_add(request):
    consumer = Consumer()
    form = Form(request, schema=ConsumerSchema(), obj=consumer)
    if request.POST and form.validate():
        try:
            if DBSession.query(Consumer).filter(Consumer.email == form.data['email']).one_or_none():
                return HTTPForbidden('Email already exists')
            form.bind(consumer)
            consumer.group = 'consumer'
            DBSession.add(consumer)
            DBSession.flush()
            return HTTPOk('You have done well, comrade')   
        except SQLAlchemyError as e:
            LOG.exception(e.message)
            return HTTPInternalServerError()
    return HTTPBadRequest('Bad request')
   
@view_config(route_name='consumer_edit', permission='view')
def consumer_edit(request):
    try:
        consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    except SQLAlchemyError as e:
        return HTTPBadRequest('Invalid ID')
    if not consumer:
        return HTTPBadRequest('No consumer')
    if (consumer.group != 'admin') and (consumer.email != unauthenticated_userid(request)):
        return HTTPForbidden('No access')
    form = Form(request, schema=ConsumerSchema(), obj=consumer)
    if request.POST and form.validate():
        try:
            if DBSession.query(Consumer).filter(Consumer.email == form.data['email']).filter(Consumer.id != consumer.id).one_or_none():
                return HTTPForbidden('Email already exists')
            form.bind(consumer)
            DBSession.flush()
            return HTTPOk('You have done well, comrade')   
        except SQLAlchemyError as e:
            LOG.exception(e.message)
            return HTTPInternalServerError()
    return HTTPBadRequest('Bad request')
   
@view_config(route_name='consumer_delete', permission='view')
def consumer_delete(request):   
    try:
        consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    except SQLAlchemyError as e:
        return HTTPBadRequest('Invalid ID')
    if not consumer:
        return HTTPBadRequest('No consumer')
    if (consumer.group != 'admin') and (consumer.email != unauthenticated_userid(request)):
        return HTTPForbidden('No access')
    try:
        DBSession.delete(consumer)
        DBSession.flush()
    except SQLAlchemyError as e:
            LOG.exception(e.message)
            return HTTPInternalServerError()
    return HTTPOk('You have done well, comrade')   

@view_config(route_name='consumer_view', permission='view', renderer='json')
def consumer_view(request):
    try:
        consumer = DBSession.query(Consumer).get(request.matchdict['id'])
    except SQLAlchemyError as e:
        return HTTPBadRequest('Invalid ID')
    if not consumer:
        return HTTPBadRequest('No consumer')
    if (consumer.group != 'admin') and (consumer.email != unauthenticated_userid(request)):
        return HTTPForbidden('No access')
    return consumer.to_json()

##############################################################################3

# @view_config(route_name='banner_add', renderer='templates/editor.mako', permission='edit', require_csrf=True)
# def banner_add(request):
#     banner = Banner()
#     form = Form(request, schema=BannerSchema(), obj=banner)
#     renderer = FormRenderer(form, csrf_field='csrf_token')
#     if request.POST and form.validate():
#         form.bind(banner)
#         try:
#             DBSession.add(banner)
#             DBSession.flush()
#             if ('image' in request.POST) and (request.POST['image'] != "") and request.POST['image'].file:
#                 filename = request.POST['image'].filename
#                 banner.image = filename
#                 image = request.POST['image'].file
#                 path = banner.full_path()
#                 file_path = os.path.join(path, filename)
#                 image.seek(0)
#                 with open(file_path, 'wb') as f:
#                     shutil.copyfileobj(image, f)
#             if not banner.image:
#                 banner.enabled = False
#             DBSession.flush()

#             url = request.route_url('admin')
#             return HTTPFound(location=url)
#         except SQLAlchemyError as e:
#             LOG.exception(e.message)
#             request.session.flash(MESSAGES['db'])
#         except IOError as e:
#             LOG.exception(e.message)
#             request.session.flash(MESSAGES['file'])
#     return {
#         'renderer': renderer
#     }


# @view_config(route_name='banner_edit', renderer='templates/editor.mako', permission='edit', require_csrf=True)
# def banner_edit(request):
#     try:
#         banner = DBSession.query(Banner).get(request.matchdict['id'])
#     except SQLAlchemyError as e:
#         request.session.flash(MESSAGES['id'])
#         url = request.route_url('admin')
#         return HTTPFound(location=url)

#     form = Form(request, schema=BannerSchema(), obj=banner)
#     renderer = FormRenderer(form, csrf_field='csrf_token')

#     if request.POST and form.validate():
#         form.bind(banner)
#         try:
#             DBSession.flush()
#             if ('image' in request.POST) and (request.POST['image'] != "") and request.POST['image'].file:
#                 filename = request.POST['image'].filename
#                 image = request.POST['image'].file
#                 banner.image = filename
#                 path = banner.full_path()
#                 if os.path.isdir(path):
#                     delete_contents(path)
#                 file_path = os.path.join(path, filename)
#                 image.seek(0)
#                 with open(file_path, 'wb') as f:
#                     shutil.copyfileobj(image, f)
#             if not banner.image:
#                 banner.enabled = False
#             DBSession.flush()

#             url = request.route_url('admin')
#             return HTTPFound(location=url)
#         except SQLAlchemyError as e:
#             LOG.exception(e.message)
#             request.session.flash(MESSAGES['db'])
#         except IOError as e:
#             LOG.exception(e.message)
#             request.session.flash(MESSAGES['file'])
#     return {
#         'renderer': renderer,
#         'path': banner.static_path('edit_image')
#     }


# @view_config(route_name='banner_delete', permission='edit', require_csrf=True)
# def banner_delete(request):
#     try:
#         banner = DBSession.query(Banner).get(request.matchdict['id'])
#         DBSession.delete(banner)
#         DBSession.flush()
#         url = request.route_url('admin')
#     except SQLAlchemyError as e:
#         LOG.exception(e.message)
#         request.session.flash(MESSAGES['delete'])
#         url = request.route_url('admin')
#     finally:
#         return HTTPFound(location=url)


# @view_config(route_name='banner_move', permission='edit', require_csrf=True)
# def banner_move(request):
#     url = request.route_url('admin')
#     form = Form(request, schema=MoveSchema())
#     if form.validate():
#         try:
#             banner = DBSession.query(Banner).get(request.matchdict['id'])
#             if form.data['upwards']:
#                 pos1 = DBSession.query(func.max(Banner.pos)).filter(
#                     Banner.pos < banner.pos).one_or_none()
#                 if pos1[0] is None:
#                     return HTTPFound(location=url)
#                 pos1 = Decimal(pos1[0])
#                 pos2 = DBSession.query(func.max(Banner.pos)).filter(
#                     Banner.pos < pos1).one_or_none()
#                 if pos2[0] is None:
#                     pos2 = 0
#                 else:
#                     pos2 = Decimal(pos2[0])
#                 banner.pos = (pos1 + pos2) / 2
#             else:
#                 pos1 = DBSession.query(func.min(Banner.pos)).filter(
#                     Banner.pos > banner.pos).one_or_none()
#                 if pos1[0] is None:
#                     return HTTPFound(location=url)
#                 pos1 = Decimal(pos1[0])
#                 pos2 = DBSession.query(func.min(Banner.pos)).filter(
#                     Banner.pos > pos1).one_or_none()
#                 if pos2[0] is None:
#                     pos2 = Banner.seq_pos.next_value()
#                 else:
#                     pos2 = Decimal(pos2[0])
#                 banner.pos = (pos1 + pos2) / 2
#             DBSession.flush()
#         except SQLAlchemyError as e:
#             LOG.exception(e.message)
#             request.session.flash(MESSAGES['move'])
#             url = request.route_url('admin')
#     else:
#         url = request.route_url('admin')
#     return HTTPFound(location=url)
