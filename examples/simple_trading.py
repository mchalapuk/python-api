from quedex_api import (
  Exchange,
  MarketStream,
  MarketStreamListener,
  MarketStreamClientFactory,
  Trader,
  UserStream,
  UserStreamListener,
  UserStreamClientFactory,
)

from twisted.internet import reactor, ssl
from autobahn.twisted.websocket import connectWS
quedex_public_key = open("keys/quedex-public-key.asc", "r").read()
exchange = Exchange(quedex_public_key, 'wss://api.quedex.net')

trader_private_key = open("keys/trader-private-key.asc", "r").read()
trader = Trader('83745263748', trader_private_key)
trader.decrypt_private_key('aaa')
user_stream = UserStream(exchange, trader)
market_stream = MarketStream(exchange)
selected_futures_id = None
sell_threshold = 10000
order_id = 0

def get_order_id():
  global order_id
  order_id += 1
  return order_id

class SimpleMarketListener(MarketStreamListener):
  def on_instrument_data(self, instrument_data):
    global selected_futures_id
    futures = [instrument for instrument in instrument_data['data'].values() if instrument['type'] == 'futures'][0]
    selected_futures_id = futures['instrument_id']

  def on_order_book(self, order_book):
    if order_book['instrument_id'] != selected_futures_id:
      return
    bids = order_book['bids']
    # if there are any buy orders and best price is MARKET or above threshold
    if bids and (not bids[0][0] or float(bids[0][0]) > sell_threshold):
      user_stream.place_order({
        'instrument_id': selected_futures_id,
        'client_order_id':  get_order_id(),
        'side': 'sell',
        'quantity': 1000,
        'limit_price': bids[0][0],
        'order_type': 'limit',
      })
market_stream.add_listener(SimpleMarketListener())
open_positions = {}
balance_threshold = 3.1415927

class SimpleUserListener(UserStreamListener):
  def on_open_position(self, open_position):
    open_positions[open_position['instrument_id']] = open_position

  def on_account_state(self, account_state):
    if float(account_state['balance']) < balance_threshold:
       # panic
       orders = []
       for open_position in open_positions.values():
        order_side = 'buy' if open_position['side'] == 'short' else 'sell'
        orders.append({
          'type': 'place_order',
          'instrument_id': open_position['instrument_id'],
          'client_order_id':  get_order_id(),
          'side': order_side,
          'quantity': open_position['quantity'],
          # pretend "market" order
          'limit_price': '0.01' if order_side == 'sell' else '1000000',
          'order_type': 'limit',
        })
        # use batch whenever a number of orders is placed at once
        user_stream.batch(orders)
user_stream.add_listener(SimpleUserListener())
class ReadyStateUserListener(UserStreamListener):
  def on_ready(self):
    connectWS(MarketStreamClientFactory(market_stream), ssl.ClientContextFactory())
user_stream.add_listener(ReadyStateUserListener())

connectWS(UserStreamClientFactory(user_stream), ssl.ClientContextFactory())
reactor.run()
