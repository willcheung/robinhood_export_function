import json
import robin_stocks
import boto3

def lambda_handler(event, context):
    import robin_stocks as r
    body = json.loads(event['body'])
    
    r.login(username=body['username'],
         password=body['password'],
         expiresIn=86400,
         by_sms=True,
         device_token='7971bb45-bad7-48d5-a117-65f928ee5c4d')
    
    # TODO implement different RH exports here
    if "operation" in body:
        if body['operation'] == 'export_options_orders':
            orders = r.export_completed_option_orders()
            status_code = 200
        elif body['operation'] == 'export_stocks_orders':
            orders = r.export_completed_stock_orders()
            status_code = 200
        else:
            return {
                'statusCode': 400,
                'body': 'Invalid operation!'
            }

    else:
        return {
            'statusCode': 400,
            'body': 'Empty operation!'
        }

    return {
        'statusCode': status_code,
        'body': json.dumps(orders)
    }
