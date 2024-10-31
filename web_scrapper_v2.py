# import required module
from bs4 import BeautifulSoup
from seleniumbase import Driver, page_actions as pa
import lxml
from plyer import notification
import pandas as pd
import re, os
from seleniumbase.common.exceptions import TimeoutException, NoSuchElementException
import tkinter as tk

desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
output_file_path = os.path.join(desktop_path, "DailyNetforce.xlsx")
credentials_file_path = "credentials.txt"
# os.path.join(desktop_path, "credentials.txt")

def read_credentials(file_path):
    credentials = {}
    with open(file_path, 'r') as file:
        for line in file:
            # Split each line by colon to get key-value pairs
            key, value = line.strip().split(':', 1)
            credentials[key] = value
    return credentials

def login_with_selenium(url, credentials):
    # Navigate to netforce
    login_url = 'https://www.netforceglobal.com/vendorUser/loginredirect'
    driver = Driver(uc=True, headless=True)
    # driver.set_window_size(1920, 1080)
    # driver.maximize_window()
    driver.get(login_url)

    # Login data comes from the credentials file
    vendor_code_field = pa.wait_for_element_visible(driver, 'input#vendorCode.logininput', timeout=10)
    vendor_code_field.send_keys(credentials['vendorCode'])
    username_field = pa.wait_for_element_visible(driver, 'input#username.logininput', timeout=10)
    username_field.send_keys(credentials['username'])
    password_field = pa.wait_for_element_visible(driver, 'input#password.logininput', timeout=10)
    password_field.send_keys(credentials['password'])
    submit_button = pa.wait_for_element_visible(driver, 'input.button', timeout=10)
    driver.execute_script("arguments[0].click()", submit_button)

    # Handle secret question if required
    try:
        secret_question = pa.wait_for_element_visible(driver, 'input#secretAnswer', timeout=10)
        secret_question.send_keys(credentials['secret_question'])
        answer_submit = pa.wait_for_element_visible(driver, 'input[type="submit"][name="_action_answerquestion"]')
        driver.execute_script("arguments[0].click()", answer_submit)
    except NoSuchElementException or TimeoutException:
        pass

    return driver

def scrape_main(driver):
    filter_button = pa.wait_for_element_visible(driver, 'input[name="_action_filterbyvendor"]', timeout=10)
    driver.execute_script("arguments[0].click()", filter_button)
    pa.wait_for_element_visible(driver, 'div.message', timeout=10)
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'lxml')
    tables = soup.find_all('table')

    if len(tables)>=4:
        forth_table = tables[3]
        headers = [header.text.strip() for header in forth_table.find_all('th')]
        rows_data = []
        rows = forth_table.find_all('tr')
        for row in rows[1:]:  # Skip the header row
            # Extract data from each row
            row_data = [
                cell.text.strip().replace('\n','') for i,cell in enumerate(row.find_all('td'))
                if i in [2, 3, 6, 8, 9]
            
            ]
            if 'premium' in row.get('class', []):
            # Add 'with evidence' string to the value in column index 9
                row_data[4] += ' (with evidence for all checks)'
            # Create a dictionary mapping column headers to row data
            row_dict = dict(zip([headers[i] for i in [2, 3, 6, 8, 9]], row_data))
            # Append the row dictionary to the list of rows
            rows_data.append(row_dict)

        # print(rows_data)
        # print(forth_table)
        
        df = pd.DataFrame(rows_data)
        df['Days Pending'] = pd.to_numeric(df['Days Pending'], errors='coerce')
        df['Days Pending'] = df['Days Pending'].fillna(0).astype(int)
        pattern_1 = r"Malaysia Nationwide (with evidence for all checks)"
        pattern_2 = r"Malaysia Nationwide"
        df['Service'] = df['Service'].str.replace("Malaysia, ", "", regex=True).str.replace(pattern_1, "Criminal check (with evidence for all checks)")
        df['Service'] = df['Service'].str.replace(pattern_2, "Criminal check (with evidence only for hits)")
        df = df.sort_values(['Screening ID'])
        # df.to_excel('output.xlsx', index=False)
        return driver, df

