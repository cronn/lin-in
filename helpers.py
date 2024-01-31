import streamlit.components.v1 as components
import streamlit as st
import pandas as pd
import numpy as np

# fuzzy match
from thefuzz import fuzz
from thefuzz import process

# visualizations
import plotly.express as px
import networkx as nx
from pyvis.network import Network
import matplotlib
import matplotlib.pyplot as plt
from PIL import Image
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator

# clean text
import re
import nltk

nltk.download("stopwords")
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer


def clean_df(df: pd.DataFrame, privacy: bool = False) -> pd.DataFrame:
    """This function cleans the dataframe containing LinkedIn
    connections data"


    Args:
        df (pd.DataFrame): data frame before cleaning

    Returns:
        pd.DataFrame: data frame after cleaning
    """
    if privacy:
        df.drop(columns=["first_name", "last_name", "email_address"])
    else:
        clean_df = (
            df
            # remomves spacing and capitalization in column names
            .clean_names()
            # drop missing values in company and position
            .dropna(subset=["company", "position"])
            # join first name and last name
            .concatenate_columns(
                column_names=["first_name", "last_name"],
                new_column_name="name",
                sep=" ",
            )
            # drop first name and last name
            .drop(columns=["first_name", "last_name"])
            # truncate company names that exceed
            .transform_column("company", lambda s: s[:35])
            .to_datetime("connected_on")
            .filter_string(
                column_name="company",
                search_string=r"[Ff]reelance|[Ss]elf-[Ee]mployed|\.|\-",
                complement=True,
            )
        )

    # fuzzy match on Data Scientist titles
    replace_fuzzywuzzy_match(clean_df, "position", "Data Scientist")
    # fuzzy match on Software Engineer titles
    replace_fuzzywuzzy_match(clean_df, "position", "Software Engineer", min_ratio=65)

    return clean_df


def replace_fuzzywuzzy_match(
    df: pd.DataFrame, column: str, query: str, min_ratio: int = 75
):
    """Replace the fuzz matches with query string
    thefuzz github : https://github.com/seatgeek/thefuzz

    Args:
        df (pd.DataFrame): data frame of connections
        column (str): column to performn fuzzy matching
        query (str): query string
        min_ratio (int, optional): minimum score to remove. Defaults to 60.
    """

    # get list of all unique positions
    pos_names = df[column].unique()

    # get top 500 close matches
    matches = process.extract(query, pos_names, limit=500)

    # filter matches with ratio >= 75
    matching_pos_name = [match[0] for match in matches if match[1] >= min_ratio]

    # for position in above_ratio:
    #     print(f"replacing {position} with {query}")

    # get rows of all close matches
    matches_rows = df[column].isin(matching_pos_name)

    # replace all rows containing close matches with query string
    df.loc[matches_rows, column] = query


