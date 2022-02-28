import logging, json, requests, asyncio, re, phonenumbers, tempfile, mimetypes, fleep
import aiogram as t # Bot, Dispatcher, executor, types
import discord as d
from aiogram.utils import markdown as tMD

config = {}
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("`config.json` not exsits!")
    exit(1)

logging.basicConfig(level=getattr(logging,config["logging"]["level"].upper()),format=config["logging"]["format"],filename=(config["logging"]["filename"] if config["logging"]["filename"] != "stdout" else None))

formats = config["main"]["format"] # normal, reply, inlineBot, DCslash, forward
lA = logging.getLogger("main")

lT = logging.getLogger("Telegram")
tT = config["telegram"]["token"]
bot_tg = t.Bot(token=tT)
Tdp = t.Dispatcher(bot_tg)
def buildUNAME(user):
    try:
        if user.title:
            return user.title
    except AttributeError:
        pass
    if user.first_name:
        if config["telegram"]["username"] == "fullname":
            return user.first_name + ((" " + user.last_name) if user.last_name != None else "")
        elif config["telegram"]["username"] == "firstname":
            return user.first_name
    return str(user.id)
@Tdp.message_handler(commands=['start'])
async def Tstart(message: t.types.Message):
    author = message.from_user
    channelID = message.chat.id
    source = "telegram/{}".format(channelID)
    lT.info("/start by `{}` from `{}`".format(author,source))
    await message.answer("ERS NG!")
async def Ton_message(message: t.types.Message):
    if message.is_command(): return
    channelID = message.chat.id
    author = message.from_user
    if message.sender_chat:
        author = message.sender_chat
    reference = message.reply_to_message # might be None
    source = "telegram/{}".format(channelID)
    output = ""
    content = message.text or ""
    media = []
    if message.contact:
        num = phonenumbers.parse("+" + message.contact.phone_number,None)
        if phonenumbers.is_valid_number(num):
            output = config["main"]["outputformats"]["contact"].format(phone=phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.INTERNATIONAL))
        else:
            output = config["main"]["outputformats"]["contact"].format(phone="INVALID " + message.contact.phone_number)
    elif message.dice:
        output = config["main"]["outputformats"]["dice"].format(emoji=message.dice.emoji,value=message.dice.value)
    elif message.game:
        output = config["main"]["outputformats"]["game"].format(title=message.game.title,description=message.game.description)
    elif message.poll:
        infos = []
        if message.poll.is_anonymous:
            infos.append("anonymous")
        if message.poll.allows_multiple_answers:
            infos.append("multiple-choice")
        if message.poll.open_period:
            infos.append("auto-closing")
        if len(infos) == 0:
            infos.append("no flags")
        info = ", ".join(infos)
        questions = []
        for x in message.poll.options:
            questions.append(x.text)
        question = "\n".join(questions)
        output = config["main"]["outputformats"]["poll"].format(type=message.poll.type,question=message.poll.question,info=info,options=question)
    elif message.venue:
        output = config["main"]["outputformats"]["venue"].format(title=message.venue.title,address=message.venue.address)
    elif message.location:
        output = config["main"]["outputformats"]["location"].format(position="{},{}".format(message.location.longitude,message.location.latitude),horizontal_accuracy=(message.location.horizontal_accuracy != None and message.location.horizontal_accuracy or 0))
    elif message.new_chat_members:
        users = []
        for x in message.new_chat_members:
            users.append(buildUNAME(x))
        output = config["main"]["outputformats"]["new_chat_members"].format(users=", ".join(users))
    elif message.left_chat_member:
        output = config["main"]["outputformats"]["left_chat_member"].format(user=buildUNAME(message.left_chat_member))
    elif message.pinned_message:
        pin_cont = message.pinned_message.text or ""
        pin_cont = pin_cont[:10] + (pin_cont[10:] and '..')
        output = config["main"]["outputformats"]["pinned"].format(msg=pin_cont)
    elif message.text:
        output = message.md_text


    async def download(downloadable: t.types.mixins.Downloadable):
        f = tempfile.TemporaryFile()
        await downloadable.download(destination_file=f)
        f.seek(0)
        name = "Unknown"
        try:
            name = str(downloadable.file_name)
        except AttributeError:
            pass
        ext = ""
        try:
            ext = mimetypes.guess_extension(downloadable.mime_type)
        except AttributeError:
            ext = fleep.get(f.read()).extension[0]
            f.seek(0)
        media.append([f,name + "." + ext])

    if message.animation:
        await download(message.animation)
    if message.audio:
        await download(message.audio)
    if message.document:
        await download(message.document)
    if message.photo:
        await download(message.photo[len(message.photo) - 1])
    if message.sticker:
        await download(message.sticker)
    if message.video:
        await download(message.video)
    if message.video_note:
        await download(message.video_note)
    if message.video_note:
        await download(message.video_note)
    if message.voice:
        await download(message.voice)

    if message.caption:
        output = config["main"]["outputformats"]["caption"].format(caption=message.caption) + " " + output

    lT.info("received message by `{}` content `{}` from `{}`".format(author.id,output,source))
    lT.info("raw {}".format(message))
    for x in config["main"]["relays"]:
        if source in x:
            for y in x:
                if source == y: continue
                platform, id = y.split("/",1)
                id = int(id)
                uname = buildUNAME(author)
                if reference:
                    source_r = "telegram/{}".format(reference.from_user.id)
                    lT.info("Reply source {}".format(source_r))
                    runame = buildUNAME(reference.from_user)
                    display_r = reference.md_text[:10] + (reference.md_text[10:] and '..')
                    if source_r in config["main"]["detectname"]:
                        tmp_name_r = re.match(config["main"]["detectname"][source_r],reference.md_text)
                        if tmp_name_r != None:
                            runame = tmp_name_r[1]
                            display_r = tmp_name_r[2][:10] + (tmp_name_r[2][10:] and '..')
                    final = formats["reply"].format(shortName=("T" if source not in config["main"]["relaynames"] else config["main"]["relaynames"][source][0]),username=uname,replyUser=runame,replyMSG=display_r,message=output)
                elif message.forward_from or message.forward_sender_name:
                    fwd_uname = buildUNAME(message.forward_from) if message.forward_from else message.forward_sender_name
                    final = formats["forward"].format(shortName=("T" if source not in config["main"]["relaynames"] else config["main"]["relaynames"][source][0]),username=uname,forwardUser=fwd_uname,message=output)
                elif message.via_bot:
                    iBOT_name = buildUNAME(message.via_bot)
                    final = formats["inlineBot"].format(shortName=("T" if source not in config["main"]["relaynames"] else config["main"]["relaynames"][source][0]),username=uname,inlineBot=iBOT_name,message=output)
                else:
                    final = formats["normal"].format(shortName=("T" if source not in config["main"]["relaynames"] else config["main"]["relaynames"][source][0]),username=uname,message=output)
                lT.info("Message {}".format(final))
                lT.info("Documents {}".format(media))
                if platform == "telegram":
                    msg = await bot_tg.send_message(chat_id=id,text=tMD.escape_md(final),parse_mode="MarkdownV2")
                    for a in media:
                        with tempfile.TemporaryFile() as b:
                            b.write(a[0].read())
                            a[0].seek(0)
                            b.seek(0)
                            await msg.answer_document(document=b,disable_notification=True,reply=True)
                elif platform == "discord":
                    files = []
                    for a in media:
                        b = tempfile.TemporaryFile()
                        b.write(a[0].read())
                        a[0].seek(0)
                        b.seek(0)
                        files.append(d.File(b,filename=str(a[1]),spoiler=False))
                    await D.get_channel(id).send(content=final,files=files)
                    for c in files:
                        c.close()
    for c in media:
        c[0].close()
