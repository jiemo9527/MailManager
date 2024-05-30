import poplib
from email.parser import Parser
from email.header import decode_header
import pyperclip
import re

from bs4 import BeautifulSoup


def read_email_accounts(file_path):
    email_accounts = []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.read().strip().split('\n')

    i = 0
    while i < len(lines):
        email = lines[i].strip()
        password = lines[i + 2].strip()
        email_accounts.append({'email': email, 'password': password})
        i += 4  # 每个账号块占四行，包括空行

    return email_accounts


# 从文件中读取邮箱账号和密码
email_accounts = read_email_accounts('163.txt')


def decode_text(encoded_text):
    decoded_parts = []
    for part in decode_header(encoded_text):
        text, encoding = part
        if isinstance(text, bytes):
            text = text.decode(encoding or 'utf-8', errors='ignore')
        decoded_parts.append(text)
    return ''.join(decoded_parts)


def decode_payload(payload, charset):
    if not payload:
        return ''
    try:
        return payload.decode(charset)
    except (UnicodeDecodeError, AttributeError):
        try:
            return payload.decode('gb18030')
        except (UnicodeDecodeError, AttributeError):
            return payload.decode('gbk', errors='ignore')


def find_continuous_data(string):  # 查找字符串中连续的数字
    result = re.findall(r"(?<!#)\b\d{4,6}\b", string)
    return result


def find_continuous_data2(string):  # 查找字符串中连续的数字
    result = re.findall(r">(\d{4,6})\b", string)
    return result


while True:
    email_input = input("\n*请输入邮箱：").strip()

    # 如果用户输入了邮箱地址，则只读取该邮箱的最后一封邮件
    if email_input:
        matched_account = None
        for account in email_accounts:
            if account['email'] == email_input:
                matched_account = account
                break
        if matched_account:
            email_accounts_to_process = [matched_account]
        else:
            print("邮箱未录入，请重新输入。")
            continue
    else:
        # 用户输入了空回车，读取所有邮箱的最后一封邮件
        email_accounts_to_process = email_accounts

    for account in email_accounts_to_process:
        try:
            # 连接到163邮箱的POP3服务器
            pop_server = 'pop.163.com'
            pop = poplib.POP3_SSL(pop_server)

            # 登录到邮箱
            pop.user(account['email'])
            pop.pass_(account['password'])

            # 获取邮件总数
            num_messages = len(pop.list()[1])

            # 只读取最后一封邮件
            last_message_index = num_messages

            # 获取最后一封邮件内容
            response, lines, octets = pop.retr(last_message_index)
            msg_content = b'\r\n'.join(lines).decode('utf-8', errors='ignore')

            # 解析邮件内容
            msg = Parser().parsestr(msg_content)

            # 提取发件人、主题和日期
            sender = msg.get('From')
            subject = msg.get('Subject')
            date = msg.get('Date')

            # 解码邮件头部
            decoded_sender = decode_text(sender)
            decoded_subject = decode_text(subject)
            decoded_date = decode_text(date)

            # 提取邮件内容
            for part in msg.walk():
                # if part.get_content_type() == 'text/plain':
                charset = part.get_content_charset()
                body = part.get_payload(decode=True)

                decoded_body = decode_payload(body, charset)
                # 去除干扰项
                decoded_body = decoded_body.strip(' ')
                decoded_body = decoded_body.replace("charset=GB18030", "")
                if find_continuous_data2(decoded_body):
                    result = find_continuous_data2(decoded_body)
                else:
                    result = find_continuous_data(decoded_body)
                if (len(result) == 1):
                    verification_code = result[0]
                    pyperclip.copy(verification_code)
                    print(str(account['email']) + '↓')
                    print(f'[{decoded_subject} 验证码:  {verification_code}  已复制到剪切板] {decoded_date}')
                    pass
                else:
                    print(str(account['email']) + '↓')
                    # 解析 HTML 并提取所有文本内容
                    soup = BeautifulSoup(decoded_body, 'html.parser')
                    text_content = soup.get_text()
                    # 去除所有空格和空行
                    cleaned_text = re.sub(r'\s+', '', text_content)
                    print(cleaned_text)
            # 关闭连接
            pop.quit()
        except Exception as e:
            print(str(account['email']) + '↓')
            print(f"【发生错误:{e}")
