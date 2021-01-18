import json
import logging
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import io
import requests
from facebook import GraphAPI
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

with open("./config.yaml", 'r') as ymlfile:
    cfg = yaml.load(ymlfile, Loader=yaml.FullLoader)

if str(cfg['logging']) == 'console':
    logging.basicConfig(format='%(levelname)s:%(asctime)s %(message)s', level=logging.DEBUG)

logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
rootLogger = logging.getLogger()

fileHandler = logging.FileHandler("{0}/{1}.log".format('./', 'post_stats'))
fileHandler.setFormatter(logFormatter)
rootLogger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(logFormatter)
rootLogger.addHandler(consoleHandler)

now = datetime.now()

test_mode = cfg['test_mode']
post = cfg['post_to_facebook']
email = cfg['send_email']
group = cfg['test_group_uid']
if not test_mode:
    group = cfg['group_uid']

urls = cfg['urls']
master_url = urls['ar_covid']
rt_url = urls['rt']

gen_bullet = cfg['generate_bullet']
gen_line = cfg['generate_line']
gen_graph = cfg['generate_xkcd_graph']
gen_state_map = cfg['generate_state_map']
gen_regional_map = cfg['generate_regional_map']

latest_index = cfg['ar_covid_latest_index']
new_data = False
post_negative_results = cfg['post_negative_results']

counties = cfg['counties']
p_county = cfg['primary_county']

c = requests.get(urls['county_geojson'])
county_boundaries = c.json()

def read_creds(filename):
    '''
    Store API credentials in a safe place.
    If you use Git, make sure to add the file to .gitignore
    '''
    with open(filename) as f:
        credentials = json.load(f)
    return credentials

def read_data(url, index):
    logging.debug('Getting data from ' + url)
    s = requests.get(url).content
    c = pd.read_csv(io.StringIO(s.decode('utf-8')), index_col=index, dtype={"fips": str})

    return c

def generate_line(df):
    df = df[df['mydate'] > '2020-09-12']
    fig = px.line(df, x='mydate', y='14d_pp',
              color="county_nam",
              line_group="county_nam",
              hover_name="county_nam",
              labels={
                  "14d_pp": "Positivity Rate",
                  "mydate": "Date"
                  })
    fig.update_traces(line=dict(width=4))

    fig.add_shape(type='line',
                x0=0,
                y0=.05,
                x1=1,
                y1=.05,
                line=dict(color='Red',dash="dot", width=5),
                xref='paper',
                yref='y')

    fig.add_annotation(text="WHO Recommended Threshold",
                  xref="paper", yref="y",
                  x=1, y=0.052, showarrow=False,
                  font=dict(color="red",size=10)
                  )

    fig.update_layout(title='14 Day Average Test Positivity Rate Over Time',
                      showlegend=True,
                      legend_title_text='County',
                      yaxis_tickformat = '.2%',
                      font=dict(size=16))
    fig.show()

