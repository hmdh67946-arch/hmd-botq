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
    
    token = (
        os.environ.get('METIAPI_TOKEN') or 
        os.environ.get('METAAPI_TOKEN') or 
        os.environ.get('TOKEN')
    )
    
    account_id = '0f7c93b4-3c22-47c3-8be2-f9eaaf46a3f5'
    
    if not token:
        print("ERROR: MetaApi Token is missing!", flush=True)
        return

    try:
        metaapi = MetaApi(token)
        print(f"Connecting to MetaApi account: {account_id}...", flush=True)
        account = await metaapi.metatrader_account_api.get_account(account_id)
        
        if account.state != 'DEPLOYED':
            await account.deploy()
            
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        # جلب وطباعة رموز التداول المتاحة في حسابك لكي نرى رمز الذهب بدقة
        print("Fetching available symbols from broker...", flush=True)
        specifications = await connection.get_symbol_specifications()
        symbols = [spec['symbol'] for spec in specifications]
        print(f"Available symbols: {symbols}", flush=True)
        
        # البحث عن الرمز الأقرب للذهب
        gold_symbols = [s for s in symbols if 'XAU' in s or 'GOLD' in s]
        print(f"Detected Gold symbols on your account: {gold_symbols}", flush=True)
        
        # استخدام أول رمز ذهب تم العثور عليه تلقائياً، أو الرجوع إلى XAUUSD
        symbol = gold_symbols[0] if gold_symbols else 'XAUUSD'
        print(f"Using trading symbol: {symbol}", flush=True)
        
        volume = 0.01
        num_orders = 10
        
        print(f"Executing {num_orders} Buy orders on {symbol}...", flush=True)
        
        for i in range(num_orders):
            try:
                res = await connection.create_market_buy_order(
                    symbol=symbol,
                    volume=volume,
                    stop_loss=0,
                    take_profit=0
                )
                print(f"-> Order {i+1} opened successfully! Order ID: {res.get('orderId')}", flush=True)
            except Exception as ord_e:
                print(f"-> Failed to open order {i+1}: {ord_e}", flush=True)
            
            await asyncio.sleep(0.4)
            
        print("=== Execution finished ===", flush=True)

    except Exception as e:
        print(f"MetaApi Error: {e}", flush=True)

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
