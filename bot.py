import os
import asyncio
import sys
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD Trading Bot is active and running!"

async def main():
    print("=== Bot execution started ===", flush=True)
    token = os.environ.get('METIAPI_TOKEN')
    account_id = os.environ.get('METIAPI_ACCOUNT_ID')
    
    if not token or not account_id:
        print("ERROR: METIAPI_TOKEN or METIAPI_ACCOUNT_ID is missing!", flush=True)
        return

    metaapi = MetaApi(token)
    try:
        print(f"Connecting to MetaApi account ID: {account_id}", flush=True)
        account = await metaapi.metatrader_account_api.get_account(account_id)
        print("Connected to account successfully:", account.name, flush=True)
        
        if account.state != 'DEPLOYED':
            print("Deploying account...", flush=True)
            await account.deploy()
            
        print("Waiting for RPC connection...", flush=True)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # جلب معلومات الحساب
        account_information = await connection.get_account_information()
        print(f"Account Balance: {account_information.get('balance')}", flush=True)
        
        symbol = 'XAUUSD'
        volume = 0.01
        num_orders = 10
        
        # يمكنك تغييرها إلى create_market_sell_order لو أردت بيع
        print(f"Starting to open {num_orders} Buy orders on {symbol} with volume {volume}...", flush=True)
        
        for i in range(num_orders):
            try:
                result = await connection.create_market_buy_order(
                    symbol=symbol, 
                    volume=volume, 
                    stop_loss=0, 
                    take_profit=0
                )
                print(f"-> Order {i+1} opened successfully. Result ID: {result.get('orderId')}", flush=True)
            except Exception as ord_err:
                print(f"-> ERROR opening order {i+1}: {ord_err}", flush=True)
            
            await asyncio.sleep(0.3)
            
        print("=== All orders batch processed ===", flush=True)
        
    except Exception as e:
        print(f"CRITICAL ERROR in trading bot main loop: {e}", flush=True)

def run_bot():
    asyncio.run(main())

if __name__ == '__main__':
    import threading
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
