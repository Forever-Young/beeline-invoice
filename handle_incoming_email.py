# -*- coding: utf-8 -*-
import logging, re
import datetime
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext.webapp.util import run_wsgi_app

import models
from utils import send_pdf, gen_date, make_mailto_link, send_text, make_mailto_link_pdf
from email.header import decode_header

def admin_p(email):
    emails = models.AdminEmails.all().filter("enabled =", True)
    for e in emails:
        if e.email in email:
            return True
    return False

def process_query(subj, sender):
    # читаем параметры
    # m.y, m-m.y, m.y-m.y, year, -month несколько раз
    # email@domain.tld несколько раз
    # все остальное - часть имени
    names = []
    send_to = []
    dates = [] # список дат из запроса, для последующего уточнения
    minus_month = 0
    ranges = [] # список пар г,м
    for item in subj.split(' '):
        if re.match("^[^@]+@\S+$", item):
            send_to.append(item)
            continue
        m = re.match("^(\d{1,2})[.](\d{4})$", item)
        if m: # м.год
            ranges.append((int(m.group(2)), (int(m.group(1)),)))
            dates.append(item)
            continue
        m = re.match("^(\d{4})$", item)
        if m: # год
            ranges.append((int(m.group(1)), range(1, 13)))
            dates.append(item)
            continue
        m = re.match("^-(\d{1,2})$", item)
        if m: # -месяц
            today = datetime.date.today()
            month = today.month
            year = today.year
            for i in range(int(m.group(1))):
                month -= 1
                if month < 1:
                    year -= 1
                    month = 12
                ranges.append((year, (month,)))
            dates.append(item)
            minus_month = (year, month)
            continue
        m = re.match("^(\d{1,2})[.](\d{4})-(\d{1,2})[.](\d{4})$", item)
        if m: # м.год-м.год
            for y in range(int(m.group(2)), int(m.group(4)) + 1):
                if y == int(m.group(2)):
                    cur_year = range(int(m.group(1)), 13)
                elif y == int(m.group(4)):
                    cur_year = range(1, int(m.group(3)) + 1)
                else:
                    cur_year = range(1, 13)
                ranges.append((y, cur_year))
            dates.append(item)
            logging.info(ranges)
            continue
        m = re.match("^(\d{1,2})-(\d{1,2})[.](\d{4})$", item)
        if m: # м-м.г
            ranges.append((int(m.group(3)), range(int(m.group(1)), int(m.group(2)) + 1)))
            dates.append(item)
            continue
        # else:
        if item and item not in (u"Re:", u"Fwd:", u"Отв:"):
            names.append(item)

    # сначала ищем имя
    names = models.Names.all().search(unicode(' '.join(names))).fetch(50)
    if len(names) > 1:
        # уточняющие запросы
        text = []
        for name in names:
            link = " ".join([name.name] + dates + send_to)
            text.append(make_mailto_link(link, name.name))
        send_text(sender, u"Уточнение запроса %s" % (subj,), text)
    elif not names:
        logging.info(u"Ничего не найдено")
        send_text(sender, u"Ответ на запрос %s" % (subj,), [u"Ничего не найдено"])
    else:
        name = names[0]
        found = False
        if not ranges:
            # отправим последнюю и список других
            today = datetime.date.today()
            month = today.month
            year = today.year
            month -= 1
            if month < 1:
                year -= 1
                month = 12
            for pdf in models.PDF.all().filter("name =", name.name).filter("year =", year).filter("month =", month).fetch(10):
                found = True
                if send_to:
                    logging.info(u"Отправляем ответ на запрос - сама детализация - на указанный адрес(а)")
                    for s in send_to:
                        send_pdf(pdf, "", s)
                        send_text(sender, u"Ответ на запрос %s" % (subj,),
                                  [u"Детализация №%s отправлена на адрес %s" % (pdf.num, send_to,)])
                else:
                    logging.info(u"Отправляем ответ на запрос - сама детализация")
                    send_pdf(pdf, "", sender)
            if not found:
                logging.info(u"Ничего не найдено")
                send_text(sender, u"Ответ на запрос %s" % (subj,), [u"Ничего не найдено"])
            text = []
            for pdf in models.PDF.all().filter("name =", name.name).filter("year =", year).filter("month <", month):
                text.append(make_mailto_link_pdf(pdf, u"%s %s" % (pdf.name, gen_date(pdf)), send_to))
            for pdf in models.PDF.all().filter("name =", name.name).filter("year <", year):
                text.append(make_mailto_link_pdf(pdf, u"%s %s" % (pdf.name, gen_date(pdf)), send_to))
            if text:
                text.insert(0, u"Ссылки на остальные детализации")
                logging.info(u"Отправляем ссылки на остальные детализации при -month")
                send_text(sender, u"Ответ на запрос %s" % (subj,), text)

        for r in ranges:
            for m in r[1]:
                pdfs = models.PDF.all()
                pdfs = pdfs.filter("name =", name.name)
                pdfs = pdfs.filter("year =", r[0])
                pdfs = pdfs.filter("month =", m)
                for pdf in pdfs.fetch(10):
                    found = True
                    if send_to:
                        logging.info(u"Отправляем ответ на запрос - сама детализация - на указанный адрес(а)")
                        for s in send_to:
                            send_pdf(pdf, "", s)
                            send_text(sender, u"Ответ на запрос %s" % (subj,),
                                      [u"Детализация №%s отправлена на адрес %s" % (pdf.num, send_to,)])
                    else:
                        logging.info(u"Отправляем ответ на запрос - сама детализация")
                        send_pdf(pdf, "", sender)
        if not found:
            logging.info(u"Ничего не найдено")
            send_text(sender, u"Ответ на запрос %s" % (subj,), [u"Ничего не найдено"])
        if minus_month:
            text = []
            for pdf in models.PDF.all().filter("name =", name.name).filter("year =", minus_month[0]).filter("month <", minus_month[1]):
                text.append(make_mailto_link(pdf, send_to, u"%s %s" % (pdf.name, gen_date(pdf))))
            for pdf in models.PDF.all().filter("name =", name.name).filter("year <", minus_month[0]):
                text.append(make_mailto_link(pdf, send_to, u"%s %s" % (pdf.name, gen_date(pdf))))
            if text:
                text.insert(0, u"Ссылки на остальные детализации")
                logging.info(u"Отправляем ссылки на остальные детализации при -month")
                send_text(sender, u"Ответ на запрос %s" % (subj,), text)

class LetterHandler(InboundMailHandler):
    def receive(self, msg):
        if hasattr(msg, "subject") and "Invoice from Beeline" in msg.subject:
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
            if hasattr(msg, "subject"):
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
            elif not subj.replace(" ", ""):
                send_text(msg.sender, u"Помощь",
                          [
                              u"Запрос пишется в теме письма",
                              u"В любом порядке могут быть: часть имени, дата, email",
                              u"Дата вида: месяц.год, месяц.год-месяц.год, месяц-месяц.год, год",
                              u"Дат можно указывать несколько, email тоже",
                              u"На указанные email отошлется сама детализация, на email спрашивающего - уведомление",
                              u"Если при поиске по имени находятся несколько человек, посылается ответ с уточняющими ссылками",
                              u"При указании даты в виде \"год\", пошлются детализации за весь год",
                              u"Так же можно указать \"-число\", пошлются детализации за последние N месяцев",
                              u"При указании только имени, пошлется последняя детализация и список ссылок на остальные",
                          ])
            else: # вся тема как строка поиска
                process_query(subj, msg.sender)

def main():
    application = webapp.WSGIApplication([LetterHandler.mapping()], debug=True)
    run_wsgi_app(application)

if __name__ == '__main__':
    main()
