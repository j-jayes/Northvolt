# utils.py

from seleniumwire import webdriver  # Import from seleniumwire
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import time
import json
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
import gzip

def setup_driver():
    """
    Setup the Selenium WebDriver with Selenium Wire capabilities.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-infobars')

    # Initialize WebDriver using ChromeDriverManager
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def extract_coordinates(driver):
    """
    Extracts the coordinates from the GraphQL response.
    """
    # Clear previous requests
    del driver.requests

    # Wait for network requests to complete
    time.sleep(1)

    # Iterate over all intercepted requests
    for request in driver.requests:
        if 'graphql' in request.url:
            try:
                # Decode the request body
                request_body = request.body.decode('utf-8')
                if '"operationName":"saleMap"' in request_body:
                    # Decode the response body
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
                print(f"Error extracting coordinates: {e}")
    return None, None

def extract_property_info_from_json(driver):
    """
    Extracts the property information from the JSON data in the <script> tag.
    Returns a dictionary with the data.
    """
    try:
        # Wait for the script tag to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, '__NEXT_DATA__'))
        )
        # Find the <script> tag with id="__NEXT_DATA__"
        script_tag = driver.find_element(By.ID, '__NEXT_DATA__')
        json_content = script_tag.get_attribute('innerHTML')
        data = json.loads(json_content)
    except (NoSuchElementException, TimeoutException, json.JSONDecodeError):
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
            return {}
    except KeyError:
        return {}
    
    # Collect all property data
    property_info = {}
    
    # Exclude image data and ad targeting
    excluded_keys = ['attributedImages', 'adTargeting']

    for key, value in property_data.items():
        if key in excluded_keys:
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

    # Process nested fields and dereference as necessary
    # (Same as previous code)
    # Process 'broker' and 'brokerAgency'
    if 'broker' in property_info and property_info['broker']:
        broker_data = property_info['broker']
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

    # Process 'districts'
    if 'districts' in property_info and property_info['districts']:
        districts_list = []
        for district in property_info['districts']:
            district_data = district
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


def get_property_links(driver, location_ids, page=1):
    """
    Extracts property links from the listing page.
    Returns a list of URLs.
    """
    base_url = 'https://www.hemnet.se/salda/bostader'
    params = f'?location_ids={location_ids}&page={page}'

    url = base_url + params
    driver.get(url)

    # Wait for the property listings to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="result-list"] a.Card_hclCard__v27k7'))
        )
    except TimeoutException:
        return []

    property_links = []

    # Find all property items based on the updated class structure
    property_items = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="result-list"] a.Card_hclCard__v27k7')
    for item in property_items:
        try:
            link = item.get_attribute('href')
            if link:
                property_links.append(link)
        except NoSuchElementException:
            continue

    return property_links

def get_total_pages(driver, location_ids):
    """
    Determines the total number of pages in the listing.
    """
    base_url = 'https://www.hemnet.se/salda/bostader'
    params = f'?location_ids={location_ids}'

    url = base_url + params
    driver.get(url)

    try:
        # Wait for the pagination to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.Pagination_hclPaginationItems__3newI'))
        )
    except TimeoutException:
        # Only one page or no pagination
        return 1

    # Find the total number of pages by looking for page numbers in the pagination items
    pagination_elements = driver.find_elements(By.CSS_SELECTOR, 'div.Pagination_hclPaginationItems__3newI a')
    page_numbers = []
    for page_element in pagination_elements:
            try:
                # Try to get the text content using 'textContent' or 'innerText' attributes
                text = page_element.get_attribute('textContent').strip() or page_element.get_attribute('innerText').strip()
                if text.isdigit():
                    page_numbers.append(int(text))
            except NoSuchElementException:
                continue
    if page_numbers:
        return max(page_numbers)
    else:
        return 1