def generate_bullet(df):
    fig = go.Figure()

    y1 = 0.1
    y2 = 0.2
    row_date = None
    axis_visible = True
    for county in counties:
        county_data = df[df['county_nam'] == county]
        row1 = county_data.iloc[0]
        row_date = row1['mydate'].strftime('%A, %b %d, %Y')
        pp_last_fourteen_days = row1['14d_pp']
        fig.add_trace(go.Indicator(
            mode = "number+gauge+delta", value = pp_last_fourteen_days,
            delta = {'reference': .05},
            domain = {'x': [0.1, 1], 'y': [y1, y2]},
            title = {'text': str(county) + " County"},
            gauge = {
                'shape': "bullet",
                'axis': {'range': [None, .2], 'visible': axis_visible},
                'threshold': {
                    'line': {'color': "red", 'width': 2},
                    'thickness': 1,
                    'value': .05},
                'bar': {'color': "black"},
                'bgcolor': 'LightGrey'}))
        y1 += 0.12
        y2 += 0.12
        axis_visible = False

    fig.update_traces(number_valueformat='.2%', selector=dict(type='indicator'))
    fig.update_traces(gauge_axis_tickformat='.2%', selector=dict(type='indicator'))
    fig.update_traces(delta_valueformat='.2%', selector=dict(type='indicator'))
    fig.update_traces(delta_increasing_color='#FF0000', selector=dict(type='indicator'))
    fig.update_traces(delta_decreasing_color='#00FF00', selector=dict(type='indicator'))
    fig.update_yaxes(automargin=True)

    fig.add_annotation(x=-1, y=4,
            text="Text annotation without arrow",
            showarrow=False,
            yshift=10)

    fig.update_layout(
        title={
            'text': "14 Day Test Positivity Rate (" + row_date + ")",
            'y':y1,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'},
        autosize=True,
        width=1300,
        height=729
    )


    fig.show()

def generate_xkcd_graph(df):
    with plt.xkcd():
        ax = df.plot(x ='mydate', y='active_cases', kind = 'line', grid = True, title = 'active covid 19 cases in union county over time', legend = False, figsize = [16, 9])
        ax.set_xlabel("date")
        ax.set_ylabel("active cases")
        ax.grid(True, linewidth=1)

        line_annotation1 = datetime(2020, 9, 13)
        line_annotation2 = datetime(2020, 11, 7)
        line_annotation3 = datetime(2020, 10, 13)
        ax.annotate('', xy=(line_annotation1, 90), xytext=(line_annotation2, 90), xycoords='data', textcoords='data', arrowprops={'arrowstyle': '|-|'})
        ax.annotate('period of calm and preparation', xy=(line_annotation3, 98), ha='center', va='center')

        # Annotate
        x_line_annotation = datetime(2020, 11, 26)

        ax.annotate('violent ritual involving maskless\nfamily gatherings and gorging on the \ncorpse of a turkey',
                    xy=(x_line_annotation, 117),
                    xycoords='data',
                    xytext=(-50,-75),
                    textcoords='offset points',
                    arrowprops=dict(headwidth=5, width=2, color='#363d46', connectionstyle="angle3,angleA=0,angleB=-90"),
                    fontsize=12)
        # Annotate
        x_line_annotation = datetime(2021, 1, 2)

        ax.annotate('SURPRISE!\na 190% increase since\nmurdering the turkey',
                    xy=(x_line_annotation, 365),
                    xycoords='data',
                    xytext=(-180,-35),
                    textcoords='offset points',
                    arrowprops=dict(headwidth=5, width=2, color='#363d46', connectionstyle="angle3,angleA=0,angleB=-90"),
                    fontsize=12)

        # Annotate
        x_line_annotation = datetime(2020, 11, 14)

        ax.annotate('warriors begin gathering at rustic shelters\nin groups to plot the mass murder of beasts\nwith white tails',
                    xy=(x_line_annotation, 75),
                    xycoords='data',
                    xytext=(-40,-90),
                    textcoords='offset points',
                    arrowprops=dict(headwidth=5, width=2, color='#363d46', connectionstyle="angle3,angleA=0,angleB=-90"),
                    fontsize=12)

        # Annotate
        x_line_annotation = datetime(2020, 12, 25)

        ax.annotate('second, morbid ritual revolving around\nhanging ornaments and lights on the\ncorpse of a tree',
                    xy=(x_line_annotation, 280),
                    xycoords='data',
                    xytext=(-290,-65),
                    textcoords='offset points',
                    arrowprops=dict(headwidth=5, width=2, color='#363d46', connectionstyle="angle3,angleA=0,angleB=90"),
                    fontsize=12)

        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.show()

def generate_state_cloropleth(latest_data, county_boundaries, min_cases, max_cases):
    fig = px.choropleth_mapbox(latest_data, geojson=county_boundaries, color='Active_Cases_10k_Pop',
        locations='fips',
        color_continuous_scale="portland",
        range_color=[min_cases, max_cases],
        mapbox_style='open-street-map',
        center={'lat': 34.8938, 'lon': -92.4426},
        zoom=6.8,
        opacity=0.6,
        title='Active Cases per 10k of Population (' + max_date.strftime('%A, %b %d, %Y') + ')',
        hover_name='county_nam',
        labels={'Active_Cases_10k_Pop': 'Active Cases/10k Population'})
    fig.update_layout(margin={"r":10,"t":30,"l":10,"b":10})
    fig.show()

def calculate_positivity_rate(data, county, period):
    county_data = data[data['county_nam'] == county]
    datetime_series = pd.to_datetime(county_data['mydate'])
    datetime_index = pd.DatetimeIndex(datetime_series.values)
    df2 = county_data.set_index(datetime_index)
    df2 = df2.sort_index()
    df2['pp'] = df2['positive'] / df2['total_tests']
    df2['14d_pp'] = df2['pp'].rolling(window=period, min_periods=1, center=False).mean()
    return df2.sort_index(ascending=False)

def group_counties(data, county1, county2):
    combo = str(county1 + ' + ' + county2)
    filtered_data = data[data['county_nam'].isin([county1, county2])]
    grouped_df = filtered_data.groupby(['mydate']).mean()
    grouped_df['combo'] = combo
    grouped_df = grouped_df.sort_values(by=['mydate'], ascending=False)
    return grouped_df

def group_all_counties(data, counties):
    filtered_data = data[data['county_nam'].isin(counties)]
    grouped_df = filtered_data.groupby(['mydate']).mean().reset_index()
    grouped_df['county_nam'] = 'All Counties'
    grouped_df = grouped_df.sort_values(by=['mydate'], ascending=False)
    return grouped_df

def generate_county_narrative(data, county):
    county_data = data[data['county_nam'] == county]
    county_data.sort_values(by=['mydate'], inplace=True, ascending=False)
    if county == p_county and gen_graph:
        generate_xkcd_graph(county_data[(county_data['mydate'] > '2020-09-10')])
    county_data['mydate'] = county_data['mydate'].dt.strftime('%A, %b %d, %Y')

    row1 = county_data.iloc[0]
    row2 = county_data.iloc[1]

    if row1['mydate'] != latest_index:
        logging.info("New Arkansas COVID data found for " + county + " County")
        with open(r'./config_old.yaml', 'w') as file:
            configuration = yaml.dump(cfg, file)
    else:
        logging.info("No new Arkansas COVID data found for " + county + " County")
        return None

    today = int(row1['active_cases'])
    yesterday = int(row2['active_cases'])
    today_date = row1['mydate']
    new_cases_today = int(row1['New_Cases_Today'])
    total_cases = int(row1['positive'])
    new_recoveries_today = int(row1['Recovered_Since_Yesterday'])
    new_deaths_today = int(row1['New_Deaths_Today'])
    total_deaths = int(row1['deaths'])
    preliminary_cfr = "{:.2%}".format(float(total_deaths/total_cases))
    pp_last_fourteen_days = row1['14d_pp']
    pp_average = ("{:.2%}".format(pp_last_fourteen_days))

    difference = today - yesterday
    direction = 'an increase'

    if difference < 0:
        direction = 'a decrease'
        difference = abs(difference)

    header_msg = '\u2190 ' + str(county).upper() + ' COUNTY \u2192'

    active_cases_msg = u"There were {today} active cases in {county} County on {today_date}. This is {direction} of {difference} from the previous day's total of {yesterday}.".format(today = today, county = county, yesterday = yesterday, difference = difference, direction = direction, today_date = today_date)
    if difference == 0:
        active_cases_msg = u"There were {today} active cases in {county} County on {today_date}. This is equal to the previous day's total.".format(today = today, county = county, today_date = today_date)

    new_info_msg = u"{new_cases_today} new cases were added and {new_recoveries_today} cases are considered newly recovered.".format(new_cases_today=new_cases_today, new_recoveries_today=new_recoveries_today)

    new_deaths_msg = u"Sadly, {new_deaths_today} more of our {county} County friends and neighbors have died due to COVID-19.".format(new_deaths_today = new_deaths_today, county = county)
    if new_deaths_today <= 0:
        new_deaths_msg = u"Fortunately, we have not lost any additional {county} County friends and neighbors to the virus.".format(county = county)

    pcfr_msg = u"The preliminary case fatality ratio in the County is currently {preliminary_cfr}".format(preliminary_cfr = preliminary_cfr)

    pp_message = "{pp_average} of tests in the County were positive over the last 14 days.\n\n\n".format(pp_average = pp_average)

    msg = "\n\n".join([header_msg, active_cases_msg, new_info_msg, new_deaths_msg, pcfr_msg, pp_message])

    cfg.update({'ar_covid_latest_index': row1['mydate']})

    with open(r'./config.yaml', 'w') as file:
        configuration = yaml.dump(cfg, file)

    return msg

def generate_positivity_explanation():
    return u'\u204d (The WHO recommends that rates of positivity in testing should remain at 5% or lower for at least 14 days before loosening restrictions.)\n\n'

def generate_cfr_explanation():
    return u'\u204d (The case fatality ratio is the proportion of deaths from a certain disease compared to the total number of people diagnosed with the disease for a particular period. A CFR is conventionally expressed as a percentage and represents a measure of disease severity. A CFR can only be considered final when all the cases have been resolved [either died or recovered]. The preliminary CFR, for example, during an outbreak with a high daily increase and long resolution time would be substantially lower than the final CFR.)\n\n'

def generate_rt_narrative():
    rt_msg = ""
    rt_data = read_data(rt_url, 2)
    rt_data['date'] = pd.to_datetime(rt_data['date'])

    uc_rt_data = rt_data[rt_data['region'] == 'AR']
    uc_rt_data.sort_values(by=['date'], inplace=True, ascending=False)
    uc_rt_data['date'] = uc_rt_data['date'].dt.strftime('%A, %b %d, %Y')

    latest_rt_row = uc_rt_data.iloc[0]
    rt_mean = "{:.3}".format(float(latest_rt_row['mean']))
    rt_date = latest_rt_row['date']

    rt_msg = u"The effective reproduction rate (R\u209c) in the State on {rt_date} was {rt_mean}.\n(Values over 1.0 mean we should expect more cases in the State, values under 1.0 mean we should expect fewer.)\n\n\n".format(rt_date=rt_date, rt_mean=rt_mean)
    return rt_msg

def post_to_facebook(group, msg):
    credentials = read_creds('./credentials.json')

    graph = GraphAPI(access_token=credentials['facebook_access_token'])

    link = 'https://arkansascovid.com/'
    groups = [group]

    logging.info("Posting to group # " + str(groups))
    for group in groups:
        graph.put_object(group, 'feed', message=msg, link=link)
        #logging.debug(graph.get_connections(group, 'feed'))

def send_email(subject, body):
    credentials = read_creds('./credentials.json')
    username = credentials['gmail_username']
    password = credentials['gmail_app_password']

    to = [username]
    print(to)

    message = MIMEText(body, 'plain', 'utf-8')
    message['Subject'] = subject
    message['From'] = username
    message['To'] = ','.join(to)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(username, password)
        server.sendmail(message['From'], message['To'], message.as_string())
        server.close()
        logging.debug('Email sent!')
    except Exception as e:
        logging.exception('Something went wrong', e)

data = read_data(master_url, 0)

data['mydate'] = pd.to_datetime(data['mydate'])
# Prepending the state FIPS number to the county FIPS number for geojson indexing purposes
data['fips'] = '05' + data['fips'].astype(str).str.zfill(3)

# calculate 14 day average positivity rate for each county of interest
frames = []
for county in counties:
    ppdf = calculate_positivity_rate(data, county, 14)
    frames.append(ppdf)
full_data = pd.concat(frames)

# beginnings of grouping to calculate regional statistics and to do analysis on county border interactions
frames = []
for county in counties:
    if county != p_county:
        g_df = group_counties(full_data, p_county, county)
        frames.append(g_df)
grouped_data = pd.concat(frames)

county_text = u', '.join(counties)
summary_msg = u"Statistics Summary for " + county_text + "\n" + now.strftime('%A, %b %d, %Y') + '\n\n'

for county in counties:
    county_msg = generate_county_narrative(full_data, county)

    if county_msg:
        new_data = True

    if new_data:
        msg = county_msg
    else:
        msg = "No new data found at " + str(now) + " for " + county + " County\n\n"

    summary_msg = summary_msg + msg

summary_msg = summary_msg + generate_rt_narrative()
summary_msg = summary_msg + generate_positivity_explanation()
summary_msg = summary_msg + generate_cfr_explanation()
summary_msg = summary_msg + u"Sources:\n - https://arkansascovid.com/\n - https://rt.live/us/AR"

logging.debug(summary_msg)

if post and (new_data or post_negative_results):
    post_to_facebook(group, summary_msg)

if email and (new_data or post_negative_results):
    subject = 'COVID-19 Support for Union County and Surrounding Areas, Daily Update for ' + now.strftime("%A, %b %d, %Y %k:%M")
    send_email(subject, summary_msg)

logging.info('post_stats complete')

if gen_bullet:
    generate_bullet(full_data)
if gen_line:
    generate_line(full_data)

if gen_state_map or gen_regional_map:
    latest_data = data.set_index('mydate')
    max_date = latest_data.index.max()
    latest_data = data.set_index('mydate')
    latest_data = data[data['mydate'] == max_date]

if gen_state_map:
    latest_data = latest_data[latest_data['county_nam'] != 'Arkansas_all_counties']
    min_cases = latest_data['Active_Cases_10k_Pop'].min()
    max_cases = latest_data['Active_Cases_10k_Pop'].max()

    generate_state_cloropleth(latest_data, county_boundaries, min_cases, max_cases)

if gen_regional_map:
    latest_data = latest_data[latest_data['county_nam'].isin(counties)]
    min_cases = latest_data['Active_Cases_10k_Pop'].min()
    max_cases = latest_data['Active_Cases_10k_Pop'].max()

    generate_state_cloropleth(latest_data, county_boundaries, min_cases, max_cases)
