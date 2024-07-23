import json
import os
import poplib
import subprocess
import sys
import webbrowser
from email.parser import Parser
from email.header import decode_header
import pyperclip
import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, font
from tkinter import Listbox, SINGLE, END
from concurrent.futures import ThreadPoolExecutor, as_completed
import winsound
from bs4 import BeautifulSoup
import logging
from tkinter import ttk
import pystray
from PIL import Image
import threading
import settings


# 创建系统托盘图标
def create_image():
    # 使用本地的icon文件
    return Image.open("resource/mailManger.ico")

def on_quit(icon, item):
    icon.stop()
    root.quit()
def show_window(icon, item):
    icon.stop()
    root.after(0, root.deiconify)
def hide_window():
    root.withdraw()
    image = create_image()
    menu = (pystray.MenuItem('打开界面', show_window), pystray.MenuItem('退出', on_quit))
    icon = pystray.Icon("test", image, "邮件管理", menu)
    threading.Thread(target=icon.run).start()


# 配置日志记录器
current_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(current_dir, 'config', 'err.log')
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
# 设置日志记录
logging.basicConfig(
    filename=log_file_path,
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# 全局变量用于保存查询结果
saved_results = []


# 读取配置文件
def read_email_accounts(file_path='config/emails.txt'):
    email_accounts = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.read().strip().split('\n')

        i = 0
        while i < len(lines):
            email = lines[i].strip()
            web_password = lines[i + 1].strip()
            account_password = lines[i + 2].strip()
            email_accounts.append({'email': email, 'web_password': web_password, 'password': account_password})
            i += 4  # 每个账号块占四行，包括空行

    except FileNotFoundError:
        logging.error(f"文件 {file_path} 未找到，请确认文件存在于当前路径下。")
        messagebox.showerror("错误", f"文件 {file_path} 未找到，请确认文件存在于当前路径下。")
    except Exception as e:
        logging.error(f"读取文件时发生错误: {e}")
        messagebox.showerror("错误", f"读取文件时发生错误: {e}")

    return email_accounts


# 收件服务器
def get_pop_server(email):
    if email.endswith('@163.com'):
        return 'pop.163.com', 995
    elif email.endswith('@qq.com'):
        return 'pop.qq.com', 995
    elif email.endswith('@gmail.com'):
        return 'pop.gmail.com', 995
    elif email.endswith('@outlook.com') or email.endswith('@hotmail.com') or email.endswith('@live.com'):
        return 'pop-mail.outlook.com', 995
    else:
        raise ValueError(f"不支持的邮箱提供商: {email}")


# 发件服务器
def get_smtp_server(email):
    domain = email.split('@')[-1]
    if domain == '163.com':
        return 'smtp.163.com', 465  # 163邮箱的SMTP服务器地址和端口
    elif domain == 'qq.com':
        return 'smtp.qq.com', 465  # QQ邮箱的SMTP服务器地址和端口
    elif domain == 'gmail.com':
        return 'smtp.gmail.com', 587  # Gmail的SMTP服务器地址和端口
    elif domain == 'outlook.com' or domain == 'hotmail.com' or domain == 'live.com':
        return 'smtp.office365.com', 587  # Outlook的SMTP服务器地址和端口
    else:
        raise ValueError("不支持的邮箱服务提供商")


# 编码&转义
def decode_text(encoded_text):
    decoded_parts = []
    for part in decode_header(encoded_text):
        text, encoding = part
        if text is not None:
            if isinstance(text, bytes):
                text = text.decode(encoding or 'utf-8', errors='ignore')
            decoded_parts.append(text)
    return ''.join(decoded_parts)
def decode_payload(payload, charset):
    if payload is None:
        return ''
    try:
        decoded_text = payload.decode(charset)
    except (UnicodeDecodeError, AttributeError):
        try:
            decoded_text = payload.decode('gb18030')
        except (UnicodeDecodeError, AttributeError):
            decoded_text = payload.decode('gbk', errors='ignore')

    # 处理特定格式的 Unicode 转义字符
    if re.search(r'\\u[0-9a-fA-F]{4}', decoded_text):
        try:
            decoded_text = decoded_text.encode('latin1').decode('unicode-escape')
        except (UnicodeDecodeError, AttributeError):
            pass

    return decoded_text


# 验证码匹配
def find_continuous_data(string):
    # 匹配不以 # 开头的 4 到 6 位数字，末尾是空格或换行
    return re.findall(r"(?<!#)\b\d{4,6}\b(?=\s|$)", string)
def find_continuous_data2(string):
    # 匹配以 > 开头的 4 到 6 位数字，末尾是空格或换行
    return re.findall(r">(\d{4,6})(?=\s|$)", string)


def replace_multiple_newlines(text):
    return re.sub(r'\s+', '', text.strip())

def fetch_emails(account, fetch_last_n=1):
    results = []
    try:
        pop_server, port = get_pop_server(account['email'])
        pop = poplib.POP3_SSL(pop_server, port)

        pop.user(account['email'])
        pop.pass_(account['password'])

        num_messages = len(pop.list()[1])
        start_index = max(1, num_messages - fetch_last_n + 1)

        for i in range(start_index, num_messages + 1):
            response, lines, octets = pop.retr(i)
            msg_content = b'\r\n'.join(lines).decode('utf-8', errors='ignore')
            msg = Parser().parsestr(msg_content)

            sender = msg.get('From')
            subject = msg.get('Subject')
            date = msg.get('Date')

            decoded_sender = decode_text(sender)
            decoded_subject = decode_text(subject)
            decoded_date = decode_text(date)

            email_header = f"{account['email']} ↓\n"
            email_info = f"时间: {decoded_date}\n"
            email_content = email_header + email_info
            email_content = email_content.strip()

            for part in msg.walk():
                charset = part.get_content_charset()
                body = part.get_payload(decode=True)
                decoded_body = decode_payload(body, charset)
                decoded_body = decoded_body.strip()
                soup = BeautifulSoup(decoded_body, 'html.parser')
                for script_or_style in soup(['script', 'style']):
                    script_or_style.decompose()


                body_tag = soup.find('body')
                if body_tag:
                    email_content += body_tag.get_text() + '\n'

                    # 查找所有的 <a> 标签
                    for a_tag in body_tag.find_all('a'):
                        link_text = a_tag.get_text(strip=True)
                        link_href = a_tag.get('href')
                        if link_text and link_href:
                            email_content += f"{link_text} ({link_href})\n"
                else:
                    email_content += soup.get_text() + '\n'
                    for a_tag in soup.find_all('a'):
                        link_text = a_tag.get_text(strip=True)
                        link_href = a_tag.get('href')
                        if link_text and link_href:
                            email_content += f"{link_text} ({link_href})\n"
            # 替换多个连续换行符为一个
            email_content = replace_multiple_newlines(email_content)
            email_content += '\n\n'
            results.append(email_content)

        pop.quit()
    except Exception as e:
        e = str(e)
        if 'must be str, not None' not in e:
            logging.error(f"处理邮箱 {account['email']} 时发生错误: {e}")
            results.append(f"{account['email']}【发生错误:{e}】\n")
    return results[::-1]
def fetch_all_emails(email_accounts, write_to_file=False):
    results = []
    seen_emails = set()  # 用于跟踪已处理的邮箱地址
    file_content = {}  # 用于保存要写入到文件中的内容
    with ThreadPoolExecutor() as executor:
        future_to_account = {executor.submit(fetch_emails, account): account for account in email_accounts}
        for future in as_completed(future_to_account):
            account = future_to_account[future]
            try:
                if account['email'] not in seen_emails:
                    seen_emails.add(account['email'])
                    fetch_results = future.result()
                    results.extend(fetch_results)
                    if write_to_file:
                        file_content[account['email']] = fetch_results
            except Exception as e:
                logging.error(f"处理邮箱 {account['email']} 时发生错误: {e}")
    return results

# 保存查询结果到本地文件
def save_results_to_file(results):
    email_data = {}
    for result in results:
        if '↓' in result:
            email, content = result.split('↓', 1)
            email_data[email] = content.strip()

    # 创建缓存目录
    os.makedirs('cache', exist_ok=True)

    # 尝试读取现有内容
    file_path = 'cache/email_contents.json'
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    # 合并新数据
    existing_data.update(email_data)

    # 写回合并后的内容
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)

