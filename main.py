# -*- coding: utf-8 -*-
from google.appengine.ext import deferred, webapp
from google.appengine.ext.webapp import util, template

from models import *
from utils import send_pdf, make_mailto_link, send_text, gen_date, mark_as_announced
from email.header import make_header

import datetime, logging

menu = [ {"url": "emails", "name": u"Настройка адресов абонентов"},
         {"url": "pdfs", "name": u"Просмотр детализаций"},
         {"url": "announce", "name": u"Список адресов для оповещения о новых детализациях"},
         {"url": "adminemails", "name": u"Список адресов, с которых можно запрашивать детализации"},
         {"url": "settings", "name": u"Настройки"},
         ]

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write(template.render('templates/main.djhtml', {"menu": menu}))

class EmailsHandler(webapp.RequestHandler):
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
        self.response.out.write(template.render('templates/emails.djhtml', params))

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
        self.response.out.write(template.render('templates/emails.djhtml', params))


class AnnounceEmailsHandler(webapp.RequestHandler):
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
        self.response.out.write(template.render('templates/announce.djhtml', params))

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
        self.response.out.write(template.render('templates/announce.djhtml', params))


class AdminEmailsHandler(webapp.RequestHandler):
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
        self.response.out.write(template.render('templates/adminemails.djhtml', params))

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
        self.response.out.write(template.render('templates/adminemails.djhtml', params))


class PDFsHandler(webapp.RequestHandler):
    def get(self):
        today = datetime.date.today() - datetime.timedelta(days=31)
        params = {
            "search": 0,
            "name": "",
            "year": today.year,
            "month": today.month,
            }
        self.response.out.write(template.render('templates/pdfs.djhtml', params))

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
        pdfs = PDF.all()
        if name:
            pdfs = pdfs.search(name, properties=['name'])
        if year:
            pdfs = pdfs.filter("year =", year)
        if month:
            pdfs = pdfs.filter("month =", month)
        pdfs = pdfs.order("-month").order("-year").fetch(50)
        for pdf in pdfs:
            params["pdfs"].append({
                "name": pdf.name,
                "num": pdf.num,
                "year": pdf.year,
                "month": "%02d" % (pdf.month,),
                "key": pdf.key(),
                })
        self.response.out.write(template.render('templates/pdfs.djhtml', params))

class PDFDownloadHandler(webapp.RequestHandler):
    def get(self, key):
        pdf = db.get(key)
        fname = u"Beeline %s %s.pdf" % (pdf.name, gen_date(pdf),)
        fname = str(make_header([(fname.encode("utf-8"), "utf-8")]))
        self.response.headers["Content-Type"] = "application/pdf; name=\"%s\"" % (fname,)
        self.response.headers["Content-Disposition"] = "filename=\"%s\"" % (fname,)
        self.response.out.write(pdf.blob)

class PDFSendHandler(webapp.RequestHandler):
    def get(self, key):
        params = {"key": key}
        self.response.out.write(template.render('templates/sendpdf.djhtml', params))

    def post(self, key):
        send_pdf(db.get(key), "", self.request.str_POST.get("email"))
        self.redirect('/pdfs/')

class SettingsHandler(webapp.RequestHandler):
    def get(self):
        settings = Settings.all().get()
        if not settings:
            settings = Settings(orgname="", announce="", bot="")
            settings.put()
        params = {"orgname": settings.orgname, "announce": settings.announce, "bot": settings.bot}
        self.response.out.write(template.render('templates/settings.djhtml', params))

    def post(self):
        settings = Settings.all().get()
        settings.orgname = unicode(self.request.str_POST.get("orgname"), "utf-8")
        try:
            settings.announce = self.request.str_POST.get("announce")
        except UnicodeDecodeError:
            settings.announce = "0"
        settings.bot = unicode(self.request.str_POST.get("bot"), "utf-8")
        settings.put()
        self.redirect('/settings/')

class AnnounceNewHandler(webapp.RequestHandler):
    def get(self):
        if Settings.all().get().announce == "1":
            pdfs = PDF.all().filter("announced = ", False).fetch(200)
            text = []
            keys = []
            for pdf in pdfs:
                label = u"%s %s" % (pdf.name, gen_date(pdf))
                text.append("<a href='%s'>%s</a>" % (make_mailto_link(pdf), label))
                keys.append(pdf.key())
            if keys:
                deferred.defer(mark_as_announced, keys, _countdown=60)
            if text:
                for email in AnnounceNew.all().filter("enabled =", True):
                    logging.info(u"Отправляем список новых детализаций на адрес %s" % (email.email,))
                    send_text(email.email, u"Новые детализации", text)


def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler),
        ('/emails/?([^/]+)?/?(delete|toggle)?/?$', EmailsHandler),
        ('/announcenew/?$', AnnounceNewHandler),
        ('/announce/?([^/]+)?/?(delete|toggle)?/?$', AnnounceEmailsHandler),
        ('/adminemails/?([^/]+)?/?(delete|toggle)?/?$', AdminEmailsHandler),
        ('/pdfs/?$', PDFsHandler),
        ('/pdfs/download/([^/]+)/?$', PDFDownloadHandler),
        ('/pdfs/send/([^/]+)/?$', PDFSendHandler),
        ('/settings/?$', SettingsHandler),
        ], debug=True)
    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()
