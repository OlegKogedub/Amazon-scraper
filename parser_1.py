import time
import re
import csv
import sys
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s')

def save_to_file(html_page, file_name):

    logging.info(f"Saving page source to {file_name}")
    with open(file_name, 'w', newline='', encoding='utf-8') as htmlFile:
            htmlFile.write(html_page) 

def extract_name(soup):
    try:
        name_element = soup.find('span', {'id': 'productTitle'})
        logging.info("Attempting to extract Name")
        if name_element:
            logging.info(f"Name found: {name_element.get_text(strip=True)}")
            return name_element.get_text(strip=True)
        else:
            logging.warning("Name element not found")
            return "Not Found"
    except Exception as e:
        logging.error(f"Error occurred while extracting Name: {str(e)}")
        return "Not Found"

def extract_asin(soup):
    try:
        asin_element = soup.find('span', {'class': 'a-declarative'}, {'data-asin': True})
        logging.info("Attempting to extract ASIN")
        if asin_element:
            logging.info(f"ASIN found: {asin_element['data-asin']}")
            return asin_element['data-asin']
        else:
            logging.warning("ASIN element not found")
            return "Not Found"
    except Exception as e:
        logging.error(f"Error occurred while extracting ASIN: {str(e)}")
        return "Not Found"

def extract_price(soup):
    try:
        price_element = soup.find('span', {'id': 'priceblock_ourprice'})
        logging.info("Attempting to extract Price")
        if price_element:
            logging.info(f"Price found: {price_element.get_text(strip=True)}")
            return price_element.get_text(strip=True)
        else:
            logging.warning("Price element not found")
            return "Not Found"
    except Exception as e:
        logging.error(f"Error occurred while extracting Price: {str(e)}")
        return "Not Found"

def extract_rating(soup):
    try:
        rating_element = soup.find('span', {'data-asin-popover': True})
        logging.info("Attempting to extract Rating")
        if rating_element:
            logging.info(f"Rating found: {rating_element.get_text(strip=True)}")
            return rating_element.get_text(strip=True)
        else:
            logging.warning("Rating element not found")
            return "Not Found"
    except Exception as e:
        logging.error(f"Error occurred while extracting Rating: {str(e)}")
        return "Not Found"

def extract_answered_questions(soup):
    try:
        qna_element = soup.find('a', {'id': 'askATFLink'})
        logging.info("Attempting to extract Answered Questions")
        if qna_element:
            logging.info(f"Answered Questions found: {qna_element.get_text(strip=True).split()[0]}")
            return qna_element.get_text(strip=True).split()[0]
        else:
            logging.warning("Answered Questions element not found")
            return "Not Found"
    except Exception as e:
        logging.error(f"Error occurred while extracting Answered Questions: {str(e)}")
        return "Not Found"

def extract_amazon_data_from_url_with_selenium(url, wait_time=2):
    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    with webdriver.Chrome(options=options) as driver:
        driver.get(url)

        try:
            element_present = EC.presence_of_element_located((By.ID, 'productTitle'))
            WebDriverWait(driver, wait_time).until(element_present)
            logging.info("productTitle is present")
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            logging.info("Page source obtained and parsed")
            return {
                "Name": extract_name(soup),
                "ASIN": extract_asin(soup),
                "Price": extract_price(soup),
                "Rating": extract_rating(soup),
                "Answered Questions": extract_answered_questions(soup)
            }
        except Exception as e:
            logging.error(f"Failed to extract data for URL {url}: {e}")
            return None

def extract_all_links_with_selenium(driver, url, max_scroll=5):
    try:
        driver.get(url)
        time.sleep(5)
        for _ in range(max_scroll):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        save_to_file(soup.prettify(), 'webPage.txt')
        logging.info("Extracting all links from the webpage")
        links = [a['href'] for a in soup.find_all('a', href=True)]
        logging.info(f"Extracted links: {links}")
        return links
    except Exception as e:
        logging.error(f"Failed to extract all links: {e}")
        return []

def extract_asin_from_links(links):
    valid_asins = set()
    for link in links:
        asin_match = re.search(r'/([A-Z0-9]{10,})', link)
        if asin_match:
            asin = asin_match.group(1)
            if len(asin) == 10 and asin.isalnum() and asin.isupper():
                valid_asins.add(asin)
                logging.info(f"Valid ASIN found: {asin}")
    logging.info(f"Total valid ASINs found: {len(valid_asins)}")
    return valid_asins

def main(start_url, output_filename="amazon_product_info.csv", max_products=10):
    logging.info("Starting the script...")
    logging.info(f"Starting with initial URL: {start_url}")
    
    processed_asins = set()
    asin_queue = []

    options = webdriver.ChromeOptions()
    options.add_argument('headless')
    with webdriver.Chrome(options=options) as driver:
        logging.info("Chrome started in headless mode")
        links = extract_all_links_with_selenium(driver, start_url)
        asin_queue.extend(list(extract_asin_from_links(links)))

    logging.info(f"Found ASINs on initial page: {len(asin_queue)}")
    
    with open(output_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["Name", "ASIN", "Price", "Rating", "Answered Questions"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        while asin_queue and len(processed_asins) < max_products:
            asin = asin_queue.pop(0)
            if asin in processed_asins:
                continue
            logging.info(f"\nProcessing ASIN: {asin}")
            url = f"https://www.amazon.com/dp/{asin}"
            product_info = extract_amazon_data_from_url_with_selenium(url)
            if product_info:
                writer.writerow(product_info)
                logging.info(f"Added product info: {product_info['Name']}")
                processed_asins.add(asin)
            else:
                logging.info(f"Failed to retrieve data for ASIN: {asin}")
            
    logging.info(f"Data collection finished. Processed products: {len(processed_asins)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Please provide a starting URL as an argument.")
        sys.exit(1)
    
    start_url = sys.argv[1]
    main(start_url)
