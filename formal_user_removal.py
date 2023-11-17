"""
This was in use in production and about to be deployed to Jenkins
When HR submits a ticket requesting a user's offboarding disable their gmail, domain accounts, and remove their VM's from our company VM portal
"""


# --- IMPORT MODULES ----------
# -----------------------------


# --- SETUP JIRA API ------------
jiraOptions = {'server': "server"}
auth_email = "email"
apiToken = "token"

jira = JIRA(options=jiraOptions, basic_auth=(auth_email , apiToken))
# -------------------------------


# --- FIND USERNAME IN AD ----------
def find_username(user_cn):
    log_info("Finding user's account...")

    # search AD for manager's name and return USERNAME
    # USERNAME can then be used to set the manager field when creating the user
    command = "get-aduser -filter \"cn -eq \'{}\'\" -Properties samaccountname | select -expandproperty samaccountname".format(user_cn)
    exec = sub.Popen(["powershell","& {" + command + "}"], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    res, err = exec.communicate()

    log_info("Found: {}@spinvfx.com".format(res.strip()))
    return res.strip()
# ----------------------------------


# --- DISABLE AD ACCOUNT ----------
def disable_ad(user_username, ticket_number):
    date = datetime.today().strftime('%Y%m%d')
    new_description = "Disabled {} per {}".format(date, ticket_number)

    command = "Get-ADUser -Filter \'samaccountname -eq \"{0}\"\' | Disable-ADAccount -PassThru | Set-ADUser -Description \"{1}\" -PassThru| Move-ADObject -TargetPath \"OU=Users - Disabled\"".format(user_username, new_description)
    exec = sub.Popen(["powershell","& {" + command + "}"], stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    res, err = exec.communicate()
    
    if len( err ) > 0: log_info("Error! Something Went Wrong With Powershell\n++++++++++\n{}\n++++++++++".format(err.strip())); exit()
# ---------------------------------


# --- REMOVE MACHINE ASSIGNMENTS ----------
def remove_machines(auth_key, user_username):
    user_email = user_username + "@spinvfx.com"
    # - DECLARE DEPLOYMENTS -
    di = {
        "uswe": "region unique id", 
        "usea": "region unique id",
        "asia": "region unique id",
        "spin": "region unique id"
        }
    # -----------------------
    # - API VALUES - 
    api_url = "Company Teradici URL"
    session = requests.Session()
    session.headers.update({"Authorization": auth_key})
    params = {'limit': 500}
    # --------------
    # - FIND AND REMOVE ASSIGNMENTS -
    for i in di:
        # - FIND ASSIGNMENTS -
        response = session.get("{0}/deployments/{1}/entitlements?upn={2}".format(api_url, di[i], user_email), params=params)
        if not response.status_code == 200:
            raise Exception(response.text)
        response_body = response.json()
        values = response_body.get('data')
        # --------------------
        # - GET ASSIGNMENT ID'S -
        for value in values:
            if not value or value is None:
                log_info("No Assignments Found In {}".format(i))
                break
            log_info("Removing Assignment - {} in {}".format(str(value['resource']['machineName']), i))
        # -----------------------
        # - REMOVE ASSIGNMENTS -
            response = session.delete("{0}/deployments/{1}/entitlements/{2}".format(api_url, value['deploymentId'], value['entitlementId'], params=params))
            if not response.status_code == 200:
                log_info("Error! CAS response code: {}".format(response.status_code))
                raise Exception(response.text)
            log_info("Removed...")
        # ----------------------
    # ------------------------------
# -----------------------------------------


# --- SUSPEND AND MOVE GMAIL ACCOUNTS ----------
def suspend_gmail(user_username):
    SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())   
    service = build('admin', 'directory_v1', credentials=creds)
    log_info("Suspending {0}@spinvfx.com and moving to Suspended OU".format(user_username))
    response = service.users().update(userKey="{0}@spinvfx.com".format(user_username), body={"suspended": True, "orgUnitPath": "/Suspended"}).execute()
    log_info(u'Confirming: Suspended={0} New Path=({1})'.format(response['suspended'], response['orgUnitPath']))
# ----------------------------------------------


# --- SEND CONFIRMATION ----------
def send_confirmation(ticket_number):
    ticket_object = jira.issue(ticket_number)
    
    log_info("Sending Confirmation")
    message = "Users Accounts Have Been Suspended"
    jira.add_comment(ticket_object, message)
    log_info("Confirmation Sent")

    log_info("Transitioning Status")
    jira.transition_issue(ticket_object, '101')
    log_info("Transitioned!")
# --------------------------------


# --- LOGGING INFO ----------
def log_info(log):
    log_dir = 'run_logs.txt'
    timestamp = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
    print(log)
    with open(log_dir, "a") as log_file:
        log_file.write("{0} : {1}\n".format(timestamp, log))
# ---------------------------


if __name__ == "__main__":
    log_info("\nBeginning")
    #1 get ticket
    ticket_number = "SSD-" + re.findall(r'\d+', input("Enter ticket number: "))[0]
    log_info(ticket_number)
    ticket = jira.issue(ticket_number)

    #2 get user_cn off ticket
    name = str(ticket.fields.customfield_10117)

    #3 match to username
    username = find_username(name)

    #4 verify the user is correct
    proceed = input("Disabling: {}\nProceed?  [y]es / [n]o ".format(username))
    if 'y' in proceed: log_info("User Input: {0} - Removing...".format(proceed))
    else: log_info("User Input: {0} - Exiting...".format(proceed)); exit()

    #5 disable AD accounts
    disable_ad(username, ticket_number)

    #6 suspend GMAIL and move OU
    suspend_gmail(username)

    #7 remove CAS assignments
    proceed = input("Remove machine assignments at this time? [y]es / [n]o ")
    if 'y' in proceed : 
        auth = input("Enter API Key: ")
        log_info("User Input: {0} - Removing...".format(proceed))
        remove_machines(auth, username)
    else: log_info("User Input: {0} - Skipping Step...".format(proceed))

    #8 send confirmation
    send_confirmation(ticket_number)
    log_info("Done!")