def add_dashes(id_value):
    if id_value is not None and re.match(r'^\d{6}\d{2}\d{4}$', id_value):
        return id_value[:6] + '-' + id_value[6:8] + '-' + id_value[8:]
    else:
        return id_value

def scrape_screening_v2(driver, df):
    df['Address'] = None
    df['ID'] = None
    for index, row in df.iterrows():
        screening_id = row['Screening ID']
        driver.get(f"https://www.netforceglobal.com/screening/process/{screening_id}")
        pa.wait_for_element_visible(driver, 'h1.titlewide', timeout=10)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        table = soup.find('table')
        rows = table.find_all('tr')

        address_info = []
        gov_id_info = None
        gov_id_found = False
        found_addresses = False

        for i, tr in enumerate(rows):
            # Get Date of Birth
            dob_tr = tr.find('td', string="Date of Birth")
            if dob_tr:
                dob_td = tr.find_all('td')
                if len(dob_td) > 1:
                    dob_value = dob_td[1].text.strip()
                    df.loc[index, 'Date of birth'] = dob_value
                else:
                    df.loc[index, 'Date of birth'] = "Not Available"
            
            # Start capturing addresses after "Addresses" row
            address_tr = tr.find('td', string="Addresses")
            if address_tr:
                found_addresses = True
                continue  # Skip to next row where actual address starts

            if found_addresses:
                # Check if we've reached the "Government IDs" section
                gov_id_tr = tr.find('td', string=lambda text: "Government IDs" in text if text else False)
                if gov_id_tr:
                    gov_id_found = True
                    continue

                # Extract address info from row if it isn't government-related
                td_elements = tr.find_all('td')
                if len(td_elements) > 1:
                    address_text = td_elements[0].text.strip()
                    address_flag = td_elements[1].text.strip()

                    # Check if the address is tagged as "Current"
                    if "Current" in address_flag:
                        address_info.append(('Current', address_text))
                    elif "Previous" in address_flag:
                        address_info.append(('Previous', address_text))
                    # else:
                    #     address_info.append(("Not Tagged", address_text))

            gov_id_tr = tr.find('td', string=lambda text: "Government IDs" in text if text else False)
            if gov_id_tr:
                gov_id_found = True
                continue

            if gov_id_found:
                td_elements = tr.find_all('td')
                gov_id_text = td_elements[0].text.strip() if td_elements else ""
                # print(gov_id_text)
                if " issued by" in gov_id_text:
                    issued_by_index = gov_id_text.find(" issued by")
                    gov_id_info = gov_id_text[:issued_by_index].strip()
                    gov_id_found = False
                else:
                    gov_id_info = "Not Available"
                    gov_id_found = False
        
        # If multiple addresses exist, select the one marked as 'Current'
        current_address = None
        for address in address_info:
            if address[0] == 'Current':
                current_address = address[1]
                break
            elif address[0] == 'Not Tagged':
                current_address = address[1]
            else:
                current_address = address[1]
        
        # Update dataframe with the found address or "Not Available"
        df.loc[index, 'Address'] = current_address if current_address else "Not Available"
        df.loc[index, 'ID'] = gov_id_info
        df['ID'] = df['ID'].apply(add_dashes)
        df['Requested'] = pd.to_datetime(df['Requested'])
        df['Requested'] = df['Requested'].dt.strftime('%d-%b-%y')
        df = df.sort_values('Days Pending', ascending=False)
        df.to_excel(output_file_path, index=False)
    driver.quit()

def popup_message(message, button_text):
    root = tk.Tk()
    root.title("Extractor")
    # root.iconbitmap('automation.ico')
    label = tk.Label(root, text=message)
    label.pack(pady=20, padx=20)
    button = tk.Button(root, text=button_text, command=root.destroy)
    button.pack(pady=10)
    root.mainloop()

popup_message("Netforce Extractor is about to start..\nClick Let's Go to proceed!", "Let's Go!")
credentials = read_credentials(credentials_file_path)
driver = login_with_selenium('https://www.netforceglobal.com/screening/listbyvendor', credentials)
if driver:
    driver, df = scrape_main(driver)
    scrape_screening_v2(driver, df)
    popup_message("Netforce Extractor has completed!", "Cool!")
    