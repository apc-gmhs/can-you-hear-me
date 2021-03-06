import schoolopy
import yaml
import time

BLOCKED = []

SUBJECT = 'subject'
BODY = 'body'

# Load staff names from file
with open('staff.yml') as file:
    # STAFF is a list of lists containing first and last names. Decoding as tuples might require extra effort
    # E.x. [['First', 'Last']]
    STAFF = yaml.load(file, Loader=yaml.FullLoader)

# Load schoology api keys from file
with open('keys.yml') as file:
    keys = yaml.load(file, Loader=yaml.FullLoader)

sc = schoolopy.Schoology(schoolopy.Auth(keys['public'], keys['secret']))

def schoology_req(endpoint, data=None):
    if data is not None:
        res = sc.schoology_auth.oauth.post(endpoint, headers=sc.schoology_auth._request_header(), auth=sc.schoology_auth.oauth.auth, json=data)
    else:
        res = sc.schoology_auth.oauth.get(endpoint, headers=sc.schoology_auth._request_header(), auth=sc.schoology_auth.oauth.auth)
    return res

def get_paged_data(
    request_function, 
    endpoint: str, 
    data_key: str,
    next_key: str = 'links',
    max_pages: int = -1, 
    *request_args, 
    **request_kwargs
):
    """
    Schoology requests which deal with large amounts of data are paged.
    This function automatically sends the several paged requests and combines the data
    """
    data = []
    page = 0
    next_url = ''
    while next_url is not None and (page < max_pages or max_pages == -1):
        json = request_function(next_url if next_url else endpoint, *request_args, **request_kwargs).json()
        try:
            next_url = json[next_key]['next']
        except KeyError:
            next_url = None
        data += json[data_key]
        page += 1

    return data

# Add all users in the GMHS building to a list, excluding many staff members.
user_ids = []
users = get_paged_data(schoology_req, 'https://api.schoology.com/v1/users?building_id=10704963&limit=200', 'user')
for user in users:
    if [user['name_first'], user['name_last']] not in STAFF:
        user_ids.append((user['uid'], user['name_first'], user['name_last']))

# Add all people that have already received messages to a "BLOCKED" list
sent = get_paged_data(schoology_req, 'https://api.schoology.com/v1/messages/sent?limit=200', 'message')
for message in sent:
    BLOCKED.append(message['recipient_ids'])

# Change to True to actually send the messages
if False:
    num = 0
    for user_id, name, last in user_ids:
        if str(user_id) in BLOCKED:
            print('SKIPPING: ' + str(user_id) + ' | ' + name)
            continue

        print(f'{num + 1} - Sending to: {user_id} ({name}) ...', end='')
        schoology_req('https://api.schoology.com/v1/messages', data={
            'subject': SUBJECT,
            'message': BODY,
            'recipient_ids': str(user_id)
        })
        print('Success')

        time.sleep(1)
        num += 1
    print('Total messages sent: ' + str(num))
