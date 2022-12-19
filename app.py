import os
import sqlite3

import pandas as pd
import plotly
# from eralchemy import render_er
import plotly.express as px
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from dash import Dash, html, dcc, Input, Output
import numpy as np
from plotly.subplots import make_subplots


layout = plotly.graph_objs.Layout(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font_color="white"
)

### utils
values = ['10th Percentile', '25th Percentile', '75th Percentile', '90th Percentile']


def scrap():
    data = []
    URL = "https://www.itjobswatch.co.uk/jobs/uk/sqlite.do"
    web = requests.get(URL)

    web_content = BeautifulSoup(web.content, 'html5lib')

    table = web_content.find('table', attrs={'class': 'summary'})
    table_body = table.find('tbody')

    headers_elements = table.find('tr', attrs={'class': 'rowHdr'}).find_all('th')[1:]
    headers_data = [el.text.strip() for el in headers_elements]
    headers = [el for el in headers_data if el]
    headers.insert(0, 'Name')
    rows = table_body.find_all('tr')

    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        data.append([ele for ele in cols if ele])

    data = list(filter(lambda x: x, data))

    df = pd.DataFrame(data, columns=headers)
    df = df.loc[df['Name'].isin(values)]
    return df


def task1() -> go.Figure:
    """
    Present a bar chart with the number of employees with the same job. Use Plotly-Dash to make
    your bar chart dynamic and allow the user to choose the job titles to be seen in the chart.
    """
    con = sqlite3.connect('hr')
    data_connected = pd.read_sql("SELECT employees.first_name, jobs.job_title " +
                                 "FROM employees " +
                                 "INNER JOIN jobs ON employees.job_id " +
                                 "= jobs.job_id", con)
    fig = px.bar(data_connected, x='job_title', color="job_title")
    return fig


def task2():
    con = sqlite3.connect('hr')
    jobs = pd.read_sql_query("select * from jobs;", con)
    jobs = jobs.iloc[1:, :]
    jobs["difference"] = jobs['max_salary'] - jobs['min_salary']
    job = jobs[['job_title', 'difference']]
    max_salary = job['difference'].max()

    dcc.RangeSlider(0, max_salary, 1000, value=[0, max_salary], id="input3"),
    dcc.Graph(id="output3")


function_pointers = {
    "employees_chart": task1,
}

app = Dash(__name__)
server = app.server

con = sqlite3.connect('hr')
jobs = pd.read_sql_query("select * from jobs;", con)
jobs = jobs.iloc[1:, :]
jobs["difference"] = jobs['max_salary'] - jobs['min_salary']
job = jobs[['job_title', 'difference']]
max_salary = job['difference'].max()

app.layout = html.Div([

    html.H1("Web Application Dashboards with Dash", style={'text-align': 'center'}),

    dcc.Dropdown(id="slct_chart",
                 options=[
                     {"label": "Employees chart", "value": "employees_chart"},
                     {"label": "Average salaries chart", "value": "average_salaries_chart"},
                 ],
                 multi=False,
                 value="employees_chart",
                 style={'width': "40%"}
                 ),

    html.Div(id='output_container', children=[]),
    html.Br(),
    dcc.Graph(id='my_map', figure={}),
    dcc.RangeSlider(0, max_salary, 1000, value=[0, max_salary], id="salary_range"),
    html.Br(),
    dcc.Graph(id="salary"),
    dcc.Input(
        id="year_salary", type="number",
        debounce=True, placeholder="Debounce True",
        value=2022,
    ),
    dcc.Graph(id='output4')
])


@app.callback(
    Output(component_id='output4', component_property='figure'),
    Input(component_id='year_salary', component_property='value')
)
def update_output(value):
    con = sqlite3.connect('hr')
    salaries = pd.read_sql_query("select salary from employees;", con)
    salaries_avg = np.around(salaries.mean(), decimals=2)
    uk_chart_df = scrap()
    uk_chart_df.columns = ['Name', '2022', '2021', '2020']
    year = str(value)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=uk_chart_df['Name'],
                   y=np.repeat(salaries_avg, 4),
                   mode='lines+markers',
                   name='',
                   fillcolor='black',
                   line=dict(color="#222A2A"),
                   )
    )
    fig.add_trace(
        go.Scatter(x=uk_chart_df['Name'],
                   y=uk_chart_df[year],
                   mode='lines+markers',
                   line=dict(color="#30f216")
                   ),
        secondary_y=True,
    )
    fig["layout"]["title"] = "Average Salaries"
    fig["layout"]["xaxis"]["title"] = "Percentile"
    fig["layout"]["yaxis"]["title"] = "Salaries"
    fig["layout"]["legend_title"] = "Options"

    fig._layout = layout
    return fig


@app.callback(
    Output(component_id='salary', component_property='figure'),
    Input(component_id='salary_range', component_property='value')
)
def update_output(value):
    minimum = value[0]
    maximum = value[-1]
    fig = go.Figure()
    fig["layout"]["xaxis"]["title"] = "Job"
    fig["layout"]["yaxis"]["title"] = "Difference between max and min"
    t = job[job["difference"] >= minimum][job["difference"] <= maximum]
    fig.add_trace(go.Bar(x=t['job_title'], y=t['difference'], name='Job differences'))
    return fig


@app.callback(
    [Output(component_id='output_container', component_property='children'),
     Output(component_id='my_map', component_property='figure')],
    [Input(component_id='slct_chart', component_property='value')]
)
def update_graph(option_slctd):
    container = "The chart chosen by user is: {}".format(option_slctd)
    fig = function_pointers[option_slctd]()
    return container, fig


if __name__ == '__main__':
    app.run_server("0.0.0.0", debug=False, port=int(os.environ.get('PORT', 8000)))
