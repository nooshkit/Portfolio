"""
When a new project comes in we were expected to create ~15 groups total for each project
This script fetches a json config file containing the groups to be created
I then check against our Google Workspace if the new group exists, if yes: create, else: skip
"""


# --- IMPORT MODULES ------------
# -------------------------------


# --- SETUP API SCOPES ----------
# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/admin.directory.user', 'https://www.googleapis.com/auth/admin.directory.group']
# -------------------------------


# --- OPEN API CONNECTION ----------
def open_connection():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if 'GSUITEAPITOKEN' in os.environ:
        creds = Credentials.from_authorized_user_file(os.environ['GSUITEAPITOKEN'])
    # -- if no valid credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(os.environ['GSUITEAPI'], SCOPES)
            creds = flow.run_local_server(port=0)

    service = build('admin', 'directory_v1', credentials=creds)
    # -- requesting a non-existant group will return a 404 Resource not found error
    # response = service.groups().get(groupKey="testing_spin@spinvfx.com").execute()
    return service
# ----------------------------------


# --- RETRIEVE GROUPS CONFIG ----------
def get_groups():
    # -- set path
    groups_json_path = "{0}/groups.json".format(os.path.dirname(os.path.realpath(__file__)))
    # -- read in groups as json object
    with open (groups_json_path, 'r') as f:
        groups = json.loads(f.read())
    
    # -- return for use 
    return groups
# -------------------------------------


# --- VERIFY GROUP EXISTENCE ----------
def validate_groups(service_obj):
    # -- import to be created groups as json/list
    groups = get_groups()
    # -- loop through each candidate and perform creation steps
    for group in groups:
        # -- inject project name retrieved from environment variable
        group = (groups[group].format(project=os.environ['proj_name']))
        # -- check if group exists in gmail
        try:
            response = service_obj.groups().get(groupKey=group).execute()
        # -- (good path) catch 'notFound' error and create group
        except HttpError:
            print("Creating Group: {0}".format(group))
            # -!!!-
            # comment below to disable creation
            create_group(group, service_obj)
            # -!!!-
        # -- group already exists, do nothing
        else:
            print("Group: {0} already exists, skipping".format(response['email']))
# -------------------------------------


# --- CREATE GROUP ----------
def create_group(group_email, service_obj):
    request_body ={
        "email": "{}".format(group_email),
        "name": "{}".format(group_email.split("@")[0]),
        "description": "Automatically generated for project: '{}'".format(os.environ['proj_name'])
    }
    try:
        service_obj.groups().insert(body=request_body).execute()
    except HttpError as err:
        print("Oops, Something went wrong!")
        if err.resp.get('content-type', '').startswith('application/json'):
            reason = json.loads(err.content).get('error').get('errors')[0].get('reason')
            print(reason)
    else:    
        print("Group Created!")
# ---------------------------


if __name__ == "__main__":
    validate_groups(open_connection())