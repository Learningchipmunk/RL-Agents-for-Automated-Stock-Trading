# -*- coding: utf-8 -*-
"""PreprocessAndTrainEnv.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1D14vrandwXmNZkUiiuVSyZSt6NEzBg0T
"""


# To parse arguments in command line
import argparse

# fetch data from Yahoo Finance API

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as pltdates
import pickle
import pathlib
import os
import json

from stable_baselines import PPO2
from stable_baselines import A2C
from stable_baselines import DDPG
#from stable_baselines import SAC
#from stable_baselines import TD3
#from stable_baselines.ddpg.policies import DDPGPolicy
from stable_baselines.common.policies import MlpPolicy

import datetime
import time

import tensorflow as tf
tf.logging.set_verbosity(tf.logging.ERROR)

from code.environments import Env_train, Env_valid, Env_trade
from code.data import get_data

"""### Added Results dir"""
def create_dirs(name):
    fig_dir = "Results/" + name + "/Figures/"
    csv_dir = "Results/" + name + "/CSVs/"
    if not os.path.exists(fig_dir):
       os.makedirs(fig_dir)
    if not os.path.exists(csv_dir):
           os.makedirs(csv_dir)

    return fig_dir, csv_dir


"""### Added a parser"""
def parse_args():
    '''Parses arguments in command line.
    E.g. python preprocessandtrainenv.py --ConfigName=auteurs

    Returns:
        object: contains the values of the parsed arguments
    '''
    # Executing with --cfg = path
    parser = argparse.ArgumentParser(description='Running model on the configuration file.')
    
    parser.add_argument('--ConfigName', metavar='-cn', type=str, default='auteurs',
                        help='Indicates the name of the config file you wish to use, defaults to `auteurs`.')

    # Reads the arguments the user wrote on the command line:
    options = parser.parse_args()

    return options

"""Creates csvs"""
def create_csv(data, path, name):
    df = pd.DataFrame.from_dict(data)
    df.to_csv(path + name + ".csv", index=False)
    return df

"""### Added all agents specified in the paper"""

def get_agent(agent_name):
    if agent_name == 'A2C': return A2C
    if agent_name == 'DDPG': return DDPG
    if agent_name == 'PPO': return PPO2

def initialize_agent(agent_name, env):
    agent = get_agent(agent_name)
    model = agent('MlpPolicy', env)
    return model

def train_agent(model, model_name, timesteps):
    start = time.time()
    model.learn(total_timesteps=timesteps)
    #model.save(f"{config.TRAINED_MODEL_DIR}/{model_name}")
    end = time.time()    
    return model

def DRL_validation(model, unique_date, test_env, test_obs):
    """make a prediction"""
    start = time.time()
    for i in range(len(unique_date)):
        action, _states = model.predict(test_obs)
        test_obs, rewards, dones, info = test_env.step(action)
    end = time.time()


def DRL_prediction(model, name, last_state, unique_date, env_trade):
    ### make a prediction based on trained model###
    obs_trade = env_trade.reset()

    for i in range(len(unique_date)):
        action, _states = model.predict(obs_trade)
        obs_trade, rewards, dones, info = env_trade.step(action)
        if i == (len(unique_date) - 1):
            last_state = env_trade.render()

    # df_last_state = pd.DataFrame({'last_state': last_state})
    # df_last_state.to_csv('results/last_state_{}_{}.csv'.format(name, i), index=False)
    return last_state

"""### Added ensemble strat"""

def plot_graph(dates, data, title="This is a cute graph", path="figures/", save=False):
    plt.figure(figsize=(16, 8))
    for key, values in data.items():
        if 'date' not in key.lower():
            plt.plot(dates, values, label=key)
    plt.title(title)
    plt.legend()
    plt.xticks(rotation=45, ha="right")
    
    if save:
        plt.savefig(path+title+'.png')
    else:
        plt.show()
    plt.close()

def data_split(df, start, end, is_last=False):
    """
    split the dataset into training or testing using date
    :param data: (df) pandas dataframe, start, end, is_last
    :return: (df) pandas dataframe
    """
    data = df[(start <= df.date) & (df.date <= end)] if is_last else df[(start <= df.date) & (df.date < end)]
    data = data.sort_values(['date'], ignore_index=True)
    data.index = data.date.factorize()[0]
    return data

def get_date(string):
    aaaa, mm, dd = [int(i) for i in string.split('/')]
    return datetime.datetime(aaaa, mm, dd)

