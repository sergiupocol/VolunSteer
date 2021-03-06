import mysql.connector
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import os
from selenium.webdriver.common.keys import Keys
import time
import datetime



num_pos = input('How many positions would you like to add?\n')

num_pos_val = int(num_pos)


### SET UP CHROME DOWNLOAD OPTIONS
chrome_options = webdriver.ChromeOptions()
prefs = {'download.default_directory':os.getcwd()}
chrome_options.add_experimental_option('prefs', prefs)


# CHANGE THIS TO WORK FOR ANYONE
driver = webdriver.Chrome(os.getcwd() + '/chromedriver', options=chrome_options)
# Optional argument, if not specified will search path.

#################################################################################
# LEADS
#################################################################################
driver.get('https://leads.uwaterloo.ca/Account/LogOn?ReturnUrl=%2f')



# GET THE USERNAME AND PASSWORD FIELDS FOR INPUT
username_box = driver.find_element_by_name('UserName')
password_box = driver.find_element_by_name('Password')


# Now get user input:
username = input('Please enter your WatIAM username:\n')
password = input('Please enter your WatIAM password:\n')

# Now get user input:
vc_username = input('Please enter your FEDS username:\n')
vc_password = input('Please enter your FEDS password:\n')

# Type the password and username in:
username_box.send_keys(username)
password_box.send_keys(password)

# submit credentials
login_button = driver.find_element_by_class_name('submitBtn')
login_button.click()

# Now that i'm logged in, I need to open the job positions:
main_menu = driver.find_element_by_xpath('//*[@id="main-menu"]/ul/li[4]/a')
main_menu.click()

# A table w 3 columns
leads_info = []

# Now I'm on the leads page. I need to get a list of positions:
leads_soup = BeautifulSoup(driver.page_source, 'html.parser')
for organization in leads_soup.find_all('fieldset'):
    if (organization.parent.name != 'fieldset'):
        continue
    org_name = "NEEDS TO BE UPDATED"
    if (organization.legend == None) :
        continue
    try:
        org_name = organization.legend.string.strip(' \t\n')
        org_name = org_name[:len(org_name) - 18]
        for position in organization.find_all('a'):
            if (position.parent.name == 'div'):
                leads_info.append([org_name, position.text, 'https://leads.uwaterloo.ca' + position.get('href')])
    except:
        continue
    finally:
        print("CRITICAL FAIL")


## CREATE A DATA FRAME WITH THE POSITIONS ON THE FIRST PAGE OF LEADS
## COLUMNS ARE ORG POS AND LINK TO INFO
## THEN SEARCH EACH ROW IN THE VC DATABSE

leads_positions = pd.DataFrame(leads_info, columns = ['Organization', 'Job Name', 'URL'])

#################################################################################
# VOLUNTEERING CENTER
#################################################################################


# GET AS INOUT THE DESIRED NUMBER OF POSITIONS TO BE UPDATED, AND HOW FAR
## uSE mySQL TO STORE WHATS ALREADY BEEN USED
### NOW GO AND SEE IF A POSITION EXISTS IN THE DB ALREADY AND IF NOT THEN...
## THE ADDING BEGINS
driver.get('https://volunteer.feds.ca/AdminListings.php?ListType=Volunteer_PositionsMembersAdmin&MenuItemID=22');


# GET THE USERNAME AND PASSWORD FIELDS FOR INPUT
vc_username_box = driver.find_element_by_name('Username')
vc_password_box = driver.find_element_by_name('Password')



# Type the password and username in:
vc_username_box.send_keys(vc_username)
vc_password_box.send_keys(vc_password)

# click LOGIN
driver.find_element_by_name('cls_logon_submit').click()

## HERE ENSURE THAT ANOTHER VOLUNTEER DIDN'T ALREADY TRY TO ENTER THE POSITION
driver.get('https://volunteer.feds.ca/AdminListings.php?ListType=Volunteer_Positionsadmin&Position_Status=1')




pending_info = []
pending_positions_soup = BeautifulSoup(driver.page_source, 'html.parser')
pending_list = pending_positions_soup.find_all('tr', class_='listTableRow listTableRowEven') + pending_positions_soup.find_all('tr', class_='listTableRow listTableRowOdd')

