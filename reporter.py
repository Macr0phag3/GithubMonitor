# -*- coding: utf-8 -*-

# 2018.11.23 11:07:07 by nobody

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib


class Reporter:
    def __init__(self, email_from, smtp_server, smtp_port, email_username=None, email_password=None):
        self.email_from = email_from
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_username = email_username
        self.email_password = email_password
        self.sent_emails_counter = 0

    def _send_email(self, email, email_to_string):
        mail_server = smtplib.SMTP(host=self.smtp_server, port=self.smtp_port)
        if int(self.smtp_port) != 25:
            mail_server.starttls()
        if self.email_username is not None:
            mail_server.login(self.email_username, self.email_password)
        try:
            mail_server.sendmail(self.email_from, email_to_string, email.as_string())
            self.sent_emails_counter += 1
        finally:
            mail_server.close()

    def alert(self, content, email_to_string):
        email = MIMEMultipart('alternative')
        email['Subject'] = "Github Monitor"
        email['From'] = self.email_from
        email['To'] = email_to_string
        part_html = MIMEText(content, 'html', 'utf-8')
        email.attach(part_html)

        self._send_email(email, email_to_string)