# 收件界面
def create_receive_frame(root, font_style):
    global saved_results
    global monitoring

    monitoring = False

    # 变量保存搜索状态
    search_index = 0
    search_results = []

    def on_receive():
        global saved_results
        email_input = email_entry.get().strip()
        output_text.delete(1.0, tk.END)
        search_results_count.config(text="")  # 清空查找结果个数
        email_accounts = read_email_accounts()
        if email_accounts:
            email_listbox.delete(0, END)
            email_listbox.insert(END, "*所有邮件最后一封*")
            for account in email_accounts:
                email_listbox.insert(END, account['email'])
            saved_results = []  # 清空保存的结果
            if email_input:
                for account in email_accounts:
                    if account['email'] == email_input:
                        results = fetch_emails(account, fetch_last_n=10)
                        for result in results:
                            output_text.insert(tk.END, result)
                        break
            else:
                saved_results = fetch_all_emails(email_accounts, write_to_file=True)
                save_results_to_file(saved_results)  # 保存结果到本地文件
                for result in saved_results:
                    output_text.insert(tk.END, result)
        else:
            messagebox.showerror("错误", "无法读取邮箱账户信息。")

    def on_email_select(event):
        selected_index = email_listbox.curselection()
        if selected_index:
            selected_email = email_listbox.get(selected_index)
            output_text.delete(1.0, tk.END)
            search_results_count.config(text="")  # 清空查找结果个数
            if selected_email == "*所有邮件最后一封*":
                email_entry.delete(0, tk.END)  # 清空输入框
                email_accounts = read_email_accounts()
                if email_accounts:
                    saved_results = fetch_all_emails(email_accounts, write_to_file=True)
                    save_results_to_file(saved_results)  # 保存结果到本地文件
                    for result in saved_results:
                        output_text.insert(tk.END, result)
                else:
                    messagebox.showerror("错误", "无法读取邮箱账户信息。")

            else:
                email_entry.delete(0, tk.END)  # 清空输入框
                email_entry.insert(0, selected_email)  # 将双击的邮箱填入输入框
                email_accounts = read_email_accounts()
                for account in email_accounts:
                    if account['email'] == selected_email:
                        results = fetch_emails(account, fetch_last_n=10)
                        for result in results:
                            output_text.insert(tk.END, result)
                        break

    def find_in_text():
        global search_index
        search = search_entry.get()
        output_text.tag_remove('found', '1.0', tk.END)
        search_results.clear()  # 清空之前的搜索结果
        count = 0
        if search:
            idx = '1.0'
            while idx:
                idx = output_text.search(search, idx, nocase=1, stopindex=tk.END)
                if idx:
                    lastidx = f"{idx}+{len(search)}c"
                    output_text.tag_add('found', idx, lastidx)
                    idx = lastidx
                    output_text.see(idx)
                    search_results.append(idx)  # 记录匹配的索引
                    count += 1
            output_text.tag_config('found', foreground='red', background='orange')
        search_results_count.config(text=f"结果数:{count}")
        search_index = 0  # 重置当前索引

    def next_result():
        global search_index
        if search_results:
            if search_index < len(search_results):
                if search_index > 0:
                    # 移除上一个匹配的标记
                    output_text.tag_remove('found', search_results[search_index - 1], f"{search_results[search_index - 1]}+{len(search_entry.get())}c")
                output_text.see(search_results[search_index])
                output_text.tag_add('found', search_results[search_index], f"{search_results[search_index]}+{len(search_entry.get())}c")
                search_index += 1
            else:
                search_index = 0  # 重置索引循环

    def display_unread_emails():
        global saved_results
        email_accounts = read_email_accounts()
        if not email_accounts:
            messagebox.showerror("错误", "无法读取邮箱账户信息。")
            return

        # 获取最新的未读邮件
        latest_results = fetch_all_emails(email_accounts, write_to_file=False)
        new_results = []

        # 读取本地 JSON 文件内容
        local_results = {}
        if os.path.exists('cache/email_contents.json'):
            with open('cache/email_contents.json', 'r', encoding='utf-8') as f:
                local_results = json.load(f)

        # 比较最新结果与本地文件内容
        for result in latest_results:
            if '↓' in result:
                email, content = result.split('↓', 1)
                content = content.strip()
                if email not in local_results or local_results[email] != content:
                    new_results.append(result)
            else:
                # 处理没有正确格式的结果
                logging.warning(f"结果格式不正确: {result}")

        # 更新输出框
        output_text.delete(1.0, tk.END)
        if new_results:
            for result in new_results:
                output_text.insert(tk.END, result)
            # 追加新邮件到本地文件
            save_results_to_file(new_results)

            # 播放提示音
            winsound.PlaySound(settings.monitoringSound, winsound.SND_FILENAME)
        else:
            output_text.insert(tk.END, "【无新邮件  (*^▽^*)!】")

    def start_monitoring():
        global monitoring
        if not monitoring:
            monitoring = True
            monitor_emails()

    def monitor_emails():
        global monitoring
        if monitoring:
            display_unread_emails()
            root.after(settings.monitoringTime, monitor_emails)  # 2分钟执行一次

    # 搜索框相关
    def toggle_search_frame(event=None):
        if search_frame.winfo_ismapped():
            search_frame.grid_forget()  # 隐藏搜索框
        else:
            search_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ew")  # 显示搜索框
            search_entry.focus_set()  # 聚焦到搜索输入框

    # 绑定 Ctrl+F 快捷键
    root.bind('<Control-f>', toggle_search_frame)

    # 创建搜索框和按钮
    search_frame = tk.Frame(root)

    search_entry = tk.Entry(search_frame, width=20, font=font_style)  # 调整宽度
    search_entry.grid(row=0, column=0, padx=5)

    search_button = tk.Button(search_frame, text="查找", command=find_in_text, font=font_style, width=6)  # 设置宽度
    search_button.grid(row=0, column=1, padx=5)

    next_button = tk.Button(search_frame, text="下一个", command=next_result, font=font_style, width=6)  # 设置宽度
    next_button.grid(row=0, column=2, padx=5)

    search_results_count = tk.Label(search_frame, text="", font=font_style)
    search_results_count.grid(row=0, column=3, padx=5)

    # 创建主界面
    frame = tk.Frame(root)
    frame.grid(row=1, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

    email_label = tk.Label(frame, text="请输入邮箱（留空读取所有邮箱）:", font=font_style)
    email_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    email_entry = tk.Entry(frame, width=30, font=font_style)
    email_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    fetch_button = tk.Button(frame, text="读取邮箱", command=on_receive, font=font_style)
    fetch_button.grid(row=0, column=2, padx=5, pady=5, sticky="w")

    # 添加“展示最新未读”按钮
    unread_button = tk.Button(frame, text="展示最新未读", command=display_unread_emails, font=font_style)
    unread_button.grid(row=0, column=4, padx=5, pady=5, sticky="w")

    # 添加“启动监听服务”按钮
    monitor_button = tk.Button(frame, text="启动监听服务", command=start_monitoring, font=font_style)
    monitor_button.grid(row=0, column=5, padx=5, pady=5, sticky="w")

    list_frame = tk.Frame(root)
    list_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ns")

    email_listbox = Listbox(list_frame, selectmode=SINGLE, font=font_style, width=40, height=40)
    email_listbox.pack(side=tk.LEFT, fill=tk.Y)

    email_listbox.bind('<<ListboxSelect>>', on_email_select)
    email_listbox.bind('<Double-1>', on_email_select)  # 绑定双击事件

    output_text = scrolledtext.ScrolledText(root, width=100, height=40, wrap=tk.WORD, font=font_style)
    output_text.grid(row=2, column=1, padx=10, pady=10, sticky="nsew")

    # 在初始化时立即读取邮箱账户并填充列表
    email_accounts = read_email_accounts()
    if email_accounts:
        email_listbox.delete(0, END)
        email_listbox.insert(END, "*所有邮件最后一封*")
        for account in email_accounts:
            email_listbox.insert(END, account['email'])
    else:
        messagebox.showerror("错误", "无法读取邮箱账户信息。")

    # 初始时隐藏搜索框
    search_frame.grid_forget()

# 发件界面
def create_send_frame(root, font_style):

    def send_email():
        sender_email = sender_combobox.get().strip()
        recipient_email = recipient_entry.get().strip()
        subject = subject_entry.get().strip()
        body = body_text.get("1.0", tk.END).strip()

        if not sender_email or not recipient_email or not subject or not body:
            messagebox.showerror("错误", "所有字段都是必填的。")
            return

        # 检查接收人邮箱格式
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, recipient_email):
            messagebox.showerror("错误", "接收人邮箱格式不正确。")
            return

        # 获取发件人邮箱的密码
        sender_password = next((account['password'] for account in email_accounts if account['email'] == sender_email), None)
        if not sender_password:
            messagebox.showerror("错误", "未找到发件人邮箱的密码。")
            return

        # 获取SMTP服务器地址和端口
        try:
            smtp_server, smtp_port = get_smtp_server(sender_email)
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            return

        # 发送邮件逻辑
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject

            # 添加邮件正文
            msg.attach(MIMEText(body, 'plain'))

            if smtp_port == 465:  # 使用SSL连接
                with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, recipient_email, msg.as_string())
            else:  # 使用STARTTLS连接
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, recipient_email, msg.as_string())

            messagebox.showinfo("成功", "邮件发送成功！")
        except Exception as e:
            logging.error(f"发送邮件时发生错误: {e}")
            messagebox.showerror("错误", f"发送邮件时发生错误: {e}")

    # 读取邮箱账户
    email_accounts = read_email_accounts()
    email_addresses = [account['email'] for account in email_accounts]

    frame = tk.Frame(root)
    frame.grid(row=1, column=0, columnspan=2, pady=10, padx=10, sticky="nsew")

    sender_label = tk.Label(frame, text="发件人邮箱:", font=font_style)
    sender_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

    sender_combobox = ttk.Combobox(frame, values=email_addresses, font=font_style, state='readonly', width=30)
    sender_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    recipient_label = tk.Label(frame, text="收件人邮箱:", font=font_style)
    recipient_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
    recipient_entry = tk.Entry(frame, width=40, font=font_style)
    recipient_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

    subject_label = tk.Label(frame, text="主题:", font=font_style)
    subject_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
    subject_entry = tk.Entry(frame, width=40, font=font_style)
    subject_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

    body_label = tk.Label(frame, text="正文:", font=font_style)
    body_label.grid(row=3, column=0, padx=5, pady=5, sticky="ne")
    body_text = scrolledtext.ScrolledText(frame, width=60, height=20, wrap=tk.WORD, font=font_style)
    body_text.grid(row=3, column=1, padx=5, pady=5, sticky="nsew")

    send_button = tk.Button(frame, text="发送邮件", command=send_email, font=font_style)
    send_button.grid(row=4, column=1, padx=5, pady=10, sticky="e")

    # 配置行列权重，使界面自适应调整
    frame.grid_rowconfigure(3, weight=1)
    frame.grid_columnconfigure(1, weight=1)

    # 设置框架占窗口的85%
    root.update_idletasks()
    width = int(root.winfo_width() * 0.85)
    height = int(root.winfo_height() * 0.85)
    frame.config(width=width, height=height)

    # 自动修正邮箱格式
    def fix_email_format(event):
        email = recipient_entry.get().strip()
        if email.endswith("com") and '.' not in email[:-3]:
            # 在 "com" 前加上一个点
            email = email[:-3] + '.' + email[-3:]
            recipient_entry.delete(0, tk.END)
            recipient_entry.insert(0, email)

    recipient_entry.bind('<FocusOut>', fix_email_format)

