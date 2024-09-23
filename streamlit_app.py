# Import necessary libraries
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
from urllib.parse import urlparse
import os

# Streamlit app title
st.title("Sitemap Report Generator")

# Function to parse sitemap or sitemap index URL
def fetch_sitemap(url):
    response = requests.get(url)
    if response.status_code == 200:
        tree = ET.ElementTree(ET.fromstring(response.content))
        root = tree.getroot()
        
        # Check if it's an index sitemap by looking for <sitemap> elements
        is_index_sitemap = root.tag == '{http://www.sitemaps.org/schemas/sitemap/0.9}sitemapindex'
        
        if is_index_sitemap:
            sitemaps = []
            # Parse all <sitemap> elements and recursively fetch referenced sitemaps
            for sitemap in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                loc = sitemap.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
                # Recursively fetch and parse each referenced sitemap
                sub_sitemap = fetch_sitemap(loc)
                if sub_sitemap is not None:
                    sitemaps.extend(sub_sitemap)  # Append the results from sub-sitemaps
            return sitemaps
        else:
            # If it's a regular sitemap, return it as a list containing a single tree
            return [tree]
    else:
        st.error(f"Failed to retrieve sitemap: {response.status_code}")
        return None

# Function to extract URLs and last modified dates from sitemap
def parse_sitemap(sitemap):
    urls = []
    for url in sitemap.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
        loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc').text
        lastmod = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
        if lastmod is not None:
            lastmod = lastmod.text
        else:
            lastmod = None  # Handle missing lastmod
        urls.append({'url': loc, 'lastmod': lastmod})
    return pd.DataFrame(urls)

# Function to extract year, subfolders, domain, and file extensions from URLs
def extract_url_info(df):
    # Ensure proper datetime conversion with utc=True
    df['lastmod'] = pd.to_datetime(df['lastmod'], errors='coerce', utc=True).dt.tz_localize(None)
    df['year'] = df['lastmod'].dt.year

    # Extract file extension (if missing, consider as 'html')
    df['file_extension'] = df['url'].apply(lambda x: os.path.splitext(urlparse(x).path)[1][1:] if os.path.splitext(urlparse(x).path)[1] else 'html')

    # Handle first subfolder
    def get_first_subfolder(url):
        split_url = urlparse(url).path.strip('/').split('/')
        # Check if there's at least one folder before the file, otherwise use the file extension
        if len(split_url) > 1 and not os.path.splitext(split_url[-1])[1]:
            return split_url[0]  # Return the first folder
        elif len(split_url) > 1 and os.path.splitext(split_url[-1])[1]:
            return split_url[0]  # Return the first folder if a file exists
        else:
            return f"{os.path.splitext(split_url[-1])[1][1:]}-Dateiendung"  # No folder but a file

    df['first_subfolder'] = df['url'].apply(lambda x: get_first_subfolder(x))

    # Handle second subfolder
    def get_second_subfolder(url):
        split_url = urlparse(url).path.strip('/').split('/')
        if len(split_url) > 2 and not os.path.splitext(split_url[-1])[1]:
            return split_url[1]  # Return the second folder if it exists
        elif len(split_url) > 2 and os.path.splitext(split_url[-1])[1]:
            return split_url[1]  # Return the second folder even if a file exists
        else:
            return 'none'  # No second folder

    df['second_subfolder'] = df['url'].apply(lambda x: get_second_subfolder(x))

    # Extract domain using urlparse and add it to the DataFrame
    df['domain'] = df['url'].apply(lambda x: urlparse(x).netloc)

    return df

# Function to generate a table of total URLs per year
def urls_per_year(df):
    year_data = df.groupby('year').size().reset_index(name='URL Count')
    if year_data.empty:
        st.write("No valid 'lastmod' data to show URLs per Year.")
    return year_data

