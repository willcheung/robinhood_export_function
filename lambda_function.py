import json
import robin_stocks
import boto3

def lambda_handler(event, context):
    import robin_stocks as r
    body = json.loads(event['body'])

    if "operation" in body:
        if body['operation'] == 'respond_to_challenge':
            response = r.respond_to_challenge(body['challenge_id'], body['sms_code'])
            print(response)
            if 'challenge' in response and response['challenge']['remaining_attempts'] > 0:
                print("Challenge not accepted")
                return {
                    'statusCode': 202,
                    'body': json.dumps({ 'challengeId': body['challenge_id'],
                                            'message': 'That code was not correct. {0} tries remaining. Please try again. '.format(
                                                response['challenge']['remaining_attempts']) }),
                    'headers': { 'Access-Control-Allow-Origin' : '*' }
                }
            else:
                print("Challenge accepted")
                r.helper.update_session('X-ROBINHOOD-CHALLENGE-RESPONSE-ID', body['challenge_id'])
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Empty operation!'),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }
    
    if "email" in body:
        user_email = body['email']
    else:
        user_email = ""
        
    response = r.login(username=body['username'],
                        password=body['password'],
                        email=user_email,
                        expiresIn=86400,
                        by_sms=True)
    
    # First time challenge goes here b/c operation=export
    if "challenge" in response:
        return {
            'statusCode': 202,
            'body': json.dumps({ 'challengeId': response['challenge']['id'],
                                    'message': "Please enter Robinhood code to verify your identity." }),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }
        
    # Robinhood return error detail
    if "access_token" not in response:
        return {
            'statusCode': 202,
            'body': json.dumps({'message': response["detail"]}),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }

    # TODO implement different RH exports here
    if body['operation'] == 'export_options_orders':
        orders = r.export_completed_option_orders()
        return {
            'statusCode': 200,
            'body': json.dumps(orders),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }
    elif body['operation'] == 'export_stocks_orders':
        orders = r.export_completed_stock_orders()
        return {
            'statusCode': 200,
            'body': json.dumps(orders),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }
    elif body['operation'] == 'export_dividends':
        dividends = r.account.get_dividends()
        return {
            'statusCode': 200,
            'body': json.dumps(dividends),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }
    elif body['operation'] == 'respond_to_challenge':
        return {
            'statusCode': 201,
            'body': json.dumps({'message': 'Verified! Now try exporting again.'}),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid operation!'),
            'headers': { 'Access-Control-Allow-Origin' : '*' }
        }
