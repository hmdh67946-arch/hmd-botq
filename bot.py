import os
import asyncio
import threading
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "Ultra-Flexible Price Flow Scalping Bot is active!"

async def trading_loop():
    print("=== Starting Ultra-Flexible Price Flow Scalper ===", flush=True)
    
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
            print("Deploying account...", flush=True)
            await account.deploy()
            
        print("Waiting for RPC connection...", flush=True)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        symbol = 'XAUUSD.ecn'
        volume = 0.01
        num_orders = 5
        target_profit = 0.15  # 0.03$ لكل صفقة × 5 صفقات = 0.15$
        max_loss = -5.00      # حد الخسارة للمجموعة 5$
        
        last_price = None
        print(f"Bot initialized. Ready to trade price flow instantly...", flush=True)
        
        while True:
            try:
                # 1. مراقبة الأرباح الفورية وإغلاق الصفقات بسرعة فائقة (كل 0.2 ثانية)
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol') == symbol]
                
                if len(group_positions) > 0:
                    total_net_profit = sum([
                        p.get('profit', 0.0) + p.get('commission', 0.0) + p.get('swap', 0.0) 
                        for p in group_positions
                    ])
                    
                    if total_net_profit >= target_profit or total_net_profit <= max_loss:
                        print(f"[TARGET HIT] Net PnL: {total_net_profit:.2f}$. Closing instantly...", flush=True)
                        close_tasks = [connection.close_position(p.get('id')) for p in group_positions]
                        await asyncio.gather(*close_tasks, return_exceptions=True)
                        print("Closed successfully. Ready for next wave...", flush=True)
                        await asyncio.sleep(1)
                    
                    await asyncio.sleep(0.2)
                    continue

                # 2. مراقبة تدفق السعر اللحظي (Price Flow) بدون شروط معقدة
                tick = await connection.get_symbol_price(symbol)
                bid = tick.get('bid', 0)
                ask = tick.get('ask', 0)
                current_price = (bid + ask) / 2
                spread = ask - bid
                
                if spread > 0.50 or last_price is None:
                    last_price = current_price
                    await asyncio.sleep(0.5)
                    continue

                # حساب التغير اللحظي البسيط جداً في السعر
                price_change = current_price - last_price
                
                # إذا صعد السعر بمقدار نقطة واحدة فجأة -> افتح شراء
                if price_change >= 0.10:
                    print(f"=== PRICE UP FLOW DETECTED (+{price_change:.2f}) -> BUY ===", flush=True)
                    buy_tasks = [
                        connection.create_market_buy_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*buy_tasks, return_exceptions=True)
                    last_price = current_price
                    
                # إذا هبط السعر بمقدار نقطة واحدة فجأة -> افتح بيع
                elif price_change <= -0.10:
                    print(f"=== PRICE DOWN FLOW DETECTED ({price_change:.2f}) -> SELL ===", flush=True)
                    sell_tasks = [
                        connection.create_market_sell_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*sell_tasks, return_exceptions=True)
                    last_price = current_price

                # تحديث السعر الأخير باستمرار
                last_price = current_price
                await asyncio.sleep(0.3)

            except Exception as loop_err:
                print(f"Loop error: {loop_err}", flush=True)
                await asyncio.sleep(1)

    except Exception as e:
        print(f"Critical error: {e}", flush=True)

def start_async_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(trading_loop())

if __name__ == '__main__':
    t = threading.Thread(target=start_async_loop)
    t.daemon = True
    t.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
