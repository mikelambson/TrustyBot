from random import choice, randint
import random
import aiohttp
import discord
import asyncio
from discord.ext import commands
from .utils.chat_formatting import *
from .utils.dataIO import dataIO
from .utils.dataIO import fileIO
from cogs.utils import checks
import datetime
import os
import string
import time



class TrustyBot:
    def __init__(self, bot):
        self.bot = bot
        self.text = dataIO.load_json("data/trustybot/messages.json")
        self.links = dataIO.load_json("data/trustybot/links.json")
        self.images = dataIO.load_json("data/trustybot/images.json")
        self.files = dataIO.load_json("data/trustybot/files.json")
        self.donotdo = dataIO.load_json("data/dnd/donotdo.json")
        self.session = aiohttp.ClientSession(loop=self.bot.loop)

    def __unload(self):
        self.session.close()

    def first_word(self, msg):
        return msg.split(" ")[0]

    def get_prefix(self, server, msg):
        prefixes = self.bot.settings.get_prefixes(server)
        for p in prefixes:
            if msg.startswith(p):
                return p
        return None

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def testcu(self, ctx):
        try:
            channel = self.bot.get_channel(id="381570669609091073")
            message = await self.bot.get_message(channel, "405191506601705473")
        except:
            print("error")
        print(message)
        

    @commands.command(pass_context=True)
    async def getavatar(self, ctx, member:discord.Member):
        await self.bot.send_message(ctx.message.channel, member.avatar_url)

    def part_of_existing_command(self, alias, server):
        '''Command or alias'''
        for command in self.bot.commands:
            if alias.lower() == command.lower():
                return True
        return False

    async def on_message(self, message):
        if len(message.content) < 2 or message.channel.is_private:
            return

        msg = message.content
        server = message.server
        channel = message.channel
        prefix = self.get_prefix(server, msg)
        if not prefix:
            return
        ignorelist = ["dickbutt", "cookie", "tinfoil", "donate", "dreams", "memes"]

        alias = self.first_word(msg[len(prefix):]).lower()
        if alias in ignorelist:
            return

        if alias in self.images:
            image = self.images[alias]
            await self.bot.send_typing(channel)
            await self.bot.send_file(channel, image)
        
        if alias in self.links:
            link = self.links[alias]
            await self.bot.send_typing(channel)
            await self.bot.send_message(channel, link)
        
        if alias in self.text:
            msg = self.text[alias]
            await self.bot.send_typing(channel)
            await self.bot.send_message(channel, msg)

    @commands.command(pass_context=True)
    async def addimage(self, ctx, command):
        """Add an image to direct upload."""
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        prefix = self.get_prefix(server, ctx.message.content)
        msg = ctx.message
        if command is not "":
            if command in self.images or self.part_of_existing_command(command, server):
                await self.bot.say("{} is already in the list, try another!".format(command))
                return
            else:
                await self.bot.say("{} added as the command!".format(command))
        await self.bot.say("Upload an image for me to use!")
        while msg is not None:
            msg = await self.bot.wait_for_message(author=author, timeout=60)
            if msg is None:
                await self.bot.say("No image uploaded then.")
                break

            if msg.attachments != []:
                filename = msg.attachments[0]["filename"]
                directory = "data/trustybot/img/" + filename
                if command is None:
                    command = filename.split(".")[0]
                if directory in self.images.values():
                    seed = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                    directory = "data/trustybot/img/" + seed + filename
                if directory not in self.images.values():
                    self.images[command] = directory
                    dataIO.save_json("data/trustybot/images.json", self.images)
                    async with self.session.get(msg.attachments[0]["url"]) as resp:
                        test = await resp.read()
                        with open(self.images[command], "wb") as f:
                            f.write(test)
                    await self.bot.send_message(channel, "{} has been added to my files!"
                                                .format(command))
                    break
            if msg.content.lower().strip() == "exit":
                await self.bot.say("Your changes have been saved.")
                break

    @commands.command(pass_context=True, aliases=["serverhelp"])
    async def helpserver(self, ctx):
        await self.bot.say("https://discord.gg/wVVrqej")

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def members(self, ctx, server_id):
        server = self.bot.get_server(id=server_id)
        member_list = sorted(server.members, key=lambda m: m.joined_at)
        new_msg = ""
        for member in member_list[:10]:
            new_msg += member.name + ": " + str((member_list.index(member)+1)) + "\n"
        await self.bot.send_message(ctx.message.channel, new_msg)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def createchannel(self, ctx, name:str, position:int):
        chn = await self.bot.create_channel(ctx.message.server, name)
        await self.bot.move_channel(chn, position)
        await self.bot.say(chn.position)

    
    @commands.command(pass_context=True)
    @checks.is_owner()
    async def listchannels(self, ctx, server_id:discord.Server=None):
        if server_id is None:
            server = ctx.message.server
        else:
            server = server_id
        channels = {}
        for channel in server.channels:
            for channel in server.channels:
                channels[channel.name] = {"id":channel.id, "pos":channel.position}
        await self.bot.say("{} ({}): {}".format(server.name, server.id, channels))
    
    @commands.command(pass_context=True)
    @checks.is_owner()
    async def nummembers(self, ctx, *, servername):
        channels = {}
        for server in self.bot.servers:
            if server.name == servername:
                await self.bot.say(len(server.members))

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def makeinvite(self, ctx, server_id):
        server = self.bot.get_server(id=server_id)
        invites = []
        for channel in server.channels:
            try:
                invite = await self.bot.create_invite(channel)
                invites.append(invite.url)
            except:
                pass
        await self.bot.say(invites)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def massinvite(self, ctx, server_id=None):

        invites = []
        for server in self.bot.servers:
            made_invite = False
            members = [member.id for member in server.members]
            if "218773382617890828" not in members:
                print(server.name)
                for channel in server.channels:
                    if made_invite:
                        continue
                    if channel.type == discord.ChannelType.text:
                        try:
                            invite = await self.bot.create_invite(channel, unique=False)
                            invites.append(invite.url)
                            made_invite = True
                        except:
                            made_invite = False
                            pass

        await self.bot.say(invites)
    
    @commands.command(pass_context=True)
    @checks.is_owner()
    async def getserverid(self, ctx):
        msg = ""
        num = 1
        for server in self.bot.servers:
            msg += "{}. {}: {}\n".format(num, server.name, server.id)
            num += 1
        await self.bot.say(msg)

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def getroles(self, ctx):
        server = ctx.message.server
        msg = ""
        for role in server.roles:
            msg += (role.name + ",")
        await self.bot.say(msg)

    @commands.command(pass_context=True)
    async def serveremojis(self, ctx, *, servername=None):
        msg = ""
        server = None
        if servername is not None:
            for servers in self.bot.servers:
                if servers.name == servername:
                    server = servers
        else:
            server = ctx.message.server

        if server is None:
            await self.bot.send_message(ctx.message.channel, "I don't see that server!")
            return
        if len(server.emojis) > 25:
            emoji_list1 = server.emojis[:25]
            index = server.emojis.index(emoji_list1[-1])
            emoji_list2 = server.emojis[index:]
        else:
            emoji_list1 = server.emojis
            emoji_list2 = None
        embed = discord.Embed(timestamp=ctx.message.timestamp)
        embed.set_author(name=server.name, icon_url=server.icon_url)
        for emoji in emoji_list1:
            embed.add_field(name=":" + emoji.name + ":",
                            value="<:" + emoji.name + ":" + emoji.id + "> ",
                            inline=True)
        await self.bot.send_message(ctx.message.channel, embed=embed)
        if emoji_list2 is not None:
            embed = discord.Embed(timestamp=ctx.message.timestamp)
            embed.set_author(name=server.name, icon_url=server.icon_url)
            for emoji in emoji_list2[1:]:
                embed.add_field(name=":" + emoji.name + ":",
                                value="<:" + emoji.name + ":" + emoji.id + "> ",
                                inline=True)
            await self.bot.send_message(ctx.message.channel, embed=embed)

    @commands.command()
    async def listimages(self):
        """List images added to bot"""
        msg = ""
        for image in self.images.keys():
            msg += image + ", "
        await self.bot.say("```" + msg[:len(msg)-2] + "```")
    
    @commands.command()
    async def listtext(self):
        """List phrases added to bot"""
        msg = ""
        for text in self.text.keys():
            msg += text + ", "
        await self.bot.say("```" + msg[:len(msg)-2] + "```")
    
    @commands.command()
    async def listlinks(self):
        """List links added to bot"""
        msg = ""
        for link in self.links.keys():
            msg += link + ", "
        await self.bot.say("```" + msg[:len(msg)-2] + "```")
    

    @commands.command(pass_context=True, aliases=["db"])
    async def dickbutt(self, ctx):
        """DickButt"""
        ext = ["png", "gif"]
        if ctx.message.server.id != "261565811309674499":
            await self.bot.upload(self.images["dickbutt"]
                                  .format(choice(ext)))
    
    @commands.command(pass_context=True)
    async def neat(self, ctx, number=None):
        """Neat"""
        files = "data/trustybot/img/neat{}.gif"
        if number is None:
            await self.bot.upload(files.format(str(choice(range(1, 6)))))
        elif number.isdigit() and (int(number) > 0 or int(number) < 8):
            await self.bot.upload(files.format(number))

    @commands.command(pass_context=True)
    async def cookie(self, ctx, user=None):
        """cookie"""
        msg = "Here's a cookie {}! :smile:"
        if user is None:
            await self.bot.upload(self.images["cookie"])
        else:
            await self.bot.upload(self.images["cookie"],
                                  content=msg.format(user))

    @commands.command(pass_context=True)
    async def reviewbrah(self, ctx):
        """Reviewbrah"""
        await self.bot.upload("data/trustybot/img/revi.png")
        await self.bot.upload("data/trustybot/img/ew.png")
        await self.bot.upload("data/trustybot/img/brah.png")
        

    @commands.command(pass_context=True, aliases=["tf"])
    async def tinfoil(self, ctx):
        """Liquid Metal Embrittlement"""
        await self.bot.upload(self.images["tinfoil"]
                              .format(choice(["1", "2"])))

    @commands.command(pass_context=True,)
    async def donate(self, ctx):
        """Donate some bitcoin!"""
        gabcoin = "1471VCzShn9kBSrZrSX1Y3KwjrHeEyQtup"
        msg = "Feel free to send bitcoin donations to `{}` :smile:"
        gabimg = "data/trustybot/img/gabbtc.jpg"
        if ctx.message.server.id == "261565811309674499":
            await self.bot.upload(gabimg)
            await self.bot.say(msg.format(gabcoin))
        else:
            await self.bot.say("Help support me  and development of TrustyBot by buying my album or donating bitcoin on my website :smile: https://trustyjaid.com/")

    # Text Commands #
    @commands.command(hidden=False)
    @commands.cooldown(1, 60, commands.BucketType.server)
    async def grep(self):
        """Get the fuck out of here with grep!"""
        await self.bot.say("Get the fuck out of here with grep!")
    
    @commands.command(pass_context=True)
    async def dnd(self, ctx, number=None):
        if number is None:
            await self.bot.say(choice(self.donotdo))
        elif number.isdigit():
            await self.bot.say(self.donotdo[int(number)-1])
        else:
            await self.bot.say(choice(self.donotdo))

    @commands.command(hidden=False)
    async def passphrase(self):
        """Wikileaks Vault7 Part 1 passphrase"""
        await self.bot.say("`SplinterItIntoAThousandPiecesAndScatterItIntoTheWinds`")

    @commands.command(name="pineal", aliases=["pineal gland"])
    async def pinealGland(self, message=None):
        """Links to pineal gland"""
        if message == "calcification" or message == "calcified":
            await self.bot.say(self.links["pineal"][1])
        if message == "healthy":
            await self.bot.say(self.links["pineal"][2])
        if message is None:
            await self.bot.say(self.links["pineal"][0])

    @commands.command(hiddent=False, pass_context=True)
    async def illuminati(self, ctx):
        """o.o"""
        emilum = ["\U0001F4A1", "\U000026A0", "\U0000203C", "\U000026D4"]
        ilum = ":bulb: :warning: :bangbang: :no_entry:"
        msg = await self.bot.say(ilum)
        for i in emilum:
            await self.bot.add_reaction(msg, emoji=i)

    @commands.command(hidden=False)
    async def halp(self, user=None):
        """How to ask for help!"""
        msg = "{} please type `;help` to be PM'd all my commands! :smile: or type `;serverhelp` to get an invite and I can help you personally."
        if user is None:
            await self.bot.say(msg.format(""))
        else:
            await self.bot.say(msg.format(user))

    @commands.command(hidden=False)
    async def dreams(self):
        """don't let your dreams be dreams"""
        await self.bot.say(self.text["dreams"].format("dreams"))

    @commands.command(hidden=False)
    async def memes(self):
        """don't let your memes be dreams"""
        await self.bot.say(self.text["dreams"].format("memes"))

    @commands.command(pass_context=True)
    async def flipm(self, ctx, *, message):
        """Flips a message"""
        msg = ""
        name = ""
        for user in message:
            char = "abcdefghijklmnopqrstuvwxyz - ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            tran = "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz - ∀qƆpƎℲפHIſʞ˥WNOԀQᴚS┴∩ΛMX⅄Z"
            table = str.maketrans(char, tran)
            name += user.translate(table) + " "
        await self.bot.say(msg + "(╯°□°）╯︵ " + name[::-1])
    
    @commands.command(pass_context=True, no_pm=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def delmessages(self, ctx, number: int):
        """Deletes last X messages.

        Example:
        cleanup messages 26"""

        channel = ctx.message.channel
        author = ctx.message.author
        server = author.server
        is_bot = self.bot.user.bot
        has_permissions = channel.permissions_for(server.me).manage_messages

        to_delete = []

        if not has_permissions:
            await self.bot.say("I'm not allowed to delete messages.")
            return
        for i in range(0, number):
            async for message in self.bot.logs_from(channel, limit=1):
                await self.bot.delete_message(message)
                # await asyncio.sleep(2)


def setup(bot):
    n = TrustyBot(bot)
    bot.add_cog(n)
