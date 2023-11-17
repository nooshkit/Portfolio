"""
I wrote this to glue together the creation of accounts and used it for all accounts I created without issue
Given a ticket requesting the creation from HR, pull the data off the ticket, then use it to create everything. Gmail accounts were handled by a daily sync
"""


# --- IMPORT MODULES ----------
# -----------------------------


jiraOptions = {'server': "server"}
auth_email = "email"
apiToken = "token"

jira = JIRA(options=jiraOptions, basic_auth=(auth_email , apiToken))


#setup ability to run powershellcommands
def posh(cmd):
    p = sub.Popen(['C:\\Windows\\System32\\WindowsPowershell\\v1.0\\powershell.exe', '-Command', '{}'.format(cmd), '|', 'Convertto-Json'], stderr=sub.PIPE, stdout=sub.PIPE, universal_newlines=True)
    res, err = p.communicate()
    if len(err) > 0:
        return err.splitlines()[0]
    else:
        try:
            res = json.loads(res)
        except ValueError:
            print("Not JSON expecting answer")
        finally:
            return res


def get_ad_users():
    #retrieves a list of users in AD
    #necessary fields are:
    #   > cn (first and last name)
    #   > samaccountname (username)
    #   > uid number
    ad_list = posh("Get-ADUser -Filter \"UIDNumber -like '*'\" -Property cn, samaccountname, UIDNumber -SearchBase \"DC=spinvfx,DC=com\" | select cn, samaccountname, UIDNumber")
    return ad_list


def get_username(name, ad_list):
    #split username into first and last
    name = name.split()
    f_name = name[0]
    name.pop(0)
    
    # add all available usernames to an array to check against
    unavail_usernames = []
    for user in ad_list:
        unavail_usernames.append(user['samaccountname'])
        
    # loop through first name, concatenate with last name
    tmp = ""
    for i in range(0, len(f_name)):
        tmp = tmp + f_name[i].lower()
        username = tmp + "".join(name).lower()[:15]
        
        # check if username exists in AD already
        if username not in unavail_usernames: return username
        else: continue
    
    return username


def get_uid_no(ad_list):
    max_uuid = 0
    for user in ad_list:
        if user['UIDNumber'] not in {40001, 40003, 40100} and max_uuid <= user['UIDNumber']:
            max_uuid = user['UIDNumber'] + 1
    
    return max_uuid


def get_password():
    # locate the file containing eligible words
    wordfile = xp.locate_wordfile()
    # set specifications on words to be used
    mywords = xp.generate_wordlist(wordfile=wordfile, min_length=5, max_length=8)

    # raw_password is the generated password
    raw_password = xp.generate_xkcdpassword(mywords, numwords=2, acrostic=False, delimiter=" ")
    # below is just format handling and adding number/character to meet requirements
    newstr = []
    numbers = ('1', '2', '3', '4', '5', '6', '7', '8', '9')
    symbols = ('!', '@', '#', '&')
    for word in raw_password.split():
        # newstr.append(random.choice(numbers))
        newstr.append(word.capitalize())
    final_password = "".join(newstr) + random.choice(numbers) + random.choice(symbols)
    
    return(final_password)


def get_info(ticket, ad_list):

    #<----[Preferred Name]---->
    name = str(ticket.fields.customfield_10089).strip()
    username = get_username(name, ad_list)
    #<----[Department]---->
    department = str(ticket.fields.customfield_10067).strip()
    #<----[Position]---->
    title = str(ticket.fields.customfield_10090).strip()
    #<----[uid number]---->
    uuid_no = get_uid_no(ad_list)
    #<----[Reports To]---->
    manager = str(ticket.fields.customfield_10093)
    for user in ad_list:
        if user['cn'] == manager:
            #print("Manager: Match! " + user['cn'] + user['samaccountname'])
            manager = user['samaccountname']
        else:
            continue
    #<----[Email]---->
    email = username + "@spinvfx.com"

    #<----[Password]---->
    password = get_password()

    # #<----[VPN]---->
    # time.sleep(0.5)
    # if 'y' in input("Add to VPN group? [y/n]"): vpn = True
    # else: vpn = False
    vpn = False

    #Stored value dictionary (Key, Value)
    value_dict = {
        "Name" : name,
        "Username" : username,
        "Email" : email,
        "Department" : department,
        "Title" : title,
        "Manager" : manager,
        "UID No" : uuid_no,
        "Password" : password,
        "VPN" : vpn
    }

    return value_dict


def send_credentials(ticket, username, password):
    
    name = ticket.fields.customfield_10089.split()
    name = name[0]

    # message to be written to jira ticket. can be formatted as necessary
    message = """
Good afternoon {0},\n
Welcome to SPIN! We are so happy to have you here! Please see below your login credentials for your Spin accounts. Email will be used for GMail and Username for Teradici:\n

Email: {1}@spinvfx.com
Username: {1}
Password: {2}\n

On your first day, please log in / arrive at 9 AM EST and get ready for oreintation at 9:30 AM EST.

If at any point you have tech issues or difficulty logging in, please submit a ticket by emailing 'ithelp@spinvfx.com'

Once you've logged in Monday morning, you will see that an email has been sent to introduce you and your training buddy. They will be your point of contact for your first week to show you the ropes!

Furthermore, you have been added to our staff's Google Classroom. Whenever you have time, you can access this Classroom to refer to our policies (like how to call in sick), procedures (like how to log your time), and more!

Have a great day, and once again, welcome to SPIN!""".format(name, username, password)
    
    jira.add_comment(ticket, message)


