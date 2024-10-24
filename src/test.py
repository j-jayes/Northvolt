from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import json
import time
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver
from io import BytesIO
import gzip

# Set up the webdriver (adjust path to your chromedriver if needed)
def setup_driver():
    """
    Setup the Selenium WebDriver.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    
    # Initialize WebDriver using ChromeDriverManager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

# Set up the driver
driver = setup_driver()

# URL of the property
url = 'https://www.hemnet.se/salda/lagenhet-2rum-sjungande-dalen-skelleftea-kommun-orkestervagen-112-3537267266547361298'

# Open the page
driver.get(url)

# Give the page some time to load
time.sleep(5)

# Find the "__NEXT_DATA__" script
next_data_script = driver.find_element(By.XPATH, "//script[@id='__NEXT_DATA__']")

# Extract the script content
next_data_json = next_data_script.get_attribute('innerHTML')

# Parse the JSON
next_data = json.loads(next_data_json)

# Navigate through the JSON data to get the necessary details
property_data = next_data['props']['pageProps']['__APOLLO_STATE__']['SoldPropertyListing:3537267266547361298']

# Extract desired information from the property data
property_info = {
    'sale_id': property_data['id'],
    'address': property_data['streetAddress'],
    'area': property_data['area'],
    'municipality': property_data['municipality']['__ref'],
    'asking_price': property_data['askingPrice']['formatted'],
    'selling_price': property_data['sellingPrice']['formatted'],
    'price_change': property_data['priceChange']['formatted'],
    'price_per_sqm': property_data['squareMeterSellingPrice']['formatted'],
    'rooms': property_data['formattedNumberOfRooms'],
    'living_area': property_data['formattedLivingArea'],
    'balcony': property_data['relevantAmenities'][0]['isAvailable'],
    'elevator': property_data['relevantAmenities'][1]['isAvailable'],
    'construction_year': property_data['legacyConstructionYear'],
    'floor': property_data['formattedFloor'],
    'monthly_fee': property_data['fee']['formatted'],
    'broker_name': property_data['broker']['__ref'],
    'broker_agency_name': property_data['brokerAgency']['__ref'],
    'sold_date': property_data['formattedSoldAt'],
    'property_link': property_data['hemnetUrl']
}


def extract_coordinates(driver):
    """
    Extract the coordinates of the property from GraphQL responses.
    """
    # Intercept network requests
    for request in driver.requests:
        if request.response and "graphql" in request.url:  # Look for GraphQL requests
            if request.response.headers.get('Content-Type') == 'application/json':
                response_body = request.response.body.decode('utf-8')
                data = json.loads(response_body)
                
                # Search for coordinates in the GraphQL response data
                try:
                    for entry in data['data']['sales']:
                        coordinates = entry['coordinates']
                        lat = coordinates['lat']
                        long = coordinates['long']
                        return lat, long
                except KeyError:
                    continue  # If no coordinates are found in this response, continue to the next request

    return None, None


# Extract the coordinates
lat, long = extract_coordinates(driver)

# Add the coordinates to the property information
property_info['latitude'] = lat
property_info['longitude'] = long


# Output the extracted information
print(json.dumps(property_info, indent=2, ensure_ascii=False))

# Close the browser
driver.quit()
