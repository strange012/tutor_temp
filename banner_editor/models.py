from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    text,
    func,
    Numeric,
    Sequence,
    event,
    ForeignKey,
    Table
)
from pyramid.threadlocal import get_current_registry
from sqlalchemy.ext.declarative import declarative_base
from exceptions import IOError


from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    relationship
)

from zope.sqlalchemy import ZopeTransactionExtension

from lib.util import PictureSize, image_resize

import os
import string
import shutil

DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
Base = declarative_base()

course_category_course = Table(
    'course_category_course', Base.metadata,
    Column('course_category_id', Integer, ForeignKey('course_category.id')),
    Column('course_id', Integer, ForeignKey('course.id'))
)

class Course(Base):
    __tablename__ = 'course'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    author = Column(String)
    provider_id = Column(Integer, ForeignKey('provider.id'))
    course_categories = relationship(
        'CourseCategory',
        secondary='course_category_course',
        backref='courses'
    )
    link = Column(String)
    description = Column(String)
    complexity = Column(Integer)
    language = Column(String)
    image = Column(Text)
    lessons = relationship('Lesson', backref='course')
    comments = relationship('Comment', backref='course')
    def to_json(self):
        return {
            'course_id' : self.id,
            'name' : self.name,
            'author' : self.author,
            'provider_id' : self.provider_id,
            'description' : self.description,
            'complexity' : self.complexity,
            'language' : self.language,
            'lessons' : [lesson.id for lesson in self.lessons],
            'course_categories' : [cat.id for cat in self.course_categories],
            'favs' : [consumer.id for consumer in self.consumers_fav],
            'bookmarks' : [consumer.id for consumer in self.consumers_bookmark]
        }

class Lesson(Base):
    __tablename__ = 'lesson'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    teacher_id = Column(Integer, ForeignKey('teacher.id'))
    course_id = Column(Integer, ForeignKey('course.id'))
    def to_json(self):
        return {
            'lesson_id' : self.id,
            'name' : self.name,
            'course_id' : self.course_id,
            'teacher_id' : self.teacher_id
        }


class Teacher(Base):
    __tablename__ = 'teacher'
    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=False)
    second_name = Column(String, nullable=False)
    lessons = relationship('Lesson', backref='teacher')
    def to_json(self):
        return {
            'teacher_id' : self.id,
            'first_name' : self.first_name,
            'second_name' : self.second_name,
            'lessons' : [lesson.id for lesson in self.lessons]
        }

class CourseCategory(Base):
    __tablename__ = 'course_category'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String)

    def to_json(self):
        return {
            'course_category_id' : self.id,
            'name' : self.name,
            'description' : self.description,
            'courses' : [course.id for course in self.courses]
        }

class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey('course.id'))
    consumer_id = Column(Integer, ForeignKey('consumer.id'))
    message = Column(String)

    def to_json(self):
        return {
            'comment_id' : self.id,
            'course_id' : self.course_id,
            'message' : self.message,
            'consumer_id' : self.consumer_id,
            'consumer_name' : self.consumer.first_name + ' ' + self.consumer.second_name
        }