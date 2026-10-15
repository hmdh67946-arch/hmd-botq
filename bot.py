import os
import asyncio
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD Trading Bot is running!"

async def main():
    token = os.environ.get('METIAPI_TOKEN')
    account_id = os.environ.get('METIAPI_ACCOUNT_ID')
    
    metaapi = MetaApi(token)
    try:
        account = await metaapi.metatrader_account_api.get_account(account_id)
        print("Connected to account:", account.name)
        
        if account.state != 'DEPLOYED':
            await account.deploy()
        
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # جلب معلومات الحساب
        account_information = await connection.get_account_information()
        print("Account Balance:", account_information['balance'])
        
        # إعدادات التداول على الذهب فقط
        symbol = 'XAUUSD'
        volume = 0.01
        num_orders = 10  # فتح 10 صفقات
        
        # مثال: فتح صفقات شراء (Buy) - يمكنك تغييرها إلى create_market_sell_order للبيع
        print(f"Starting to open {num_orders} Buy orders on {symbol}...")
        
        for i in range(num_orders):
            try:
                result = await connection.create_market_buy_order(
                    symbol=symbol, 
                    volume=volume, 
                    stop_loss=0,  # يمكن إضافة وقف خسارة إذا أردت
                    take_profit=0 # يمكن حساب الهدف لتعويض السبريد (0.03) + الربح المطلوب
                )
                print(f"Order {i+1} opened successfully: {result.get('orderId')}")
            except Exception as ord_err:
                print(f"Error opening order {i+1}: {ord_err}")
            
            # فاصل زمني قصير بين كل صفقة وأخرى لتجنب الضغط على السيرفر
            await asyncio.sleep(0.5)
            
        print("All target orders processed.")
        
    except Exception as e:
        print("Error in trading bot:", e)

def run_bot():
    asyncio.run(main())

if __name__ == '__main__':
    import threading
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