for pending_pos in pending_list:
    try:
        organization = pending_pos.find('td', class_='listCell colnum_2 mode-normal').text.strip('\n')
        title = pending_pos.find('a').text
        pending_info.append([organization, title])
    except:
        continue
pending_positions = pd.DataFrame(pending_info, columns=['Organization', 'Job Name'])


driver.get('https://volunteer.feds.ca/Listings.php?ListType=Volunteer_PositionsAll&MenuItemID=1')

for index, row in leads_positions.iterrows():
    if (num_pos_val == 0):
        break

    driver.find_element_by_name('keyword').clear()
    driver.find_element_by_name('keyword').send_keys(row['Job Name'])
    driver.find_element_by_name("Action").click()
    if (driver.find_element_by_id('listCellNoMatch_Volunteer_PositionsAll') == None):
        continue
    ### NOW CHECK IF THERES A MATCH WITH PENDING POSITIONS
    match = False



    for index_pending, row_pending in pending_positions.iterrows():
        if (((row['Organization'] in row_pending['Organization']) or (row_pending['Organization'] in row['Organization']))
                and ((row['Job Name'] in row_pending['Job Name']) or (row_pending['Job Name'] in row['Job Name']))):
            match = True
    if match:
        driver.get('https://volunteer.feds.ca/Listings.php?ListType=Volunteer_PositionsAll&MenuItemID=1')
        continue


    # NOW DO ALL THE STUFF HERE
    ############################### FILLING IN THE FORM

    # GET THE URL WITH INFO
    driver.get(row['URL'])

    position_info_soup = BeautifulSoup(driver.page_source, 'html.parser')
    all_text = position_info_soup.find('fieldset')
    text_info = ""
    for string in all_text.stripped_strings:
        text_info = text_info + repr(string)

    text_info = text_info.replace('\'\'', ' ')

    # text info has ALL THE INFO YOU NEED TO FILL OUT THE FORM
    # START FILLING OUT THE FORM
    driver.get('https://volunteer.feds.ca/AdminEdit.php?FormAction=Add&ListType=Volunteer_PositionsAdmin')



    ## SELECT THE ORGANIZATION
    for org_option in driver.find_elements_by_tag_name('option'):
        parent = org_option.find_element_by_xpath('..')
        if (parent.get_attribute('class') != 'requiredField AEFField AEFField AEFFieldVolunteer_PositionsAdminAgency_number'):
            continue

        if (org_option.text.strip() in row['Organization']) or \
                (row['Organization'] in org_option.text.strip()):
            org_option.click()
            break


    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminPosition_Title"]').send_keys(row['Job Name'])
    description = text_info[(text_info.index('Job Description: ') + len('Job Description: ')):text_info.index(' Application Open')]
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminDuties"]').send_keys(description)
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminAreasOfInterest1"]').click()
    try:
        end_date = text_info[text_info.index('Application Deadline: ') + len('Application Deadline: '):text_info.index(' PM')]
    except:
        end_date = datetime.datetime.today()
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminTerm_Date"]').send_keys(end_date[:len(end_date) - 6])
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminDuration"]/option[3]').click()
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminSpecialeventdate"]').clear()
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminSpecialeventenddate"]').clear()
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminTimeCommitment1"]').click()
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminVolType1"]').click()
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminApply_type2"]').click()
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminapply_link"]').send_keys(row['URL'])
    driver.find_element_by_xpath('//*[@id="Volunteer_PositionsAdminGeographical_Location6"]').click()


    driver.find_element_by_xpath('//*[@id="AEFTblVolunteer_PositionsAdmin"]/tbody/tr[32]/td/input').click()

    num_pos_val = num_pos_val - 1
    driver.get('https://volunteer.feds.ca/Listings.php?ListType=Volunteer_PositionsAll&MenuItemID=1')
    #### SERGIU MAKE SURE U RETURN TO THE PREVIOUS PAGE


print("DONE! Please go and review the information and publish the positions!")
driver.quit()