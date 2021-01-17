import json
import logging
import yaml
import pandas as pd
import io
import requests

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter


with open("/users/robrogers/usr/local/facebook/config.yaml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

if str(cfg['logging']) == 'console':
    logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s', level=logging.DEBUG)

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("{0}/{1}.log".format('/users/robrogers/usr/local/facebook', 'post_stats'))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

def read_data(url, index):
    logging.debug('Getting data from ' + url)
    s = requests.get(url).content
    c = pd.read_csv(io.StringIO(s.decode('utf-8')), index_col=index)

    return c

nyt_live_url = 'https://github.com/nytimes/covid-19-data/raw/master/live/us-counties.csv'
nyt_h_url = 'https://github.com/nytimes/covid-19-data/raw/master/us-counties.csv'

states = ['Arkansas', 'Louisiana']
counties = ['Union', 'Columbia', 'Ouachita', 'Calhoun', 'Bradley']
states_counties = {'Arkansas': ['Union', 'Columbia', 'Ouachita', 'Calhoun', 'Bradley'], 'Louisiana': ['Union']}

live_df = read_data(nyt_live_url, None)
live_df = live_df[live_df.state.isin(states)]
live_df = live_df[live_df.county.isin(counties)]
live_df = live_df[['date', 'county', 'state', 'fips', 'cases', 'deaths']]
live_df['date'] = pd.to_datetime(live_df['date'])

historical_df = read_data(nyt_h_url, None)
historical_df = historical_df[historical_df.state.isin(states)]
historical_df = historical_df[historical_df.county.isin(counties)]
historical_df['date'] = pd.to_datetime(historical_df['date'])

merged_df = pd.concat([live_df, historical_df])

frames = []
for state, county_list in states_counties.items():
    for county in county_list:
        logging.info(state + " " + county)
        county_df = merged_df[(merged_df.state == state) & (merged_df.county == county)]
        county_df.sort_values(by=['date'], inplace=True, ascending=False)
        county_df['New_Cases_Today'] = county_df['cases'] - county_df['cases'].shift(-1).fillna(0)
        county_df['New_Deaths_Today'] = county_df['deaths'] - county_df['deaths'].shift(-1).fillna(0)
        print (county_df.head(10))
        frames.append(county_df)

merged_df = pd.concat(frames)
merged_df.sort_values(by=['date'], inplace=True, ascending=False)
print (merged_df.head(20))

merged_df.to_csv('nyt_filtered.csv', index=False)