# 添加邮箱界面
def create_add_account_frame(root, font_style):
    def save_accounts():
        accounts_text = accounts_entry.get("1.0", tk.END).strip()
        if not accounts_text:
            messagebox.showerror("错误", "请输入邮箱账号信息。")
            return

        existing_emails = set()
        try:
            with open('config/emails.txt', 'r', encoding='utf-8') as f:
                lines = f.read().strip().split('\n')
                for i in range(0, len(lines), 4):
                    existing_emails.add(lines[i].strip())
        except FileNotFoundError:
            pass  # 如果文件不存在，则认为没有已存在的邮箱

        new_accounts = accounts_text.split('\n')
        accounts_to_save = []

        for account in new_accounts:
            if '##' not in account or len(account.split('##')) != 3:
                messagebox.showerror("错误", f"格式不正确: {account}\n请使用'邮箱账号##web端密码##账号密码'格式。")
                return

            email, web_password, account_password = map(str.strip, account.split('##'))
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                messagebox.showerror("错误", f"邮箱格式不正确: {email}")
                return
            if email in existing_emails:
                messagebox.showerror("错误", f"该账号已存在: {email}")
                return
            accounts_to_save.append(f"{email}\n{web_password}\n{account_password}\n\n")
            existing_emails.add(email)

        # 删除文件末尾的空行，并新增一行空行
        try:
            with open('config/emails.txt', 'r+', encoding='utf-8') as f:
                lines = f.readlines()
                while lines and not lines[-1].strip():
                    lines.pop()
                lines.append('\n')  # 新增一行空行
                f.seek(0)
                f.truncate()
                f.writelines(lines)
        except FileNotFoundError:
            with open('config/emails.txt', 'w', encoding='utf-8') as f:
                f.write('\n')  # 文件不存在时，创建文件并新增一行空行

        try:
            with open('config/emails.txt', 'a', encoding='utf-8') as f:
                f.writelines(accounts_to_save)
            messagebox.showinfo("成功", "邮箱账号信息已保存。")
        except Exception as e:
            logging.error(f"保存邮箱账号信息时发生错误: {e}")
            messagebox.showerror("错误", f"保存邮箱账号信息时发生错误: {e}")

    def open_email_file():
        # 获取程序所在的路径
        program_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        email_file_path = os.path.join(program_dir, 'config', 'emails.txt')

        if not os.path.exists(email_file_path):
            os.makedirs(os.path.dirname(email_file_path), exist_ok=True)
            with open(email_file_path, 'w', encoding='utf-8') as f:
                pass

        try:
            if os.name == 'nt':  # Windows
                os.startfile(email_file_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(('open' if sys.platform == 'darwin' else 'xdg-open', email_file_path))
        except Exception as e:
            logging.error(f"打开emails.txt文件时发生错误: {e}")
            messagebox.showerror("错误", f"打开emails.txt文件时发生错误: {e}")

    frame = tk.Frame(root)
    frame.grid(row=1, column=0, columnspan=2, pady=10, padx=10, sticky="nsew")

    instruction_text = tk.Text(frame, width=60, height=4, wrap=tk.WORD, font=font_style, bg=root.cget("bg"), bd=0,
                               highlightthickness=0)
    instruction_text.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    instruction_text.insert(tk.END, "请输入邮箱账号信息，格式为：\n")
    instruction_text.insert(tk.END, "邮箱账号##web端密码##账号密码\n", "highlight")
    instruction_text.insert(tk.END, "每行一个账号信息，请核对信息准确")
    instruction_text.tag_configure("highlight", foreground="orange")
    instruction_text.config(state=tk.DISABLED)  # 设置为只读

    accounts_entry = scrolledtext.ScrolledText(frame, width=60, height=20, wrap=tk.WORD, font=font_style)
    accounts_entry.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

    button_frame = tk.Frame(frame)
    button_frame.grid(row=2, column=0, pady=10, sticky="w")

    save_button = tk.Button(button_frame, text="保存", command=save_accounts, font=font_style)
    save_button.grid(row=0, column=0, padx=5)

    manual_config_button = tk.Button(button_frame, text="手动配置", command=open_email_file, font=font_style)
    manual_config_button.grid(row=0, column=1, padx=5)

    # 配置行列权重，使界面自适应调整
    frame.grid_rowconfigure(1, weight=1)
    frame.grid_columnconfigure(0, weight=1)


def main():
    global root
    root = tk.Tk()
    root.title("邮件管理")
    # 获取屏幕宽度和高度
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # 设置窗口大小为屏幕宽度和高度
    window_width = int(screen_width * settings.custom_width)
    window_height = int(screen_height * settings.custom_height)

    # 设置窗口大小和位置
    root.geometry(
        f"{window_width}x{window_height}+{(screen_width - window_width) // 2}+{(screen_height - window_height) // 2}")

    font_style = font.Font(size=12)  # 调整字体大小

    def switch_to_receive():
        for widget in root.winfo_children():
            if isinstance(widget, tk.Frame) and widget != button_frame:
                widget.destroy()
        create_receive_frame(root, font_style)

    def switch_to_send():
        for widget in root.winfo_children():
            if isinstance(widget, tk.Frame) and widget != button_frame:
                widget.destroy()
        create_send_frame(root, font_style)

    def switch_to_add_account():
        for widget in root.winfo_children():
            if isinstance(widget, tk.Frame) and widget != button_frame:
                widget.destroy()
        create_add_account_frame(root, font_style)

    def open_about_link():
        webbrowser.open("https://github.com/jiemo9527/MailManager")

    # 创建按钮框架
    button_frame = tk.Frame(root)
    button_frame.grid(row=0, column=0, columnspan=2, pady=10, padx=10, sticky="ew")

    receive_button = tk.Button(button_frame, text="[收 件]", command=switch_to_receive, font=font_style)
    receive_button.pack(side=tk.LEFT, padx=0)

    send_button = tk.Button(button_frame, text="[发 件]", command=switch_to_send, font=font_style)
    send_button.pack(side=tk.LEFT, padx=0)

    add_account_button = tk.Button(button_frame, text="[添加邮箱]", command=switch_to_add_account, font=font_style)
    add_account_button.pack(side=tk.LEFT, padx=0)

    about_button = tk.Button(button_frame, text="[关于]", command=open_about_link, font=font_style)
    about_button.pack(side=tk.LEFT, padx=0)

    # 配置行列权重，使界面自适应调整
    root.grid_rowconfigure(2, weight=1)
    root.grid_columnconfigure(1, weight=1)

    switch_to_receive()  # 默认打开收件界面

    # 绑定窗口最小化事件
    root.protocol("WM_DELETE_WINDOW", hide_window)

    root.mainloop()


if __name__ == "__main__":
    main()
