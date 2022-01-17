from code.Environment import Env
import numpy as np
import pandas as pd

class Env_train(Env):
    def __init__(self, df, config, start_day=0):
        super().__init__(df, start_day, config)

    def terminalStep(self):
        df_total_value = pd.DataFrame(self.asset_memory)
        df_total_value.columns = ['account_value']
        df_total_value['daily_return']=df_total_value.pct_change(1)
        sharpe = (252**0.5)*df_total_value['daily_return'].mean()/df_total_value['daily_return'].std()
        self.sharpe = sharpe
        
        return self.state, self.reward, self.terminal, {"sharpe": sharpe, "total_assets": self.calculate_assets()}

class Env_valid(Env):
    def __init__(self, df, config, start_day=0, turbulence_threshold=140, iteration=''):
        super().__init__(df, start_day, config)

        self.turbulence_threshold = turbulence_threshold
        self.turbulence = 0        
        self.iteration=iteration

    def run_trades(self, actions):
        if self.turbulence >= self.turbulence_threshold:
            actions = -1*np.array(self.state[1 : self.dimension_stock+1])
        self.turbulence = self.df['turbulence'].iloc[self.day]

        super().run_trades(actions)

    def terminalStep(self):
        df_total_value = pd.DataFrame(self.asset_memory)
        df_total_value.columns = ['account_value']
        df_total_value['daily_return']=df_total_value.pct_change(1)
        sharpe = (4**0.5)*df_total_value['daily_return'].mean()/df_total_value['daily_return'].std()
        self.sharpe = sharpe
        
        return self.state, self.reward, self.terminal, {"sharpe": sharpe, "total_assets": self.calculate_assets()}

    def reset(self):
        self.turbulence = 0
        return super().reset()

class Env_trade(Env):
    def __init__(self, df, config, start_day=0, turbulence_threshold=140, iteration='', initial=True, previous_state=[], model_name=''):
        super().__init__(df, start_day, config)

        self.turbulence_threshold = turbulence_threshold
        self.turbulence = 0
        self.iteration = iteration
        self.model_name = model_name
        self.initial = initial
        self.previous_state = previous_state

    def run_trades(self, actions):
        if self.turbulence >= self.turbulence_threshold:
            actions = -1*np.array(self.state[1 : self.dimension_stock+1])
        self.turbulence = self.df['turbulence'].values[self.day]

        super().run_trades(actions)

    def terminalStep(self): #step, terminal: plot self.asset_memory
        df_total_value = pd.DataFrame(self.asset_memory)
        df_total_value.columns = ['account_value']
        df_total_value['daily_return']=df_total_value.pct_change(1)
        sharpe = (4**0.5)*df_total_value['daily_return'].mean()/df_total_value['daily_return'].std()
        self.sharpe = sharpe
        
        return self.state, self.reward, self.terminal, {"sharpe": sharpe, "total_assets": self.calculate_assets()}

    def reset(self):
        if self.initial or len(self.previous_state)==0:
            self.turbulence = 0
            return super().reset()

        self.turbulence = 0
        previous_total_asset = self.previous_state[0] + \
            sum([self.previous_state[1+i] * self.previous_state[1+i+self.dimension_stock] for i in range(self.dimension_stock)])
        self.asset_memory = [previous_total_asset]
        self.day = self.initial_day
        self.cost = 0
        self.trades = 0
        self.terminal = False 
        self.rewards_memory = []
        self.state = self.previous_state[:self.dimension_stock+1] + list(self.df.close.iloc[self.day]) + self.ConcatMacdRsiCciAdx(self.day)

        return self.state
