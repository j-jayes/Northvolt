from requests_html import HTMLSession
# from folder called utils and file called scraper-utils.py import the functions get_data and parse_html
from utils.scraper import get_data, parse_html, collect_property_links
from utils.storage import save_to_parquet, load_parquet
import pandas as pd
import os
import logging
import time
import random

def main(location_ids="location_ids%5B%5D=17860"):
    # Step 1: Collect the links to the properties
    # create a new HTML session
    session = HTMLSession()
    # initiate logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # set the params
    base_url = f"https://www.hemnet.se/salda/bostader?{location_ids}"
    min_area = 60
    max_area = 65
    step = 5

    # Get the date 
    date = pd.Timestamp.now().strftime("%Y-%m-%d")

    # property links file
    property_links_file = f"data/properties/raw/hemnet_links_{date}.parquet"

    # collect the property links if the file does not exist
    if not os.path.exists(property_links_file):
        property_links = collect_property_links(base_url, min_area, max_area, step)
        df_links = pd.DataFrame(property_links, columns=['url'])
        save_to_parquet(df_links, property_links_file)
    else:
        df_links = load_parquet(property_links_file)

    print(f"Collected a total of {len(df_links)} property links.")
    
    # ensure output folder exists
    os.makedirs('data/properties/raw', exist_ok=True)
    save_to_parquet(df_links, f'data/properties/raw/hemnet_links_{date}.parquet')

    # Step 2: Collect the data from the property links
    # Create cache file in the output folder
    cache_file = f'data/properties/raw/hemnet_properties_cache_{date}.parquet'
    
    property_data_cache = load_parquet(cache_file)

    for index, row in df_links.iterrows():
        try:
            url = row['url']
            
            if not property_data_cache.empty and url in property_data_cache['url'].values:
                logging.info(f"Skipping already scraped URL: {url}")
                continue

            r = session.get(url)
            data = parse_html(r.html.html)
            # add the url to the data
            data['url'] = url
            
            property_data_cache = pd.concat([property_data_cache, pd.DataFrame([data])], ignore_index=True)
            # save the cache to the file
            save_to_parquet(property_data_cache, cache_file)
            logging.info(f"Data collected for {url}")
            # sleep for between 5 and 10 seconds
            time.sleep(5 + 5 * random.random())
        except Exception as e:
            logging.error(f"Error collecting data for {url}: {e}")

    # Step 2: Convert the list of dictionaries into a DataFrame
    df_properties = pd.DataFrame(property_data_cache)

    # Step 3: Save the DataFrame to a Parquet file with the date
    save_to_parquet(df_properties, f'data/properties/raw/hemnet_properties_{date}_final.parquet')
    # Write a message to the log
    logging.info(f"Data saved to data/properties/raw/hemnet_properties_{date}.parquet")


if __name__ == "__main__":
    main()