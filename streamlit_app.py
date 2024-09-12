import streamlit as st
import xml.etree.ElementTree as ET
from collections import Counter
import matplotlib.pyplot as plt
import io

# App Title
st.title("🎈 Sitemap Analyzer")

# File uploader
uploaded_file = st.file_uploader("Upload your sitemap.xml", type="xml")

if uploaded_file:
    # Parse the uploaded XML file
    tree = ET.parse(uploaded_file)
    root = tree.getroot()

    # Define namespace
    namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

    # Initialize list to collect URLs
    urls = []

    # Check if it's a regular sitemap, news sitemap, or index sitemap
    if root.tag.endswith("sitemapindex"):
        # Handle index sitemap
        st.write("Detected: Index Sitemap")
        urls = [url.text for url in root.findall(".//ns:loc", namespaces)]
    elif root.tag.endswith("urlset"):
        # Handle regular and news sitemaps
        st.write("Detected: Regular or News Sitemap")
        urls = [url.text for url in root.findall(".//ns:loc", namespaces)]

    # Group URLs by the first folder after the domain
    def get_first_folder(url):
        try:
            return url.split('/')[3]  # Extract the first folder
        except IndexError:
            return 'root'  # If no folder, categorize as 'root'

    if urls:
        first_folders = [get_first_folder(url) for url in urls]

        # Count occurrences of each folder
        folder_counts = Counter(first_folders)

        # Display the data
        st.subheader("Folder Distribution")
        st.write(folder_counts)

        # Plot a bar chart
        st.subheader("Visualization")
        fig, ax = plt.subplots()
        ax.bar(folder_counts.keys(), folder_counts.values())
        plt.xticks(rotation=90)
        plt.title('URLs Grouped by First Folder')
        plt.xlabel('First Folder')
        plt.ylabel('Number of URLs')

        # Display the chart
        st.pyplot(fig)
    else:
        st.warning("No URLs found in the sitemap.")
