# -*- coding: utf-8 -*-
import logging, re
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail

import models
from utils import send_pdf, gen_date, make_mailto_link, send_text
from email.header import decode_header

def admin_p(email):
    emails = models.AdminEmails.all().filter("enabled =", True)
    for e in emails:
        if e.email in email:
            return True
    return False

def is_month(str):
    if re.match("^\d{1,2}$", str):
        return True
    else:
        return False

def is_year(str):
    if re.match("^\d{4}$", str):
        return True
    else:
        return False

def is_email(str):
    if re.match("^[^@]+@\S+$", str):
        return True
    else:
        return False

class LetterHandler(InboundMailHandler):
    def receive(self, msg):
        if "Invoice from Beeline" in msg.subject:
            logging.info(u"Пришло письмо от invoice@beeline.ru")
            body = msg.body.decode()
            m = re.search(u"Уважа[^ ]+[ ]+г[^ ]+[ ]+(.+?)[.]", body, flags=re.M)
            if m:
                abonent = unicode(m.group(1))
            else:
                m = re.search(u"Уважаемый Клиент.*", body, flags=re.M)
                if m:
                    abonent = models.Settings.all().get().orgname
                else:
                    abonent = u""
            if abonent:
                logging.info(u"Абонент - %s" % (abonent,))
                pdf_fname, pdf = list(msg.attachments[0])
                pdf = pdf.decode()
                m = re.match("^(\d+)_(\d+).[pP]df$", pdf_fname)
                num, date = m.groups()
                m = re.match("^(\d\d\d\d)(\d\d)(\d\d)$", date)
                year, month = [int(x) for x in m.groups()[:2]]
                if not models.PDF.all().filter("num =", num).get():
                    rec = models.PDF(blob=db.Blob(pdf), name=abonent, num=num, year=year, month=month, announced=False)
                    rec.put()
                    if not models.Names.all().filter("name =", abonent).get():
                        models.Names(name=abonent).put()
                    # ищем в EmailAddresses имя абонента и посылаем ему письма (на все адреса)
                    for e in models.EmailAddresses.all().filter("enabled =", True).filter("name =", abonent):
                        send_pdf(rec, e.name, e.email)
        elif admin_p(msg.sender):
            subj = []
            for item in decode_header(msg.subject):
                if item[1]:
                    subj.append(unicode(item[0], item[1]))
                else:
                    subj.append(item[0])
            subj = ' '.join(subj)
            logging.info(u"Получен запрос: %s" % (subj,))
            m = re.match("^beeline get (\d+)( [^@]+@\S+)?$", subj)
            if m:
                num = m.group(1)
                logging.info(u"Получена команда: get, параметры: %s", num)
                pdf = models.PDF.all().filter("num =", num).get()
                if pdf:
                    send_to = m.group(2)
                    if send_to:
                        logging.info(u"Отправляем ответ на запрос - сама детализация - на указанный адрес")
                        send_pdf(pdf, "", send_to)
                        send_text(msg.sender, u"Ответ на запрос %s" % (subj,),
                                  [u"Детализация отправлена на адрес %s" % (send_to,)])
                    else:
                        send_pdf(pdf, "", msg.sender)
            else:# вся тема как строка поиска
                pdfs = models.PDF.all()
                names = []
                year = 0
                month = 0
                send_to = ""
                for item in subj.split(' '):
                    if is_month(item):
                        month = int(item)
                    elif is_year(item):
                        year = int(item)
                    elif is_email(item):
                        send_to = item
                    else:
                        names.append(item)
                pdfs = pdfs.search(unicode(' '.join(names)), properties=['name'])
                if year:
                    pdfs = pdfs.filter("year =", year)
                if month:
                    pdfs = pdfs.filter("month =", month)
                text = []
                pdfs = pdfs.order("-month").order("-year").fetch(50)

                if len(pdfs) == 1:
                    if send_to:
                        logging.info(u"Отправляем ответ на запрос - сама детализация - на указанный адрес")
                        send_pdf(pdfs[0], "", send_to)
                        send_text(msg.sender, u"Ответ на запрос %s" % (subj,),
                                  [u"Детализация отправлена на адрес %s" % (send_to,)])
                    else:
                        logging.info(u"Отправляем ответ на запрос - сама детализация")
                        send_pdf(pdfs[0], "", msg.sender)
                else:
                    for pdf in pdfs:
                        label = u"%s %s" % (pdf.name, gen_date(pdf))
                        text.append("<a href='%s'>%s</a>" % (make_mailto_link(pdf, send_to), label))
                    if not text:
                        text.append(u"Ничего не найдено")
                    logging.info(u"Отправляем ответ на запрос")
                    send_text(msg.sender, u"Ответ на запрос %s" % (subj,), text)


def main():
    application = webapp.WSGIApplication([LetterHandler.mapping()], debug=True)
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
