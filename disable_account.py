"""
Given a username disable their gmail account, migrate it to the suspended users list, and disable their domain accounts
"""


# --- IMPORT MODULES ----------
# -----------------------------


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user']


def main():
    """Shows basic usage of the Admin SDK Directory API.
    Prints the emails and names of the first 10 users in the domain.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
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


# --- API CALL GOES HERE -------------------------------------------------------

    username = input("Enter Username: ")
    response = service.users().update(userKey="{0}@spinvfx.com".format(username), body={"suspended": True, "orgUnitPath": "/Suspended"}).execute()
    print(json.dumps(response, sort_keys=True, indent=4))

# ------------------------------------------------------------------------------


# Working. Commented out due to irrelevance / uses PowerShell 
# --- HANDLE DOMAIN ACCOUNT ----------------------------------------------------

    # date = input("Enter Date (yyyymmdd): ")
    # ticket = input("Enter Full Ticket (SSD-xxxx): ")
    # desc = "Disabled {0} per {1}".format(date, ticket)
    # command = "Get-ADUser -Filter \'samaccountname -eq \"{0}\"\' -Properties Description | Disable-ADAccount -PassThru | Set-ADUser -Description \"$($_.Description) {1}\" -PassThru| Move-ADObject -TargetPath \"OU=Users - Disabled\"".format(username, desc)
    # exec = sub.Popen(["powershell","& {" + command + "}"])

# ------------------------------------------------------------------------------


if __name__ == '__main__':
    main()