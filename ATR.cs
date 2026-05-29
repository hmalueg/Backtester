using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using T4.API.ChartData.Indicator;
using static System.Windows.Forms.VisualStyles.VisualStyleElement;

namespace Backtester
{
    internal static class ATR
    {
        private static readonly decimal[] lambdas = { 0.80m, 0.90m, 0.929m, 0.95m };
        private static readonly Func<decimal, decimal, decimal, decimal> CalcRange = EwmaATR;


        public static Dictionary<int, Tuple<decimal, decimal>> Process(List<Window> windows)
        {
            Dictionary<int, Tuple<decimal, decimal>> lambdaAndMseByYear = new Dictionary<int, Tuple<decimal, decimal>>();

            foreach (Window window in windows)
            {
                decimal bestLambda = GetBestLambda(window.Train);
                decimal atr = CalcATR(window.Train, bestLambda);
                decimal valMSE = GetValidationMSE(window.Validation, bestLambda, atr);

                lambdaAndMseByYear[window.ValidationYear] = Tuple.Create(bestLambda, valMSE);
            }

            return lambdaAndMseByYear;
        }

        private static decimal GetBestLambda(IReadOnlyList<DataPoint> train)
        {
            List<Tuple<decimal, decimal>> mseByLambda = new List<Tuple<decimal, decimal>>();

            foreach (decimal lambda in lambdas)
            {
                double halfLife = HalfLife((double)lambda);
                List<decimal> trainMSEs = new List<decimal>();
                decimal atr = 0.0m;

                for (int i = 0; i < train.Count; i++)
                {
                    if (i > 3 * halfLife)
                    {
                        trainMSEs.Add(CalcSquaredError(atr, train[i].TrueRange()));
                    }
                    atr = CalcRange(atr, train[i].TrueRange(), lambda);
                }

                mseByLambda.Add(Tuple.Create(lambda, trainMSEs.Average()));
            }

            return mseByLambda.Find(i => i.Item2 == mseByLambda.Min(j => j.Item2)).Item1;
        }

        // passing in training's atr so we don't have to re-seed
        private static decimal GetValidationMSE(IReadOnlyList<DataPoint> validation, decimal lambda, decimal atr)
        {
            List<decimal> validationMSEs = new List<decimal>();

            foreach (DataPoint dataPoint in validation)
            {
                validationMSEs.Add(CalcSquaredError(atr, dataPoint.TrueRange()));
                atr = CalcRange(atr, dataPoint.TrueRange(), lambda);
            }

            return  validationMSEs.Average();
        }

        private static decimal CalcATR(IReadOnlyList<DataPoint> train, decimal lambda)
        {
            decimal atr = 0.0m;
            foreach (DataPoint dataPoint in train)
            {
                atr = CalcRange(atr, dataPoint.TrueRange(), lambda);
            }
            return atr;
        }

        private static decimal CalcSquaredError(decimal atr, decimal trueRange)
        {
            return (atr - trueRange) * (atr - trueRange);
        }


        private static decimal EwmaATR(decimal atr, decimal trueRange, decimal lambda)
        {
            // use the mean tracking formula instead?
            return (1 - lambda) * trueRange + lambda * atr;
        }

        private static double HalfLife(double lambda)
        {
            return Math.Log(2.0) / -Math.Log(lambda);
        }
    }

}
