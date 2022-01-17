import pandas as pd
import numpy as np
import copy
from os.path import isfile
from stockstats import StockDataFrame as Sdf
from finrl.finrl_meta.preprocessor.yahoodownloader import YahooDownloader
from finrl.finrl_meta.finrl_meta_config import DOW_30_TICKER, NAS_100_TICKER, SP_500_TICKER, FAANG_TICKER


def addTurbulence(data):
    DataWithTurbulence = copy.deepcopy(data)

    PivotPrice = copy.copy(data).pivot(index="date", columns="tic", values="close").pct_change()
    DataUnic = copy.copy(data).date.unique()
    DataTurb = [0] * 252
    count = 0
    for date_id in range(252, len(DataUnic)):

        PriceCurrent = PivotPrice[PivotPrice.index == DataUnic[date_id]]
        PriceHist = PivotPrice[ (PivotPrice.index < DataUnic[date_id]) & (PivotPrice.index >= DataUnic[date_id - 252]) ]
        HistPriceFilt = PriceHist.iloc[PriceHist.isna().sum().min() : ].dropna(axis=1)
        TMP = (PriceCurrent[[x for x in HistPriceFilt]] - np.mean(HistPriceFilt, axis=0)).values.dot\
        (np.linalg.pinv(HistPriceFilt.cov())).dot((PriceCurrent[[x for x in HistPriceFilt]] - np.mean(HistPriceFilt, axis=0)).values.T)
        
        if TMP > 0:
            count += 1
            Turbtmp = TMP[0][0] if count > 2 else 0
        else:
            Turbtmp = 0
        
        DataTurb.append(Turbtmp)

    DataTurb = pd.DataFrame({"date": PivotPrice.index, "turbulence": DataTurb})
    DataWithTurbulence = DataWithTurbulence.merge(DataTurb, on="date")
    DataWithTurbulence = DataWithTurbulence.sort_values(["date", "tic"]).reset_index(drop=True)

    return DataWithTurbulence

def dataWithTechIndicators(df):
    """
    Args: data df
    Returns: data df with technical indicators
    """
    data = copy.deepcopy(df).sort_values(["tic", "date"])
    stock = Sdf.retype(copy.copy(data))

    for indic in ['macd', 'rsi_30', 'cci_30', 'dx_30']:
        indic_data = pd.DataFrame()
        for tic_id in range(len(stock.tic.unique())):
                indic_tmp = pd.DataFrame(stock[stock.tic == stock.tic.unique()[tic_id]][indic])
                indic_tmp["tic"], indic_tmp["date"] = stock.tic.unique()[tic_id], list(data[data.tic == stock.tic.unique()[tic_id]]["date"])
                indic_data = indic_data.append(indic_tmp, ignore_index=True)

        data = data.merge(indic_data[["tic", "date", indic]], on=["tic", "date"], how="left")
    data.sort_values(["date", "tic"], inplace=True)
    return data

def preProcess(data):
    ProcessedData = dataWithTechIndicators(data)

    ProcessedData = addTurbulence(ProcessedData)

    ProcessedData.fillna(method='ffill', inplace=True)
    ProcessedData.fillna(method='bfill', inplace=True)
    return ProcessedData

def get_stocks(data_name):
    # test tickers with https://query2.finance.yahoo.com/v1/finance/search?q=eth
    ticker_lists = {
        'dow_30': DOW_30_TICKER,
        'nas_100': NAS_100_TICKER,
        'sp_500': SP_500_TICKER,
        'faang': FAANG_TICKER,
        'crypto': ['btc-usd', 'ltc-usd'],#, 'eth-usd', 'bch-usd'],
        'memes': ['eth-btc', 'ltc-btc', 'bch-btc', 'doge-btc', 'shib-btc', 'uni3-btc']
    }
    if data_name in ticker_lists.keys(): return ticker_lists[data_name]

def get_data(data_name, force_reload=False):
    if isfile('./data/'+data_name+'.csv') and not force_reload:
        data = pd.read_csv('data/'+data_name+'.csv')
    else:
        data = YahooDownloader(start_date = '2009-01-01', end_date = '2021-11-01', ticker_list = get_stocks(data_name)).fetch_data()
        data = preProcess(data)    
        data.to_csv('data/'+data_name+'.csv', index=False)
    
    data['date'] = pd.to_datetime(data['date'])
    return len(get_stocks(data_name)), data
