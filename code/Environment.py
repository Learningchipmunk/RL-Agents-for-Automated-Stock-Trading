import gym
from gym.utils import seeding
from gym import spaces
import numpy as np

class Env(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, df, start_day, config):
        self.shares_per_trade = config["shares_per_trade"]
        self.initial_balance = config["initial_balance"]
        self.dimension_stock = config["amount_tickers"]
        self.transac_fee = config["transac_fee"]
        self.reward_scaling = config["reward_scaling"]

        self.initial_day = start_day
        self.day = start_day
        self.df = df
        self.action_space = spaces.Box(low = -1, high = 1,shape = (self.dimension_stock,))
        self.terminal = False

        self.state = [self.initial_balance] + [0]*self.dimension_stock + list(self.df.close.iloc[self.day]) + self.ConcatMacdRsiCciAdx(self.day)
        self.observation_space = spaces.Box(low=0, high=np.inf, shape = (len(self.state),))
        self.reward = 0
        self.cost = 0
        self.asset_memory = [self.initial_balance] # Memorizes the portfolio's value at each step for cumulative return 
        self.cash_memory  = [self.initial_balance] # Memorizes the portfolio's cash at each step
        self.portfolio_memory = [[0]*self.dimension_stock] # Memorize portfolio composition at every step
        self.rewards_memory = []
        self.trades = 0
        self.sharpe = 0
        self._seed()

    def ConcatMacdRsiCciAdx(self, i):
        return sum([list(self.df[tech].iloc[i]) for tech in ['macd', 'rsi_30', 'cci_30', 'dx_30']], [], )

    def calculate_assets(self):
        return self.state[0] + sum([self.state[1+i] * self.state[1+i+self.dimension_stock] for i in range(self.dimension_stock)])

    def sell_batch(self, actions):
        shares = np.array(self.state[1 : self.dimension_stock+1])
        prices = np.array(self.state[self.dimension_stock+1 : self.dimension_stock*2+1])
        actions = np.where(actions<0, -actions, 0)
        qty = np.minimum(actions, shares).astype('int32')

        self.state[0] += np.sum(prices * qty * (1 - self.transac_fee))
        for i, q in enumerate(qty):
            self.state[i+1] -= q
        self.cost += prices * qty * self.transac_fee
        self.trades += 1

    def buy_stock(self, index, action):
        price = self.state[index+self.dimension_stock+1]
        qty = int(min(action, self.state[0] // (price * (1+self.transac_fee))))
        self.state[index + 1] += qty
        self.state[0] -= (1 + self.transac_fee) * price * qty
        self.cost += self.transac_fee * price * qty
        self.trades += 1
        
    def run_trades(self, actions):
        actions = actions * self.shares_per_trade
        self.sell_batch(actions)
        
        ### Consider weighing with price or taking smallest first
        actions_sorted = np.argsort(actions)
        for idx in actions_sorted[::-1][:(actions>0).sum()]: 
            self.buy_stock(idx, actions[idx])

    def terminalStep(self):
        return self.state, self.reward, self.terminal, {"total_assets":self.calculate_assets()}

    def step(self, actions):
        self.terminal = self.day >= len(self.df.index.unique())-1


        if self.terminal:
            return self.terminalStep()

        begin_total_asset = self.calculate_assets()
        self.run_trades(actions)

        self.day += 1
        self.state =  self.state[:self.dimension_stock+1] + list(self.df.close.iloc[self.day]) + self.ConcatMacdRsiCciAdx(self.day)

        end_total_asset = self.calculate_assets()
        self.asset_memory.append(end_total_asset)
        self.cash_memory.append(self.state[0])
        self.portfolio_memory.append(self.state[1:self.dimension_stock+1])
        self.reward = end_total_asset - begin_total_asset            
        self.rewards_memory.append(self.reward)
        self.reward = self.reward*self.reward_scaling


        return self.state, self.reward, self.terminal, {}

    def reset(self):
        self.asset_memory = [self.initial_balance]
        self.cash_memory  = [self.initial_balance]
        self.portfolio_memory = [[0]*self.dimension_stock]
        self.day = self.initial_day
        self.cost = 0
        self.trades = 0
        self.terminal = False
        self.rewards_memory = []
        self.state = [self.initial_balance] + [0]*self.dimension_stock + list(self.df.close.iloc[self.day]) + self.ConcatMacdRsiCciAdx(self.day)
        return self.state
    
    def render(self, mode='human', close=False):
        return self.state

    def _seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]