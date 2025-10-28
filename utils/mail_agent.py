import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pandas as pd
import logging

class Mailer:
    def __init__(self, sender, password, receiver, cc_ids):
        self.sender = sender
        self.password = password
        self.receiver = receiver
        self.receiver_cc = cc_ids
        self.logger = logging.getLogger('shopify_tracker')

    def send_alert(self, subject, body, df):
        """
        Send email with HTML table body.
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender
            msg['To'] = self.receiver
            msg['Cc'] = self.receiver_cc
            msg['Subject'] = subject

            html_table = df.to_html(index=False, border=1)
            html_content = f"""
            <html>
                <body>
                    <p>{body}</p>
                    <h3> Product Ratio Summary</h3>
                    {html_table}
                </body>
            </html>
            """
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)

            self.logger.info(f" Email sent successfully to {self.receiver}.")
        except Exception as e:
            self.logger.error(f" Failed to send email: {e}")
