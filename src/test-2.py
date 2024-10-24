from seleniumwire import webdriver  # Import from seleniumwire
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from io import BytesIO
import gzip


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

def extract_coordinates(driver):
    # Iterate over all intercepted requests
    for request in driver.requests:
        if 'graphql' in request.url:
            if request.response:
                try:
                    # Decode the request body
                    request_body = request.body.decode('utf-8')
                    if '"operationName":"saleMap"' in request_body:
                        # Decompress the response body if it's gzip-compressed
                        response_body = request.response.body
                        if request.response.headers.get('Content-Encoding') == 'gzip':
                            buf = BytesIO(response_body)
                            f = gzip.GzipFile(fileobj=buf)
                            response_body = f.read()
                        else:
                            response_body = response_body.decode('utf-8')
                        
                        data = json.loads(response_body)
                        # Extract coordinates
                        coordinates = data['data']['sales'][0]['coordinates']
                        lat = coordinates['lat']
                        long = coordinates['long']
                        return lat, long
                except Exception as e:
                    print(f"Error processing request: {e}")
    return None, None



def extract_property_info_from_json(driver):
    """
    Extracts the property information from the JSON data in the <script> tag.
    Returns a dictionary with the data.
    """
    from selenium.common.exceptions import NoSuchElementException

    # Wait for the page to load necessary elements
    time.sleep(2)

    try:
        # Find the <script> tag with id="__NEXT_DATA__"
        script_tag = driver.find_element(By.XPATH, '//script[@id="__NEXT_DATA__"]')
        json_content = script_tag.get_attribute('innerHTML')
        data = json.loads(json_content)
    except NoSuchElementException:
        print("JSON data not found in the page.")
        return {}
    except json.JSONDecodeError:
        print("Error decoding JSON data.")
        return {}

    # Navigate through the JSON data to extract property information
    try:
        apollo_state = data['props']['pageProps']['__APOLLO_STATE__']
        # The property ID is under 'SoldPropertyListing:<ID>'
        # Extract the ID dynamically
        for key in apollo_state.keys():
            if key.startswith('SoldPropertyListing:'):
                property_data = apollo_state[key]
                break
        else:
            print("Property data not found in JSON.")
            return {}
    except KeyError as e:
        print(f"KeyError: {e}")
        return {}

    # Collect all property data
    property_info = {}

    # Extract all fields from 'broker' to 'landArea'
    for key, value in property_data.items():
        # Skip images as per your request
        if key in ['attributedImages', 'adTargeting']:
            continue

        # Handle nested references
        if isinstance(value, dict) and '__ref' in value:
            ref_key = value['__ref']
            referenced_data = apollo_state.get(ref_key, {})
            property_info[key] = referenced_data
        elif isinstance(value, list):
            # For lists, process each item
            processed_list = []
            for item in value:
                if isinstance(item, dict) and '__ref' in item:
                    ref_key = item['__ref']
                    referenced_data = apollo_state.get(ref_key, {})
                    processed_list.append(referenced_data)
                else:
                    processed_list.append(item)
            property_info[key] = processed_list
        else:
            property_info[key] = value

    # Process nested fields for 'broker' and 'brokerAgency'
    if 'broker' in property_info and property_info['broker']:
        broker_data = property_info['broker']
        # Extract broker details
        property_info['broker'] = {
            'name': broker_data.get('name', ''),
            'email': broker_data.get('email', ''),
            'phoneNumber': broker_data.get('phoneNumber', ''),
            'description': broker_data.get('description', ''),
            'id': broker_data.get('id', ''),
            'slug': broker_data.get('slug', ''),
            'hasActiveProfile': broker_data.get('hasActiveProfile', False),
            'canonicalUrl': broker_data.get('canonicalUrl', '')
        }

    if 'brokerAgency' in property_info and property_info['brokerAgency']:
        agency_data = property_info['brokerAgency']
        # Extract agency details
        property_info['brokerAgency'] = {
            'id': agency_data.get('id', ''),
            'name': agency_data.get('name', ''),
            'phoneNumber': agency_data.get('phoneNumber', ''),
            'email': agency_data.get('email', ''),
            'websiteUrl': agency_data.get('websiteUrl', ''),
            'slug': agency_data.get('slug', ''),
            'offersSellingPrices': agency_data.get('offersSellingPrices', False),
            'isKronofogden': agency_data.get('isKronofogden', False),
            'developer': agency_data.get('developer', False)
        }

    # Process 'districts' to include their keys
    if 'districts' in property_info and property_info['districts']:
        districts_list = []
        for district in property_info['districts']:
            district_data = district  # Already dereferenced
            districts_list.append({
                'id': district_data.get('id', ''),
                'fullName': district_data.get('fullName', ''),
                '__typename': district_data.get('__typename', '')
            })
        property_info['districts'] = districts_list

    # Process 'municipality' and 'county'
    for loc_field in ['municipality', 'county']:
        if loc_field in property_info and property_info[loc_field]:
            loc_data = property_info[loc_field]
            property_info[loc_field] = {
                'id': loc_data.get('id', ''),
                'fullName': loc_data.get('fullName', ''),
                '__typename': loc_data.get('__typename', '')
            }

    # Process 'relevantAmenities'
    if 'relevantAmenities' in property_info and property_info['relevantAmenities']:
        amenities_list = []
        for amenity in property_info['relevantAmenities']:
            amenities_list.append({
                'kind': amenity.get('kind', ''),
                'isRelevant': amenity.get('isRelevant', False),
                'isAvailable': amenity.get('isAvailable', False)
            })
        property_info['relevantAmenities'] = amenities_list

    # Process 'housingForm' and 'tenure'
    if 'housingForm' in property_info and property_info['housingForm']:
        housing_form = property_info['housingForm']
        property_info['housingForm'] = {
            'name': housing_form.get('name', ''),
            'symbol': housing_form.get('symbol', ''),
            'primaryGroup': housing_form.get('primaryGroup', '')
        }

    if 'tenure' in property_info and property_info['tenure']:
        tenure = property_info['tenure']
        property_info['tenure'] = {
            'name': tenure.get('name', ''),
            'symbol': tenure.get('symbol', '')
        }

    # Process 'askingPrice', 'sellingPrice', 'priceChange', 'runningCosts'
    money_fields = ['askingPrice', 'sellingPrice', 'priceChange', 'runningCosts']
    for field in money_fields:
        if field in property_info and property_info[field]:
            money_data = property_info[field]
            property_info[field] = {
                'formatted': money_data.get('formatted', ''),
                'amount': money_data.get('amount', None),
                'amountInCents': money_data.get('amountInCents', None)
            }

    # Convert 'soldAt' timestamp to readable date
    if 'soldAt' in property_info and property_info['soldAt']:
        try:
            sold_at_timestamp = float(property_info['soldAt'])
            from datetime import datetime
            sold_at_date = datetime.fromtimestamp(sold_at_timestamp)
            property_info['soldAt'] = sold_at_date.strftime('%Y-%m-%d')
        except ValueError:
            pass  # Keep the original value if conversion fails

    # Include fields that may be NULL in this instance
    possible_fields = [
        'fee', 'formattedFloor', 'squareMeterSellingPrice',
        'yearlyArrendeFee', 'yearlyLeaseholdFee', 'housingCooperative'
    ]
    for field in possible_fields:
        if field not in property_info:
            property_info[field] = None  # Set to None if not present

    return property_info


# Initialize the driver
driver = setup_driver()

# Navigate to the target URL
url = 'https://www.hemnet.se/salda/villa-6rum-moro-backe-skelleftea-kommun-pulkstigen-1-2861477661473764060'
driver.get(url)


# Extract coordinates
latitude, longitude = extract_coordinates(driver)
if latitude and longitude:
    print(f"Latitude: {latitude}, Longitude: {longitude}")
else:
    print("Coordinates not found.")

# Extract property information from JSON
property_info = extract_property_info_from_json(driver)

# Add coordinates to property_info
property_info['latitude'] = latitude
property_info['longitude'] = longitude

# Close the driver
driver.quit()

# Display the collected property information
print("\nCollected Property Information:")
for key, value in property_info.items():
    print(f"{key}: {value}")

# Optional: Convert to pandas DataFrame for storage in Parquet file
import pandas as pd

# Since property_info may contain nested dictionaries/lists, we need to flatten it
from pandas.io.json import json_normalize

# Flatten the dictionary
df = json_normalize(property_info, sep='_')

# Display the DataFrame
print("\nDataFrame:")
print(df)

# Save to Parquet file
df.to_parquet('property_info.parquet', index=False)