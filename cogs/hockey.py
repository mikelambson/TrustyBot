import discord
import aiohttp
import asyncio
import json
import os
from datetime import datetime
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
try:
    from .oilers import Oilers
except ImportError:
    pass

numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}
class Hockey:

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        self.settings = dataIO.load_json("data/hockey/settings.json")
        self.url = "https://statsapi.web.nhl.com"
        self.teams = dataIO.load_json("data/hockey/teams.json")
        self.headshots = "https://nhl.bamcontent.com/images/headshots/current/168x168/{}.jpg"
        self.loop = bot.loop.create_task(self.get_team_goals())

    def __unload(self):
        self.loop.cancel()

    @commands.command(hidden=True, pass_context=True)
    @checks.is_owner()
    async def testgoallights(self, ctx):
        hue = Oilers(self.bot)
        await hue.oilersgoal2()

    async def team_playing(self, games):
        """Check if team is playing and returns game link and team name"""
        is_playing = False
        links = {}
        for game in games:
            if game["teams"]["away"]["team"]["name"] in self.settings and game["status"]["abstractGameState"] != "Final":
                is_playing = True
                links[game["teams"]["away"]["team"]["name"]] = game["link"]
            if game["teams"]["home"]["team"]["name"] in self.settings and game["status"]["abstractGameState"] != "Final":
                is_playing =True
                links[game["teams"]["home"]["team"]["name"]] = game["link"]
        return is_playing, links

    async def get_team_goals(self):
        """Loop to check what teams are playing and see if a goal was scored"""
        await self.bot.wait_until_ready()
        while self is self.bot.get_cog("Hockey"):
            async with self.session.get(self.url + "/api/v1/schedule") as resp:
                data = await resp.json()
            is_playing, games = await self.team_playing(data["dates"][0]["games"])
            num_goals = 0
            # print(games)
            while is_playing and games != {}:
                for team, link in games.items():
                    print(team)
                    async with self.session.get(self.url + link) as resp:
                        data = await resp.json()
                    # print(data)
                    event = data["liveData"]["plays"]["allPlays"]
                    home_team = data["gameData"]["teams"]["home"]["name"]
                    home_shots = data["liveData"]["linescore"]["teams"]["home"]["shotsOnGoal"]
                    home_score = data["liveData"]["linescore"]["teams"]["home"]["goals"]
                    home_abr = data["gameData"]["teams"]["home"]["abbreviation"]
                    away_team = data["gameData"]["teams"]["away"]["name"]
                    away_shots = data["liveData"]["linescore"]["teams"]["away"]["shotsOnGoal"]
                    away_score = data["liveData"]["linescore"]["teams"]["away"]["goals"]
                    away_abr = data["gameData"]["teams"]["away"]["abbreviation"]
                    score_msg = {"Home":home_team, "Home Score":home_score, "Home Shots":home_shots,
                                 "Away": away_team, "Away Score":away_score, "Away Shots":away_shots}
                    goals = [goal for goal in event if goal["result"]["eventTypeId"] == "GOAL"]
                    if len(goals) == 0:
                        continue
                    await self.check_team_goals(goals, team, score_msg)
                if data["gameData"]["status"]["abstractGameState"] == "Final":
                    # print("Final")
                    # Clears the game data from the settings file
                    self.settings[team]["goal_id"] = {}
                    dataIO.save_json("data/hockey/settings.json", self.settings)
                    del games[team]
                if games == {}:
                    is_playing = False
                    break
                await asyncio.sleep(60)
            print(is_playing)
            await asyncio.sleep(300)

    async def check_team_goals(self, goals, team, score_msg):
        goal_ids = [str(goal_id["about"]["eventId"]) for goal_id in goals]
        goal_list = list(self.settings[team]["goal_id"])
        for goal in goals:
            goal_id = str(goal["about"]["eventId"])
            if goal_id not in goal_list:
                # Posts goal information and saves data for verification later
                msg_list = await self.post_team_goal(goal, team, score_msg)
                self.settings[team]["goal_id"][goal_id] = {"goal":goal,"messages":msg_list}
                dataIO.save_json("data/hockey/settings.json", self.settings)
            if goal_id in goal_list:
                # Checks if the goal data has changed and edits all previous posts with new data
                old_goal = self.settings[team]["goal_id"][goal_id]["goal"]
                if goal != old_goal:
                    print("attempting to edit")
                    old_msgs = self.settings[team]["goal_id"][goal_id]["messages"]
                    self.settings[team]["goal_id"][goal_id]["goal"] = goal
                    dataIO.save_json("data/hockey/settings.json", self.settings)
                    await self.post_team_goal(goal, team, score_msg, old_msgs)

        for old_goal in goal_list:
            if old_goal not in goal_ids:
                old_msgs = self.settings[team]["goal_id"][old_goal]["messages"].items()
                for channel_id, message_id in old_msgs:
                    channel = self.bot.get_channel(id=channel_id)
                    message = await self.bot.get_message(channel, message_id)
                    try:
                        await self.bot.delete_message(message)
                    except:
                        print("I can't delete messages in {}".format(channel.server.name))
                        pass
                del self.settings[team]["goal_id"][old_goal]
                dataIO.save_json("data/hockey.settings.json", self.settings)

    async def post_team_goal(self, goal, team, score_msg, og_msg=None):
        """Creates embed and sends message if a team has scored a goal"""
        
        scorer = self.headshots.format(goal["players"][0]["player"]["id"])
        scoring_team = self.teams[goal["team"]["name"]]
        period = goal["about"]["ordinalNum"]
        home = goal["about"]["goals"]["home"]
        away = goal["about"]["goals"]["away"]
        period_time_left = goal["about"]["periodTimeRemaining"]
        strength = goal["result"]["strength"]["name"]
        if strength == "Even":
            strength = "Even Strength"
        if goal["result"]["emptyNet"]:
            strength = "Empty Net"
        em = discord.Embed(description=strength + " Goal by " + goal["result"]["description"],
                           colour=int(self.teams[goal["team"]["name"]]["home"].replace("#", ""), 16))
        em.set_author(name="🚨 " + goal["team"]["name"] + " " + strength + " GOAL 🚨", 
                      url=self.teams[goal["team"]["name"]]["team_url"],
                      icon_url=self.teams[goal["team"]["name"]]["logo"])
        em.add_field(name=score_msg["Home"], value=str(home))
        em.add_field(name=score_msg["Away"], value=str(away))
        em.add_field(name="Shots " + score_msg["Home"], value=score_msg["Home Shots"])
        em.add_field(name="Shots " + score_msg["Away"], value=score_msg["Away Shots"])
        em.set_thumbnail(url=scorer)
        em.set_footer(text="{} left in the {} period"
                      .format(period_time_left, period), icon_url=self.teams[goal["team"]["name"]]["logo"])
        em.timestamp = datetime.strptime(goal["about"]["dateTime"], "%Y-%m-%dT%H:%M:%SZ")
        msg_list = {}
        if og_msg is None:
            if "oilers" in goal["team"]["name"].lower():
                try:
                    hue = Oilers(self.bot)
                    await hue.oilersgoal2()
                except:
                    pass
            for channels in self.settings[team]["channel"]:
                role = None
                channel = self.bot.get_channel(id=channels)
                server = channel.server
                for roles in server.roles:
                    if roles.name == goal["team"]["name"] + " GOAL":
                        role = roles
                try:
                    if role is None:
                        msg = await self.bot.send_message(channel, embed=em)
                        msg_list[channel.id] = msg.id
                    else:  
                        msg = await self.bot.send_message(channel, role.mention, embed=em)
                        msg_list[channel.id] = msg.id
                except:
                    print("Could not post goal in {}".format(channels))
                    pass
            # print(msg_list)
            return msg_list
        else:
            for channel_id, message_id in og_msg.items():
                role = None
                channel = self.bot.get_channel(id=channel_id)
                # print("channel {} ID {}".format(channel, message_id))
                message = await self.bot.get_message(channel, message_id)
                # print("I can get the message")
                server = message.server
                for roles in server.roles:
                    if roles.name == goal["team"]["name"] + " GOAL":
                        role = roles
                if role is None:
                    await self.bot.edit_message(message, embed=em)
                else:  
                    await self.bot.edit_message(message, role.mention, embed=em)
            return

    @commands.group(pass_context=True, name="hockey", aliases=["nhl"])
    async def hockey_commands(self, ctx):
        """Various Hockey related commands"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @hockey_commands.command(pass_context=True)
    @checks.is_owner()
    async def hockeytwitter(self, ctx):
        server = self.bot.get_server(id="381567805495181344")
        for team in self.teams:
            team = team.replace(".", "")
            team = team.replace(" ", "-")
            if team.startswith("Montr"):
                team = "montreal-canadiens"
            await self.bot.create_channel(server, name=team.lower() + "-twitter")

    @hockey_commands.command(pass_context=True, hidden=True, name="reset")
    async def reset_hockey(self, ctx):
        for team in self.settings:
            self.settings[team]["goal_id"] = {}
        dataIO.save_json("data/hockey/settings.json", self.settings)
        await self.bot.say("Cleared saved hockey data.")


    @hockey_commands.command(pass_context=True, name="add", aliases=["add_goals"])
    @checks.admin_or_permissions(manage_channels=True)
    async def add_goals(self, ctx, team, channel:discord.Channel=None):
        """Adds a hockey team goal updates to a channel"""
        try:
            team = [team_name for team_name in self.teams if team.lower() in team_name.lower()][0]
        except IndexError:
            await self.bot.say("{} is not an available team!".format(team))
            return
        if channel is None:
            channel = ctx.message.channel
        if team not in self.settings:
            self.settings[team] = {"channel":[channel.id], "goal_id": {}}
        if channel.id in self.settings[team]["channel"]:
            await self.bot.send_message(ctx.message.channel, "I am already posting {} goals in {}!".format(team, channel.mention))
            return
        self.settings[team]["channel"].append(channel.id)
        dataIO.save_json("data/hockey/settings.json", self.settings)
        await self.bot.say("{} goals will be posted in {}".format(team, channel.mention))

    @hockey_commands.command(pass_context=True, name="del", aliases=["remove", "rem"])
    @checks.admin_or_permissions(manage_channels=True)
    async def remove_goals(self, ctx, team, channel:discord.Channel=None):
        """Removes a teams goal updates from a channel"""
        try:
            team = [team_name for team_name in self.teams if team.lower() in team_name.lower()][0]
        except IndexError:
            await self.bot.say("{} is not an available team!".format(team))
            return
        if channel is None:
            channel = ctx.message.channel
        if team not in self.settings:
            await self.bot.send_message(ctx.message.channel, "I am not posting {} goals in {}".format(team, channel.mention))
            return
        if channel.id in self.settings[team]["channel"]:
            self.settings[team]["channel"].remove(channel.id)
            dataIO.save_json("data/hockey/settings.json", self.settings)
            await self.bot.say("{} goals will stop being posted in {}".format(team, channel.mention))

    @hockey_commands.command(pass_context=True, name="role")
    async def team_role(self, ctx, *, team):
        """Set your role to a team role"""
        server = ctx.message.server
        if server.id != "381567805495181344":
            await self.bot.send_message(ctx.message.channel, "Sorry that only works on TrustyJAID's Oilers Server!")
            return
        try:
            team = [team_name for team_name in self.teams if team.lower() in team_name.lower()][0]
        except IndexError:
            await self.bot.say("{} is not an available team!".format(team))
            return
        role = [role for role in server.roles if role.name == team][0]
        await self.bot.add_roles(ctx.message.author, role)
        await self.bot.send_message(ctx.message.channel, "Role applied.")

    @hockey_commands.command(pass_context=True, name="goals")
    async def team_goals(self, ctx, *, team=None):
        """Subscribe to goal notifications"""
        server = ctx.message.server
        member = ctx.message.author
        if server.id != "381567805495181344":
            await self.bot.send_message(ctx.message.channel, "Sorry that only works on TrustyJAID's Oilers Server!")
            return
        if team is None:
            team = [role.name for role in member.roles if role.name in self.teams]
            for t in team:
                role = [role for role in server.roles if role.name == t + " GOAL"]
                for roles in role:
                    await self.bot.add_roles(ctx.message.author, roles)
                await self.bot.send_message(ctx.message.channel, "Role applied.")
        else:
            try:
                team = [team_name for team_name in self.teams if team.lower() in team_name.lower()][0]
            except IndexError:
                await self.bot.say("{} is not an available team!".format(team))
                return
            role = [role for role in server.roles if role.name == team][0]
            await self.bot.add_roles(ctx.message.author, role)
            await self.bot.send_message(ctx.message.channel, "Role applied.")

    async def game_menu(self, ctx, post_list: list,
                         team_set=None,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""

        game = post_list[page]
        async with self.session.get(self.url + game["link"]) as resp:
            game_data = await resp.json()
        home_team = game_data["liveData"]["linescore"]["teams"]["home"]["team"]["name"]
        home_shots = game_data["liveData"]["linescore"]["teams"]["home"]["shotsOnGoal"]
        home_score = game_data["liveData"]["linescore"]["teams"]["home"]["goals"]
        away_team = game_data["liveData"]["linescore"]["teams"]["away"]["team"]["name"]
        away_shots = game_data["liveData"]["linescore"]["teams"]["away"]["shotsOnGoal"]
        away_score = game_data["liveData"]["linescore"]["teams"]["away"]["goals"]
        logo = self.teams[home_team]["logo"] if team_set is None else self.teams[team_set]["logo"]
        team_url = self.teams[home_team]["team_url"] if team_set is None else self.teams[team_set]["team_url"]
        game_time = game["gameDate"]
        timestamp = datetime.strptime(game_time, "%Y-%m-%dT%H:%M:%SZ")
        game_state = game_data["gameData"]["status"]["abstractGameState"]
        title = "{away} @ {home} {state}".format(away=away_team, home=home_team, state=game_state)
        if team_set is None:
            colour = int(self.teams[home_team]["home"].replace("#", ""), 16)
        else:
            colour = int(self.teams[team_set]["home"].replace("#", ""), 16)
        em = discord.Embed(timestamp=timestamp, colour=colour)
        em.set_author(name=title, url=team_url, icon_url=logo)
        em.set_thumbnail(url=logo)
        em.add_field(name="Home Team", value=home_team)
        em.add_field(name="Away Team", value=away_team)
        if game_state != "Preview":
            em.add_field(name="Home Shots on Goal", value=home_shots)
            em.add_field(name="Away Shots on Goal", value=away_shots)
            em.add_field(name="Home Score", value=str(home_score))
            em.add_field(name="Away Score", value=str(away_score))
            if game_state == "Live":
                event = game_data["liveData"]["plays"]["allPlays"]
                period = game_data["liveData"]["linescore"]["currentPeriodOrdinal"]
                period_time_left = game_data["liveData"]["linescore"]["currentPeriodTimeRemaining"]
                goals = [goal for goal in event if goal["result"]["eventTypeId"] == "GOAL"]
                if period_time_left[0].isdigit():
                    msg = "{} Left in the {} period".format(period_time_left, period)
                else:
                    msg = "{} of the {} period".format(period_time_left, period)
                em.description = event[-1]["result"]["description"]
                if goals != []:
                    em.add_field(name="{} Goal".format(goals[-1]["team"]["name"]), value=goals[-1]["result"]["description"])
                em.add_field(name="Period", value=msg)
        em.set_footer(text="Game start ", icon_url=logo)
        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=em)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")
            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=em)
        react = await self.bot.wait_for_reaction(
            message=message, user=ctx.message.author, timeout=timeout,
            emoji=["➡", "⬅", "❌"]
        )
        if react is None:
            await self.bot.remove_reaction(message, "⬅", self.bot.user)
            await self.bot.remove_reaction(message, "❌", self.bot.user)
            await self.bot.remove_reaction(message, "➡", self.bot.user)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            next_page = 0
            if page == len(post_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.game_menu(ctx, post_list, team_set=team_set,
                                        message=message,
                                        page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(post_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.game_menu(ctx, post_list, team_set=team_set,
                                        message=message,
                                        page=next_page, timeout=timeout)
        else:
            return await\
                self.bot.delete_message(message)

    async def roster_menu(self, ctx, post_list: list,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        player_list = post_list[page]
        async with self.session.get(self.url + player_list["person"]["link"] + "?expand=person.stats&stats=yearByYear") as resp:
            player_data = await resp.json()
        player = player_data["people"][0]
        year_stats = [league for league in player["stats"][0]["splits"] if league["league"]["name"] == "National Hockey League"][-1]
        name = player["fullName"]
        number = player["primaryNumber"]
        position = player["primaryPosition"]["name"]
        headshot = self.headshots.format(player["id"])
        team = player["currentTeam"]["name"]
        em = discord.Embed(colour=int(self.teams[team]["home"].replace("#", ""), 16))
        em.set_author(name="{} #{}".format(name, number), url=self.teams[team]["team_url"], icon_url=self.teams[team]["logo"])
        em.add_field(name="Position", value=position)
        em.set_thumbnail(url=headshot)
        if position != "Goalie":
            post_data = {"Shots" : year_stats["stat"]["shots"],
                        "Goals" : year_stats["stat"]["goals"],
                        "Assists" : year_stats["stat"]["assists"],
                        "Hits" : year_stats["stat"]["hits"],
                        "Face Off Percent" : year_stats["stat"]["faceOffPct"],
                        "+/-" : year_stats["stat"]["plusMinus"],
                        "Blocked Shots" : year_stats["stat"]["blocked"],
                        "PIM" : year_stats["stat"]["pim"]}
            for key, value in post_data.items():
                if value != 0.0:
                    em.add_field(name=key, value=value)
        else:
            saves = year_stats["stat"]["saves"]
            save_percentage = year_stats["stat"]["savePercentage"]
            goals_against_average = year_stats["stat"]["goalAgainstAverage"]
            em.add_field(name="Saves", value=saves)
            em.add_field(name="Save Percentage", value=save_percentage)
            em.add_field(name="Goals Against Average", value=goals_against_average)
        
        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=em)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")
            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=em)
        react = await self.bot.wait_for_reaction(
            message=message, user=ctx.message.author, timeout=timeout,
            emoji=["➡", "⬅", "❌"]
        )
        if react is None:
            await self.bot.remove_reaction(message, "⬅", self.bot.user)
            await self.bot.remove_reaction(message, "❌", self.bot.user)
            await self.bot.remove_reaction(message, "➡", self.bot.user)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            next_page = 0
            if page == len(post_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.roster_menu(ctx, post_list,
                                        message=message,
                                        page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(post_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.roster_menu(ctx, post_list,
                                        message=message,
                                        page=next_page, timeout=timeout)
        else:
            return await\
                self.bot.delete_message(message)

    @hockey_commands.command(pass_context=True)
    async def emojis(self, ctx):
        emoji = ""
        for team in self.teams:
            await self.bot.say("<:" + self.teams[team]["emoji"] + "> ")
        # await self.bot.say(emoji)

    async def standings_menu(self, ctx, post_list: list,
                         display_type,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        # Change between standing pages
        em = discord.Embed()
        standing_list = post_list[page]
        
        if display_type == "division":
            conference = standing_list["conference"]["name"]
            division = standing_list["division"]["name"]
            for team in standing_list["teamRecords"]:
                team_name = team["team"]["name"]
                emoji = "<:" + self.teams[team_name]["emoji"] + ">"
                wins = team["leagueRecord"]["wins"]
                losses = team["leagueRecord"]["losses"]
                ot = team["leagueRecord"]["ot"]
                gp = team["gamesPlayed"]
                pts = team["points"]
                pl = team["divisionRank"]
                msg = "GP: **{gp}** W: **{wins}** L: **{losses}** OT: **{ot}** PTS: **{pts}**".format(pl=pl,emoji=emoji, wins=wins, losses=losses, ot=ot, pts=pts, gp=gp)
                timestamp = datetime.strptime(team["lastUpdated"], "%Y-%m-%dT%H:%M:%SZ")
                em.add_field(name=pl + ". " + emoji + " " + team_name, value=msg, inline=True)
                em.timestamp = timestamp
                em.set_footer(text="Stats last Updated")
            if conference == "Eastern":
                em.colour = int("c41230", 16)
                em.set_author(name=division + " Division", url="https://www.nhl.com/standings")#, icon_url="https://upload.wikimedia.org/wikipedia/en/thumb/1/16/NHL_Eastern_Conference.svg/1280px-NHL_Eastern_Conference.svg.png")
            if conference == "Western":
                em.colour = int("003e7e", 16)
                em.set_author(name=division + " Division", url="https://www.nhl.com/standings")#, icon_url="https://upload.wikimedia.org/wikipedia/en/thumb/6/65/NHL_Western_Conference.svg/1280px-NHL_Western_Conference.svg.png")
        if display_type == "conference":
            conference = "Eastern" if page == 0 else "Western"
            new_list = sorted(standing_list, key=lambda k: int(k["conferenceRank"]))
            for team in new_list:
                team_name = team["team"]["name"]
                emoji = "<:" + self.teams[team_name]["emoji"] + ">"
                wins = team["leagueRecord"]["wins"]
                losses = team["leagueRecord"]["losses"]
                ot = team["leagueRecord"]["ot"]
                gp = team["gamesPlayed"]
                pts = team["points"]
                pl = team["conferenceRank"]
                msg = "GP: **{gp}** W: **{wins}** L: **{losses}** OT: **{ot}** PTS: **{pts}**".format(pl=pl,emoji=emoji, wins=wins, losses=losses, ot=ot, pts=pts, gp=gp)
                timestamp = datetime.strptime(team["lastUpdated"], "%Y-%m-%dT%H:%M:%SZ")
                em.add_field(name=pl + ". " + emoji + " " + team_name, value=msg, inline=True)
                em.timestamp = timestamp
                em.set_footer(text="Stats last Updated")
            if conference == "Eastern":
                em.colour = int("c41230", 16)
                em.set_author(name=conference + " Conference", url="https://www.nhl.com/standings", icon_url="https://upload.wikimedia.org/wikipedia/en/thumb/1/16/NHL_Eastern_Conference.svg/1280px-NHL_Eastern_Conference.svg.png")
            if conference == "Western":
                em.colour = int("003e7e", 16)
                em.set_author(name=conference + " Conference", url="https://www.nhl.com/standings", icon_url="https://upload.wikimedia.org/wikipedia/en/thumb/6/65/NHL_Western_Conference.svg/1280px-NHL_Western_Conference.svg.png")
        if display_type == "teams":
            team = standing_list
            team_name = team["team"]["name"]
            league_rank = team["leagueRank"]
            division_rank = team["divisionRank"]
            conference_rank = team["conferenceRank"]
            emoji = "<:" + self.teams[team_name]["emoji"] + ">"
            wins = team["leagueRecord"]["wins"]
            losses = team["leagueRecord"]["losses"]
            ot = team["leagueRecord"]["ot"]
            gp = team["gamesPlayed"]
            pts = team["points"]
            streak = "{} {}".format(team["streak"]["streakNumber"], team["streak"]["streakType"])
            goals = team["goalsScored"]
            goals_against = team["goalsAgainst"]
            timestamp = datetime.strptime(team["lastUpdated"], "%Y-%m-%dT%H:%M:%SZ")
            em.set_author(name="# {} {}".format(league_rank, team_name), url="https://www.nhl.com/standings", icon_url=self.teams[team_name]["logo"])
            em.colour = int(self.teams[team_name]["home"].replace("#", ""), 16)
            em.set_thumbnail(url=self.teams[team_name]["logo"])
            em.add_field(name="Division", value="# " + division_rank)
            em.add_field(name="Conference", value="# " + conference_rank)
            em.add_field(name="Wins", value=wins)
            em.add_field(name="Losses", value=losses)
            em.add_field(name="OT", value=ot)
            em.add_field(name="Points", value=pts)
            em.add_field(name="Games Played", value=gp)
            em.add_field(name="Goals Scored", value=goals)
            em.add_field(name="Goals Against", value=goals_against)
            em.add_field(name="Current Streak", value=streak)
            em.timestamp = timestamp
            em.set_footer(text="Stats last Updated", icon_url=self.teams[team_name]["logo"])


        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=em)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")
            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=em)
        react = await self.bot.wait_for_reaction(
            message=message, user=ctx.message.author, timeout=timeout,
            emoji=["➡", "⬅", "❌"]
        )
        if react is None:
            await self.bot.remove_reaction(message, "⬅", self.bot.user)
            await self.bot.remove_reaction(message, "❌", self.bot.user)
            await self.bot.remove_reaction(message, "➡", self.bot.user)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            next_page = 0
            if page == len(post_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.standings_menu(ctx, post_list,
                                        display_type=display_type,
                                        message=message,
                                        page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(post_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.standings_menu(ctx, post_list,
                                        display_type=display_type,
                                        message=message,
                                        page=next_page, timeout=timeout)
        else:
            return await\
                self.bot.delete_message(message)

    @hockey_commands.command(pass_context=True)
    async def standings(self, ctx, *, search=None):
        """Displays current standings for each division"""
        async with self.session.get("https://statsapi.web.nhl.com/api/v1/standings") as resp:
            data = await resp.json()
        conference = ["eastern", "western", "conference"]
        division = ["metropolitan", "atlantic", "pacific", "central", "division"]
        try:
            team = [team_name for team_name in self.teams if search.lower() in team_name.lower()][0]
        except:
            team = None
        division_data = []
        conference_data = []
        team_data = []
        eastern = [team for record in data["records"] for team in record["teamRecords"] if record["conference"]["name"] =="Eastern"]
        western = [team for record in data["records"] for team in record["teamRecords"] if record["conference"]["name"] =="Western"]
        all_teams = [team for record in data["records"] for team in record["teamRecords"]]
        conference_data.append(eastern)
        conference_data.append(western)
        all_teams = sorted(all_teams, key=lambda k: int(k["leagueRank"]))
        division_data = [record for record in data["records"]]
        if search is None or search.lower() in division:
            if search is not None:
                division_search = None
                for record in division_data:
                    if search.lower() == record["division"]["name"].lower():
                        division_search = record
                index = division_data.index(division_search)
                await self.standings_menu(ctx, division_data, "division", None, index)
            else:
                await self.standings_menu(ctx, division_data, "division")
        elif search.lower() in conference:
            if search.lower() == "eastern":
                await self.standings_menu(ctx, conference_data, "conference", None, 0)
            else:
                await self.standings_menu(ctx, conference_data, "conference", None, 1)
        elif team is not None or "team" in search.lower():
            if team is None:
                await self.standings_menu(ctx, all_teams, "teams")
            else:
                team_data = None
                for teams in all_teams:
                    if teams["team"]["name"] == team:
                        team_data = teams
                index = all_teams.index(team_data)
                await self.standings_menu(ctx, all_teams, "teams", None, index)

    @hockey_commands.command(pass_context=True)
    async def games(self, ctx, *, team=None):
        """Gets all NHL games this season or selected team"""
        games_list = []
        page_num = 0
        today = datetime.today()
        url = "{base}/api/v1/schedule?startDate={year}-9-1&endDate={year2}-9-1"\
              .format(base=self.url, year=today.year, year2=today.year+1)
        
        if team is not None:
            try:
                team = [team_name for team_name in self.teams if team.lower() in team_name.lower()][0]
            except IndexError:
                await self.bot.send_message(ctx.message.channel, "{} Does not appear to be an NHL team!".format(team))
                return
            url += "&teamId={}".format(self.teams[team]["id"])
        async with self.session.get(url) as resp:
            data = await resp.json()
        for dates in data["dates"]:
            games_list += [game for game in dates["games"]]
        for game in games_list:
            game_time = datetime.strptime(game["gameDate"], "%Y-%m-%dT%H:%M:%SZ")
            if game_time >= today:
                page_num = games_list.index(game)
                break
        if games_list != []:
            await self.game_menu(ctx, games_list, team, None, page_num)
        else:
            await self.bot.send_message(ctx.message.channel, "{} have no recent or upcoming games!".format(team))

    @hockey_commands.command(pass_context=True)
    async def players(self, ctx, *, search):
        """Gets the current team roster"""
        rosters = {}
        players = []
        teams = [team for team in self.teams if search.lower() in team.lower()]
        if teams != []:
            for team in teams:
                url = "{}/api/v1/teams/{}/roster".format(self.url, self.teams[team]["id"])
                async with self.session.get(url) as resp:
                    data = await resp.json()
                for player in data["roster"]:
                    players.append(player)
        else:
            for team in self.teams:
                url = "{}/api/v1/teams/{}/roster".format(self.url, self.teams[team]["id"])
                async with self.session.get(url) as resp:
                    data = await resp.json()
                rosters[team] = data["roster"]
            
            for team in rosters:
                for player in rosters[team]:
                    if search.lower() in player["person"]["fullName"].lower():
                        players.append(player)
        
        if players != []:
            await self.roster_menu(ctx, players)
        else:
            await self.bot.send_message(ctx.message.channel, "{} is not an NHL team or Player!".format(search))

def check_folder():
    if not os.path.exists("data/hockey"):
        print("Creating data/tweets folder")
        os.makedirs("data/hockey")

def check_file():
    data = {}
    f = "data/hockey/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default settings.json...")
        dataIO.save_json(f, data)

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Hockey(bot))