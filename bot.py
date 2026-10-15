import os
import asyncio
import threading
import pandas as pd
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "Ultra-Fast Candle Scalping Bot is active!"

async def trading_loop():
    print("=== Starting Ultra-Fast Candle Scalping Bot Worker ===", flush=True)
    
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
        target_profit = 0.15  # 0.03$ لكل صفقة × 5 صفقات = 0.15$ مجموع الربح المستهدف بالشمعة
        max_loss = -5.00      # حد الخسارة للمجموعة 5$
        
        print(f"Bot initialized. Ready to scalp candles for 0.15$ target...", flush=True)
        
        while True:
            try:
                # 1. حلقة مراقبة فائقة السرعة (كل 0.2 ثانية) للإغلاق الفوري مع حركة الشمعة
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol') == symbol]
                
                if len(group_positions) > 0:
                    total_net_profit = sum([
                        p.get('profit', 0.0) + p.get('commission', 0.0) + p.get('swap', 0.0) 
                        for p in group_positions
                    ])
                    
                    # الإغلاق الفوري وبدون أي تأخير عند تحقيق الهدف (0.15$) أو حد الخسارة (-5$)
                    if total_net_profit >= target_profit or total_net_profit <= max_loss:
                        print(f"[CANDLE TARGET HIT] Net PnL: {total_net_profit:.2f}$. Closing instantly...", flush=True)
                        
                        close_tasks = [connection.close_position(p.get('id')) for p in group_positions]
                        await asyncio.gather(*close_tasks, return_exceptions=True)
                        
                        print("Orders closed successfully. Waiting for next candle setup...", flush=True)
                        await asyncio.sleep(1)
                    
                    # فحص سريع متكرر 5 مرات في الثانية الواحدة
                    await asyncio.sleep(0.2)
                    continue

                # 2. البحث عن إشارة دخول جديدة فور اكتمال الشمعة أو بدء زخمها
                candles = await account.get_historical_candles(symbol, '1m', None, 100)
                if not candles or len(candles) < 60:
                    await asyncio.sleep(2)
                    continue
                
                df = pd.DataFrame(candles)
                close = df['close']
                
                ema5 = close.ewm(span=5, adjust=False).mean().iloc[-1]
                ema13 = close.ewm(span=13, adjust=False).mean().iloc[-1]
                ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
                
                delta = close.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                current_rsi = rsi.iloc[-1]
                
                current_price = close.iloc[-1]
                prev_candle_bullish = df['close'].iloc[-2] > df['open'].iloc[-2]
                prev_candle_bearish = df['close'].iloc[-2] < df['open'].iloc[-2]
                
                tick = await connection.get_symbol_price(symbol)
                spread = tick.get('ask', 0) - tick.get('bid', 0)
                
                if spread > 0.50:
                    await asyncio.sleep(1)
                    continue

                buy_condition = (
                    ema5 > ema13 and
                    current_price > ema50 and
                    current_rsi > 55 and
                    prev_candle_bullish
                )

                sell_condition = (
                    ema5 < ema13 and
                    current_price < ema50 and
                    current_rsi < 45 and
                    prev_candle_bearish
                )

                if buy_condition:
                    print(f"=== BUY CANDLE SIGNAL ===", flush=True)
                    buy_tasks = [
                        connection.create_market_buy_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*buy_tasks, return_exceptions=True)
                        
                elif sell_condition:
                    print(f"=== SELL CANDLE SIGNAL ===", flush=True)
                    sell_tasks = [
                        connection.create_market_sell_order(symbol=symbol, volume=volume, stop_loss=0, take_profit=0)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*sell_tasks, return_exceptions=True)

                await asyncio.sleep(1)

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
