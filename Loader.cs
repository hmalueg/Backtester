using System;
using System.Collections.Generic;
using System.Text;

using T4;
using T4.API;
using T4.API.ChartData;

namespace Backtester
{
    internal readonly struct TradeBar
    {
        internal TradeBar(DateTime tradeDate, decimal open, decimal close, decimal high, decimal low)
        {
            TradeDate = tradeDate;
            Open = open;
            Close = close;
            High = high;
            Low = low;
        }

        internal readonly DateTime TradeDate;
        internal readonly decimal Open;
        internal readonly decimal Close;
        internal readonly decimal High;
        internal readonly decimal Low;
    }

    internal readonly struct Settlement
    {
        internal Settlement(DateTime tradeDate, decimal price)
        {
            TradeDate = tradeDate;
            Price = price;
        }

        internal readonly DateTime TradeDate;
        internal readonly decimal Price;
    }

    internal class Loader
    {
        private readonly Host host_;

        private ChartDataSeries data_;
        private Contract contract_;

        private const int DAYS = 365 * 9;

        public Loader()
        {
            host_ = new Host(APIServerType.Live, "PCM_TargeAlert", "2DC998A4-4CC3-4E27-B6ED-CCE9D85A788C", "895", "Malueg2", "Winter25$");
            host_.LoginResponse += host_LoginResponse;
        }

        private void host_LoginResponse(LoginResponseEventArgs e)
        {
            if (e.Result == LoginResult.Success)
            {
                LoadMarket("CME_C", "ZC");
                //LoadMarket("CME_C", "ZS"); // soybeans
                //LoadMarket("CME_C", "ZW"); // wheat
                //LoadMarket("CME_C", "ZL"); // soybean oil
            }
        }

        public void LoadMarket(string exchange_id, string contract_id)
        {
            contract_ = host_.MarketData.GetContract(exchange_id, contract_id);
            contract_.BeginRequestActiveMarket(DateTime.Today, MarketRequestComplete); // it wants this, idk why
        }

        private void MarketRequestComplete(ActiveMarketRequest activeMarketRequest)
        {
            data_ = new ChartDataSeries(contract_, new ChartDataArgs());
            data_.DataLoadComplete += DataLoadComplete;
            data_.LoadHistoricalChartData(DateTime.Now.AddDays(-DAYS), DateTime.Now);
        }

        private void DataLoadComplete(object sender, DataLoadCompleteEventArgs args)
        {
            List<TradeBar> tradeBars = ToDataPoints(data_.TradeBars);
            Dictionary<DateTime, Settlement> settlements = ToSettlements(data_.Settlements);

            List<Window> trainingWindows = DataProcessing.Split(tradeBars, settlements);
            Dictionary<int, Tuple<decimal, decimal>> result = ATR.Process(trainingWindows);
        }

        #region convert to user created objects for easy testing
        public static List<TradeBar> ToDataPoints(IList<IDataPoint> tradeBars)
        {
            List<TradeBar> dataPoints = new List<TradeBar>();

            foreach (BarDataPoint bar in tradeBars)
            {
                TradeBar point = new TradeBar(bar.TradeDate, bar.OpenPrice, bar.ClosePrice, bar.HighPrice, bar.LowPrice);
                dataPoints.Add(point);
            }

            return dataPoints;
        }

        public static Dictionary<DateTime, Settlement> ToSettlements(IList<MarketSettlementDataPoint> marketSettlementDataPoint)
        {
            Dictionary<DateTime, Settlement> settlements = new Dictionary<DateTime, Settlement>();

            foreach (MarketSettlementDataPoint settlement in marketSettlementDataPoint)
            {
                Settlement s = new Settlement(settlement.TradeDate, settlement.SettlementPrice);
                settlements[settlement.TradeDate] = s;
            }

            return settlements;
        }
        #endregion
    }
}
