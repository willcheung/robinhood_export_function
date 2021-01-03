"""Contains all functions for the purpose of logging in and out to Robinhood."""
import getpass
import os
import random
import boto3
import sys
import json

import robin_stocks.helper as helper
import robin_stocks.urls as urls

def generate_device_token():
    """This function will generate a token used when loggin on.

    :returns: A string representing the token.

    """
    rands = []
    for i in range(0, 16):
        r = random.random()
        rand = 4294967296.0 * r
        rands.append((int(rand) >> ((3 & i) << 3)) & 255)

    hexa = []
    for i in range(0, 256):
        hexa.append(str(hex(i+256)).lstrip("0x").rstrip("L")[1:])

    id = ""
    for i in range(0, 16):
        id += hexa[rands[i]]

        if (i == 3) or (i == 5) or (i == 7) or (i == 9):
            id += "-"

    return(id)


def respond_to_challenge(challenge_id, sms_code):
    """This function will post to the challenge url.

    :param challenge_id: The challenge id.
    :type challenge_id: str
    :param sms_code: The sms code.
    :type sms_code: str
    :returns:  The response from requests.

    """
    url = urls.challenge_url(challenge_id)
    payload = {
        'response': sms_code
    }
    response = helper.request_post(url, payload)
    print(response)
    return(response)


def login(username=None, password=None, expiresIn=86400, scope='internal', by_sms=True, store_session=True, mfa_code=None, device_token = generate_device_token()):
    """This function will effectively log the user into robinhood by getting an
    authentication token and saving it to the session header. By default, it
    will store the authentication token in DynamoDB and load that value
    on subsequent logins.

    :param username: The username for your robinhood account, usually your email.
        Not required if credentials are already cached and valid.
    :type username: Optional[str]
    :param password: The password for your robinhood account. Not required if
        credentials are already cached and valid.
    :type password: Optional[str]
    :param expiresIn: The time until your login session expires. This is in seconds.
    :type expiresIn: Optional[int]
    :param scope: Specifies the scope of the authentication.
    :type scope: Optional[str]
    :param by_sms: Specifies whether to send an email(False) or an sms(True)
    :type by_sms: Optional[boolean]
    :param store_session: Specifies whether to save the log in authorization
        for future log ins.
    :type store_session: Optional[boolean]
    :param mfa_code: MFA token if enabled.
    :type mfa_code: Optional[str]
    :returns:  A dictionary with log in information. The 'access_token' keyword contains the access token, and the 'detail' keyword \
    contains information on whether the access token was generated or loaded from DynamoDB.

    """
    
    dynamodb = boto3.resource('dynamodb', endpoint_url="http://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table('robinhood_users')
    
    # Challenge type is used if not logging in with two-factor authentication.
    if by_sms:
        challenge_type = "sms"
    else:
        challenge_type = "email"

    url = urls.login_url()
    payload = {
        'client_id': 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS',
        'expires_in': expiresIn,
        'grant_type': 'password',
        'password': password,
        'scope': scope,
        'username': username,
        'challenge_type': challenge_type,
        'device_token': device_token
    }

    if mfa_code:
        payload['mfa_code'] = mfa_code

    # Get Item
    try:
        db_response = table.get_item(Key={'username': username})
    except ClientError as e:
        print(e.response['Error']['Message'])

    # If authentication has been stored in DynamoDB then load it. Stops login server from being pinged so much.
    if db_response.get('Item'):
        # If store_session has been set to false then delete DynamoDB record, otherwise try to load it.
        # Loading from DynamoDB will fail if the acess_token has expired.
        if store_session:
            try:
                access_token = db_response['Item']['access_token']
                token_type = db_response['Item']['token_type']
                refresh_token = db_response['Item']['refresh_token']
                # Set device_token to be the original device token when first logged in.
                existing_device_token = db_response['Item']['device_token']
                payload['device_token'] = existing_device_token
                print("Using old device token to avoid challenge.")
                # Set login status to True in order to try and get account info.
                helper.set_login_state(True)
                helper.update_session(
                    'Authorization', '{0} {1}'.format(token_type, access_token))
                # Try to load account profile to check that authorization token is still valid.
                res = helper.request_get(
                    urls.portfolio_profile(), 'regular', payload, jsonify_data=False)
                # Raises exception is response code is not 200.
                res.raise_for_status()
                print('access_token:' + access_token + ' token_type:' + token_type +
                        ' scope:' + scope + ' detail: logged in using authentication in DynamoDB' +
                        ' refresh_token: ' + refresh_token)
            except Exception:
                print("ERROR: There was an issue logging in. Authentication may be expired - logging in normally.")
                print("Unexpected exception:", sys.exc_info()[0])
                helper.set_login_state(False)
                helper.update_session('Authorization', None)
        else:
            # Delete username from DynamoDB
            db_response = table.delete_item(
                Key={
                    'username': username
                }
            )
            
    print("Posting to URL")
    data = helper.request_post(url, payload)
    print("After posting to URL")
    print(data)
    # Handle case where mfa or challenge is required.
    if data:
        if 'mfa_required' in data:
            mfa_token = input("Please type in the MFA code: ")
            payload['mfa_code'] = mfa_token
            res = helper.request_post(url, payload, jsonify_data=False)
            while (res.status_code != 200):
                mfa_token = input(
                    "That MFA code was not correct. Please type in another MFA code: ")
                payload['mfa_code'] = mfa_token
                res = helper.request_post(url, payload, jsonify_data=False)
            data = res.json()
        elif 'challenge' in data:
            print("Challenged. Saving device_token.")
            print(data)
            table.put_item(
              Item={
                    'username': username,
                    'token_type': "",
                    'access_token': "",
                    'refresh_token': "",
                    'device_token': payload['device_token']
                    }
            )
            return(data)
        # Update Session data with authorization or raise exception with the information present in data.
        if 'access_token' in data:
            token = '{0} {1}'.format(data['token_type'], data['access_token'])
            helper.update_session('Authorization', token)
            helper.set_login_state(True)
            data['detail'] = "logged in with brand new authentication code."
            print("logged in with brand new authentication code.")
            if store_session:
                table.put_item(
                  Item={
                        'username': username,
                        'token_type': data['token_type'],
                        'access_token': data['access_token'],
                        'refresh_token': data['refresh_token'],
                        'device_token': payload['device_token']
                        }
                )
        else:
            return(data)
    else:
        raise Exception('Error: Trouble connecting to robinhood API. Check internet connection.')
    
    return(data)


@helper.login_required
def logout():
    """Removes authorization from the session header.

    :returns: None

    """
    helper.set_login_state(False)
    helper.update_session('Authorization', None)
