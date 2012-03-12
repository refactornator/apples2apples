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
      'United Nations', 'Salvador Dali', 'Supermodels', 'Gila Monsters', 'Lollipops',
      'Pigs', 'Eleanor Roosevelt', 'The Cold War', 'Brad Pitt', 'Soy Sauce', 'Swiss Cheese',
      'My Family', 'A Nine Iron', 'Bad Dogs', 'Skiing', 'Hillary Rodham Clinton', 'Bill Gates',
      'Rednecks', 'Global Warming', 'My Personality', 'Going to the Dentist', 'Oral Surgery',
      'Pit Bulls', 'Body Odor', 'Sports Channels', 'Lemons', 'Boyfriends', 'Snakes', 'Glaciers',
      'Parenting', 'The 1960s', 'A Crawl Space', 'Dr. Kevorkian', 'Mahatma Gandhi', 'Porsche Boxter',
      'Science Fair Projects', 'Crazy Horse', 'Hollywood', 'Lenin\'s Tomb', 'The Green Bay Packers',
      'Leeches', 'A Morgue', 'Waterbeds', 'Cleaning the Bathroom', 'The IRS', 'Thomas Edison',
      'Nuclear Power Plants', 'State Fairs', 'The Far Right', 'Root Beer Floats', 'The Statue of Liberty',
      'Cleopatra', 'Electric Eels', 'Baking Cookies', 'Elvis Presley', 'The Pentagon', 'Jacques Cousteau',
      'Baby Showers', 'A Locker Room', 'Cigarette Burns', 'Beauty and the Beast', 'John F. Kennedy',
      'Paying Taxes', 'Lawyers', 'The Milky Way', 'The Dallas Cowboys', 'Crystal Balls', 'Gold Chains',
      'Keanu Reeves', 'Socks', 'Napoleon Bonaparte', 'Alfred Hitchcock', 'Bankruptcy', 'A Sunset']

greenCards = ['Nasty', 'Charismatic', 'Naive', 'Shocking', 'Comfortable', 'Insulting', 'Rare', 'Friendly',
              'Spunky', 'Classic', 'Swift', 'Dreamy', 'Bright', 'Unforgettable', 'Senseless', 'Intense',
              'Bold', 'Manly', 'Clueless', 'Ordinary', 'Relaxing', 'Silly', 'Ancient', 'Innocent', 'Snappy',
              'Shiny', 'Healthy', 'Luscious', 'Arrogant', 'Frazzled', 'Distinguished', 'Complicated',
              'Melodramatic', 'Cosmopolitan', 'Adorable', 'Rich', 'Principled', 'Animated', 'Corrupt',
              'Boisterous', 'Horrifying', 'Risky', 'Chewy', 'Miserable', 'Misunderstood', 'Explosive',
              'Luxurious', 'Heartless', 'Handsome', 'Lazy', 'Glitzy', 'Comical', 'Cool', 'European',
              'Loud', 'Crazed', 'Dramatic', 'Selfish', 'Cheesy', 'Spiritual', 'Cute', 'Believable',
              'Normal', 'Bogus']

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
  cardsInPlay = []
  players = {}
  judges = []
  discardPile = []
  greenDiscardPile = []

  def getOrCreatePlayer(self, sid):
    if not self.players.has_key(sid):
      self.players[sid] = Player()
      self.players[sid].cards = []
      while len(self.players[sid].cards) < 7:
        newCard = choice(redCards)
        if newCard not in self.discardPile:
          self.players[sid].cards.append(newCard)
          self.discardPile.append(newCard)
    if len(self.players) == 1:
      self.players[sid].judge = True
      self.judges.append(sid)
    return self.players[sid]
  
  def deletePlayer(self, sid):
    del self.players[sid]

  def getNumberOfPlayers(self):
    counter = 0
    for sid in self.players:
      if self.players[sid].judge is not True:
        counter += 1
    return counter

  def getCardsPlayed(self):
    cardCount = 0
    for player in self.players:
      if self.players[player].played_card != '':
        cardCount += 1
    return cardCount

  def getPlayer(self, sid):
    return self.players[sid]

  def getPlayerScore(self, sid):
    return self.players[sid].score

  def pickWinner(self, card):
    self.cardsInPlay = []
    self.greenDiscardPile.append(self.greenCard)
    judged = False
    for sid in self.players:
      if self.players[sid].judge == True:
        self.players[sid].judge = False
      else:
        player = self.players[sid]
        if sid not in self.judges and not judged:
          player.judge = True
          self.judges.append(sid)
          judged = True
        if player.played_card == card:
          player.score += 1
          player.won_cards.append(player.played_card)

        player.cards.remove(player.played_card)
        while len(player.cards) < 7:
          player.cards.append(choice(redCards))
        player.played_card = ''
    self.greenCard = choice(greenCards)
  
  def play_card(self, sid, card):
    self.cardsInPlay.append(card)
    self.players[sid].played_card = card

gameObject = Game()

class Player():
  score = 0
  cards = []
  won_cards = []
  played_card = ''
  judge = False

class GameUpdater():
  game = None

  def __init__(self, game):
    self.game = game

  def get_game_message(self, sid):
    player = self.game.getPlayer(sid)
    gameUpdate = {
      'greenCard': self.game.greenCard,
      'cardsPlayed': self.game.getCardsPlayed(),
      'numberOfPlayers': self.game.getNumberOfPlayers(),
      'score': player.score,
      'judge': player.judge
    }

    if player.judge == True:
      gameUpdate['cards'] = self.game.cardsInPlay
    else:
      gameUpdate['cards'] = player.cards
    return simplejson.dumps(gameUpdate)

  def send_update(self):
    for player in self.game.players:
      message = self.get_game_message(player)
      channel.send_message(player, message)


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
  def post(self):
    card = self.request.get('c')
    session = get_current_session()
    gameObject.play_card(session.sid, card)
    GameUpdater(gameObject).send_update()

class PickWinner(webapp.RequestHandler):
  def post(self):
    card = self.request.get('c')
    gameObject.pickWinner(card)
    GameUpdater(gameObject).send_update()

class MainHandler(webapp.RequestHandler):
  def get(self):
    session = get_current_session()
    session['is_playing'] = True

    player = gameObject.getOrCreatePlayer(session.sid)

    d = {}
    d['score'] = player.score
    d['cards'] = player.cards
    d['token'] = channel.create_channel(session.sid)
    d['current_green_card'] = gameObject.greenCard

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
                                      ('/pick_winner', PickWinner),
                                      ('/_ah/channel/connected/', UserConnectedHandler),
                                      ('/_ah/channel/disconnected/', UserDisconnectedHandler)])

def main(): run_wsgi_app(application)
if __name__ == '__main__': main()








