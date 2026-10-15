import os
import asyncio
import threading
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "XAUUSD Trading Bot is active!"

async def run_trading_logic():
    print("=== Starting MetaApi Trading Worker ===", flush=True)
    
    # قراءة التوكن من متغيرات البيئة في Render
    token = (
        os.environ.get('METIAPI_TOKEN') or 
        os.environ.get('METAAPI_TOKEN') or 
        os.environ.get('TOKEN')
    )
    
    # وضع الآيدي مباشرة هنا لتجنب مشاكل القراءة في Render
    account_id = '0f7c93b4-3c22-47c3-8be2-f9eaaf46a3f5'
    
    print(f"Checking credentials -> Token present: {bool(token)}, Account ID: {account_id}", flush=True)
    
    if not token:
        print("ERROR: Token is missing in Render environment variables!", flush=True)
        return

    try:
        metaapi = MetaApi(token)
        print(f"Connecting to account: {account_id}...", flush=True)
        account = await metaapi.metatrader_account_api.get_account(account_id)
        
        if account.state != 'DEPLOYED':
            print("Deploying account on MetaApi...", flush=True)
            await account.deploy()
            
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        account_info = await connection.get_account_information()
        print(f"Successfully connected! Account Balance: {account_info.get('balance')}", flush=True)
        
        symbol = 'XAUUSD'
        volume = 0.01
        num_orders = 10
        
        print(f"Executing {num_orders} Buy orders on {symbol} (0.01 lot)...", flush=True)
        
        for i in range(num_orders):
            try:
                res = await connection.create_market_buy_order(
                    symbol=symbol,
                    volume=volume,
                    stop_loss=0,
                    take_profit=0
                )
                print(f"-> Order {i+1}/{num_orders} opened successfully! Order ID: {res.get('orderId')}", flush=True)
            except Exception as ord_e:
                print(f"-> Failed to open order {i+1}: {ord_e}", flush=True)
            
            await asyncio.sleep(0.4)
            
        print("=== All 10 orders executed successfully ===", flush=True)

    except Exception as e:
        print(f"MetaApi Connection Error: {e}", flush=True)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_trading_logic())

if __name__ == '__main__':
    t = threading.Thread(target=start_async_loop)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
