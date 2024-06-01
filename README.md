# MailManager
多邮箱管理工具
## 功能
- 多账号管理
- 读取单个或全体邮件
- 发件任意切换账号
- 消息通知&定时任务
### 支持的邮箱服务
- qq.com
- 163.com
- outlook.com(不建议使用，消息同步贼慢)
- gmail.com
- ...

### 协议
- pop、smtp（imap虽好，但不是都支持）

### 使用说明
1. 【添加邮箱】栏按格式批量录入邮箱账号信息；或手动修改config/emails.txt
2. 【收件】分为全体邮箱读取最后一封；或单个邮箱读取最后5封。通过左侧账号列表或顶部输入账号两种方式 （默认全体1，单个5）
3. 如需读取全体最新，请点击展示最新未读；或启动监听服务接收语音提示（默认2分钟一次）
4. 【发件】可直接选取邮箱列表之一，发件对象只允许唯一
5. 最小化系统托盘

Gmail使用需要，生成应用密码作为授权码：   
启用此帐户上的两步验证。
https://myaccount.google.com/signinoptions/two-step-verification
启用两步验证后，您需要访问以下 URL：
• https://security.google.com/settings/security/apppasswords
