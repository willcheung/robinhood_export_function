import json
import robin_stocks
import boto3

def lambda_handler(event, context):
    import robin_stocks as r
    body = json.loads(event['body'])

    if "operation" in body:
        if body['operation'] == 'respond_to_challenge':
            response = r.respond_to_challenge(body['challenge_id'], body['sms_code'])
            
            if 'challenge' in response and response['challenge']['remaining_attempts'] > 0:
                print("Challenge not accepted!")
                return {
                    'statusCode': 202,
                    'challengeId': body['challenge_id'],
                    'body': 'That code was not correct. {0} tries remaining. Please try again: '.format(
                        response['challenge']['remaining_attempts'])
                }
            else:
                print("Challenge accepted!")
                r.helper.update_session('X-ROBINHOOD-CHALLENGE-RESPONSE-ID', body['challenge_id'])
    else:
        return {
            'statusCode': 400,
            'body': 'Empty operation!'
        }
    
    response = r.login(username=body['username'],
                        password=body['password'],
                        expiresIn=86400,
                        by_sms=True)
    
    # First time challenge goes here b/c operation=export
    if "challenge" in response:
        return {
            'statusCode': 202,
            'challengeId': response['challenge']['id'],
            'body': "Please enter Robinhood code for validation."
        }
        
    # Robinhood return error detail
    if "access_token" not in response:
        return {
            'statusCode': 401,
            'body': response["detail"]
        }

    # TODO implement different RH exports here
    if body['operation'] == 'export_options_orders':
        orders = r.export_completed_option_orders()
        return {
            'statusCode': 200,
            'body': json.dumps(orders)
        }
    elif body['operation'] == 'export_stocks_orders':
        orders = r.export_completed_stock_orders()
        return {
            'statusCode': 200,
            'body': json.dumps(orders)
        }
    else:
        return {
            'statusCode': 400,
            'body': 'Invalid operation!'
        }
