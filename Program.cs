using Backtester;
using System;
using System.Threading;
using System.Windows.Forms;

static class Program
{
    private static Backtester.Loader loader_;

    /// <summary>
    /// The main entry point for the application.
    /// </summary>
    [STAThread]
    static void Main()
    {
        Console.WriteLine("Application started.");
        loader_ = new Backtester.Loader();

        try
        {
            Application.Run();
        }
        finally
        {
            Application.Exit();
        }
    }
}
