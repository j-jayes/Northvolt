from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# Set up Selenium to use browser and capture network traffic
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

# Go to the page
driver.get("https://www.hemnet.se/salda/lagenhet-2rum-norrbole-skelleftea-kommun-asgatan-33c-4588327981333684215")

# Access the network requests made by the browser
for request in driver.requests:
    if "SingleImageSearch" in request.url:
        if request.response:
            print(request.response.body)

# Close the browser
driver.quit()
