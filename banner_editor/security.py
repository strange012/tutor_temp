import bcrypt

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Table
)
from sqlalchemy.orm import relationship

from models import Base, DBSession, Course, CourseCategory

from pyramid.security import (
    Allow
)


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
    interests = relationship(
        'CourseCategory',
        secondary='user_interests',
        backref='users'
    )
    fav_courses = relationship(
        'Course',
        secondary='consumer_fav_courses',
        backref='users'
    )
    def to_json(self):
        return {
            'first_name' : self.first_name,
            'second_name' : self.second_name,
            'email' : self.email,
            'gender' : self.gender,
            'interests' : DBSession.query(CourseCategory.id).filter(CourseCategory in self.interests).all(),
            'fav_courses' : DBSession.query(Course.id).filter(Course in self.fav_courses).all()
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


# class Group(Base):
#     __tablename__ = 'group'
#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False, unique=True)
#     users = relationship('User', backref='group')
#     def __str__(self):
#         return 'group:' + self.name


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
