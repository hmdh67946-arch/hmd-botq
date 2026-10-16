import os
import asyncio
import threading
import pandas as pd
from flask import Flask
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

@app.route('/')
def home():
    return "Candle-Momentum Scalper is active!"

async def trading_loop():
    print("=== Starting Candle-Momentum Scalper ===", flush=True)
    
    token = (
        os.environ.get('METIAPI_TOKEN') or 
        os.environ.get('METAAPI_TOKEN') or 
        os.environ.get('TOKEN')
    )
    account_id = '7b045775-a813-4c07-ae98-9d1945aefe1c'
    
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
            
        print("Waiting for synchronization...", flush=True)
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()
        
        symbol = 'XAUUSD.m'
        volume = 0.01
        num_orders = 5
        
        # مسافة الهدف ووقف الخسارة بالدولار/النقاط للذهب (0.03$ إلى 0.04$ كهدف، ووقف خسارة محمي)
        profit_distance = 0.035 
        loss_distance = 0.45   # مسافة وقف الخسارة للـ SL المباشر على السيرفر
        emergency_max_loss = -4.50 # طوارئ الإغلاق الجماعي
        
        print(f"Bot fully synchronized for {symbol}. Trading with candle momentum...", flush=True)
        
        while True:
            try:
                # مراقبة سريعة لحماية الطوارئ الإجمالية
                positions = await connection.get_positions()
                group_positions = [p for p in positions if p.get('symbol') == symbol]
                
                if len(group_positions) > 0:
                    total_net_profit = sum([
                        p.get('profit', 0.0) + p.get('commission', 0.0) + p.get('swap', 0.0) 
                        for p in group_positions
                    ])
                    
                    if total_net_profit <= emergency_max_loss:
                        print(f"[EMERGENCY CLOSE] Loss limit reached: {total_net_profit:.2f}$. Closing instantly...", flush=True)
                        close_tasks = [connection.close_position(p.get('id')) for p in group_positions]
                        await asyncio.gather(*close_tasks, return_exceptions=True)
                        await asyncio.sleep(1)
                    
                    await asyncio.sleep(0.05)
                    continue

                # تحليل شمعة الـ M3 الحالية وسلوكها (سعر الإغلاق مقارنة بسعر الافتتاح أو الشمعة السابقة)
                candles = await account.get_historical_candles(symbol, '3m', None, 5)
                if not candles or len(candles) < 3:
                    await asyncio.sleep(1)
                    continue
                
                current_candle = candles[-1]
                open_price = current_candle.get('open', 0)
                close_price = current_candle.get('close', 0)
                
                tick = await connection.get_symbol_price(symbol)
                if not tick:
                    await asyncio.sleep(0.1)
                    continue
                    
                bid = tick.get('bid', 0)
                ask = tick.get('ask', 0)
                
                # شروط سلوك الشمعة: إذا كانت الشمعة صاعدة (إغلاق أعلى من الافتتاح) -> شراء مع اتجاهها
                # إذا كانت الشمعة هابطة (إغلاق أقل من الافتتاح) -> بيع مع اتجاهها
                is_bullish_candle = close_price > open_price
                is_bearish_candle = close_price < open_price

                if is_bullish_candle:
                    print(f"=== BULLISH CANDLE -> OPENING 5 BUY ORDERS WITH TP/SL ===", flush=True)
                    target_tp = round(ask + profit_distance, 2)
                    target_sl = round(ask - loss_distance, 2)
                    buy_tasks = [
                        connection.create_market_buy_order(symbol=symbol, volume=volume, stop_loss=target_sl, take_profit=target_tp)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*buy_tasks, return_exceptions=True)
                    # انتظار قليل بعد فتح الصفقة لتجنب التكرار السريع في نفس الشمعة
                    await asyncio.sleep(5)
                    
                elif is_bearish_candle:
                    print(f"=== BEARISH CANDLE -> OPENING 5 SELL ORDERS WITH TP/SL ===", flush=True)
                    target_tp = round(bid - profit_distance, 2)
                    target_sl = round(bid + loss_distance, 2)
                    sell_tasks = [
                        connection.create_market_sell_order(symbol=symbol, volume=volume, stop_loss=target_sl, take_profit=target_tp)
                        for _ in range(num_orders)
                    ]
                    await asyncio.gather(*sell_tasks, return_exceptions=True)
                    await asyncio.sleep(5)

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
    port = int(os.environ.get('PORT', 10000))
    t = threading.Thread(target=start_async_loop)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=port)
