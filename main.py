# -*- coding: utf-8 -*-

import os
import webapp2
import jinja2
import datetime
import logging

from google.appengine.ext import deferred

from models import *
from utils import send_pdf, make_mailto_link_pdf, make_mailto_link, send_text, gen_date, mark_as_announced, delete_pdfs
from email.header import make_header


menu = [ {"url": "pdfs", "name": u"Просмотр детализаций"},
         {"url": "announce", "name": u"Список адресов для оповещения о новых детализациях"},
         {"url": "adminemails", "name": u"Список адресов, с которых можно запрашивать детализации"},
         {"url": "delete", "name": u"Удаление старых детализаций"},
         ]

class MainHandler(webapp2.RequestHandler):
    def get(self):
        template = jinja_environment.get_template('main.html')
        self.response.out.write(template.render({"menu": menu}))

class EmailsHandler(webapp2.RequestHandler):
    def get(self, key="", action=""):
        params = {}
        params["selected"] = 0
        if key:
            if action == "delete":
                db.get(key).delete()
                self.redirect('/emails/')
                return
            elif action == "toggle":
                email = db.get(key)
                if email.enabled == True:
                    email.enabled = False
                else:
                    email.enabled = True
                email.put()
                self.redirect('/emails/')
                return
            else:
                params["selected"] = 1
                params["key"] = key
                if key == "add":
                    params["name"] = ""
                    params["email"] = ""
                    params["submit"] = u"Добавить"
                else:
                    e = db.get(key)
                    params["name"] = e.name
                    params["email"] = e.email
                    params["submit"] = u"Сохранить"
        else:
            emails = EmailAddresses.all()
            params["emails"] = list()
            for e in emails:
                params["emails"].append({"key": e.key(), "name": e.name,
                    "email": e.email, "enable_disable":
                    u"Выключить" if e.enabled else u"Включить"})
        template = jinja_environment.get_template('emails.html')
        self.response.out.write(template.render(params))

    def post(self, key="", action=""):
        params = {}
        params["selected"] = 0
        if key == "add":
            email = EmailAddresses()
        else:
            email = db.get(key)
        email.name = unicode(self.request.str_POST.get("name"), encoding="utf-8")
        email.email = unicode(self.request.str_POST.get("email"), encoding="utf-8")
        email.put()

        emails = EmailAddresses.all()
        params["emails"] = list()
        for e in emails:
            params["emails"].append({"key": e.key(), "name": e.name,
                    "email": e.email, "enable_disable":
                    u"Выключить" if e.enabled else u"Включить"})
        template = jinja_environment.get_template('emails.html')
        self.response.out.write(template.render(params))


class AnnounceEmailsHandler(webapp2.RequestHandler):
    def get(self, key="", action=""):
        params = {}
        params["add"] = 0
        if key:
            if action == "delete":
                db.get(key).delete()
                self.redirect('/announce/')
                return
            elif action == "toggle":
                email = db.get(key)
                if email.enabled == True:
                    email.enabled = False
                else:
                    email.enabled = True
                email.put()
                self.redirect('/announce/')
                return
            else:
                params["add"] = 1
        else:
            emails = AnnounceNew.all()
            params["emails"] = list()
            for e in emails:
                params["emails"].append({"key": e.key(),
                    "email": e.email, "enable_disable":
                    u"Выключить" if e.enabled else u"Включить"})
        template = jinja_environment.get_template('announce.html')
        self.response.out.write(template.render(params))

    def post(self, key="", action=""):
        params = {}
        params["add"] = 0
        email = AnnounceNew()
        email.email = unicode(self.request.str_POST.get("email"), encoding="utf-8")
        email.put()

        emails = AnnounceNew.all()
        params["emails"] = list()
        for e in emails:
            params["emails"].append({"key": e.key(), "email": e.email, "enable_disable":
                    u"Выключить" if e.enabled else u"Включить"})
        template = jinja_environment.get_template('announce.html')
        self.response.out.write(template.render(params))


class AdminEmailsHandler(webapp2.RequestHandler):
    def get(self, key="", action=""):
        params = {}
        params["add"] = 0
        if key:
            if action == "delete":
                db.get(key).delete()
                self.redirect('/adminemails/')
                return
            elif action == "toggle":
                email = db.get(key)
                if email.enabled == True:
                    email.enabled = False
                else:
                    email.enabled = True
                email.put()
                self.redirect('/adminemails/')
                return
            else:
                params["add"] = 1
        else:
            emails = AdminEmails.all()
            params["emails"] = list()
            for e in emails:
                params["emails"].append({"key": e.key(), "email": e.email, "enable_disable":
                    u"Выключить" if e.enabled else u"Включить"})
        template = jinja_environment.get_template('adminemails.html')
        self.response.out.write(template.render(params))

    def post(self, key="", action=""):
        params = {}
        params["add"] = 0
        email = AdminEmails()
        email.email = unicode(self.request.str_POST.get("email"), encoding="utf-8")
        email.put()

        emails = AdminEmails.all()
        params["emails"] = list()
        for e in emails:
            params["emails"].append({"key": e.key(), "email": e.email, "enable_disable":
                    u"Выключить" if e.enabled else u"Включить"})
        template = jinja_environment.get_template('adminemails.html')
        self.response.out.write(template.render(params))


