import bcrypt
import re
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Table,
    ARRAY,
)
from sqlalchemy.orm import relationship

from models import Base, DBSession, Course, CourseCategory

from pyramid.security import (
    Allow
)

class ContentTypePredicate(object):
    def __init__(self, val, config):
        self.any_char = val.find('*')
        self.val = val

    TYPES = {
        'image' : ['png', 'jpeg', 'jpg', 'gif']
    }
    def text(self):
        return 'content type = %s' % self.val
    phash = text

    def __call__(self, context, request):
        if self.any_char < 0:
            return request.content_type == self.val
        else:
            p1 = re.compile('([a-zA-Z]+)/*')
            m1 = p1.match(self.val)
            p2 = re.compile('([a-zA-Z]+)/([a-zA-Z]+)')
            m2 = p2.match(request.content_type)
            return m1 and m2 and (m1.group(1) == m2.group(1)) and (m2.group(2) in self.TYPES[m1.group(1)])

class Root(object):
    __name__ = ''
    __acl__ = [
        (Allow, 'group:admin', 'edit'),
        (Allow, 'group:admin', 'add'),
        (Allow, 'group:admin', 'view'),
        (Allow, 'group:provider', 'add'),
        (Allow, 'group:provider', 'view'),
        (Allow, 'group:consumer', 'view')
    ]

    def __init__(self, request):
        pass


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    user_type = Column(String)
    group = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(Text)
    __mapper_args__ = {
        'polymorphic_identity' : 'user',
        'polymorphic_on' : user_type
    }

consumer_fav_courses = Table(
    'consumer_fav_courses', Base.metadata,
    Column('consumer_id', Integer, ForeignKey('consumer.id')),
    Column('course_id', Integer, ForeignKey('course.id'))
)

consumer_bookmarks = Table(
    'consumer_bookmarks', Base.metadata,
    Column('consumer_id', Integer, ForeignKey('consumer.id')),
    Column('course_id', Integer, ForeignKey('course.id'))
)

consumer_interests = Table(
    'user_interests', Base.metadata,
    Column('consumer_id', Integer, ForeignKey('consumer.id')),
    Column('course_category_id', Integer, ForeignKey('course_category.id'))
)

class Consumer(User):
    __tablename__ = 'consumer'
    id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity':'consumer'
    }
    first_name = Column(String, nullable=False)
    second_name = Column(String, nullable=False)
    gender = Column(String, nullable=False)

    comments = relationship('Comment', backref='consumer')

    languages = Column(ARRAY(String))
    interests = relationship(
        'CourseCategory',
        secondary='user_interests',
        backref='users'
    )
    fav_courses = relationship(
        'Course',
        secondary='consumer_fav_courses',
        backref='consumers_fav'
    )

    bookmarks = relationship(
        'Course',
        secondary='consumer_bookmarks',
        backref='consumers_bookmark'
    )
    def to_json(self):
        return {
            'consumer_id' : self.id,
            'first_name' : self.first_name,
            'second_name' : self.second_name,
            'email' : self.email,
            'languages' : self.languages,
            'gender' : self.gender,
            'interests' : [{'id' : cat.id, 'name' : cat.name} for cat in self.interests],
            'fav_courses' : [course.id for course in self.fav_courses],
            'bookmarks' : [course.id for course in self.bookmarks]
        }

class Provider(User):
    __tablename__ = 'provider'
    id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity':'provider'
    }
    name = Column(String, nullable=False, unique=True)
    website = Column(String, nullable=False)
    about = Column(String, nullable=False)
    courses = relationship('Course', backref='provider')

    def to_json(self):
        return {
            'provider_id' : self.id,
            'email' : self.email,
            'name' : self.name,
            'website' : self.website,
            'about' : self.about,
            'courses' : [course.id for course in self.courses]
        }


def hash_password(pw):
    hashed_pw = bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt())
    return hashed_pw.decode('utf-8')


def check_password(expected_hash, pw):
    if expected_hash is not None:
        return bcrypt.checkpw(pw.encode('utf-8'), expected_hash.encode('utf-8'))
    return False


def groupfinder(email, request):
    user = DBSession.query(User).filter(User.email == email).first()
    if user:
        return ['group:' + user.group]
    return None
