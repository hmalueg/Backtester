using System;
using System.Collections.Generic;
using System.Linq;
using T4.API.ChartData;

namespace Backtester
{
    internal struct DataPoint
    {
        internal DataPoint(TradeBar tradeBar, Settlement settlement, Settlement previousSettlement)
        {
            TradeBar = tradeBar;
            Settlement = settlement;
            PreviousSettlement = previousSettlement;
        }

        internal readonly TradeBar TradeBar;
        internal readonly Settlement Settlement;
        internal readonly Settlement PreviousSettlement;

        internal decimal TrueRange() { return Math.Max(TradeBar.High, PreviousSettlement.Price) - Math.Min(TradeBar.Low, PreviousSettlement.Price); }
    }


    internal readonly struct Window
    {
        internal Window(IReadOnlyList<DataPoint> train, IReadOnlyList<DataPoint> validation, IReadOnlyList<int> trainYears, int validationYear)
        {
            Train = train;
            Validation = validation;
            TrainYears = trainYears;
            ValidationYear = validationYear;
        }

        internal readonly IReadOnlyList<DataPoint> Train;
        internal readonly IReadOnlyList<DataPoint> Validation;
        internal readonly IReadOnlyList<int> TrainYears;
        internal readonly int ValidationYear;
    }

    internal static class DataProcessing
    {
        private const int TrainYearCount = 3;
        private const int WindowCount = 7;

        // Walk-forward split: each window has TrainYearCount calendar years of training
        // data followed by the next calendar year as validation. The window slides forward
        // one year at a time, producing WindowCount windows.
        public static List<Window> Split(List<TradeBar> tradeBars, Dictionary<DateTime, Settlement> settlements)
        {
            SortedDictionary<int, List<DataPoint>> dataPointsByYear = new SortedDictionary<int, List<DataPoint>>();
            int firstYear = tradeBars.Min(b => b.TradeDate.Year);
            tradeBars = tradeBars.OrderBy(b => b.TradeDate).ToList();
            Settlement previousSettlement = new Settlement();

            foreach (TradeBar bar in tradeBars)
            {
                if (!settlements.TryGetValue(bar.TradeDate, out Settlement settle))
                {
                    Console.WriteLine("missing settle for dt " + bar.TradeDate);
                    continue;
                }

                DataPoint point = new DataPoint(bar, settle, previousSettlement);
                previousSettlement = settle;

                int year = bar.TradeDate.Year;
                if (year == firstYear)
                {
                    continue;
                }
                
                if (!dataPointsByYear.TryGetValue(year, out List<DataPoint> dataPoints))
                {
                    dataPoints = new List<DataPoint>();
                    dataPointsByYear[year] = dataPoints;
                }

                if (point.PreviousSettlement.TradeDate - point.TradeBar.TradeDate > TimeSpan.FromDays(3))
                {
                    Console.WriteLine("settle-trade gap for dt " + point.TradeBar.TradeDate);
                }

                dataPoints.Add(point);
            }

            int[] years = dataPointsByYear.Keys.ToArray();
            int needed = TrainYearCount + WindowCount;
            if (years.Length < needed)
            {
                throw new InvalidOperationException(
                    $"Need {needed} distinct calendar years for {WindowCount} windows " +
                    $"with {TrainYearCount}yr train; got {years.Length}.");
            }

            var windows = new List<Window>(WindowCount);
            for (int i = 0; i < WindowCount; i++)
            {
                var trainYears = new int[TrainYearCount];
                var train = new List<DataPoint>();
                for (int j = 0; j < TrainYearCount; j++)
                {
                    int y = years[i + j];
                    trainYears[j] = y;
                    train.AddRange(dataPointsByYear[y]);
                }

                int valYear = years[i + TrainYearCount];
                var validation = dataPointsByYear[valYear];

                windows.Add(new Window(train, validation, trainYears, valYear));
            }

            return windows;
        }
    }
}
