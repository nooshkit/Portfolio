"""
This script was a spot test at the request of the executives
Given a user check what their Google Meets history was for the time frame, then write it to a report
"""


# --- IMPORT MODULES ----------
# -----------------------------


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


# The ID of spreadsheet.
spreadsheet_id = '1_CAx2GZihPlATjWWKu3dsuO-GA1n_5Meg5NNf432Bas'


date = datetime.today().strftime('%Y%m%d')


# --- OPEN API CONNECTION ----------
def open_connection(body):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if 'GSUITEAPITOKEN' in os.environ:
        print("Found Token")
        creds = Credentials.from_authorized_user_file(os.environ['GSUITEAPITOKEN'], SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(os.environ['GSUITEAPI'], SCOPES)
            creds = flow.run_local_server(port=0)
    print("Auth. Successful, building service...")
    service = build('sheets', 'v4', credentials=creds)

    try:
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    except HttpError as err:
        print(err)
# ----------------------------------


# --- SEND CSV DATA ----------
def build_request():
    with open('/home/jenkins/machine_assignments/{}.csv'.format(date), 'r') as csv_file:
        csv_contents = csv_file.read()
    
    body = {'requests': [
            {'addSheet': {
                'properties': {
                    'title': date, 'sheet_id': date
                    }
                }
            },
            {'pasteData': {
                'coordinate': {
                    'sheetId': date, 
                    'rowIndex': '0', 
                    'columnIndex': '0'
                    }, 
                "data": csv_contents, 
                "type": 'PASTE_NORMAL', 
                "delimiter": ','
                }
            },
            {'sortRange': {
                "range": {
                    "sheetId": date, 
                    "startRowIndex": 1, 
                    "startColumnIndex": 0}, 
                    "sortSpecs": [
                        {"sortOrder": "ASCENDING", 
                         "dimensionIndex": 0
                         }
                    ]
                }
            }                        
                    ]
            }

    return body
# ----------------------------


if __name__ == '__main__':
    open_connection(build_request())