### Added Simple Baseline
def buy_and_hold(data, initial_balance, transac_fee):
    money_available = initial_balance/len(data.close.iloc[0])
    qty = (money_available // (np.array(data.close.iloc[0]) * (1+transac_fee))).astype('int32')

    portfolio_value = np.array([])
    for i in range(len(data.date.unique())):
        value = np.dot(qty, data.close.iloc[i])
        portfolio_value = np.append(portfolio_value, value)

    return portfolio_value

def run_ensemble_strategy(config_name):
    '''Ensemble Strategy that combines PPO, A2C and DDPG

    Args:
        config_name (str): The name of the config file we need to load

    Returns:
        (dict, dict): Returns two dicts. `cumulative_returns` stores the results for each agent, 
                      `model_used` stores the choices made by the ensemble strategy.
    '''
    config = json.load(open('configs/'+config_name+'.json', 'r'))

    # rebalance_window is the number of months to retrain the model
    rebalance_window = config["rebalance_window"]
    dates = [get_date(config[date]) for date in ["date_start_train", "date_start_validation", "date_start_trade", "date_end"]]
    turbulence_threshold = config["turbulence_threshold"]
    
    amount_tickers, df = get_data(config["data_name"])
    config["amount_tickers"] = amount_tickers

    print("============Start Ensemble Strategy============")
    # for ensemble model, it's necessary to feed the last state
    # of the previous model to the current model as the initial state
    last_state_ensemble = []

    # Regrouping data by date
    df = df.groupby('date').agg({'close': list, 'macd': list, 'rsi_30': list, 'cci_30': list, 'dx_30': list, 'turbulence': 'max'})
    df.reset_index(level=0, inplace=True)
    
    ### ======================= Splitting data between train, val and test ======================= ###
    ## We then proceed to split the dataset:
    d1, d2, d3, d4 = dates

    # Train
    train = data_split(df, d1, d2)
    unique_train_date = train.date.unique()

    # Validation
    valid = data_split(df, d2, d3)
    unique_valid_date = valid.date.unique()

    # Trade
    trade = data_split(df, d3, d4, is_last=True)#timedelta(2) because of split does not take last date
    unique_trade_date = trade.date.unique()

    ### ======================= Initialize agents and their environments ======================= ###
    agent_names   = ['A2C', 'PPO', 'DDPG']    

    # Train
    training_envs = [Env_train(train, config) for name in agent_names]
    models        = []
    for env, name in zip(training_envs, agent_names):
        model = initialize_agent(name, env)
        models.append(model)

    # Validation
    valid_envs = [Env_valid(valid, config, turbulence_threshold=turbulence_threshold) for name in agent_names]

    ### =======================        Training and Validation Phase     ======================= ###
    model_names = ['A2C_dow', 'PPO_dow', 'DDPG_dow']
    timesteps   = config["timesteps"]
    sharpes     = []

    print("======Training has started from: ", d1, "to ", d2)
    for model, model_name, training_env, valid_env, timestep in zip(models, model_names, training_envs, valid_envs, timesteps):
        training_env.reset()
        obs_val = valid_env.reset()

        # Training agent
        t1 = time.time()
        model = train_agent(model, model_name, timestep) 
        t2 = time.time()

        # Evaluates the model on validation to get its respective sharpe ratio
        DRL_validation(model=model, unique_date=unique_valid_date, test_env=valid_env, test_obs=obs_val)
        sharpe = valid_env.sharpe
        sharpes.append(sharpe) 

        print("   ", model_name + " Sharpe Ratio: ", sharpe, "Training Time: %.3fs"%(t2-t1))
    print("============Training Done============")

    ### =======================               Trading Phase              ======================= ###
    print("============Trading has started from:", unique_trade_date[0], "to", unique_trade_date[-1])
    model_ensemble         = None
    last_state_ensemble    = [] # We started trading, therefore the last state is empty (It will be initialized in trade_env)
    portfolio_value_memory = np.array([]) #Remembers the portfolio's value for ensemble strategy, useful to compute cumulative return
    cash_memory            = np.array([]) #Remembers the portfolio's cash for ensemble strategy.
    model_used             = {key:[] for key in ['A2C', 'PPO', 'DDPG']}
    model_used             = {"Trading Quarter": [], **model_used, "Used": []}
    for iter_num in range(0, len(unique_trade_date), rebalance_window):
        ## Choosing best model
        sharpe_a2c, sharpe_ppo, sharpe_ddpg = sharpes
        model_a2c, model_ppo, model_ddpg    = models

        # Model Selection based on sharpe ratio
        if (sharpe_ppo >= sharpe_a2c) & (sharpe_ppo >= sharpe_ddpg):
            model_ensemble = model_ppo
            model_used['Used'].append('PPO')
        elif sharpe_a2c >= sharpe_ddpg:
            model_ensemble = model_a2c
            model_used['Used'].append('A2C')
        else:
            model_ensemble = model_ddpg
            model_used['Used'].append('DDPG')

        # Adds sharpe ratio to dict
        model_used['PPO'].append(sharpe_ppo)
        model_used['A2C'].append(sharpe_a2c)
        model_used['DDPG'].append(sharpe_ddpg)
        
        ## Trading with the chosen model
        start_date, end_date = unique_trade_date[iter_num], unique_trade_date[min(iter_num + rebalance_window, len(unique_trade_date)-1)]
        is_last              = end_date == unique_trade_date[-1]
        trade_i              = data_split(df, start=start_date, end=end_date, is_last=is_last)
        trade_env            = Env_trade(trade_i, config, initial=False, previous_state=last_state_ensemble, turbulence_threshold=turbulence_threshold)
        last_state_ensemble  = DRL_prediction(model=model_ensemble, 
                                              name="ensemble", 
                                              last_state=last_state_ensemble, 
                                              unique_date=trade_i.date.unique(), 
                                              env_trade=trade_env)
        portfolio_value_memory = np.append(portfolio_value_memory, np.array(trade_env.asset_memory))
        cash_memory            = np.append(cash_memory, np.array(trade_env.cash_memory))

        # Storing trading quarter:
        model_used["Trading Quarter"].append(pd.to_datetime(str(start_date)).strftime("%Y/%m/%d")+"-"+pd.to_datetime(str(end_date)).strftime("%Y/%m/%d"))
        
        ## Running all three models on same timeframe in order to chose the next ensemble model
        # Initializing trade env for each nodel with 3 month worth of data
        valid_envs_i = [Env_valid(trade_i, config, turbulence_threshold=turbulence_threshold) for name in model_names]
        sharpes      = []
        for model, model_name, valid_env in zip(models, model_names, valid_envs_i):
            obs_val = valid_env.reset()

            DRL_validation(model=model, unique_date=trade_i.date.unique(), test_env=valid_env, test_obs=obs_val)
            sharpe = valid_env.sharpe

            sharpes.append(sharpe) 


    ## Computing cumulative reward of ensemble strategy in the time frame d3 to d4
    initial_value          = config['initial_balance']
    portfolio_value_memory = portfolio_value_memory.reshape(-1)
    cumulative_return      = (portfolio_value_memory - initial_value) / initial_value

    ### Trading with only one method at a time:
    trading_envs       = [Env_trade(trade, config, turbulence_threshold=turbulence_threshold) for name in agent_names]
    cumulative_returns = {key.split("_")[0]:[] for key in model_names}
    cumulative_returns = {"Dates": unique_trade_date, **cumulative_returns, "Ensemble": cumulative_return}
    cash_memories      = {key.split("_")[0]:[] for key in model_names}
    cash_memories      = {"Dates": unique_trade_date, **cash_memories, "Ensemble": cash_memory}
    portfolio_memories = {key.split("_")[0]:[] for key in model_names}
    for model, model_name, test_env in zip(models, model_names, trading_envs):
        obs_val    = valid_env.reset()
        model_name = model_name.split("_")[0]

        DRL_prediction(model=model, name=model_name, unique_date=unique_trade_date, last_state=[], env_trade=test_env)
        cumulative_returns[model_name] = (np.array(test_env.asset_memory) - initial_value) / initial_value
        cash_memories[model_name]      = test_env.cash_memory
        portfolio_memories[model_name] = test_env.portfolio_memory

    ### Adding naive portfolio allocation
    cumulative_return_naive = buy_and_hold(data=trade, initial_balance=initial_value, transac_fee=config['transac_fee'])
    cumulative_return_naive = (cumulative_return_naive - initial_value) / initial_value
    cumulative_returns      = {**cumulative_returns, "Naive allocation": cumulative_return_naive}

    print("============Trading Done")

    return cumulative_returns, cash_memories, model_used, portfolio_memories



"""Executing Ensemble Strategy and saving the results."""
if __name__ == "__main__":
    ## Parse args
    options = parse_args()
    config_name = options.ConfigName

    ## Create directories for experiment
    fig_dir, csv_dir = create_dirs(config_name)

    ## Ensemble Strategy
    start = time.time()    
    cumulative_returns, cash_memories, model_used, portfolio_memories = run_ensemble_strategy(config_name)
    print("Total computation time:", time.time()-start)

    ## Generate results
    create_csv(cumulative_returns, csv_dir, "Cumulative return for all strategies")
    create_csv(cash_memories, csv_dir, "Cash held for all four agents")
    create_csv(model_used, csv_dir, "Sharpe Ratios and Model Used for each Window")
    plot_graph(cumulative_returns['Dates'], cumulative_returns, title="Cumulative Return with Transaction cost", path=fig_dir, save=True)
    plot_graph(cash_memories['Dates'], cash_memories, title="Cash Held", path=fig_dir, save=True)
    for model_name, portfolio in portfolio_memories.items():
        df = pd.DataFrame(portfolio)
        df.to_csv(csv_dir + model_name + "_trade_portfolio.csv", index=False)