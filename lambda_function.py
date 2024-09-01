import json
import boto3
import os
import anthropic
from datetime import datetime

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Set environment variables for DynamoDB table name and Anthropic API key
TABLE_NAME = os.environ['DYNAMODB_TABLE']
ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    # Get the bucket and file name from the S3 event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    
    # Retrieve the file from S3
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    file_content = s3_response['Body'].read().decode('utf-8')
    
    print("The customer reviews are : ",file_content)

    # Create the prompt
    prompt = f"""
    Human: You are a summarisation assistant. Your task is to summarise product reviews given to you as a list. Within this list, there are individual product reviews in an array.
    Create a JSON document with the following fields:
    summary - A summary of these reviews in less than 250 words
    overall_sentiment - The overall sentiment of the reviews
    sentiment_confidence - How confident you are about the sentiment of the reviews
    reviews_positive - The percent of positive reviews
    reviews_neutral - The percent of neutral reviews
    reviews_negative - The percent of negative reviews
    action_items - A list of action items to resolve the customer complaints (don't put something which is already good and there is no customer complaint)
    Your output should be raw JSON - do not include any sentences or additional text outside of the JSON object.
    Here is the list of reviews that I want you to summarise:
    {file_content}
    Assistant:"""

    # Call the Anthropic API
    message = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    output = message.content
    
    analysis=json.loads(output[0].text)

    table.put_item(
    Item={
        'date': datetime.today().strftime('%Y-%m-%d'),
        'create_time': datetime.today().strftime('%Y-%m-%dT%H:%M:%S'),
        'reviews_summary': analysis["summary"],
        'overall_sentiment': analysis["overall_sentiment"],
        'sentiment_confidence': str(analysis["sentiment_confidence"]),
        'reviews_positive': str(analysis["reviews_positive"]),
        'reviews_negative': str(analysis["reviews_negative"]),
        'reviews_neutral': str(analysis["reviews_neutral"]),
        'action_items': ', '.join(analysis['action_items']),
    }
)

    return {
        'statusCode': 200,
        'body': json.dumps('Summarization completed and stored successfully.')
    }
