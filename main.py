import os
import logging
import datetime

from random import choice
from django.utils import simplejson
from google.appengine.api import users
from google.appengine.api import channel
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from gaesessions import get_current_session

redCards = ['Ninjas', 'Tree Huggers', 'Ireland', 'Worms', 'Having a Baby', 'X-Rays',
      'Prince Charming', 'Wimbledon', 'Black Velvet', 'Bubble Gum', 'Europe', 
      'United Nations', 'Salvador Dali', 'Supermodels', 'Gila Monsters']

greenCards = ['Nasty', 'Charismatic', 'Naive', 'Shocking', 'Comfortable', 'Insulting']


#cleanupInterval = datetime.timedelta(minutes = 1)

currentGreenCard = ""

#class Game(db.Model):
#  """All the data we store for a game"""
#  userX = db.UserProperty()
#  userO = db.UserProperty()
#  board = db.StringProperty()
#  moveX = db.BooleanProperty()
#  winner = db.StringProperty()
#  winning_board = db.StringProperty()

class Game():
  greenCard = choice(greenCards)
  players = {}

  def getOrCreatePlayer(self, sid):
    if not self.players.has_key(sid):
      self.players[sid] = Player()
    return self.players[sid]
  
  def deletePlayer(self, sid):
    logging.info(self.players)
    del self.players[sid]

  def getNumberOfPlayers(self):
    return len(self.players)

gameObject = Game()

class Player():
  score = 0
  cards = []
  won_cards = []

class GameUpdater():
  game = None

  def __init__(self, game):
    self.game = game

  def get_game_message(self):
    logging.info(self.game.getNumberOfPlayers())
    gameUpdate = {
      'numberOfPlayers': self.game.getNumberOfPlayers()
    }
    return simplejson.dumps(gameUpdate)

  def send_update(self):
    message = self.get_game_message()
    players = self.game.players
    for player in players:
      channel.send_message(player, message)

  def check_win(self):
    if self.game.moveX:
      # O just moved, check for O wins
      wins = Wins().o_wins
      potential_winner = self.game.userO.user_id()
    else:
      # X just moved, check for X wins
      wins = Wins().x_wins
      potential_winner = self.game.userX.user_id()
      
    for win in wins:
      if win.match(self.game.board):
        self.game.winner = potential_winner
        self.game.winning_board = win.pattern
        return

  def make_move(self, position, user):
    if position >= 0 and user == self.game.userX or user == self.game.userO:
      if self.game.moveX == (user == self.game.userX):
        boardList = list(self.game.board)
        if (boardList[position] == ' '):
          boardList[position] = 'X' if self.game.moveX else 'O'
          self.game.board = "".join(boardList)
          self.game.moveX = not self.game.moveX
          self.check_win()
          self.game.put()
          self.send_update()
          return


class GameFromRequest():
  game = None;

  def __init__(self, request):
    user = users.get_current_user()
    game_key = request.get('g')
    if user and game_key:
      self.game = Game.get_by_key_name(game_key)

  def get_game(self):
    return self.game

def render_template(h, file, template_vals):
  path = os.path.join(os.path.dirname(__file__), 'templates', file)
  h.response.out.write(template.render(path, template_vals))

class OpenedPage(webapp.RequestHandler):
  def post(self):
    GameUpdater(gameObject).send_update()

class PlayCard(webapp.RequestHandler):
  def get(self):
    card self.request.get('c')
    session = get_current_session()

class MainHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    session['is_playing'] = True
    logging.info(session)

    d = {}
    d['current_green_card'] = gameObject.greenCard

    player = gameObject.getOrCreatePlayer(session.sid)
    logging.info(player)

    while len(player.cards) < 7:
      player.cards.append(choice(redCards))

    d['score'] = player.score
    d['cards'] = player.cards
    token = channel.create_channel(session.sid)
    d['token'] = token

    render_template(self, "index.html", d)

class UserConnectedHandler(webapp.RequestHandler):
  def post(self):
    logging.info('UserConnectedHandler')
    #client_id = str(self.request.get('from'))

class UserDisconnectedHandler(webapp.RequestHandler):
  def post(self):
    logging.info('UserDisconnectedHandler')
    client_id = str(self.request.get('from'))
    gameObject.deletePlayer(client_id)
    GameUpdater(gameObject).send_update()

application = webapp.WSGIApplication([('/', MainHandler),
                                      ('/opened', OpenedPage),
                                      ('/play_card', PlayCard),
                                      ('/_ah/channel/connected/', UserConnectedHandler),
                                      ('/_ah/channel/disconnected/', UserDisconnectedHandler)])

def main(): run_wsgi_app(application)
if __name__ == '__main__': main()