def close_step(parent_ticket_no, x):
    #   > [0] parent ticket -- x
    #   > [1] create ad account -- x + 1
    #   > [2] create ldap acocunt -- x + 2
    #   > [3] create gmail account -- x + 3
    #   > [4] create shotgrid account -- x + 4
    close = "SSD-" + str(int(parent_ticket_no) + int(x))
    jira.transition_issue(close, "Done")


def create_user(value_dict, ticket_no):
    
    ou = "OU=Users - Active,DC=SPINVFX,DC=COM"
    #split names into first and last (fname = 0, lname = 1)
    names = value_dict["Name"].split()
    fname = names.pop(0)
    lname = "".join(names)

    date = datetime.today().strftime('%Y%m%d')

    command = """
    $name = """ + '"{}"'.format(value_dict["Name"]) + """
    $f_name = """ + '"{}"'.format(fname) + """
    $l_name = """ + '"{}"'.format(lname) + """
    $username = """ + '"{}"'.format(value_dict["Username"]) + """
    $email = """ + '"{}"'.format(value_dict["Email"]) + """
    $uuid_no = """ + '"{}"'.format(value_dict["UID No"]) + """
    $department = """ + '"{}"'.format(value_dict["Department"]) + """
    $title = """ + '"{}"'.format(value_dict["Title"]) + """
    $manager = """ + '"{}"'.format(value_dict["Manager"]) + """
    $password = ConvertTo-SecureString """ + '"{}"'.format(value_dict["Password"]) + """ -AsPlainText -Force
    $ou = """ + '"{}"'.format(ou) + """
    $vpn_val = """ + '"{}"'.format(value_dict["VPN"]) + """
    $date = """ + '"{}"'.format(date) + """
    $ticket_no = """ + '"{}"'.format(ticket_no) + """


    $groups = @("GPO Applied", "spinactive", "spinusers", "vfx")
    $primary = get-adgroup vfx -properties @("primaryGroupToken")

    New-ADUser -Name $name -GivenName $f_name -Surname $l_name -SamAccountName $username -UserPrincipalName $email -EmailAddress $email -Title $title -Department $department -Manager $manager -AccountPassword $password -Path $ou -ChangePasswordAtLogon 0 -Enabled 1 -OtherAttributes @{uidnumber=$uuid_no ; loginShell=\"/bin/bash\" ; unixHomeDirectory=\"/spin/ldap_accounts/$username\" ; gidNumber=\"1100\" ; uid=$uuid_no}
    ForEach ($group in $groups) {Add-ADPrincipalGroupMembership $username -MemberOf $group}
    Set-ADuser $username -replace @{primaryGroupID=$primary.primaryGroupToken} -Description \"Created $date per $ticket_no\"
    """

    # =====Debugging======
    # print(command)

    # choice = input("Create User? [y/n/[c]hange] \n").lower()
    # if 'n' in choice:
    #     exit()

    time.sleep(1)
    print("AD Account Created...")
    time.sleep(1)
    print("Adding Groups...")
    time.sleep(1.5)
    print("Done!")

    exec = sub.Popen(["powershell","& {" + command + "}"])


if __name__ == "__main__":
    #get list of ad users for later
    ad_list = get_ad_users()
    #regex to parse out numbers then cleaned up and returned in the format "SSD-XXXX"
    raw_ticket_no = re.findall(r'\d+', input("Enter ticket number: "))[0]
    ticket_no = "SSD-" + raw_ticket_no
    #get the requested ticket
    ticket = jira.issue(ticket_no)
    #get necessary values off ticket
    fields = get_info(ticket, ad_list)
    # approve fields // allow changes before finalization
    # very delicate and has to be entered EXACTLY. Should remove
    while True:
        time.sleep(0.5)
        print("\n----Using----")
        for keys, values in fields.items():
            print(keys + ": " + str(values))
        print("-------------\n")

        choice = input("Create User? [y/n/[c]hange] \n").lower()
        if 'n' in choice: exit() 
        elif 'c' in choice:
            print("\nCapitalization and spelling MATTER here! This is not the best method to change values!\n")
            change_key = input("Enter field to change: ").capitalize()
            change_value = input("Enter desired value: ")
            fields[change_key] = change_value
        else: break

    # Create the user in AD and Add to groups
    create_user(fields, ticket_no)
    # Attach created credentials to ticket
    print("Writing Credentials to Ticket...")
    send_credentials(ticket, fields["Username"], fields["Password"])
    # Close subtask for AD account
    close_step(raw_ticket_no, "1")
    

    input("\nPress 'ENTER' to exit...")
    exit()