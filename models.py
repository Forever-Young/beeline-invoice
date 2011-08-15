# -*- coding: utf-8 -*-

from google.appengine.ext import db, search

class PDF(db.Model):
    blob = db.BlobProperty()
    name = db.StringProperty()
    num = db.StringProperty()
    year = db.IntegerProperty()
    month = db.IntegerProperty()
    announced = db.BooleanProperty()

class EmailAddresses(db.Model):
    name = db.StringProperty()
    email = db.StringProperty()
    enabled = db.BooleanProperty(default=True)

class AnnounceNew(db.Model):
    email = db.StringProperty()
    enabled = db.BooleanProperty(default=True)

class AdminEmails(db.Model):
    email = db.StringProperty()
    enabled = db.BooleanProperty(default=True)

class Settings(db.Model):
    orgname = db.StringProperty() # название организации, заменяет Клиент
    announce = db.StringProperty() # оповещать о новых детализациях? 1 - да, другое - нет
    bot = db.StringProperty() # адрес бота

class Names(search.SearchableModel): # ФИО, присутствующие в базе PDF, для suggest
    name = db.StringProperty()
