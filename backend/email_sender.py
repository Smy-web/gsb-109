import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List

class EmailSender:
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: str,
        attachments: List[str] = None
    ) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject

            msg.attach(MIMEText(body_html, 'html', 'utf-8'))

            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        part = MIMEBase('application', 'octet-stream')
                        with open(file_path, 'rb') as file:
                            part.set_payload(file.read())
                        encoders.encode_base64(part)
                        filename = os.path.basename(file_path)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}'
                        )
                        msg.attach(part)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            text = msg.as_string()
            server.sendmail(self.from_email, to_emails, text)
            server.quit()
            return True
        except Exception as e:
            print(f"邮件发送失败: {str(e)}")
            return False

    def send_parent_email(
        self,
        parent_emails: List[str],
        student_names: str,
        project_title: str,
        warm_feedback: str,
        ai_summary: str,
        technical_feedback: str = "",
        project_file: str = None
    ) -> bool:
        html_body = self._generate_parent_email_html(
            student_names,
            project_title,
            warm_feedback,
            ai_summary,
            technical_feedback
        )

        subject = f"【编程夏令营】{student_names}的项目展示精彩回顾"
        
        attachments = [project_file] if project_file and os.path.exists(project_file) else None
        
        return self.send_email(
            to_emails=parent_emails,
            subject=subject,
            body_html=html_body,
            attachments=attachments
        )

    def _generate_parent_email_html(
        self,
        student_names: str,
        project_title: str,
        warm_feedback: str,
        ai_summary: str,
        technical_feedback: str
    ) -> str:
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 15px; text-align: center; color: white; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .header p {{ margin: 10px 0 0; opacity: 0.9; }}
                .content {{ background: #fff; padding: 30px; border-radius: 15px; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .section {{ margin-bottom: 25px; }}
                .section h2 {{ color: #667eea; font-size: 18px; margin-bottom: 10px; border-left: 4px solid #667eea; padding-left: 10px; }}
                .project-info {{ background: #f0f4ff; padding: 15px; border-radius: 10px; }}
                .project-info strong {{ color: #667eea; }}
                .feedback {{ background: #fff8e1; padding: 20px; border-radius: 10px; border-left: 4px solid #ffb300; }}
                .tech-feedback {{ background: #e8f5e9; padding: 15px; border-radius: 10px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                .signature {{ margin-top: 20px; font-style: italic; color: #888; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌟 编程夏令营项目展示会</h1>
                    <p>见证孩子的成长与创造力</p>
                </div>
                <div class="content">
                    <div class="section">
                        <p>亲爱的家长您好！</p>
                        <p>非常高兴向您汇报 {student_names} 在本次编程夏令营中的精彩表现！</p>
                    </div>
                    
                    <div class="section">
                        <h2>🎯 项目信息</h2>
                        <div class="project-info">
                            <p><strong>项目名称：</strong>{project_title}</p>
                            <p><strong>项目简介：</strong>{ai_summary}</p>
                        </div>
                    </div>
                    
                    <div class="section">
                        <h2>💝 老师的话</h2>
                        <div class="feedback">
                            {warm_feedback}
                        </div>
                    </div>
                    
                    {f'''
                    <div class="section">
                        <h2>💻 技术点评</h2>
                        <div class="tech-feedback">
                            {technical_feedback}
                        </div>
                    </div>
                    ''' if technical_feedback else ''}
                    
                    <div class="signature">
                        <p>感谢您对我们编程夏令营的支持！</p>
                        <p>编程夏令营全体导师 敬上</p>
                    </div>
                </div>
                <div class="footer">
                    <p>© 2024 青少年编程夏令营 | 让编程成为孩子的超能力</p>
                </div>
            </div>
        </body>
        </html>
        """
