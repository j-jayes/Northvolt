# main.py

import pandas as pd
from utils import setup_driver, extract_coordinates, extract_property_info_from_json, get_property_links, get_total_pages
from selenium.common.exceptions import TimeoutException
import logging
import sys
import time

def main(location_ids):
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()

    driver = setup_driver()

    all_property_data = []

    # Get total number of pages
    total_pages = get_total_pages(driver, location_ids)
    logger.info(f"Total pages to scrape: {total_pages}")

    for page in range(1, total_pages + 1):
        logger.info(f"Scraping page {page} of {total_pages}")
        property_links = get_property_links(driver, location_ids, page)
        logger.info(f"Found {len(property_links)} property links on page {page}")

        for link in property_links:
            logger.info(f"Scraping property: {link}")
            try:
                driver.get(link)
                # Wait for page to load
                time.sleep(2)
                property_info = extract_property_info_from_json(driver)
                latitude, longitude = extract_coordinates(driver)
                property_info['latitude'] = latitude
                property_info['longitude'] = longitude
                all_property_data.append(property_info)
            except Exception as e:
                logger.error(f"Error scraping property {link}: {e}")
                continue

    driver.quit()

    # Convert the list of dictionaries to a DataFrame
    df = pd.json_normalize(all_property_data, sep='_')

    # Save to Parquet file
    df.to_parquet('properties/properties.parquet', index=False)
    logger.info("Data saved to properties/properties.parquet")

if __name__ == '__main__':
    # Check if location_ids is provided as a command-line argument
    if len(sys.argv) > 1:
        location_ids = sys.argv[1]
    else:
        # Default location_ids if not provided
        location_ids = '17860'  # Skellefteå kommun
    main(location_ids)