# Function to generate a bar chart of URLs in the last 12 months
def urls_last_12_months(df):
    if df['lastmod'].notna().sum() > 0:
        last_12_months = df[df['lastmod'] >= (pd.Timestamp.now() - pd.DateOffset(months=12)).tz_localize(None)]
        monthly_count = last_12_months.groupby(last_12_months['lastmod'].dt.to_period('M')).size()
        if not monthly_count.empty:
            st.bar_chart(monthly_count)
        else:
            st.write("No URLs in the last 12 months to plot.")
    else:
        st.write("No 'lastmod' data to plot URLs in the last 12 months.")

# Function to generate a bar chart of URLs per first subfolder
def urls_per_first_subfolder(df):
    folder_count = df.groupby('first_subfolder').size().sort_values(ascending=False)
    if not folder_count.empty:
        st.bar_chart(folder_count)
    else:
        st.write("No subfolders data to plot.")

# Function to generate a bar chart of URLs per second subfolder
def urls_per_second_subfolder(df):
    folder_count = df.groupby('second_subfolder').size().sort_values(ascending=False)
    if not folder_count.empty:
        st.bar_chart(folder_count)
    else:
        st.write("No second subfolder data to plot.")

# Function to generate a table of URLs per file extension
def urls_per_file_extension(df):
    file_extension_data = df.groupby('file_extension').size().reset_index(name='URL Count').sort_values(by='URL Count', ascending=False)
    if file_extension_data.empty:
        st.write("No file extensions data to show.")
    return file_extension_data

# Function to generate a table of URLs per domain
def urls_per_domain(df):
    domain_data = df.groupby('domain').size().reset_index(name='URL Count').sort_values(by='URL Count', ascending=False)
    if domain_data.empty:
        st.write("No domain data to show.")
    return domain_data

# Function to generate a table with URL, Last mod, First folder, and Second folder
def generate_full_url_info_table(df):
    full_info_table = df[['url', 'lastmod', 'first_subfolder', 'second_subfolder']].sort_values(by=['url'])
    return full_info_table

# Function to find and list duplicate URLs
def find_duplicates(df):
    duplicate_urls = df[df.duplicated(['url'], keep=False)].sort_values(by=['url'])
    return duplicate_urls

# Main function to generate report from sitemap URL
def generate_report(sitemap_url):
    sitemaps_data = fetch_sitemap(sitemap_url)
    
    if sitemaps_data:
        if isinstance(sitemaps_data, list):
            # If it's a list of multiple sitemaps, concatenate the parsed data
            all_entries = []
            for sitemap_tree in sitemaps_data:
                df = parse_sitemap(sitemap_tree)
                all_entries.append(df)
            df = pd.concat(all_entries, ignore_index=True)
        else:
            # Single sitemap
            df = parse_sitemap(sitemaps_data)

        df = extract_url_info(df)

        # Display total number of URLs
        st.write(f"Total number of URLs: {len(df)}")

        # Display URLs per year table
        st.write("URLs per Year:")
        year_data = urls_per_year(df)
        st.dataframe(year_data)

        # Generate bar charts
        urls_last_12_months(df)
        urls_per_first_subfolder(df)
        urls_per_second_subfolder(df)

        # Display URLs per file extension table
        st.write("\nURLs per File Extension:")
        file_extension_data = urls_per_file_extension(df)
        st.dataframe(file_extension_data)

        # Display URLs per domain table
        st.write("\nURLs per Domain:")
        domain_data = urls_per_domain(df)
        st.dataframe(domain_data)

        # Display full URL info table
        st.write("\nFull URL Info Table (URL, Last mod, First folder, Second folder):")
        full_info_table = generate_full_url_info_table(df)
        st.dataframe(full_info_table)

        # Check for duplicates and display duplicate URLs table
        st.write("\nDuplicate URLs (if any):")
        duplicate_urls = find_duplicates(df)
        if len(duplicate_urls) > 0:
            st.dataframe(duplicate_urls)
        else:
            st.write("No duplicate URLs found.")

# Streamlit input field and button
sitemap_url = st.text_input('Enter Sitemap URL', '')
if st.button('Generate Report'):
    if sitemap_url:
        generate_report(sitemap_url)
    else:
        st.error("Please enter a valid sitemap URL")
