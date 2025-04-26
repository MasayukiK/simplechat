# lambda/index.py
import json
import os
import boto3
import re  # 正規表現モジュールをインポート
from botocore.exceptions import ClientError
import urllib.request


# Lambda コンテキストからリージョンを抽出する関数
def extract_region_from_arn(arn):
    # ARN 形式: arn:aws:lambda:region:account-id:function:function-name
    match = re.search('arn:aws:lambda:([^:]+):', arn)
    if match:
        return match.group(1)
    return "us-east-1"  # デフォルト値

# グローバル変数としてクライアントを初期化（初期値）
#bedrock_client = None

# モデルID
#MODEL_ID = os.environ.get("MODEL_ID", "us.amazon.nova-lite-v1:0")

def lambda_handler(event, context):
    try:
        print("Received event:", json.dumps(event))
        
        # Cognitoで認証されたユーザー情報を取得
        user_info = None
        if 'requestContext' in event and 'authorizer' in event['requestContext']:
            user_info = event['requestContext']['authorizer']['claims']
            print(f"Authenticated user: {user_info.get('email') or user_info.get('cognito:username')}")
        
        # リクエストボディの解析
        body = json.loads(event['body'])
        message = body['message']
        conversation_history = body.get('conversationHistory', [])
        
        print("Processing message:", message)
        #print("Using model:", MODEL_ID)
        
        # 会話履歴を使用
        messages = conversation_history.copy()
        
        # ユーザーメッセージを追加
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Day1/03_FastAPI 用のリクエストペイロードを構築
        # 会話履歴を含含まない
        # 　　含める場合はどうするか？APIはリスト（辞書）をサポートせず、入力は単純な string。
        #     以下のような文字列を作って送ればよいか？ YAML にする？
        #       ---
        #       あなたとの会話の履歴もふまえて、質問に答えてください。
        #       - 会話の履歴
        #           - わたし： xxx
        #           - あなた： yyy
        #               ...
        #       - 質問：zzz
        #       ---

        do_sample=True
        theJson = {
            "prompt": message,
            "max_new_tokens": 512,
            "do_sample": do_sample,
            "temperature": 0.7,
            "topP": 0.9
        }
        
        theJsonDump = json.dumps(theJson)
        theJsonDumpEncoded = theJsonDump.encode("utf-8")
        print("Calling 03_FastAPI with payload:", theJsonDump)
        
        
        # APIを呼び出し
        theWebApiUrl = "https://5afa-34-83-88-225.ngrok-free.app" # CHANGE HERE !
        req = urllib.request.Request(
                f"{theWebApiUrl}/generate",
                data=theJsonDumpEncoded,
                headers={"Content-Type": "application/json"},
                method="POST"
        )

        with urllib.request.urlopen(req) as response:
            theHttpStatus = response.getcode()
            if theHttpStatus == 200:
                theApiResultStr = response.read().decode("utf-8")
                theApiResultJson = json.loads(theApiResultStr)
                print( "SPI response :", json.dumps(theApiResultJson))

                assistant_response = theApiResultJson["generated_text"]

            else:
                print( f"ERROR: {theHttpStatus}" )
                assistant_response = f"ERROR: {theHttpStatus}"

        
        # アシスタントの応答を会話履歴に追加
        messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # 成功レスポンスの返却
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_response,
                "conversationHistory": messages
            })
        }
        
    except Exception as error:
        print("Error:", str(error))
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST"
            },
            "body": json.dumps({
                "success": False,
                "error": str(error)
            })
        }
