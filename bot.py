import os
import asyncio
import threading
import pandas as pd
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "Lightning-Fast M3 Scalping Bot is active!"

async def trading_loop():
    print("=== Starting Lightning-Fast M3 Scalper Worker ===", flush=True)
    
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
        
        symbol = 'XAUUSD.m'
        volume = 0.01
        num_orders = 5
        target_profit = 0.15  # 0.03$ لكل صفقة × 5 صفقات = 0.15$ الهدف الإجمالي
        max_loss = -5.00      # حد الخسارة للمجموعة 5$
        
        last_price = None
        print(f"Bot initialized for M3 with symbol {symbol}. Lightning-fast mode activated...", flush=True)
        
        while True:
            try:
                # 1. مراقبة فائقة السرعة للأرباح (كل 0.1 ثانية) للإغلاق الفوري
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol') == symbol]
                
                if len(group_positions) > 0:
                    total_net_profit = sum([
                        p.get('profit', 0.0) + p.get('commission', 0.0) + p.get('swap', 0.0) 
                        for p in group_positions
                    ])
                    
                    if total_net_profit >= target_profit or total_net_profit <= max_loss:
                        print(f"[LIGHTNING CLOSE] Net PnL: {total_net_profit:.2f}$. Closing all 5 orders simultaneously...", flush=True)
                        close_tasks = [connection.close_position(p.get('id')) for p in group_positions]
                        await asyncio.gather(*close_tasks, return_exceptions=True)
                        print("Orders closed instantly. Ready for next wave...", flush=True)
                        await asyncio.sleep(0.5)
                    
                    await asyncio.sleep(0.1)
                    continue

                # 2. جلب بيانات فريم M3 للتحقق من الاتجاه السريع
                candles = await account.get_historical_candles(symbol, '3m', None, 30)
                if not candles or len(candles) < 15:
                    await asyncio.sleep(1)
                    continue
                
                df = pd.DataFrame(candles)
                close = df['close']
                
                ema5 = close.ewm(span=5, adjust=False).mean().iloc[-1]
                ema13 = close.ewm(span=13, adjust=False).mean().iloc[-1]
                
                tick = await connection.get_symbol_price(symbol)
                bid = tick.get('bid', 0)
                ask = tick.get('ask', 0)
                current_price = (bid + ask) / 2
                spread = ask - bid
                
                if spread > 0.50 or last_price is None:
                    last_price = current_price
                    await asyncio.sleep(0.2)
                    continue

                price_change = current_price - last_price
                
                buy_condition = (ema5 > ema13) and (price_change >= 0.06)
                sell_condition = (ema5 < ema13) and (price_change <= -0.06)

                if buy_condition:
                    print(f"=== LIGHTNING BUY SIGNAL -> OPENING 5 ORDERS TOGETHER ===", flush=True)
                    buy_tasks = [
                        connection.create_market_buy_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*buy_tasks, return_exceptions=True)
                    last_price = current_price
                    
                elif sell_condition:
                    print(f"=== LIGHTNING SELL SIGNAL -> OPENING 5 ORDERS TOGETHER ===", flush=True)
                    sell_tasks = [
                        connection.create_market_sell_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*sell_tasks, return_exceptions=True)
                    last_price = current_price

                last_price = current_price
                await asyncio.sleep(0.2)

            except Exception as loop_err:
                print(f"Loop error: {loop_err}", flush=True)
                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"Critical error: {e}", flush=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    
    t = threading.Thread(target=lambda: asyncio.run(trading_loop()))
    t.daemon = True
    t.start()
    
    app.run(host='0.0.0.0', port=port)
