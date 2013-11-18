# -*- coding: utf-8 -*-
from google.appengine.api import mail
from google.appengine.ext import db
import logging
from models import Settings, PDF
from google.appengine.runtime import DeadlineExceededError

rus_months = [u"Январь", u"Февраль", u"Март", u"Апрель", u"Май",
              u"Июнь", u"Июль", u"Август", u"Сентябрь", u"Октябрь", u"Ноябрь", u"Декабрь"]

def gen_date(pdf):
    return u"%d-%02d %s" % (pdf.year, pdf.month, rus_months[pdf.month - 1])

def send_pdf(pdf, name, email):
    logging.info(u"Отправляем детализацию абонента %s на адрес %s" % (pdf.name, email))
    message = mail.EmailMessage()
    message.sender = Settings.all().get().bot
    if name:
        message.to = u"%s <%s>" % (name, email)
    else:
        message.to = email
    message.subject = u"Детализация Beeline абонента %s %s %s" % (pdf.name, gen_date(pdf), pdf.num)
    message.attachments = [(u"Beeline %s %s %s.pdf" % (pdf.name, gen_date(pdf), pdf.num), pdf.blob)]
    message.body = u"Детализация во вложении"
    message.send()

def send_text(to, subject, text):
    message = mail.EmailMessage()
    message.sender = Settings.all().get().bot
    message.to = to
    message.subject = subject
    message.body = '\n'.join(text)
    message.html = u"<html><body>%s</body></html>" % ('<br>'.join(text),)
    message.send()

def make_mailto_link_pdf(pdf, label, send_to=[]):
    return "<a href='mailto:%s?subject=beeline%%20get%%20%s%s&body=.'>%s</a>" % (Settings.all().get().bot, pdf.num, "%20" + " ".join(send_to) if send_to else "", label)

def make_mailto_link(text, label):
    return "<a href='mailto:%s?subject=%s&body=.'>%s</a>" % (Settings.all().get().bot, text, label)

def mark_as_announced(keys):
    logging.info(u"Отмечаем детализации как announced")
    for key in keys:
        pdf = db.get(key)
        pdf.announced = True
        pdf.put()

def delete_pdfs(keys, start = 0):
    logging.info(u"Удаляем детализации")
    try:
        for i, key in enumerate(keys[start:]):
            pdf = db.get(key)
            if pdf:
                pdf.delete()
            start = i
    except DeadlineExceededError:
        deferred.defer(delete_pdfs, keys, start)
