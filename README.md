# 青少年编程夏令营 · 家长邮件发送子系统

## 这个仓库是什么

为期两周的青少年编程夏令营，结营那天每组孩子上台展示作品。展示结束后，班主任在后台点一下，系统就把这个项目的作品回顾发给家长：一段温暖评语、一段 AI 生成的项目简介、导师的技术点评，外加孩子的作品文件（Scratch 的 `.sb3`，动辄几十 MB）。

这里裁剪出来的只有**发邮件**这一段：Web 路由、ORM、录音转写、AI 评语生成都不在范围内，不要去找它们。上游调用方是夏令营后台的 Flask 服务。

## 目录

- `backend/email_sender.py` — 本次要改的模块，就这一个文件。

`backend` 没有 `__init__.py`，按命名空间包用。验证命令必须从仓库根目录、用 `-m` 的形式跑，这样仓库根才会进 `sys.path`，`from backend.email_sender import EmailSender` 才解析得到。

## 运行环境

教务内网机器，离线。`~/venvs/gsb-camp` 里只有 `requirements-task.txt` 列出来的包；这个模块本身只用标准库（`smtplib` / `email.mime` / `os`）。**测试里必须用替身把 `smtplib` 顶掉，不得真连任何 SMTP 服务器，不得联网，不得新增第三方依赖。**替身要真的把每封信的收件人列表和报文文本捕获下来供断言，不要写一个对报文不做任何检查就返回成功的替身。临时文件用 `tmp_path`，跑完整套测试之后仓库工作树必须干净。

## 上游怎么用这个模块（硬约定）

上游 Flask 服务的调用点是固定的，按关键字参数传：

```
sender = EmailSender(Config.SMTP_SERVER, Config.SMTP_PORT, Config.SMTP_USERNAME,
                     Config.SMTP_PASSWORD, Config.SMTP_FROM_EMAIL)

parent_emails = [e.strip() for e in project.parent_emails.split(',') if e.strip()]

success = sender.send_parent_email(
    parent_emails=parent_emails,
    student_names=project.student_names,
    project_title=project.title,
    warm_feedback=presentation.warm_feedback or '',
    ai_summary=presentation.ai_summary or '',
    technical_feedback=presentation.technical_feedback or '',
    project_file=project.project_file_path,
)
if success:
    presentation.email_sent = True
    presentation.email_sent_at = datetime.utcnow()
```

注意最后那三行：上游拿这个布尔值直接决定要不要把 `email_sent` 落成 True，落错了家长那边就会显示「已发送」而其实没发出去，或者反过来被班主任再点一次。所以布尔值的口径不是随手定的东西，见下面 F3。

`send_email` 是内部通用发送口，除了 `send_parent_email`，后台还有一个「补发通知」的定时任务在调它。

---

## 现有行为（preserve 清单，一条都不能动）

这些是下游和家长们已经习惯的东西：

**P1 签名与返回类型。**

```
EmailSender(smtp_server, smtp_port, username, password, from_email)          # 位置参数顺序
send_email(to_emails, subject, body_html, attachments=None) -> bool
send_parent_email(parent_emails, student_names, project_title, warm_feedback,
                  ai_summary, technical_feedback="", project_file=None) -> bool
```

方法名、既有参数的名字与顺序、返回类型都是 bool——都不许改。要加东西只能用**带默认值的可选关键字参数**，加在上游已经在用的那些参数后面。

**P2 异常不外抛。** 发送链路上的任何异常都不得冒到调用方；上游没有 try/except，冒出去就是一个 500。失败只能通过返回值和你新加的结果明细表达。

**P3 邮件主题格式。** `【编程夏令营】{student_names}的项目展示精彩回顾`，一字不改。

**P4 HTML 正文模板。** `_generate_parent_email_html` 生成的结构和全部中文标记文字保持现状，包括：`编程夏令营项目展示会` 页头、`亲爱的家长您好！`、`项目信息` 段里的 `项目名称：` 与 `项目简介：`、`老师的话` 段、`技术点评` 段、`编程夏令营全体导师 敬上` 落款、`© 2024 青少年编程夏令营` 页脚，以及内联的 `<style>` 块。`technical_feedback` 为空串时**整段「技术点评」不出现**，这个条件渲染也要保住。

**P5 MIME 结构。** 报文是 `multipart/mixed`；`From` 头等于 `from_email`；`Subject` 头等于主题；第一个 payload 是 `text/html`、charset 为 `utf-8`；每个附件是一个 `application/octet-stream` 的 part，base64 编码。

**P6 附件的存在性判断。** `send_parent_email` 里，`project_file` 为 `None` 或者磁盘上不存在时，这封信不带附件（不是整批失败）。

---

## 本次要做的扩展

结营那天一个班三十二个项目、每个项目两到四个家长邮箱，班主任是一个一个点过去的。现在这套「一封信抄送全部家长、一次投递定生死」的写法撑不住了，教务那边提了几件事：