class PDFsHandler(webapp2.RequestHandler):
    def get(self):
        today = datetime.date.today() - datetime.timedelta(days=31)
        params = {
            "search": 0,
            "name": "",
            "year": today.year,
            "month": today.month,
            }
        template = jinja_environment.get_template('pdfs.html')
        self.response.out.write(template.render(params))

    def post(self):
        name = unicode(self.request.str_POST.get("name"), "utf-8")
        try:
            year = int(self.request.str_POST.get("year"))
        except ValueError:
            year = 0
        try:
            month = int(self.request.str_POST.get("month"))
        except ValueError:
            month = 0
        params = {
            "search": 1,
            "name": name,
            "year": year,
            "month": month,
            "pdfs": [],
            }
        if name:
            for name in Names.all().search(name).fetch(10):
                pdfs = PDF.all()
                pdfs = pdfs.filter("name =", name.name)
                if year:
                    pdfs = pdfs.filter("year =", year)
                if month:
                    pdfs = pdfs.filter("month =", month)
                pdfs = pdfs.order("-year").order("-month").fetch(50)
                for pdf in pdfs:
                    params["pdfs"].append({
                        "name": pdf.name,
                        "num": pdf.num,
                        "year": pdf.year,
                        "month": "%02d" % (pdf.month,),
                        "key": pdf.key(),
                        })
        else:
            pdfs = PDF.all()
            if year:
                pdfs = pdfs.filter("year =", year)
            if month:
                pdfs = pdfs.filter("month =", month)
            pdfs = pdfs.order("-year").order("-month").fetch(50)
            for pdf in pdfs:
                params["pdfs"].append({
                    "name": pdf.name,
                    "num": pdf.num,
                    "year": pdf.year,
                    "month": "%02d" % (pdf.month,),
                    "key": pdf.key(),
                    })

        template = jinja_environment.get_template('pdfs.html')
        self.response.out.write(template.render(params))


class PDFDownloadHandler(webapp2.RequestHandler):
    def get(self, key):
        pdf = db.get(key)
        fname = u"Beeline %s %s.pdf" % (pdf.name, gen_date(pdf),)
        fname = str(make_header([(fname.encode("utf-8"), "utf-8")]))
        self.response.headers["Content-Type"] = "application/pdf; name=\"%s\"" % (fname,)
        self.response.headers["Content-Disposition"] = "filename=\"%s\"" % (fname,)
        self.response.out.write(pdf.blob)

class PDFSendHandler(webapp2.RequestHandler):
    def get(self, key):
        pdf = db.get(key)
        name = pdf.name
        email = EmailAddresses.all().filter("name =", name).get()
        params = {"key": key}
        if email:
            params.update({"email": email.email})
        template = jinja_environment.get_template('sendpdf.html')
        self.response.out.write(template.render(params))

    def post(self, key):
        send_pdf(db.get(key), "", self.request.str_POST.get("email"))
        self.redirect('/pdfs/')

class SettingsHandler(webapp2.RequestHandler):
    def get(self):
        settings = Settings.all().get()
        if not settings:
            settings = Settings(orgname="", announce="0", bot="")
            settings.put()
        params = {"orgname": settings.orgname, "announce": bool(int(settings.announce)), "bot": settings.bot}
        template = jinja_environment.get_template('settings.html')
        self.response.out.write(template.render(params))

    def post(self):
        settings = Settings.all().get()
        settings.orgname = unicode(self.request.str_POST.get("orgname"), "utf-8")
        settings.announce = '1' if self.request.str_POST.get("announce") == 'on' else '0'
        settings.bot = unicode(self.request.str_POST.get("bot"), "utf-8")
        settings.put()

        params = {"orgname": settings.orgname, "announce": bool(int(settings.announce)), "bot": settings.bot}
        template = jinja_environment.get_template('settings.html')
        self.response.out.write(template.render(params))


class AnnounceNewHandler(webapp2.RequestHandler):
    def get(self):
        if Settings.all().get().announce == "1":
            pdfs = PDF.all().filter("announced = ", False).fetch(200)
            text = []
            keys = []
            for pdf in pdfs:
                text.append(make_mailto_link_pdf(pdf, u"%s %s" % (pdf.name, gen_date(pdf))))
                keys.append(pdf.key())
            if keys:
                deferred.defer(mark_as_announced, keys, _countdown=60)
            if text:
                for email in AnnounceNew.all().filter("enabled =", True):
                    logging.info(u"Отправляем список новых детализаций на адрес %s" % (email.email,))
                    send_text(email.email, u"Новые детализации", text)


class DeleteHandler(webapp2.RequestHandler):
    def get(self):
        params = {
            "year": "",
            "month": "",
            }
        template = jinja_environment.get_template('delete.html')
        self.response.out.write(template.render(params))

    def post(self):
        try:
            year = int(self.request.str_POST.get("year"))
        except ValueError:
            year = 0
        try:
            month = int(self.request.str_POST.get("month"))
        except ValueError:
            month = 0
        if year and month:
            pdfs = PDF.all().filter("year =", year).filter("month =", month)
        keys = []
        for pdf in pdfs:
            keys.append(pdf.key())
        deferred.defer(delete_pdfs, keys)
        self.redirect('/')


jinja_environment = jinja2.Environment(autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

app = webapp2.WSGIApplication([
        ('/', MainHandler),
        ('/emails/?([^/]+)?/?(delete|toggle)?/?$', EmailsHandler),
        ('/announcenew/?$', AnnounceNewHandler),
        ('/announce/?([^/]+)?/?(delete|toggle)?/?$', AnnounceEmailsHandler),
        ('/adminemails/?([^/]+)?/?(delete|toggle)?/?$', AdminEmailsHandler),
        ('/pdfs/?$', PDFsHandler),
        ('/pdfs/download/([^/]+)/?$', PDFDownloadHandler),
        ('/pdfs/send/([^/]+)/?$', PDFSendHandler),
        ('/settings/?$', SettingsHandler),
        ('/delete/?$', DeleteHandler),
        ], debug=True)