Tdp.register_message_handler(Ton_message,content_types=t.types.ContentType.all())

lD = logging.getLogger("Discord")
token_dpy = config["discord"]["token"]
class cD(d.Client):
    async def on_ready(self):
        lD.info("Discord: Username: `{0.name}` ID: `{0.id}`".format(self.user))
    async def on_message(self, message):
        bot_tg.set_current(bot_tg)
        channelID = message.channel.id
        content = message.content
        author = message.author
        reference = message.reference and message.reference.resolved # might be None
        source = "discord/{}".format(message.channel.id)
        if author == self.user: return
        lD.info("received message by `{}` content `{}` from `{}`".format(author.id,content,source))
        media = []
        for x in message.attachments:
            f = tempfile.TemporaryFile()
            await x.save(f)
            media.append([f,x.filename])
        for x in config["main"]["relays"]:
            if source in x:
                for y in x:
                    if source == y: continue
                    platform, id = y.split("/",1)
                    id = int(id)
                    if reference:
                        source_r = "discord/{}".format(reference.author.id)
                        lD.info("Reply source {}".format(source_r))
                        name_r = (reference.author.display_name if config["discord"]["username"] == "nickname" else reference.author.name)
                        display_r = reference.content[:10] + (reference.content[10:] and '..')
                        if source_r in config["main"]["detectname"]:
                            tmp_name_r = re.match(config["main"]["detectname"][source_r],reference.content)
                            if tmp_name_r != None:
                                name_r = tmp_name_r[1]
                                display_r = tmp_name_r[2][:10] + (tmp_name_r[2][10:] and '..')
                        message = formats["reply"].format(shortName=("D" if source not in config["main"]["relaynames"] else config["main"]["relaynames"][source][0]),username=(author.display_name if config["discord"]["username"] == "nickname" else author.name),replyUser=name_r,replyMSG=display_r,message=content)
                    else:
                        message = formats["normal"].format(shortName=("D" if source not in config["main"]["relaynames"] else config["main"]["relaynames"][source][0]),username=(author.display_name if config["discord"]["username"] == "nickname" else author.name),message=content)
                    if platform == "telegram":
                        msg = await bot_tg.send_message(chat_id=id,text=tMD.escape_md(message),parse_mode="MarkdownV2")
                        for a in media:
                            with tempfile.TemporaryFile() as b:
                                b.write(a[0].read())
                                a[0].seek(0)
                                b.seek(0)
                                await msg.answer_document(document=b,disable_notification=True,reply=True)
                    elif platform == "discord":
                        files = []
                        for a in media:
                            b = tempfile.TemporaryFile()
                            b.write(a[0].read())
                            a[0].seek(0)
                            b.seek(0)
                            files.append(d.File(b,filename=str(a[1]),spoiler=False))
                        await self.get_channel(id).send(content=message,files=files)
                        for c in files:
                            c.close()
        for c in media:
            c[0].close()
D = cD() # a discord client object

# Run the telegram and discord bot
# Goal: both bot run on the same time

lA.info("Done, starting bots...")

# GNOME's code
"""
async def main():
    #exec_tg = t.executor.Executor(Tdp, skip_updates=True)
    telegram_bot = Tdp.start_polling() #exec_tg.start()
    print(dir(D))
    discord_bot = D.start(token_dpy)

    await asyncio.gather(telegram_bot, discord_bot)
asyncio.run(main())
"""
# gogurt enjoyer's code
def main():
    loop = asyncio.get_event_loop()
    loop.create_task(D.start(token_dpy))
    t.executor.start_polling(Tdp)
main()






