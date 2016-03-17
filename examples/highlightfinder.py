'''
Created on Jul 12, 2014

@author: Chris
'''
import sys
from demoinfocsgo.demodump import DemoDump

TEAM_T = 2
TEAM_CT = 3

class Player(object):
    def __init__(self, name, userid, networkid):
        self.name = name
        self.userid = userid
        self.networkid = networkid
        self.kills = 0
        self.deaths = 0
        self.assists = 0

        self.kills_this_round = 0
        self.clutch_kills = 0
        self.is_connected = True
        self.is_alive = False
        self.team = 0  # 2 is T, 3 is CT?

class HighlightFinder(object):
    def __init__(self, filename):
        self.filename = filename
        self.demo = DemoDump()
        self.players = {}
        self.current_round = 0
        self.highlights = []

    def parse(self):
        if self.demo.open(filename):
            print "Beginning parsing"
            self.demo.register_on_gameevent("player_connect", self.player_connected)
            self.demo.register_on_gameevent("player_connect_full", self.player_connected)
            self.demo.register_on_gameevent("player_disconnect", self.player_disconnected)
            self.demo.register_on_gameevent("player_team", self.player_join_team)
            self.demo.register_on_gameevent("player_spawn", self.player_spawn)
            self.demo.register_on_gameevent("round_announce_match_start", self.game_start)  # only start counting when warmup is over
            self.demo.dump()
        else:
            print "Demo unparsable"
        pass

    def player_connected(self, data):
        if data.userid not in self.players.keys():
            self.players[data.userid] = Player(data.name, data.userid, "")
        self.players[data.userid].is_connected = True

    def player_disconnected(self, data):
        if data.networkid == 'BOT':  # if bot, just remove
            self.players.pop(data.userid, None)
        else:
            self.players[data.userid].is_connected = False

    def player_join_team(self, data):
        if data.team == 0:  # disconnect?
            return
        if data.userid not in self.players.keys(): # can spawn before demo starts
            self.player_spawn(data)
        self.players[data.userid].team = data.team

    def player_spawn(self, data):
        if data.userid not in self.players.keys(): # can connect before demo starts
            self.player_connected(data)
        self.players[data.userid].is_alive = True
        self.players[data.userid].kills_this_round = 0
        self.players[data.userid].clutch_kills = 0

    def game_start(self, data):
        self.current_round = 0
        self.demo.register_on_gameevent('round_start', self.round_start)
        self.demo.register_on_gameevent('round_end', self.round_end)
        self.demo.register_on_gameevent('player_death', self.player_death)

    def round_start(self, data):
        self.current_round += 1

    def round_end(self, data):
        print "Round ended, winner: %i, reason: %i, message: %s" % (data.winner, data.reason, data.message)
        for player in self.players.values():
            if player.kills_this_round >= 3:
                self.highlights.append("%i got a %ik in round %i" % (player.userid, player.kills_this_round, self.current_round))
            if player.is_alive and player.team == data.winner and self.count_alive(player.team) == 1 and self.count_alive(self.invert_team(player.team)) == 0 and player.clutch_kills >= 2:
                self.highlights.append("%i clutched a 1v%i in round %i" % (player.userid, player.clutch_kills, self.current_round))

    def player_death(self, data):
        self.players[data.userid].deaths += 1
        self.players[data.userid].is_alive = False

        if data.userid != data.attacker:  # not suicide?
            self.players[data.attacker].kills += 1
            self.players[data.attacker].kills_this_round += 1  # used for finding highlights

            if self.count_alive(self.players[data.attacker].team) == 1:
                self.players[data.attacker].clutch_kills += 1
            print "%i killed %i with %s%s" % (self.players[data.attacker].userid, self.players[data.userid].userid, data.weapon, " (headshot)" if data.headshot else "")

        if data.assister != 0:  # someone assisted
            self.players[data.assister].assists += 1

    def count_alive(self, teamid):
        alive = 0
        for player in self.players.values():
            if player.is_connected and player.is_alive and player.team == teamid:
                alive += 1
        return alive

    def invert_team(self, teamid):
        if teamid == 2 or teamid == 3:
            return 3 if teamid == 2 else 2
        return teamid

    def print_results(self):
        print "%i players found" % len(self.players)
        for playerid, player in self.players.items():
            if player.networkid != "BOT":
                print vars(player)

        print ""
        print "Highlights: %i" % len(self.highlights)
        for highlight in self.highlights:
            print highlight


if __name__ == '__main__':
    filename = sys.argv[1]

    if len(sys.argv) <= 1:
        print "highlightfinder.py demofile.dem"
        sys.exit()
    hlfinder = HighlightFinder(filename)
    hlfinder.parse()
    hlfinder.print_results()
