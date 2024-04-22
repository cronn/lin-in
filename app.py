# import libraries
import re
import streamlit as st
import pandas as pd
import janitor
import streamlit.components.v1 as components
from zipfile import ZipFile
from pathlib import Path
import shutil

# helper functions
from helpers import *


def get_data(usr_file, data="connections") -> pd.DataFrame:

    if usr_file is None:
        return

    with ZipFile(usr_file, "r") as zipObj:
        # Extract all the contents of zip file in current directory
        zipObj.extractall("data")

    raw_df = pd.read_csv("data/Connections.csv", skiprows=3)

    if data == "messages":
        raw_df = pd.read_csv("data/messages.csv")

    # delete the data
    shutil.rmtree("data", ignore_errors=True)

    return raw_df


def main():
    # streamlit config
    st.set_page_config(
        page_title="LIN-IN - LinkedIn Insights",
        page_icon="https://www.cronn.de/img/favicon/favicon.png",
        initial_sidebar_state="expanded",
        layout="wide",
    )
    st.markdown(
        """
        <h1 style='text-align: center; color: #03c03c;'>LIN-IN</h1>
        <h3 style='text-align: center; color: white;'>LinkedIn Insights</h3>
        """,
        unsafe_allow_html=True,
    )

    # center image
    col1, col2, col3 = st.columns([1, 5, 1])

    st.subheader("Instructions:")
    st.markdown(
    """
    1. Login to LinkedIn 
    2. Click on "Me" on the top bar and open "Settings & Privacy" 
    3. Click on "Data privacy" and then "Get a copy of your data"
    4. Select "Want something.." and choose "Connections" and "Messages" 
    5. Wait approx. 20 min, until you receive an E-Mail with the download link to your data export 
    """
    )

    st.subheader("Please upload your LinkedIn data export:")

    # upload files
    usr_file = st.file_uploader("Drop your zip file", type={"zip"})

    df_ori = get_data(usr_file)

    # if data not uploaded yet, return None
    if df_ori is None:
        return

    df_clean = clean_df(df_ori)

    with st.expander("Show raw data"):
        st.dataframe(df_ori)

    # Data wrangling
    agg_df_company = agg_sum(df_clean, "company")
    agg_df_position = agg_sum(df_clean, "position")

    this_month_df = df_clean[
        (df_clean["connected_on"].dt.month == 1)
        & (df_clean["connected_on"].dt.year == 2022)
    ]

    # Getting some stats
    total_conn = len(df_ori)
    top_pos = agg_df_position["position"][0]
    top_comp = agg_df_company["company"][0]
    second_comp = agg_df_company["company"][1]
    top_pos_count = agg_df_position["count"][0]
    first_c = df_clean.iloc[-1]
    last_c = df_clean.iloc[0]

    # calculating stats
    st.markdown(
        """
        ---
        ### Overview of your Connections
        """
    )

    # Metrics
    pos, comp, conn = st.columns(3)
    pos.metric("Top Position", f"{top_pos[0:18]}..." if len(top_pos) > 18 else top_pos)
    comp.metric("Top Company", f"{top_comp[0:18]}..." if len(top_comp) > 18 else top_comp)
    conn.metric("Total Connections", f"{total_conn}", len(this_month_df))

    st.markdown(
        f"""
        - You have _{len(this_month_df)}_ new connections this month, with a total of _{total_conn}_
        - Most of your connections work at **{top_comp}**, closely followed by {second_comp}
        - You have _{top_pos_count}_ connections working as **{top_pos}**
        - Your first ever connection is {first_c['name']} and they work as a {first_c.position} at {first_c.company}
        - Your most recent connection is {last_c['name']} and they work as a {last_c.position} at {last_c.company}
        ---
        """
    )

    # top n companies and positions
    st.subheader(f"Companies & Positions")
    top_n = st.slider("How many connections per company and per position. Use the slider to control the maximum.", 0, len(agg_df_company["company"]), 10, key="1")

    company_plt, positions_plt = st.columns(2)
    company_plt.plotly_chart(plot_bar(agg_df_company, top_n), use_container_width=True, color="#03c03c")
    positions_plt.plotly_chart(
        plot_bar(agg_df_position, top_n), use_container_width=True
    )

    col1, col2 = st.columns(2)
    with col1:
        with st.expander("View top companies data", expanded=True):
            st.dataframe(agg_df_company)
    with col2:
        with st.expander("View top positions data", expanded=True):
            st.dataframe(agg_df_position)

    # connections timeline
    st.subheader("Connections in relation to time")
    st.write("Connections per day as timeline")
    st.plotly_chart(plot_timeline(df_clean), use_container_width=True)

    st.write("Summary of connections per weekday")
    st.plotly_chart(plot_day(df_clean), use_container_width=True)

    st.write("Total number of connections over time")
    st.plotly_chart(plot_cumsum(df_clean), use_container_width=True)

    # Graph network
    st.subheader("Company Network")
    company_cutoff = st.slider(
        "Shows the companies of your connections. Minimum number of connections per company:",
        1,
        50,
        3,
        key="3",
    )
    company_logarithmic = False
    if st.checkbox("logarithmic scale", key="check_01"):
        company_logarithmic = True

    generate_network(df_clean, agg_df_company, company_logarithmic, company_cutoff, "position")

    st.subheader("Positions Network")
    position_cutoff = st.slider(
        "Shows all positions of your connections. Minimum positions of connections per company:",
        1,
        50,
        3,
        key="4",
    )
    position_logarithmic = False
    if st.checkbox("logarithmic scale", key="check_02"):
        position_logarithmic = True
    generate_network(df_clean, agg_df_position, position_logarithmic, position_cutoff, "name")

    # emails
    st.subheader("E-Mail")
    st.write("Connections that provide an E-Mail adress")
    emails = df_clean[df_clean.notnull()["email_address"]].drop(
        ["connected_on", "weekday"], axis=1
    )
    st.dataframe(emails)

    # chats
    st.subheader("Chats analysis")
    messages = get_data(usr_file, data="messages")
    messages["DATE"] = pd.to_datetime(messages["DATE"], format="%Y-%m-%d %H:%M:%S UTC")
    messages["DATE"] = (
        messages["DATE"].dt.tz_localize("UTC").dt.tz_convert("US/Central")
    )

    total, from_count, to_count = st.columns(3)
    total.metric("Total Conversations", f"{messages['CONVERSATION ID'].nunique()}")
    from_count.metric("Total Sent", f"{messages.FROM.nunique()}")
    to_count.metric("Total Received", f"{messages.TO.nunique()}")

    messages_FROM = agg_sum(messages, "FROM").iloc[1:]
    messages_TO = agg_sum(messages, "TO").iloc[1:]

    from_plt, to_plt = st.columns(2)
    from_plt.plotly_chart(
        plot_bar(messages_FROM, top_n, title="Messages FROM"), use_column_width=True
    )
    to_plt.plotly_chart(
        plot_bar(messages_TO, top_n, title="Messages TO"), use_column_width=True
    )

    st.write("Summary of messages per hour of day")

    st.plotly_chart(plot_chat_hour(messages), use_container_width=True)

    st.write(
        "Trend chart of messages. Hover over the dots to see with whom."
    )
    st.plotly_chart(plot_chat_people(messages), use_container_width=True)

    # tree maps
    st.subheader("Tree Maps")
    st.write("Company-centric perspective")
    df_tree = df_clean.dropna(subset=['company', 'position'])
    st.plotly_chart(px.treemap(df_tree, path=[px.Constant(''), 'company', 'position', 'name'], height = 800), use_container_width=True)
    
    st.write("position-centric perspective")
    st.plotly_chart(px.treemap(df_tree, path=[px.Constant(''), 'position', 'company', 'name'], height = 800), use_container_width=True)
    


if __name__ == "__main__":
    main()
