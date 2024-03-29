import discord, json, os, time, re, datetime
from apiclient import discovery
from google.oauth2 import service_account

intents = discord.Intents.none()
intents.guilds = True
intents.messages = True

client = discord.Client(intents=intents)

with open("Config/token.json") as token_file:
    tokens = json.load(token_file)
    
with open("Config/config.json") as config_file:
    config = json.load(config_file);

with open("Config/help.json") as help_file:
    helpdata = json.load(help_file)

prefix = config["prefix"]

verifylogid = tokens["verifylogid"]

remindmsg = config["verifyremindmsg"]

startactivity = discord.Game(name="Type {}help to get started!".format(prefix))

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
secret_file = "Config/client_secret.json"
credentials = service_account.Credentials.from_service_account_file(secret_file, scopes=scopes)
service = discovery.build('sheets','v4',credentials=credentials)

def extract_id(possibleidstr): # works for user ids, and mentions
    try:
        return(int(possibleidstr))
    except ValueError:
        if(re.match("<@!?[0-9]*?>", possibleidstr)):
            if(possibleidstr[2] == "!"):
                possibleid = possibleidstr[3:-1]
            else:
                possibleid = possibleidstr[2:-1]
            try:
                return(int(possibleid))
            except ValueError:
                return -1
        else:
            return -1

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=startactivity)