**F1 一人一封信。** 同一个项目下的家长现在是塞在同一封信的收件人里的，家长 A 打开邮件能看到家长 B、家长 C 的邮箱地址。去年就有家长投诉过这件事，教务明确要求：**一个批次里每个家长地址单独成一封信，`To` 头里只有本人**。同一个批次里各封信的主题、正文、附件内容保持一致。

**F2 连接与中断。** 一个批次里几十封信，不要每封都重新连一次 SMTP；批次进行中连接断掉或者被服务器限流踢掉时怎么处理（重连一次接着发、还是把剩下的地址全部记为失败），是个取舍点，见下。

**F3 逐人结果与布尔值口径。** 现在一个地址被服务器拒了，整批返回 `False`，可前面几个地址其实已经投递出去了；班主任看到失败就再点一次，已经收到的家长于是收到第二封、第三封。运维那边翻日志也翻不出到底谁收到了谁没收到——失败只 `print` 一行就没了。

要求：调用方能拿到**每个地址**的结果（至少区分「已发送」「发送失败」「因退订跳过」「因重复跳过」四种）和失败原因。但 P1 摆在那儿，返回类型必须还是 bool，所以怎么把明细暴露出去是个取舍点。同时你必须明确定下布尔值的口径：批次里至少有一个有效地址时，什么情况返回 True、什么情况返回 False——上游拿它写 `email_sent`，见上面那段代码。

**F4 幂等重发。** 同一批次里已经成功投递过的地址，第二次调用不得再发一遍。批次键从哪来（调用方传进来、还是由主题加地址派生）是个取舍点；台账存在哪里（进程内存、调用方注入的存储对象、`tmp_path` 下的文件）也是取舍点，但不得联网、不得往仓库工作目录里写东西。

**F5 退订名单。** 有家长通过邮件页脚的链接退了订。退订名单里的地址要记成「因退订跳过」，**一封信都不许发给他**，而且他的跳过不能影响同批次其他家长的投递结果。名单怎么传进来受 P1 约束：只能用可选关键字参数或者构造函数的可选参数。

**F6 地址清洗。** 运营是从 Excel 里粘的家长邮箱，`Project.parent_emails` 那个逗号串里什么样的脏数据都有：两侧带空格、空项、同一个地址大小写不同地写了两遍。清洗口径固定为：去两侧空白、丢掉空项、去重且保留首次出现的顺序。

> 大小写怎么归并是个取舍点：域名部分肯定不区分大小写，本地部分（`@` 前面）归不归并由你定——归并了可能把两个真实存在的不同邮箱合成一个，不归并又挡不住运营重复粘贴。选定一种，把理由写进下面那一节。

**F7 附件只读一次。** 逐人发送之后，一份 40 MB 的 `.sb3` 作品文件不能在每个收件人那儿都从磁盘重读一遍。同一个批次里同一份附件只读一次，各封信里的附件字节完全相同。批次进行中附件文件消失或者读不出来时怎么办，是个取舍点。

---

## 测试要求

新建 `tests/`。上面 P1–P6、F1–F7 每一条至少一条测试，用替身 SMTP 捕获**每封信**的收件人列表和报文文本，断言可观察的结果——报文里的 `To` 头、part 的数量与类型、字节内容、返回的布尔值、逐人明细——不要只断言「没抛异常」或者「返回了一个布尔值」。

至少要有一条负例钉住 F4：把「已成功投递过的地址跳过」那一步从实现里去掉，这条测试必须变红。

测试不得联网，不得依赖 `.env` 或真实环境变量，不得往仓库工作目录写文件，不得真的 `sleep` 几十秒。

## 已定口径与自定口径

F2（连接中断）、F3（明细怎么暴露、布尔值口径）、F4（批次键、台账存哪）、F6（大小写归并）、F7（附件读不出来）这五处标了取舍点，两种做法都算完成，但你必须选一种，把选择和理由写进下面这一节，并让实现和文档一致。评审只看这里和你最后的总结。

### 本次做题人填写

（把你的取舍和理由写在这里。）

## 已知问题（另有排期，别顺手修）

下面这些确实是问题，但已经排到下个迭代，本次**不验收**，保持现状即可，不要顺手改：

- 附件的文件名：`Content-Disposition` 是把整串 `attachment; filename= 小明_海底世界.sb3` 交给 `add_header` 的，中文文件名会被整体 RFC2047 编码，家长下载下来的附件没有名字或者是一串看不懂的字符；`filename=` 后面还多了一个空格。**照现状留着**，本次只要求附件字节正确、只读一次。
- HTML 正文不做转义，孩子名字或作品名里带尖括号会原样进邮件。
- 清洗之后名单为空时仍然返回 `True`（一封都没发也算成功）。**照现状留着**，不要改成 `False`。
- 465 端口（SMTP_SSL）现在会走 `starttls()` 直接失败。本次只处理 587 这类 STARTTLS 端口。
