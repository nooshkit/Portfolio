"""
This script goes to our company VM portal and pulls down a list of all users along with their assigned VM's
It is designed to run daily off of our Jenkins deployment
"""


# --- IMPORT MODULES ---------- 
# -----------------------------


api_url = "Company Teradici Portal"


# --- GET DEPLOYMENT API TOKEN ----------
def get_token(credentials):
    # - setup values
    request_body = dict(username=credentials.get('username'),
              password=credentials.get('apiKey'),
              tenantId=credentials.get('tenantId'))
    # - sign in as service account
    response = requests.post("{0}/auth/signin".format(api_url), json=request_body)
    
    # - verify response code
    if not response.status_code == 200:
      raise Exception(response.text)
    
    # - grab response
    response_body = response.json()

    # - set token for next use
    auth_token = response_body.get('data').get('token')

    # - establish session object for future calls
    session = requests.Session()

    session.headers.update({"Authorization": auth_token})

    return session
# ---------------------------------------


# --- PARSE JSON RESPONSE ----------
def parse_json(response, deployment):
    # - takes in json of all assignents in a deployment
    response_body = response.json()

    date = datetime.today().strftime('%Y%m%d')

    with open('/home/jenkins/machine_assignments/{}.csv'.format(date), 'a') as f:
        f.write("user, machine, deployment\n")

        # - parse out the desired values
        for line in response_body.get('data'):
            f.write(("{0}, {1}, {2}".format(line['upn'], line['resource']['machineName'], deployment)) + "\n")
# ----------------------------------


# --- GET CREDENTIALS ----------
def get_credentials():
    cred_from_secret = os.environ['CREDENTIALS']
    try:
        with open(cred_from_secret, 'r') as f:
            creds = json.loads(f.read())
            return creds
    except FileNotFoundError:
        return {}
# ------------------------------


if __name__ == "__main__":
    # - setup values for later use
    params = {'limit': 500}
    
    creds = get_credentials()

    # - loop through credentials dictionary
    for deployment in creds:
        # - get session object from 'get_token' for each deployment
        s = get_token(creds[deployment])
        
        # - get all machine assignments in each deployment
        response = s.get("{0}/deployments/{1}/entitlements".format(api_url, creds[deployment]['deploymentId']), params=params)
        
        # - verify successful status code is returned
        if not response.status_code == 200:
            raise Exception(response.text)

        # - pass to function to handle and print json results
        parse_json(response, deployment)