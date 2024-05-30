import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_email_credentials(email, file_path='163.txt'):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    for i in range(0, len(lines), 4):
        if lines[i].strip() == email:
            password = lines[i + 2].strip()
            return email, password
    return None, None

def send_email(sender_email, password, receiver_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    smtp_server = "smtp.163.com"
    port = 465

    try:
        server = smtplib.SMTP_SSL(smtp_server, port)
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print("邮件发送成功!")
    except Exception as e:
        print(f"邮件发送失败: {e}")
    finally:
        server.quit()

def main():
    while True:
        sender_email = input("请输入你的邮箱: ")
        email, password = get_email_credentials(sender_email)

        if not email or not password:
            print("无法找到对应的邮箱账号或授权码。")
            continue

        receiver_email = input("收件人的邮箱: ")
        subject = input("邮件主题: ")
        body = input("邮件内容: ")

        send_email(sender_email, password, receiver_email, subject, body)

if __name__ == "__main__":
    main()
