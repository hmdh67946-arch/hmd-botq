import os
import asyncio
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "MT5 Trading Bot is running!"

async def main():
    # ضع رمز التوثيق (Token) وحساب MetaApi الخاص بك هنا أو عبر متغيرات البيئة في رندر
    token = os.environ.get('METIAPI_TOKEN', 'YOUR_TOKEN')
    account_id = os.environ.get('METIAPI_ACCOUNT_ID', 'YOUR_ACCOUNT_ID')
    
    metaapi = MetaApi(token)
    try:
        account = await metaapi.metatrader_account_api.get_account(account_id)
        print("Connected to account:", account.name)
        
        # الانتظار حتى يصبح الحساب جاهزاً
        if account.state != 'DEPLOYED':
            await account.deploy()
        
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # جلب معلومات الحساب كمثال
        account_information = await connection.get_account_information()
        print("Account Balance:", account_information['balance'])
        
    except Exception as e:
        print("Error connecting to MetaApi:", e)

def run_bot():
    asyncio.run(main())

if __name__ == '__main__':
    # تشغيل البوت في الخلفية وتشغيل سيرفر ويب لكي يقبله موقع Render
    import threading
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