@client.event
async def on_message(message):
    global prefix
    global helpdata
    global verifylogid
    global config
    global remindmsg
    if message.author == client.user:
        return
    if not (message.content.startswith(prefix)):
        return
    if (message.author.bot):
        if (message.author.id == 155149108183695360):
            await message.channel.send("Act your age, Dynosaur.")
        return
    args = (message.content[1:]).split(" ")
    if len(args) == 0:
        return
    command = args.pop(0)
    #perms means the permission the user has: developer -> 50, admin -> 40, HRs -> 30, verified members -> 20, message sent in DM -> 10, all users -> 0
    perms = 0
    isDM = False
    if message.author.id in [156390113654341632,676596209627955231]: 
        perms = 50
    if isinstance(message.channel, discord.abc.GuildChannel):
        if message.author.guild_permissions.administrator:
            perms = 40
        else:
            for role in message.author.roles:
                if role.id == 923519711445151796 and perms < 30:
                    perms = 30
                if role.id == 923519711386419230 and perms < 20:
                    perms = 20
    else:
        isDM = True
        if(perms < 10):
            perms = 10
    if (command == "help" and perms >= 0):
        targetcmd = ""
        if len(args) == 0:
            targetcmd = "all"
        else:
            targetcmd = args[0]
        if targetcmd.startswith(prefix):
            targetcmd = targetcmd[1:]
        output = ""
        if targetcmd == "all":
            for cmd,data in helpdata.items():
                if data["perms"] <= perms:
                    displaycmd = cmd + ' '
                    desc = data["description"]
                    if (desc[0:12] == "|subcommand|"):
                        displaycmd = ""
                        desc = desc[12:]
                    output += "`{0}{1}{2}`- {3}\n".format(prefix,displaycmd,data["usage"],desc)
            await message.channel.send(output+"Note that arguments encased in angle brackets (`<>`) are mandatory, while those encased in square brackets (`[]`) are optional.")
            return
        elif targetcmd in helpdata:
            data = helpdata[targetcmd]
            if data["perms"] <= perms:
                displaycmd = targetcmd + ' '
                desc = data["description"]
                if (desc[0:12] == "|subcommand|"):
                    displaycmd = ""
                    desc = desc[12:]
                await message.channel.send("`{0}{1}{2}`- {3}\n Note that arguments encased in angle brackets (`<>`) are mandatory, while those encased in square brackets (`[]`) are optional.".format(prefix,displaycmd,data["usage"],desc))
                return
            else:
                await message.channel.send("You cannot access the help for this command/subcommand.")
                return
        else:
            await message.channel.send("The command {}{} is not a command or subcommand.".format(prefix,targetcmd))
            return
    if (command == "getsource" and perms >= 0):
        await message.channel.send("This bot is open source, the source code is at: <https://github.com/RandomGamer123/VerificationBot>.")
        return
    if (command == "remind" and perms >= 40):
        if len(args) == 0:
            await message.channel.send("You need at least 1 argument for this command. Command format: {0}remind <user>".format(prefix))
            return
        tomessageid = extract_id(args[0])
        if(tomessageid == -1):
            await message.channel.send("No valid user ID detected in `{0}`. User ID argument must be a mention or their user id directly.".format(args[0]))
            return
        userobj = await client.fetch_user(tomessageid)
        if not userobj:
            await message.channel.send("User with user id `{0}` not found.".format(tomessageid))
            return
        embed = discord.Embed(title=remindmsg[0], description=remindmsg[1], timestamp=datetime.datetime.utcnow(), color=int(remindmsg[2],16))
        try:
            await userobj.send(embed=embed)
            await message.channel.send("User successfully reminded.")
        except discord.Forbidden:
            await message.channel.send("DM failed to send, likely due to the user having DMs disabled or having blocked the bot.")
    if (command == "verify" and perms >=0):
        if len(args) == 0:
            await message.channel.send("Verification instructions: Visit <{0}> to get a verification code valid for 5 minutes. Then input your code and Roblox username in Discord using the command `{1}verify <code> <username>`. Do not include the brackets.".format(config["verification_link"], prefix))
            return
        if len(args) < 2:
            await message.channel.send("You need at least 2 arguments for this command. Command format: {0}verify <code> <username>. Do not include the brackets. Visit <{1}> to get the verification code.".format(prefix, config["verification_link"]))
            return
        code = args.pop(0)
        name = " ".join(args)
        if (code[0] == "<" or code[-1] == ">"):
            await message.channel.send("Do not include the angle brackets with the code or username, please try again.")
            return
        verifycodes = (service.spreadsheets().values().get(spreadsheetId = verifylogid, range = "RobloxCodePairs!A2:F", majorDimension="ROWS", valueRenderOption = "UNFORMATTED_VALUE").execute())["values"]
        grouprank = -1
        newcodelist = verifycodes[:]
        emptyvals = 0
        boughtclass = "EC"
        rename = ""
        userrobloxid = 0
        for i in range(len(verifycodes)):
            codepair = verifycodes[i]
            if codepair[3] < time.time():
                newcodelist.remove(codepair)
                emptyvals = emptyvals + 1
            else:
                if codepair[2] == code:
                    if codepair[0].lower() == name.lower():
                        grouprank = codepair[4]
                        boughtclass = codepair[5]
                        emptyvals = emptyvals + 1
                        newcodelist.remove(codepair)
                        rename = codepair[0]
                        userrobloxid = codepair[1]
        if (grouprank == -1):
            await message.channel.send("A matching code and username combination cannot be found or your code has expired. Please generate a new code.")
            return
        if isinstance(message.channel, discord.abc.GuildChannel):
            roleguild = message.guild
        else:
            roleguild = client.get_guild(config["main_guild"])
        if ((message.guild is not None) and (message.guild.id == config["main_guild"])):
            userobj = message.author
        else:
            #userobj = roleguild.get_member(message.author.id)
            userobj = await roleguild.fetch_member(message.author.id)
        await userobj.edit(nick=rename)
        if (grouprank == 0):
            notingrouprole = discord.utils.get(roleguild.roles, name="NOT IN GROUP")
            verifiedrole = discord.utils.get(roleguild.roles, name="Verified")
            await userobj.remove_roles(verifiedrole)
            await userobj.add_roles(notingrouprole,reason="User is not in the group.")
            await message.channel.send("You are not in the group. Please submit a request to join the group and wait until you are accepted, then request a new code and reverify. The related roles have been given.")
        if (grouprank > 0):
            verifiedrole = discord.utils.get(roleguild.roles, name="Verified")
            passengersrole = discord.utils.get(roleguild.roles, name="Passengers")
            await userobj.add_roles(verifiedrole,reason="User is in the group.")
            await userobj.add_roles(passengersrole,reason="User is in the group.")
            if message.guild.id == config["main_guild"]:
                notingrouprole = discord.utils.get(roleguild.roles, name="NOT IN GROUP")
                if grouprank == 50:
                    traineerole = discord.utils.get(roleguild.roles, name="Trainee")
                    await userobj.add_roles(traineerole)
                if (grouprank >= 100):
                    staffrole = discord.utils.get(roleguild.roles, name="Staff Members")
                    await userobj.add_roles(staffrole)
                    traineerole = discord.utils.get(roleguild.roles, name="Trainee")
                    await userobj.remove_roles(traineerole)
                if boughtclass == "GI":
                    execpass = discord.utils.get(roleguild.roles, name="Executive Passengers")
                    classrole = discord.utils.get(roleguild.roles, name="Gold Investors")
                    await userobj.add_roles(execpass)
                    await userobj.add_roles(classrole)
                if boughtclass == "SI":
                    execpass = discord.utils.get(roleguild.roles, name="Executive Passengers")
                    classrole = discord.utils.get(roleguild.roles, name="Silver Investors")
                    await userobj.add_roles(execpass)
                    await userobj.add_roles(classrole)
                if boughtclass == "FC":
                    execpass = discord.utils.get(roleguild.roles, name="Executive Passengers")
                    classrole = discord.utils.get(roleguild.roles, name="First Class")
                    await userobj.add_roles(execpass)
                    await userobj.add_roles(classrole)
                if boughtclass == "BC":
                    execpass = discord.utils.get(roleguild.roles, name="Executive Passengers")
                    classrole = discord.utils.get(roleguild.roles, name="Business Class")
                    await userobj.add_roles(execpass)
                    await userobj.add_roles(classrole)
                await userobj.remove_roles(notingrouprole)
            await message.channel.send("Verification complete.")
        clearcommand = (service.spreadsheets().values().clear(spreadsheetId = verifylogid, range = "RobloxCodePairs!A2:F")).execute()
        response = (service.spreadsheets().values().update(spreadsheetId = verifylogid, range = "RobloxCodePairs!A2:F", valueInputOption="RAW", body = {"range":"RobloxCodePairs!A2:F","majorDimension":"ROWS","values":newcodelist})).execute()
    if (command == "manualverify" and perms >= 30):
        if(len(args) < 1):
            await message.channel.send("Invalid arguments. Command format: {0}manualverify <user> [nickname]".format(prefix))
            return
        targetid = extract_id(args[0])
        if(targetid == -1):
            await message.channel.send("No valid user ID detected in `{0}`. User ID argument must be a mention or their user id directly.".format(args[0]))
            return
        if isinstance(message.channel, discord.abc.GuildChannel):
            roleguild = message.guild
        else:
            roleguild = client.get_guild(config["main_guild"])
        userobj = await roleguild.fetch_member(targetid)
        if not userobj:
            await message.channel.send("User with user id `{0}` not found.".format(targetid))
            return
        verifiedrole = discord.utils.get(roleguild.roles, name="Verified")
        passengersrole = discord.utils.get(roleguild.roles, name="Passengers")
        notingrouprole = discord.utils.get(roleguild.roles, name="NOT IN GROUP")
        await userobj.add_roles(verifiedrole, passengersrole, reason="Manual verification")
        await userobj.remove_roles(notingrouprole, reason="Manual verification")
        args.pop(0)
        if(len(args) > 0):
            renameto = " ".join(args)
            await userobj.edit(nick=renameto)
        await message.channel.send("Manually verified user <@"+str(targetid)+">")

if os.getenv("BOTTOKEN"):
    bottoken = os.getenv("BOTTOKEN")
else: 
    bottoken = tokens["bottoken"]
client.run(bottoken)