def agg_sum(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Does a value count on company and positions and sorts by count

    Args:
        df (pd.DataFrame): data frame before aggregation
        name (str): company | position

    Returns:
        pd.DataFrame: aggregated data frame
    """
    df = df[name].value_counts().reset_index()
    df.columns = [name, "count"]
    df = df.sort_values(by="count", ascending=False)
    return df


def plot_bar(df: pd.DataFrame, rows: int, title=""):
    height = 500
    if rows > 25:
        height = 900

    name, count = list(df.columns)

    fig = px.histogram(
        df.head(rows),
        x=count,
        y=name,
        template="plotly_dark",
        color_discrete_sequence=['#03c03c'],
        hover_data={name: False},
    )
    fig.update_layout(
        height=height,
        width=600,
        margin=dict(pad=5),
        hovermode="y",
        yaxis_title="",
        xaxis_title="",
        title=title,
        yaxis=dict(autorange="reversed"),
    )

    return fig


def plot_timeline(df: pd.DataFrame):
    df = df["connected_on"].value_counts().reset_index()
    df.rename(columns={"index": "connected_on", "connected_on": "count"}, inplace=True)
    df = df.sort_values(by="connected_on", ascending=True)
    fig = px.line(df, x="connected_on", y="count", color_discrete_sequence=['#03c03c'], markers=True)

    # add range slider
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                ),
                bgcolor="black",
            ),
            rangeslider=dict(visible=True),
            type="date",
        ),
        xaxis_title="Date",
    )

    return fig


def plot_day(df: pd.DataFrame):

    # get weekday name
    df["weekday"] = df["connected_on"].dt.day_name()
    df = df["weekday"].value_counts().reset_index()
    df.rename(columns={"index": "weekday_name", "weekday": "count"}, inplace=True)

    cats = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    df["weekday_name"] = pd.Categorical(
        df["weekday_name"], categories=cats, ordered=True
    )
    df = df.sort_values("weekday_name")

    # plot weekday in plotly
    fig = px.histogram(
        df,
        x="weekday_name",
        y="count",
        template="plotly_dark",
        color_discrete_sequence=['#03c03c']
    )
    fig.update_layout(
        height=500,
        width=700,
        margin=dict(pad=5),
        xaxis_title="",
        yaxis_title="",
    )
    return fig


def plot_cumsum(df: pd.DataFrame):
    df = df["connected_on"].value_counts().reset_index()
    df.rename(columns={"index": "connected_on", "connected_on": "count"}, inplace=True)
    df = df.sort_values(by="connected_on", ascending=True)
    df["cum_sum"] = df["count"].cumsum()

    fig = px.area(df, x="connected_on", y="cum_sum", color_discrete_sequence=['#03c03c'])

    fig.update_layout(
        xaxis=dict(
            rangeslider=dict(visible=True),
            type="date",
        ),
        xaxis_title="Date",
        yaxis_title="count",
    )

    return fig


def generate_network(
    df: pd.DataFrame, agg_df: pd.DataFrame, log_bool: bool, cutoff: int = 5, popover_type="position"
):
    """This function generates a network of connections of the user

    Args:
        df (pd.DataFrame): data frame containing
        agg_df (pd.DataFrame):
        cutoff (int, optional): the min number of connections at which nodes are created. Defaults to 5.
    """

    col_name = agg_df.columns[0]

    # initialize a graph
    g = nx.Graph()
    # intialize user as central node
    g.add_node("you", color="#157d35")

    # create network and provide specifications
    nt = Network(height="800px", width="100%", bgcolor="#0E1117", font_color="white")

    # reduce size of connections
    df_reduced = agg_df.loc[agg_df["count"] >= cutoff]

    # use iterrows tp iterate through the data frame
    for _, row in df_reduced.iterrows():

        # store company name and count
        name = row[col_name][:50]
        count = row["count"]

        title = f"{name} - {count} connections\n"
        positions = set([x for x in df[name == df[col_name]][popover_type]])
        positions = "".join("{}\n".format(x) for x in positions)

        hover_info = title + positions

        if log_bool:
            count = np.log(count) * 7

        g.add_node(name, size=count * 1.7, title=hover_info, color="#03c03c")
        g.add_edge("you", name, color="grey")

    # generate the graph
    nt.from_nx(g)
    nt.hrepulsion()
    nt.toggle_stabilization(True)
    #nt.show("network.html")

    # Save and read graph as HTML file (on Streamlit Sharing)
    try:
        path = "/tmp"
        nt.save_graph(f"{path}/network.html")
        HtmlFile = open(f"{path}/network.html", "r", encoding="utf-8")

    # Save and read graph as HTML file (locally)
    except:
        path = "/html_files"
        nt.save_graph(f"{path}/network.html")
        HtmlFile = open(f"{path}/network.html", "r", encoding="utf-8")

    # Load HTML file in HTML component for display on Streamlit page
    components.html(HtmlFile.read(), height=850)


def plot_chat_hour(chats: pd.DataFrame):
    chats["HOUR"] = chats["DATE"].dt.hour

    # plot chat by hour

    chats["HOUR"].value_counts().reset_index(name="count").sort_values(by="index")

    # plot a value count of hours
    fig = px.bar(
        chats["HOUR"].value_counts().reset_index(name="count").sort_values(by="index"),
        x="index",
        y="count",
        color_discrete_sequence=['#03c03c']
    )
    fig.update_layout(xaxis_title="hour of day")
    fig.update_xaxes(type="category")
    return fig


def plot_chat_people(chats: pd.DataFrame):
    # join all people on a particular day into a set
    chats["DATE"] = chats["DATE"].dt.date
    date_people = (
        chats.groupby("DATE")[["FROM", "TO"]]
        .agg(lambda x: x.unique().tolist())
        .reset_index()
    )
    date_people["people"] = date_people.apply(
        lambda x: set(x["FROM"] + x["TO"]), axis=1
    )
    date_people = date_people[["DATE", "people"]]

    # counts of date
    chats_time = chats["DATE"].value_counts().reset_index()
    chats_time.rename(columns={"index": "DATE", "DATE": "count"}, inplace=True)
    chats_time.sort_values(by="DATE")
    chats_time = chats_time.sort_values(by="DATE")

    # merge date_people with chats_time to get people column
    date_count_people = chats_time.merge(date_people, on="DATE", how="left")
    # join set into one string and ignore strings that are nan
    date_count_people["people"] = date_count_people["people"].apply(
        lambda x: "<br>".join(map(str, x) if str(x) != "nan" else x)
    )
    date_count_people

    # value count on date column
    fig = px.line(date_count_people, x="DATE", y="count", hover_data=["people"], color_discrete_sequence=['#03c03c'], markers=True)

    # print("plotly express hovertemplate:", fig.data[0].hovertemplate)

    # change hover template to show only people
    fig.update_traces(hovertemplate="%{customdata[0]}")

    # add range slider
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list(
                    [
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all"),
                    ]
                ),
                bgcolor="black",
            ),
            rangeslider=dict(visible=True),
            type="date",
        ),
        xaxis_title="Date",
    )
    return fig
