import os
import telebot
import sqlite3
import time
import random
import re

dir = "/path/to/dir"
bot_token = "<your_bot_token>"
court_group_id = "<group_id>"

bot = telebot.TeleBot(bot_token, parse_mode=None)
if not os.path.exists(dir):
    os.makedirs(dir)

# build database
db_path = os.path.join(dir, "exchange.db")
if not os.path.exists(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE files (\
            id INTEGER PRIMARY KEY, \
            file_id TEXT, \
            text TEXT, \
            msg_id INTEGER, \
            fullname TEXT, \
            username TEXT, \
            user_id INTEGER, \
            dislike INTEGER, \
            like INTEGER, \
            super INTEGER, \
            view INTEGER, \
            timestamp INTEGER \
        )')
        cursor.execute('CREATE TABLE comments (\
            id INTEGER PRIMARY KEY, \
            user_id INTEGER, \
            comment TEXT, \
            msg_id INTEGER, \
            reply_id INTEGER, \
            timestamp INTEGER \
        )')
        cursor.execute('CREATE TABLE users (\
            id INTEGER PRIMARY KEY, \
            user_id INTEGER, \
            fullname TEXT, \
            nickname TEXT, \
            username TEXT, \
            sex TEXT, \
            prefer TEXT, \
            soulmate_id INTEGER, \
            is_judge INTEGER, \
            is_admin INTEGER, \
            is_banned INTEGER, \
            upload INTEGER, \
            comment INTEGER, \
            soulmate INTEGER, \
            rate INTEGER, \
            timestamp INTEGER \
        )')
        conn.commit()

# button_click database
btndb_path = f"{dir}/button_clicks.db"
with sqlite3.connect(btndb_path) as conn:
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS button_clicks ( \
        id INTEGER PRIMARY KEY, \
        user_id INTEGER, \
        msg_id INTEGER, \
        clicked INTEGER, \
        timestamp INTEGER \
    )')
    conn.commit()

def mark_click(user_id, msg_id):
    timestamp = time.time()
    with sqlite3.connect(btndb_path) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO button_clicks \
            (user_id, clicked, msg_id, timestamp) \
            VALUES (?, 1, ?, ?)',(user_id, msg_id, timestamp))
        conn.commit()

def get_clickstatus(user_id, msg_id):
    with sqlite3.connect(btndb_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT clicked FROM button_clicks \
            WHERE user_id=? AND msg_id=?',(user_id, msg_id))
        record = cursor.fetchone()
        clicked = record[0] if record else 0
    clicked = True if clicked > 0 else False
    return clicked

def auto_unban(user_id):
    is_banned, _ = getbanstatus(user_id)
    if is_banned:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT max(timestamp) FROM files WHERE user_id=?',(user_id,))
            last_time = cursor.fetchone()[0]
            now = time.time()
            if last_time < now - 24 * 60 * 60:
                cursor.execute('UPDATE users SET is_banned=is_banned-1 WHERE user_id=?',(user_id,))
                is_banned, _ = getbanstatus(user_id)
                if not is_banned:
                    anon = getanon(user_id)
                    msg_text = f"Dear *{anon}*, Now you're unbanned. Sorry for banning you before. \
Please don't ever send low quality images again. Have fun."
                    try:
                        bot.send_message(user_id, msg_text, parse_mode="Markdown")
                        sys_msg = "Has been unbanned by system."
                        monitor(user_id, sys_msg)
                    except:
                        sys_msg = f"Has been unbanned by system. But {anon} blocked the bot."
                        monitor(user_id, sys_msg)

def check_lazy_judges():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE is_judge=1 OR is_banned > 2')
        records = cursor.fetchall()
        for record in records:
            user_id = record[0]
            kick_lazyjudge(user_id)
            auto_unban(user_id)

def kick_lazyjudge(user_id):
    now = time.time()
    lazy = False
    last_time = None
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_judge FROM users WHERE user_id=?',(user_id,))
        record = cursor.fetchone()[0]
        is_judge = True if record else False
    if is_judge:
        with sqlite3.connect(btndb_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT max(timestamp) FROM button_clicks \
                WHERE user_id=? LIMIT 1',(user_id,))
            record = cursor.fetchone()[0]
            
            if record:
                last_time = record
                if last_time < now - 24 * 60 * 60:
                    lazy = True
        member = bot.get_chat_member(court_group_id, user_id)
        if not member.status in ["member"]:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET is_judge=NULL WHERE user_id=?',(user_id,))
                conn.commit()
    else:
        member = bot.get_chat_member(court_group_id, user_id)
        if member.status in ["member"]:
            bot.ban_chat_member(court_group_id, user_id, 60)
            msg_text = f"Hi. Dear. You're not our judge anymore. Anyway, I had to remove \
you from the chat. Sorry."
            try:
                bot.send_message(user_id, msg_text)
            except:
                sys_msg = "Sending message failed. Bot been blocked by the user."
                monitor(user_id, sys_msg)
    if lazy:
        try:
            member = bot.get_chat_member(court_group_id, user_id)
            if member.status in ["member"]:
                bot.ban_chat_member(court_group_id, user_id, 60)

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET is_judge=NULL WHERE user_id=?',(user_id,))
                conn.commit()
            anon = getanon(user_id)
            msg_text = f"Dear *{anon}*. Because of your lazy judging. We decide \
remove you from the court. Anyway thanks for your service. We'll invite you another \
time if you're still active in our community."
            try:
                bot.send_message(user_id, msg_text, parse_mode="Markdown")
            except:
                sys_msg = "Sending message failed. Bot been blocked by the user."
                monitor(user_id, sys_msg)
            sys_msg = "Has been kicked out the court group because of lazy"
            monitor(user_id, sys_msg)
        except:
            pass

def promote_judge(user_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_judge=1 WHERE user_id=?',(user_id,))
        conn.commit()
        anon = getanon(user_id)
        msg_text = f"Dear *{anon}* You have been promoted as Judge. Congratulations!"
        try:
            bot.send_message(user_id, msg_text)
        except:
            sys_msg = "Sending message failed. Bot been blocked by the user."
            monitor(user_id, sys_msg)
        sys_msg = "Has been promoted as Judge."
        monitor(user_id, sys_msg)

def monitor(user_id, sys_msg):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT fullname, username FROM users WHERE user_id=?',(user_id,))
        fullname, username = cursor.fetchone()
    fullname = f"{fullname}(@{username}, {user_id})" if username else f"{fullname}({user_id})"
    print(f"\033[31m{fullname} \033[32m{sys_msg}\033[0m")

# get photo score by vote used in swapback
def getscore(dislike=0, like=0, super=0):
    score = round(super * 2 + like - dislike * 2)
    return score

def getadmin(user_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE user_id=?',(user_id,))
        status = cursor.fetchone()
        status = status[0] or 0
        is_admin = True if status == 1 else False
        return is_admin

def getbanstatus(chat_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT is_banned FROM users WHERE user_id=?',(chat_id,))
        status = cursor.fetchone()
        status = status[0] or 0
        is_banned = True if status > 2 else False
        bantime = (status - 3) * 24
        return is_banned, bantime

def getanon(user_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT nickname, is_admin, is_judge, sex \
            FROM users WHERE user_id=? LIMIT 1',(user_id,))
        nickname, is_admin, is_judge, sex = cursor.fetchone()
        if is_judge:
            anon = f"🐰Judge{nickname}" if sex == "female" else f"🦊Judge{nickname}"
        elif is_admin:
            anon = f"🐙Admin{nickname}" if sex == "female" else f"🐡Admin{nickname}"
        else:
            anon = f"👧Anon{nickname}" if sex == "female" else f"👦Anon{nickname}"
    return anon

def update_comment_count(user_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT comment FROM users WHERE user_id=?',(user_id,))
        record = cursor.fetchone()[0] or 0
        comment_count = record + 1 or 1
        cursor.execute('UPDATE users SET comment=? WHERE user_id=?',(comment_count, user_id))
        conn.commit()

# invite judge
def invite_judge(user_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT comment, rate, upload, is_judge FROM users WHERE user_id=?',(user_id,))
        comment, rate, upload, is_judge = cursor.fetchone()
        comment = comment or 0
        rate = rate or 0
        upload = upload or 0
        is_judge = is_judge or False
        if not is_judge:
            activity = comment + rate + upload
            if activity in [20, 100, 500, 1000]:
                btn = telebot.types.InlineKeyboardButton
                markup = telebot.types.InlineKeyboardMarkup()
                judge_refuse = btn(f"No. I don't want to.", callback_data=f"judge_refuse")
                judge_accept = btn(f"Yes. Sounds great.", callback_data=f"judge_accept")
                markup.add(judge_refuse)
                markup.add(judge_accept)
                msg_text = f"Hi. We have seen you're pretty active here. As a lively \
member of this community, you have the chance to be a judge and make a difference for \
its improvement. In this role, you'll have the exciting opportunity to look at all the \
incoming pictures and decide if they're ready for everyone to see!"
                bot.send_message(user_id, msg_text, reply_markup=markup)

# judge invite handle
@bot.callback_query_handler(func=lambda call: call.data.startswith("judge_"))
def handle_judge_invite(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    command = call.data.split("_")[1]
    if command == "refuse":
        msg_text = "Can't believe you refused it... How dare you?"
        bot.edit_message_text(msg_text, chat_id, msg_id)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT comment FROM users WHERE user_id=?',(chat_id,))
            comment = cursor.fetchone()[0] or 0
            comment = comment + 1
            cursor.execute('UPDATE users SET comment=? WHERE user_id=?',(comment, chat_id))
            conn.commit()

        sys_msg = f"Refused judge offer"
        monitor(chat_id, sys_msg)
    if command == "accept":
        expire = time.time() + 5 * 60
        invite_link = bot.create_chat_invite_link(court_group_id, \
            member_limit=1, expire_date=expire).invite_link
        msg_text = f"Great. I know you'll accept this cool offer. Who will refuse right? \
There's a court group exists. There, you'll be able to review the pictures that members \
submit and determine if they are original or potentially stolen. Our goal is to maintain \
a platform for people to share their real photos. Here's the exclusive invite \
link: \n\n{invite_link}\n\nPlease keep it confidential and do not share it with anyone else."
        bot.edit_message_text(msg_text, chat_id, msg_id)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT comment FROM users WHERE user_id=?',(chat_id,))
            comment = cursor.fetchone()[0] or 0
            comment = comment + 1
            cursor.execute('UPDATE users SET is_judge=?, comment=? WHERE user_id=?',(1, comment, chat_id))
            conn.commit()
        sys_msg = f"Accepted judge offer"
        monitor(chat_id, sys_msg)

# court buttons
def get_court_buttons(msg_id, unapprove_count=0, approve_count=0, mid=None, cid=None, text=None):
    bad = f" {unapprove_count}" if unapprove_count != 0 else ""
    good = f" {approve_count}" if approve_count != 0 else ""

    if text:
        text = f"{text}\n"
        text = re.sub(r"Published:(.*)", r"`Published:\1`", text)
        text = re.sub(r"By:(.*)", r"`By:\1`", text)
        text = re.sub(r"Rate this.*\n", r"", text)
        text = re.sub(r"Approve or.*\n", r"", text)
    else:
        text = ""

    btn = telebot.types.InlineKeyboardButton
    markup = telebot.types.InlineKeyboardMarkup()
    tail = f"{unapprove_count}_{approve_count}_{msg_id}"
    btn_unapprove = btn(f"Unapprove{bad}", callback_data=f"court_unapprove_{tail}")
    btn_approve = btn(f"Approve{good}", callback_data=f"court_approve_{tail}")

    if approve_count > 99:
        markup = None
        msg_text = f"{text}This one is approved."
    elif unapprove_count > 99:
        markup = None
        msg_text = f"{text}This one is unapproved." 
    else:
        markup.add(btn_unapprove, btn_approve)

    if not mid:
        return markup
    else:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, dislike FROM files WHERE msg_id=?',(msg_id,))
            send_id, dislike = cursor.fetchone()
        msg_text = f"{text}Rate this picture."
        if approve_count // 1.5 > unapprove_count:
            msg_text = f"{text}This one is approved."
            markup = None
            send_text = "Congratulations! Your photo has been approved as good. Keep it up."
            is_banned, _ = getbanstatus(send_id)
            if not is_banned:
                try:
                    bot.send_message(send_id, send_text, reply_to_message_id=msg_id, allow_sending_without_reply=True)
                except:
                    sys_msg = "Sending message failed. Bot been blocked by the user."
                    monitor(send_id, sys_msg)
                sys_msg = "Has been Noted because of his photo been approved."
                monitor(send_id, sys_msg)
        elif unapprove_count // 1.5 > approve_count:
            msg_text = f"{text}This one is unapproved."
            markup = None
            dislike = dislike or 0
            dislike = dislike + 20
            cursor.execute('UPDATE files SET dislike=? WHERE msg_id=?',(dislike, msg_id))
            cursor.execute('SELECT is_banned FROM users WHERE user_id=?',(send_id,))
            record = cursor.fetchone()
            is_banned = record[0] + 1 if record[0] else 1
            cursor.execute('UPDATE users SET is_banned=? WHERE user_id=?',(is_banned, send_id))
            conn.commit()
            send_text = "Unfortunately. Your content has unapproved by most of our Judges. \
Your photo is considered low quality content and we take the quality of our community very seriously. \
Please do not spam this bot or you may face consequences such as being banned. Think about it, if someone \
seen these unintresting images how is the feel? so, don't be so damn selfish."
            is_banned, _ = getbanstatus(send_id)
            if not is_banned:
                try:
                    bot.send_message(send_id, send_text, reply_to_message_id=msg_id, allow_sending_without_reply=True)
                except:
                    sys_msg = "Sending message failed. Bot been blocked by the user."
                    monitor(send_id, sys_msg)
                sys_msg = "Has been warned because of his photo been unapproved."
                monitor(send_id, sys_msg)
        bot.edit_message_caption(msg_text, cid, mid, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("court_"))
def handle_court(call):
    command = call.data.split("_")[1]
    unapprove_count = int(call.data.split("_")[2])
    approve_count = int(call.data.split("_")[3])
    msg_id = int(call.data.split("_")[4])
    mid = call.message.message_id
    cid = call.message.chat.id
    user_id = call.from_user.id
    text = call.message.caption

    if command == "unapprove":
        unapprove_count = unapprove_count + 1
        sys_msg = f"Unpproved the photo(msg_id={msg_id})."
    elif command == "approve":
        approve_count = approve_count + 1
        sys_msg = f"Approved the photo(msg_id={msg_id})."
    clicked = get_clickstatus(user_id, msg_id)
    if not clicked:
        get_court_buttons(msg_id, unapprove_count, approve_count, mid, cid, text)
        mark_click(user_id, msg_id)
        
        monitor(user_id, sys_msg)
    else:
        bot.answer_callback_query(call.id, "You have already voted.")

# send to court
def send_court(msg_id):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT file_id, text, user_id, timestamp \
            FROM files WHERE msg_id=?',(msg_id,))
        file_id, text, user_id, timestamp = cursor.fetchone()
        date = time.strftime("%Y/%m/%d", time.gmtime(timestamp))
        anon = getanon(user_id)
        text = f"{text}\n" if text else ""
        caption = f"{text}`Published: {date}`\n`By: {anon}`\n`Approve or no?`"
        markup = get_court_buttons(msg_id)
        sendmsg_id = bot.send_photo(court_group_id, file_id, caption, \
            parse_mode="Markdown", reply_markup=markup, protect_content=True).message_id
        # when send to court update dislike as 0
        cursor.execute('UPDATE files SET dislike=0 WHERE msg_id=?',(msg_id,))
        conn.commit()
    try:
        bot.delete_message(court_group_id, sendmsg_id - 5)
    except:
        print("Delete message failed.")

def store_photo(message):
    file_id = message.photo[-1].file_id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    fullname = f"{first_name} {last_name}" if last_name else first_name
    username = message.from_user.username
    user_id = message.from_user.id
    timestamp = message.date
    msg_id = message.id
    text = message.caption

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT count(msg_id), text, max(timestamp) \
            FROM files WHERE msg_id=?',(msg_id,))
        count, db_text, _ = cursor.fetchone()
        f_exists = True if count > 0 else False

        if f_exists and db_text != text:
            cursor.execute('UPDATE files SET text=? WHERE msg_id=?',(text, msg_id))
            conn.commit()
        else:
            # before user confirm dislike is 20 on default it'll update to 0 in send_court
            cursor.execute('INSERT INTO files \
                (file_id, fullname, username, user_id, text, msg_id, timestamp, dislike) \
                VALUES (?, ?, ?, ?, ?, ?, ?, 20)', \
                (file_id, fullname, username, user_id, text, msg_id, timestamp))
            conn.commit()

        sys_msg = f"Has send a photo(msg_id={msg_id}) with caption: {text}"
        monitor(user_id, sys_msg)
    return msg_id

def rate_buttons(dislike=None, like=None, super=None, msg_id=None):
    dislike = dislike or 0
    like = like or 0
    super = super or 0

    button = telebot.types.InlineKeyboardButton
    tail = f"{dislike}_{like}_{super}_{msg_id}"
    markup = telebot.types.InlineKeyboardMarkup()
    btn_dislike = button(f"😒 {dislike}", callback_data=f"rate_dislike_{tail}")
    btn_like = button(f"😊 {like}", callback_data=f"rate_like_{tail}")
    btn_super = button(f"😍 {super}", callback_data=f"rate_super_{tail}")
    markup.add(btn_dislike, btn_like, btn_super)

    return markup

def swapback(chat_id):
    now_time = time.time()
    markup = None

    editlater = bot.send_message(chat_id, "Swapping photo...").message_id
    check_lazy_judges()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT prefer FROM users WHERE user_id=?',(chat_id,))
        prefer = cursor.fetchone()[0]
        prefer = "all" if not prefer else prefer

        num = 0
        while True:
            start_time = now_time - 24 * 60 * 60
            cursor.execute('SELECT file_id, text, dislike, like, \
                super, timestamp, msg_id, user_id \
                FROM files \
                WHERE timestamp BETWEEN ? AND ? AND NOT user_id=? \
                ORDER BY RANDOM() limit 1',(start_time, now_time, chat_id))
            records = cursor.fetchone()
            try:
                file_id, text, dislike, like, super, timestamp, msg_id, user_id = records
                score = getscore(dislike or 0, like or 0, super or 0)
                cursor.execute('SELECT sex FROM users WHERE user_id=?', (user_id,))
                sex = cursor.fetchone()[0]
                sex = "boy" if sex == "male" else sex
                sex = "girl" if sex == "female" else sex
                sex = prefer if prefer == "all" else sex
                score = -20 if sex != prefer else score
                # detect if the file is visited before
                cursor.execute('SELECT count(reply_id) FROM comments WHERE reply_id=? AND user_id=?',(msg_id, chat_id))
                visit_num = cursor.fetchone()[0]
                score = -21 if visit_num > 0 else score

                # print(f"\nscore={score}\nperfer={prefer}\nsex={sex}\ndislike={dislike}")
                # print(f"like={like}\nsuper={super}\nvisit_num={visit_num}\nnum={num}\n")

                if score < -10:
                    num = num + 1
                    if num > 49:
                        break
                    continue
            except:
                bot.edit_message_text("No pictures in the database yet.", chat_id, editlater)
                file_id = None
                break
            if file_id:
                break
            else:
                now_time = now_time - 24 * 60 * 60 + 1

    if file_id:
        text = text if text else ""
        comment_section = ""

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT comment, user_id, timestamp \
                FROM comments WHERE reply_id=?', (msg_id,))
            records = cursor.fetchall()
            is_comment = True if records else None
            if is_comment:
                comments = []
                for record in records:
                    comment, reply_uid, reply_time = record
                    anon = getanon(reply_uid)
                    comments.append(f"`{anon}`: {comment}") if comment else None
                    comment_section = "\n".join(comments)

        date = time.strftime("%Y/%m/%d", time.gmtime(timestamp))
        anon = getanon(user_id)
        by = f"`Published: {date}\nBy: {anon}`"
        caption = f"{text}\n{by}\n\n{comment_section}"

        bot.delete_message(chat_id, editlater)
        markup = rate_buttons(dislike, like, super, msg_id)
        bot.send_photo(chat_id, file_id, caption, reply_markup=markup, \
            parse_mode="Markdown", protect_content=True)
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # update user's upload count
            cursor.execute('SELECT upload FROM users WHERE user_id=?',(chat_id,))
            upload = cursor.fetchone()[0]
            upload = 1 if not upload else upload + 1
            cursor.execute('UPDATE users SET upload=? WHERE user_id=?',(upload, chat_id))
            # update files view count
            cursor.execute('SELECT view FROM files WHERE file_id=?',(file_id,))
            view = cursor.fetchone()[0]
            view = 1 if not view else view + 1
            cursor.execute('UPDATE files SET view=? WHERE file_id=?',(view, file_id))
            # insert a view log into comment section
            timestamp = time.time()
            cursor.execute('INSERT INTO comments (reply_id, timestamp, user_id) \
                VALUES (?, ?, ?)',(msg_id, timestamp, chat_id))
            conn.commit()
        sys_msg = f"Swapped a photo(msg_id={msg_id})"
        monitor(chat_id, sys_msg)
    else:
        sys_msg = f"Didn't have any photos in database."
        monitor(chat_id, sys_msg)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def confirm(call):
    command = call.data.split("_")[1]
    dislike = int(call.data.split("_")[2])
    like = int(call.data.split("_")[3])
    super = int(call.data.split("_")[4])
    msg_id = int(call.data.split("_")[5])
    chat_id = call.message.chat.id
    text = call.message.caption

    if command == "dislike":
        dislike = dislike + 1
    elif command == "like":
        like = like + 1
    elif command == "super":
        super = super + 1

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE files SET dislike=?, like=?, super=? \
            WHERE msg_id=?',(dislike, like, super, msg_id))
        cursor.execute('SELECT rate FROM users where user_id=?',(chat_id,))
        rate = cursor.fetchone()[0]
        rate = 1 if not rate else rate + 1
        cursor.execute('UPDATE users SET rate=? WHERE user_id=?',(rate, chat_id))
        conn.commit()
    param = f"[-](tg://msg?id={msg_id})"
    text = re.sub(r"(\w+\d+):", r"`\1`:", text) if text else None
    text = re.sub(r"Published:(.*)", r"`Published:\1`", text)
    text = re.sub(r"By:(.*)", r"`By:\1`", text)
    msg_text = f"{text}\n{param} `You're voted. reply to comment.`" if text else f"\n{param} `You're voted. reply to comment.`"
    bot.edit_message_caption(msg_text, chat_id, call.message.message_id, parse_mode="Markdown")

    sys_msg = f"Rate a photo as {command}"
    monitor(chat_id, sys_msg)

def yesno(chat_id, msg_id, send_court_id, command=None):
    if not command:
        msg_id = bot.send_message(chat_id, "loading...", \
            reply_to_message_id=msg_id).message_id

    markup_tail = f"{chat_id}_{msg_id}_{send_court_id}"
    markup = telebot.types.InlineKeyboardMarkup()
    btn_yes = telebot.types.InlineKeyboardButton("Yes, please.", callback_data=f"confirm_yes_{markup_tail}")
    btn_no = telebot.types.InlineKeyboardButton("No, I'll pick another.", callback_data=f"confirm_no_{markup_tail}")
    markup.add(btn_yes)
    markup.add(btn_no)

    if command == "yes":
        msg_text = "The photo published."
        bot.edit_message_text(msg_text, chat_id, msg_id)
        swapback(chat_id)
        send_court(send_court_id)
    elif command == "no":
        msg_text = "Canceled."
        bot.edit_message_text(msg_text, chat_id, msg_id)
    else:
        msg_text = "You can edit description before posting... Are you sure ready to post?"
        bot.edit_message_text(msg_text, chat_id, msg_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def confirm(call, last_opration_time={}):
    command = call.data.split("_")[1]
    chat_id = int(call.data.split("_")[2])
    msg_id = int(call.data.split("_")[3])
    send_court_id = int(call.data.split("_")[4])
    #Anti flood
    user_id = call.from_user.id
    now = time.time()
    last_time = last_opration_time.get(user_id, 0)
    interval = now - last_time
    if interval < 1:
        bot.answer_callback_query(call.id, "You're submitting too quick. Please slow down.")
    else:
        yesno(chat_id, msg_id, send_court_id, command)
        sys_msg = f"Clicked {command} while confirm uploading photo."
        monitor(chat_id, sys_msg)
    last_opration_time[user_id] = now

@bot.message_handler(commands=["help"])
def handle_invite(message):
    is_private = True if not message.chat.title else False
    if is_private:
        msg_text = f"*How to use*\n\nIt's simple and straightforward. You upload a photo and \
in return receive a photo from someone else. Regarding privacy, be aware that your photo will be \
shared with another person. The decision on which photo to share is entirely up to you.\n\n\
*How to comment*\n\nAfter you rated photo you received, Just reply to the photo and that's it. \
The poster will receive your comment and he/she also could reply you. Have fun."
        
        bot.send_message(message.chat.id, msg_text, parse_mode="Markdown")
        sys_msg = "Clicked the /help"
        monitor(message.chat.id, sys_msg)

@bot.message_handler(commands=["testgeneratename"])
def test_run(message):
    nickname = random.randint(1,99)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT nickname FROM users')
        records = cursor.fetchall()

        for record in records:
            if nickname == int(record[0]):
                nickname = random.randint(100,999)
                continue

@bot.message_handler(commands=["pullaphoto"])
def pull_message(message):
    if not message.chat.title:
        swapback(message.chat.id)

@bot.message_handler(commands=["ban"])
def ban_member(message):
    user_id = message.from_user.id
    is_admin = getadmin(user_id)
    ban_num = True
    try:
        ban_num = int(message.text.split()[1])
        if len(str(ban_num)) > 4:
            ban_num = None
            msg_text = "Name has be up to 3 digits"
            bot.send_message(user_id, msg_text)
    except:
        ban_num = None
        msg_text = "Incorrect name. It has to be number."
        bot.send_message(user_id, msg_text)

    if is_admin and ban_num:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT count(nickname) FROM users WHERE nickname=?',(ban_num,))
            record = cursor.fetchone()[0]
            if record > 0:
                cursor.execute('UPDATE users SET is_banned=is_banned+5 WHERE nickname=?',(ban_num,))
                conn.commit()
                # unapprove all his/her photos
                cursor.execute('SELECT user_id FROM users WHERE nickname=?',(ban_num,))
                banned_user_id = cursor.fetchone()[0]
                cursor.execute('UPDATE files SET dislike=20 WHERE user_id=? \
                    AND `like` is NULL AND `super` is NULL',(banned_user_id,))
                conn.commit()
                msg_text = f"Success. Anon{ban_num} been banned."
                bot.send_message(user_id, msg_text)
            else:
                msg_text = f"Failed. No one with this name."
                bot.send_message(user_id, msg_text)

@bot.message_handler(commands=["changemyanonname"])
def change_name(message):
    cando = True
    user_id = message.from_user.id
    msg_text = "Something wrong."
    try:
        wanted_name = int(message.text.split()[1])
        if len(str(wanted_name)) > 4:
            wanted_name = None
            msg_text = "Name has be up to 3 digits"
    except:
        wanted_name = None
        msg_text = "Incorrect name. It has to be number."
    if wanted_name:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT nickname, timestamp FROM users')
            records = cursor.fetchall()
            for record in records:
                nickname, _ = record
                if int(nickname) == int(wanted_name):
                    cando = False
                    msg_text = "The name is already taken."
                    break
            if cando:
                cursor.execute('UPDATE users SET nickname=? WHERE user_id=?',(wanted_name, user_id,))
                conn.commit()
                anon = getanon(user_id)
                msg_text = f"Your new name is now: {anon}"
    bot.send_message(user_id, msg_text, parse_mode="Markdown")

@bot.message_handler(commands=["info"])
def pull_message(message):
    chat_id = message.chat.id
    if not message.chat.title:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT count(file_id) FROM files')
            total_photos = cursor.fetchone()[0]
            cursor.execute('SELECT count(user_id) FROM users')
            total_users = cursor.fetchone()[0]
            cursor.execute('SELECT count(user_id) FROM users WHERE is_banned > 2')
            banned_users = cursor.fetchone()[0]
            cursor.execute('SELECT upload FROM users WHERE user_id=?',(chat_id,))
            total_upload = cursor.fetchone()[0]
            total_upload = total_upload or 0
            cursor.execute('SELECT count(comment) FROM comments WHERE user_id=? AND comment IS NOT NULL',(chat_id,))
            total_comments = cursor.fetchone()[0]
            cursor.execute('SELECT SUM(upload+comment+rate) AS score FROM users WHERE user_id=?',(chat_id,))
            score = cursor.fetchone()
            score = score[0] if score else 0
        anon = getanon(chat_id)
        msg_text = f"Dear *{anon}*:\n\
*Community info:*\n\n\
Total photos: {total_photos}\n\
Total users: {total_users}\n\
Banned users: {banned_users}\n\n\
*Your info:*\n\
Total upload:{total_upload}\n\
Total comments:{total_comments}\n\
Your score: {score}"

        bot.send_message(chat_id, msg_text, \
            parse_mode="MARKDOWN", disable_web_page_preview=True)
        sys_msg = "Watched /info"
        monitor(chat_id, sys_msg)

@bot.message_handler(commands=["start"])
def handle_start(message):
    is_private = True if not message.chat.title else False
    if is_private:
        chat_id = message.from_user.id
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        fullname = f"{first_name} {last_name}" if last_name else first_name
        username = message.from_user.username
        user_id = message.from_user.id
        timestamp = message.date

        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT count(user_id) FROM users WHERE user_id=?',(chat_id,))
            record = cursor.fetchone()[0]
            user_exists = True if record > 0 else False

        if not user_exists:
            nickname = random.randint(1,99)
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT nickname FROM users')
                records = cursor.fetchall()

                for record in records:
                    if nickname == int(record[0]):
                        nickname = random.randint(100,999)
                        continue
                
                cursor.execute('INSERT INTO users \
                    (fullname, user_id, username, nickname, timestamp) \
                    VALUES (?, ?, ?, ?, ?)', \
                    (fullname, user_id, username, nickname, timestamp))
                conn.commit()
        else:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT nickname FROM users WHERE user_id=?',(chat_id,))
                nickname = cursor.fetchone()
                nickname = nickname[0] if nickname else None

        anon = getanon(chat_id)
        msg_text = f"Hi *{anon}*, welcome to our community where we value privacy. \
You can share your photo here and connect with other members. If you are active and \
participate in the community, you may even become a \"Judge.\" However, it's important \
to remember that any low-quality photos or harassing behavior will not be tolerated and \
may result in a ban. We wish you a fun and engaging experience here."

        msg_text = f"{msg_text}"
        bot.send_message(chat_id, msg_text, \
            parse_mode="MARKDOWN", disable_web_page_preview=True)
        
        msg_text = f"Now. Are you a man?"
        
        btn = telebot.types.InlineKeyboardButton
        markup = telebot.types.InlineKeyboardMarkup()
        btn_male = btn("Yes. I'm a male", callback_data=f"start_male")
        btn_female = btn("No. I'm a female", callback_data=f"start_female")
        markup.add(btn_male)
        markup.add(btn_female)
        bot.send_message(chat_id, msg_text, reply_markup=markup)

        sys_msg = f"Just clicked the /start setting, His nickname is Anon{nickname}"
        monitor(chat_id, sys_msg)

@bot.callback_query_handler(func=lambda call: call.data.startswith("start_"))
def start_command(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    command = call.data.split("_")[1]
    all_done = False

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        if command in ["male", "female"]:
            cursor.execute('UPDATE users SET sex=? WHERE user_id=?',(command, chat_id))
            conn.commit()
        elif command in ["girl", "boy", "all"]:
            cursor.execute('UPDATE users SET prefer=? WHERE user_id=?',(command, chat_id))
            conn.commit()
            all_done = True

    if not all_done:
        msg_text = "What photos do you prefer?"
        btn = telebot.types.InlineKeyboardButton
        markup = telebot.types.InlineKeyboardMarkup()
        btn_girl = btn("I want to see girls", callback_data=f"start_girl")
        btn_boy = btn("I want to see boys", callback_data=f"start_boy")
        btn_all = btn("TRUE MAN CHOOSE ALL", callback_data=f"start_all")
        markup.add(btn_girl)
        markup.add(btn_boy)
        markup.add(btn_all)
        bot.edit_message_text(msg_text, chat_id, msg_id, reply_markup=markup)
    else:
        bot.edit_message_text("All done.", chat_id, msg_id)

    sys_msg = f"Finished the /start settings"
    monitor(chat_id, sys_msg)

# receive photos
@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    chat_id = message.from_user.id
    msg_id = message.message_id
    is_private = True if not message.chat.title else False

    if is_private:
        is_banned, bantime = getbanstatus(chat_id)
        # store file first
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        download_file = bot.download_file(file_info.file_path)
        os.makedirs(f"{dir}/download/{chat_id}/photos", exist_ok=True)
        path = f"{dir}/download/{chat_id}/{file_info.file_path}"
        with open(path, "wb") as f:
            f.write(download_file)
        new_path = f"{dir}/download/{chat_id}/{message.photo[-1].file_unique_id}.jpg"
        os.rename(path, new_path)

        if not is_banned:
            send_court_id = store_photo(message)
            yesno(message.chat.id, msg_id, send_court_id)
            invite_judge(chat_id)
        else:
            bot.send_message(chat_id, f"Sorry. You're been banned for {bantime} hours.")

            sys_msg = f"Discovered he's been banned."
            monitor(chat_id, sys_msg)

# edit photo caption
@bot.edited_message_handler(content_types=["photo"])
def handle_caption(message):
    is_private = True if not message.chat.title else False
    if is_private:
        store_photo(message)
        sys_msg = f"Edited photo caption: {message.caption}"
        monitor(message.chat.id, sys_msg)

# comment system
@bot.message_handler(func=lambda message: message.chat.type == "private")
def handle_text(message):
    is_reply = True if message.reply_to_message else False
    try:
        is_puretext = True if not message.reply_to_message.photo else False
    except:
        is_puretext = False
    reply_id = None
    msg_id = message.message_id
    user_id = message.chat.id
    timestamp = message.date
    text = message.text

    if is_reply:
        try:
            for entity in message.reply_to_message.caption_entities:
                if entity.type == "text_link":
                    reply_id = entity.url.split("id=")[-1]
        except:
            reply_id = None

        if reply_id:
            edit_id = message.reply_to_message.message_id
            caption = message.reply_to_message.caption.replace("- You're voted. reply to comment.", "").replace("- Replied.", "")
            caption = re.sub(r"(\w+\d+):", r"`\1`:", caption)
            caption = re.sub(r"Published:(.*)", r"`Published:\1`", caption)
            caption = re.sub(r"By:(.*)", r"`By:\1`", caption)

            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('INSERT INTO comments \
                    (msg_id, comment, reply_id, timestamp, user_id) \
                    VALUES (?, ?, ?, ?, ?)', (msg_id, text, reply_id, timestamp, user_id))
                conn.commit()

                cursor.execute('SELECT user_id FROM files WHERE msg_id=?',(reply_id,))
                send_id = cursor.fetchone()
                send_id = send_id[0] if send_id else None

            anon = getanon(user_id)
            try:
                bot.send_message(send_id, f"`{anon}`: {text}", reply_to_message_id=reply_id, \
                    parse_mode="Markdown", disable_web_page_preview=True, allow_sending_without_reply=True)
                sys_msg = f"Has left a comment on photo:{text}"
                monitor(send_id, sys_msg)
            except:
                sys_msg = "Sending message failed. Bot been blocked by the user."
                monitor(send_id, sys_msg)
            update_comment_count(user_id)
            msg_text = f"{caption}`{anon}`: {text}\n\n[-](tg://msg?id={reply_id}) `Replied.`"
            bot.edit_message_caption(msg_text, user_id, edit_id, parse_mode="Markdown")

            sys_msg = f"Replied to photo(msg_id={msg_id}): {text}"
            monitor(user_id, sys_msg)
        elif is_puretext:
            bot_text = message.reply_to_message.text.split(": ", 1)[-1]
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id, msg_id, reply_id, max(timestamp) \
                    FROM comments WHERE comment=? LIMIT 1',(bot_text,))
                db_user_id, db_msg_id, db_reply_id, _ = cursor.fetchone()
                
                cursor.execute('INSERT INTO comments \
                    (msg_id, comment, reply_id, timestamp, user_id) \
                    VALUES (?, ?, ?, ?, ?)',(msg_id, text, db_reply_id, timestamp, user_id))
                conn.commit()

            anon = getanon(user_id)

            try:
                bot.send_message(db_user_id, f"`{anon}`: {text}", reply_to_message_id=db_msg_id, \
                    parse_mode="Markdown", disable_web_page_preview=True, allow_sending_without_reply=True)
                update_comment_count(user_id)
                sys_msg = f"Replied to comment(msg_id={msg_id}): {text}"
                monitor(user_id, sys_msg)
            except:
                pass
        else:
            bot.send_message(user_id, "Please comment after rate.")

            sys_msg = f"Failed to reply(msg_id={msg_id}): {text}"
            monitor(user_id, sys_msg)

bot.infinity_polling(timeout=10, long_polling_timeout=5)
